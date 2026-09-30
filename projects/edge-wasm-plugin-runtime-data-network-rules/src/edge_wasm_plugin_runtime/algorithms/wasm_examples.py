"""Inspectable, self-contained WebAssembly examples for the local workbench."""

import base64


JSON_NORMALIZER_WAT = r'''(module
  (memory (export "memory") 1 16)
  (func (export "alloc") (param i32) (result i32) i32.const 0)
  (func (export "run") (param $ptr i32) (param $len i32) (result i64)
    (local $cursor i32) (local $end i32) (local $byte i32)
    local.get $ptr local.set $cursor
    local.get $ptr local.get $len i32.add local.set $end
    (block $done
      (loop $next
        local.get $cursor local.get $end i32.ge_u br_if $done
        local.get $cursor i32.load8_u local.set $byte
        local.get $byte i32.const 65 i32.ge_u
        local.get $byte i32.const 90 i32.le_u i32.and
        if
          local.get $cursor local.get $byte i32.const 32 i32.add i32.store8
        end
        local.get $cursor i32.const 1 i32.add local.set $cursor
        br $next))
    local.get $ptr i64.extend_i32_u i64.const 32 i64.shl
    local.get $len i64.extend_i32_u i64.or))'''


def json_normalizer_artifact() -> str:
    import wasmtime
    return base64.b64encode(wasmtime.wat2wasm(JSON_NORMALIZER_WAT)).decode()
