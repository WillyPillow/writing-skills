# RFC 2514: `union_initialization_and_drop`

- Feature Name: `union_initialization_and_drop`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

## Summary

A union may not have a field whose type needs drop glue. Drop glue is the code that runs automatically when a variable goes out of scope, and it drops the variable and, recursively, all of its fields. A union may still implement `Drop` itself. This RFC specifies when a program may move out of a union field, and when the union's own `drop` is called. To prevent the compiler from inserting a drop that the programmer did not ask for, it also restricts implicit uses of `DerefMut` on union fields.

## Motivation

The compiler tracks, for every local variable, whether it is initialized, and it inserts a drop at the end of the scope for each initialized variable that needs one. For structs this tracking is per field. After `let a = s.x;` moves a non-`Copy` field out of `s`, the compiler knows that `s.x` is uninitialized, and it drops only the remaining fields. Moving out of a struct that implements `Drop` is an error, because its `drop` would then see a partly moved value.

For unions, these rules have not been written down. [TODO: author to state what the compiler does today in each of the cases below, and whether any of it is considered a bug.] The questions are:

1. A union's fields share storage. After a move out of one field, is the union still initialized, partly initialized, or uninitialized?
2. Does writing to one field initialize the union?
3. If the union implements `Drop`, when is that `drop` called?

There is also a hazard that does not come from initialization tracking. Consider:

```rust
use std::mem::ManuallyDrop;

union U {
    s: ManuallyDrop<String>,
    n: u64,
}

let mut u = U { n: 0 };
unsafe {
    *u.s = String::from("hello");
}
```

The field `s` has type `ManuallyDrop<String>`, which has no drop glue, so the union is allowed. The assignment `*u.s = ...` goes through `ManuallyDrop`'s `DerefMut` to a `String` place. Assigning to a `String` place drops the old `String` first. The old "`String`" here is the bytes of the `u64` and whatever follows it, so the program drops a `String` that was never created. Its behavior is undefined. Nothing in the source says "drop" here. The drop is inserted by the compiler, and it is reached through a deref that the programmer may not have noticed. The restriction on `DerefMut` in this RFC exists for this case.

## Guide-level explanation

### Fields without drop glue

Every field of a union must have a type without drop glue. `Copy` types qualify, as does `ManuallyDrop<T>` for any `T`. To store a value that needs dropping, such as a `String`, wrap it in `ManuallyDrop` and drop it yourself when you know it is the active field.

Because no field has drop glue, the compiler never drops a field of a union on its own. If a union needs cleanup, it implements `Drop`, and its `drop` method decides which field is active and acts on it.

### Writing to a field

Assigning to a field initializes the whole union:

```rust
let mut u: U;
u.n = 1; // u is now initialized
```

The assignment is safe and does not drop anything, because the old contents of the field have no drop glue. [TODO: confirm that this assignment is intended to be safe even when `u` is uninitialized beforehand.]

Assigning to part of a field, such as `u.pair.0 = 1`, does not initialize the union. If `u` is uninitialized, such an assignment is an error, as it is for a struct field of an uninitialized struct.

### Moving out of a field

Reading a field is unsafe, because the compiler does not know which field is active. If the field's type is `Copy`, reading copies it and leaves the union as it was.

If the field's type is not `Copy`, reading it moves out of it. Because all fields share storage, moving out of one field moves out of the whole union. After `let s = unsafe { u.s };`, the union `u` is uninitialized. Every later use of `u`, other than assigning a new value to it or one of its fields, is an error.

If the union implements `Drop`, moving out of any of its fields is an error. This is the same rule as for structs that implement `Drop`: the union's `drop` would otherwise run on a value whose contents have been taken.

### When `drop` is called

If a union implements `Drop`, the compiler calls its `drop` when the union goes out of scope while initialized, and when it is overwritten as a whole. It does not call it when a field is assigned, because that assignment does not end the union's lifetime. [TODO: author to confirm this choice. A field assignment replaces the active contents, and some union `Drop` implementations may expect to run before that.]

## Reference-level explanation

### Initialization tracking

The compiler tracks initialization of a union as a single unit, not per field. The following rules define its state:

1. Assigning a value to the union as a whole, or to one of its fields, makes the union initialized.
2. Moving out of a field whose type is not `Copy` makes the union uninitialized.
3. Moving out of a field of a union that implements `Drop` is an error.
4. Assigning to a place nested inside a field, such as `u.f.x`, requires the union to be initialized. It does not change the union's state.

A union field is a place like a struct field, so taking a reference to it, `&u.f` or `&mut u.f`, requires the union to be initialized. [TODO: confirm.]

### Implicit drop

At the end of its scope, an initialized union is dropped by calling its `Drop::drop`, if it has one. Its fields are never dropped, since none has drop glue.

### Restriction on `DerefMut`

When the compiler resolves a place expression, it may insert a call to `DerefMut::deref_mut` to auto-dereference a value, as in `*u.s` or `u.s.push_str("x")`. This RFC forbids such an inserted call when its receiver is a union field or a place inside one.

The programmer can still call the method explicitly, through `(*(&mut u.s)).push_str("x")` or `ManuallyDrop::deref_mut(&mut u.s)`. Writing the call out makes the dereference visible, and with it the possibility that the place behind it is about to be dropped.

[TODO: the exact boundary of the restriction. Candidates for the author to decide between: forbid all implicit `DerefMut` on union fields; or forbid it only when the resulting place is the target of an assignment, the case that inserts a drop. The second is narrower and breaks less code, but method calls through implicit `DerefMut` can also drop values internally.]

The restriction applies to `DerefMut` only. Implicit `Deref` through a shared reference cannot cause an assignment, so it cannot insert a drop.

## Drawbacks

The `DerefMut` restriction makes union code more verbose. `u.s.push_str("x")` must become an explicit `deref_mut` call. [TODO: author to say how much existing code uses implicit `DerefMut` on union fields, since unions with non-`Copy` fields may still be unstable at the time of this RFC, which would mean no stable code is affected.]

Tracking initialization per union rather than per field loses precision. A union with two `Copy` fields cannot be partly initialized, though nothing about the storage forbids it. Since fields share storage, per-field tracking would mostly track the same bytes twice. This is the reason given here for accepting the loss, and the author should confirm it.

Forbidding moves out of a union that implements `Drop` rules out some patterns. For example, a `drop` that checks a flag and does nothing in one state would not care whether a field was moved out. The workaround is the same as for structs: use `ptr::read` on the field. [TODO: author to confirm.]

## Rationale and alternatives

The rules above follow those for structs wherever the shared storage of union fields does not force a difference. A programmer who knows the struct rules therefore has to learn only what changes because the fields overlap.

[TODO: author to list the alternatives actually considered. A suggestion for the author to evaluate, not a recorded alternative: allow fields with drop glue and never drop them automatically. This removes the need for `ManuallyDrop` in union definitions, but it means a union field of type `String` behaves unlike a `String` anywhere else, which is the kind of surprise this RFC is trying to remove.]

## Unresolved questions

- Whether assigning to a field of an uninitialized union is safe.
- Whether a field assignment calls the union's `drop`.
- The boundary of the `DerefMut` restriction.
- Whether to lint, rather than error, in any of these cases during a transition period.
