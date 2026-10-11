# RFC 2514: union_initialization_and_drop

- Feature name: `untagged_unions`
- Start date: [TODO: date]
- RFC PR: [TODO: link]
- Tracking issue: [TODO: link]

## Summary

Union fields may not have types that need drop glue. Drop glue is the code that runs automatically when a value goes out of scope: it drops the value and, recursively, all its fields. A union may still implement `Drop` itself. This RFC specifies when code may move out of a union field and when the union's own `drop` runs. To prevent drop from being called on a union field by accident, it also restricts implicit uses of `DerefMut` on union fields.

## Motivation

A union stores one of several fields in the same memory, and the compiler does not know which one is active. If a field had drop glue, the compiler could not know whether to run it when the union goes out of scope, or when a new value is assigned to the field. Running it on the wrong field would read bytes of one type as another. Forbidding drop glue in union fields removes the question: dropping a union, or overwriting a field, never drops a field.

That rule leaves two questions open.

The first is how the borrow checker treats initialization and moves for unions. Reading a field is unsafe, but moving out of a field is still a move, and the compiler must decide what state the union is in afterward. If a union implements `Drop`, the compiler must also decide whether that `drop` runs after a move.

The second is a gap in the drop-glue rule itself. A common way to put a type with drop glue in a union is to wrap it in `ManuallyDrop<T>`, which has no drop glue. `ManuallyDrop<T>` implements `DerefMut<Target = T>`. Assignment through that `DerefMut` drops the old `T`:

```rust
union U {
    s: ManuallyDrop<String>,
    n: u64,
}

let mut u = U { n: 0 };
unsafe {
    *u.s = String::from("hi");   // drops the old String first
}
```

The assignment calls `DerefMut::deref_mut` on `u.s`, then assigns to the resulting `&mut String`, which drops the `String` already there. But `u.s` was never initialized: the active field is `n`, so the `String` being dropped is the bytes of a `u64` read as a `String`. This is undefined behavior. The code looks like a plain field write, the kind of write that the drop-glue rule was meant to make safe, and the drop is not visible in the source.

[TODO: link the issue or bug report where this case was found, if one exists.]

## Guide-level explanation

For initialization and moves, the compiler treats a union like a struct whose fields all occupy the same place. Two rules follow.

Writing any field initializes the whole union. After `u.n = 5`, all of `u` counts as initialized, and so does every field, from the borrow checker's point of view. Reading `u.s` afterward is still unsafe, because the programmer must know that the bytes form a valid `String`.

Moving out of any field moves out of the whole union. After `let s = unsafe { u.s };`, `u` is moved, and no field of `u` may be used until one is written again.

```rust
union V {
    a: ManuallyDrop<String>,
    b: u64,
}

let mut v = V { b: 1 };
let x = unsafe { v.b };   // u64 is Copy: v is still initialized
let mut w = V { a: ManuallyDrop::new(String::new()) };
let y = unsafe { w.a };   // moves out of w
// unsafe { w.b }         // error: use of moved value `w`
w.b = 2;                  // re-initializes w
```

If a union implements `Drop`, moving out of a field is an error, just as moving out of a field of a struct that implements `Drop` is an error. The union's `drop` runs when the union goes out of scope while initialized. Assigning to a field of the union does not run the union's `drop`, because only the field is replaced, not the union.

Assignments to a union field that would go through `DerefMut` implicitly are rejected. To write the `String` in the example above, write the whole field:

```rust
u.s = ManuallyDrop::new(String::from("hi"));   // no drop of the old value
```

This assignment is safe: `ManuallyDrop<String>` has no drop glue, so nothing is dropped. A programmer who knows that `u.s` is active and wants to drop the old `String` can write `*ManuallyDrop::deref_mut(&mut u.s) = ...` explicitly, inside `unsafe`.

## Reference-level explanation

### Fields

A union field must have a type that has no drop glue. The compiler accepts `Copy` types, `ManuallyDrop<T>` for any `T`, and arrays and tuples of these. [TODO: confirm the exact set, and whether the rule is stated as "no drop glue" or as an explicit list. The two differ for types that are not `Copy` and have no drop glue, such as a struct of `ManuallyDrop` fields.]

### Initialization and moves

For the borrow checker, a union place is tracked as a single unit:

1. A write to any field of a union marks the union as initialized.
2. A move out of any field marks the union as uninitialized.
3. A field of a field, such as `u.f.x`, is treated the same way. A move out of `u.f.x` moves out of all of `u`.
4. Reading a field of a union whose field type is `Copy` does not move it.

The rules are conservative. They do not allow the programmer to move out of one field and keep using another, even when the fields do not overlap in memory. Unions guarantee nothing about layout beyond their `repr`, so the compiler does not assume any two fields are disjoint. [TODO: confirm that partial moves out of `repr(C)` unions with non-overlapping fields are not intended.]

### Drop

When a union goes out of scope:

1. If the union is initialized and implements `Drop`, its `drop` method runs.
2. No field is dropped, since no field has drop glue.

Moving out of a field of a union that implements `Drop` is a compile error. Without that rule the compiler would have to choose between running `drop` on a union that has been partly moved out of and skipping a `drop` the programmer wrote. Structs with a `Drop` impl already have this rule, so unions follow it.

### DerefMut on union fields

When the compiler resolves a place expression in an assignment, a compound assignment, or a `&mut` borrow, and an auto-deref step would call `DerefMut::deref_mut` on a place that is a union field, or that is reached through a union field without an intervening dereference of a pointer, the compiler reports an error. Explicit calls to `deref_mut` are not affected.

The rule applies to every type that implements `DerefMut`, not only to `ManuallyDrop`. A field can hold any `Copy` type, and a user type could be `Copy` and also implement `DerefMut`, which would raise the same problem. [TODO: confirm whether the rule should be limited to assignments, where the drop happens, or also cover `&mut` borrows, which do not drop by themselves but let later code do so.]

## Drawbacks

The `DerefMut` rule rejects some correct code. When `u.s` is known to be active, `*u.s = value` is valid and drops the old value on purpose. That code must now use an explicit `deref_mut` call. The cost is a longer expression where the drop is intended, in exchange for no implicit drop where it is not.

The move rules treat any move from any field as a move from the whole union. Code that uses a union with several non-overlapping `repr(C)` fields cannot move out of them one at a time.

The rule for the `DerefMut` restriction depends on how place expressions are resolved, so it is harder to state in user-facing terms than the other rules here. Error messages need to suggest the explicit form.

## Rationale and alternatives

The "struct whose fields all overlap" model reuses rules that Rust programmers already know, and needs no new concept in the borrow checker.

[TODO: Was a model where the compiler tracks the active field considered? It would allow more programs but needs flow-sensitive tracking, which unions were designed to avoid. Record whether it was considered and why it lost.]

[TODO: Was a lint, instead of an error, considered for implicit `DerefMut` on union fields? Record why an error was chosen.]

## Unresolved questions

- The exact set of field types allowed in a union.
- Whether the `DerefMut` restriction covers `&mut` borrows or only assignments.
