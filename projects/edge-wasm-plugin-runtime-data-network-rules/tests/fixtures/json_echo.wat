;; edge-json-v1: host writes JSON at alloc(length), run returns pointer/length.
;; A fresh instance is created for every invocation, so offset zero is reusable.
(module
  (memory (export "memory") 1 16)
  (func (export "alloc") (param i32) (result i32)
    i32.const 0)
  (func (export "run") (param $ptr i32) (param $len i32) (result i64)
    local.get $ptr
    i64.extend_i32_u
    i64.const 32
    i64.shl
    local.get $len
    i64.extend_i32_u
    i64.or))
