"""Bounded edge-json-v1 execution without host imports or WASI capabilities.

The module exports a 32-bit ``memory``, ``alloc(i32 length) -> i32 pointer``,
and ``run(i32 pointer, i32 length) -> i64 result``. Input and output are UTF-8
JSON objects. The result packs the output pointer in its high 32 bits and
the output length in its low 32 bits. Each invocation gets a fresh instance.
Compilation is limited by artifact size; the execution deadline starts before
instantiation and includes any module start function, allocation, and run.
"""

import json
import math
from threading import Timer
import time
from typing import Any, Dict, Optional, Tuple

import wasmtime

from edge_wasm_plugin_runtime.domain.models import ExecutionStatus, PluginManifest, ResourceLimits


class OutputLimitError(ValueError):
    pass


def finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("JSON output contains a non-finite number")
    return parsed


def execute_wasm(
    artifact: bytes, manifest: PluginManifest, encoded_input: bytes, limits: ResourceLimits,
) -> Tuple[Dict[str, Any], ExecutionStatus, Optional[str], float, str, Optional[int]]:
    started = time.perf_counter()
    output: Dict[str, Any] = {}
    status = ExecutionStatus.SUCCESS
    error = None
    fuel_consumed = None
    config = wasmtime.Config()
    config.consume_fuel = True
    config.epoch_interruption = True
    config.wasm_threads = False
    config.wasm_memory64 = False
    config.parallel_compilation = False
    try:
        with wasmtime.Engine(config) as engine, wasmtime.Module(engine, artifact) as module, wasmtime.Store(engine) as store:
            if manifest.abi_version != "edge-json-v1":
                raise ValueError("Only edge-json-v1 is supported")
            if module.imports:
                raise ValueError("Host and WASI imports are unavailable; plugins must be self-contained")
            store.set_limits(
                memory_size=limits.max_memory_mb * 1024 * 1024,
                table_elements=10_000, instances=1, tables=1, memories=1,
            )
            store.set_fuel(limits.fuel)
            store.set_epoch_deadline(1)
            deadline = Timer(limits.timeout_ms / 1000, engine.increment_epoch)
            deadline.daemon = True
            execution_started = time.perf_counter()
            deadline.start()
            try:
                instance = wasmtime.Instance(store, module, [])
                exports = instance.exports(store)
                memory = exports.get("memory")
                alloc = exports.get("alloc")
                run = exports.get(manifest.entrypoint)
                if not isinstance(memory, wasmtime.Memory):
                    raise ValueError("edge-json-v1 requires an exported memory")
                i32, i64 = wasmtime.ValType.i32(), wasmtime.ValType.i64()
                for function, name, params, results in (
                    (alloc, "alloc", [i32], [i32]),
                    (run, manifest.entrypoint, [i32, i32], [i64]),
                ):
                    if not isinstance(function, wasmtime.Func):
                        raise ValueError(f"edge-json-v1 requires an exported {name} function")
                    signature = function.type(store)
                    if list(signature.params) != params or list(signature.results) != results:
                        raise ValueError(f"Invalid edge-json-v1 signature for {name}")
                pointer = alloc(store, len(encoded_input)) & 0xFFFFFFFF
                if pointer + len(encoded_input) > memory.data_len(store):
                    raise ValueError("alloc returned an input pointer outside linear memory")
                memory.write(store, encoded_input, pointer)
                packed = run(store, pointer, len(encoded_input)) & 0xFFFFFFFFFFFFFFFF
                output_pointer, output_length = packed >> 32, packed & 0xFFFFFFFF
                if output_length > limits.max_output_bytes:
                    raise OutputLimitError("Output exceeds max_output_bytes")
                if output_pointer + output_length > memory.data_len(store):
                    raise ValueError("run returned an output range outside linear memory")
                raw_output = memory.read(store, output_pointer, output_pointer + output_length)
                output = json.loads(bytes(raw_output).decode("utf-8"), parse_float=finite_float, parse_constant=finite_float)
                if not isinstance(output, dict):
                    raise ValueError("edge-json-v1 output must be a JSON object")
                if (time.perf_counter() - execution_started) * 1000 > limits.timeout_ms:
                    status, error, output = ExecutionStatus.TIMEOUT, "Execution exceeded timeout_ms", {}
            finally:
                deadline.cancel()
                deadline.join()
                fuel_consumed = limits.fuel - store.get_fuel()
    except wasmtime.Trap as exc:
        exhausted = exc.trap_code in {wasmtime.TrapCode.OUT_OF_FUEL, wasmtime.TrapCode.INTERRUPT}
        status = ExecutionStatus.TIMEOUT if exhausted else ExecutionStatus.TRAP
        error = "Execution exhausted its fuel budget" if exc.trap_code == wasmtime.TrapCode.OUT_OF_FUEL else str(exc)[:500]
        output = {}
    except OutputLimitError as exc:
        status, error, output = ExecutionStatus.OUTPUT_LIMIT, str(exc), {}
    except (wasmtime.WasmtimeError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        status, error, output = ExecutionStatus.ERROR, str(exc)[:500], {}
    elapsed = (time.perf_counter() - started) * 1000
    return output, status, error, elapsed, "wasmtime-edge-json-v1", fuel_consumed
