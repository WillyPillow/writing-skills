# RFC 2514: union_initialization_and_drop

- Feature Name: `union_initialization_and_drop`
- Start Date: 2018-09-19
- RFC PR: rust-lang/rfcs#2514
- Rust Issue: rust-lang/rust#55149

## Summary

Unions do not allow fields of types that require drop glue (the code that is automatically run when a variable goes out of scope: recursively dropping the variable and all its fields), but they may still `impl Drop` themselves. We specify when one may move out of a union field and when the union's `drop` is called. To avoid undesired implicit calls of drop, we also restrict the use of `DerefMut` when unions are involved.

## Motivation

Unions were stabilized in Rust 1.19 with the restriction, from RFC 1444, that every field must be `Copy`, or be `ManuallyDrop<T>`, or a reference. This ensures that the compiler never has to guess which field of a union is active when the union goes out of scope: no field needs drop, so dropping the union is a no-op unless the union has an `impl Drop` of its own.

RFC 1444 left several questions open, and the compiler has been making choices on them without a specification.

1. Can a union with a `Drop` impl be partially moved out of? If a field is moved out, is the `drop` still called on the remainder?
2. When is `Drop::drop` called on a union? Does an assignment to a field cause the old contents to be dropped?
3. What does it mean to write to a field through a place expression such as `u.a.b = 5` when `u.a` is a struct? Does the compiler consider `u.a` initialized by this write?
4. How do unions interact with `DerefMut` when a field's type implements `Deref`?

These matter because unions are the foundation for types like `MaybeUninit<T>`, `ManuallyDrop<T>`, and user-defined tagged unions, and unsafe code relies on being able to predict when destructors run. A union that wraps a resource, such as a handle or a lock guard, may well want its own `Drop`, and the owner of that union needs to know the contract.

## Guide-level explanation

A union can implement `Drop`. If it does, `drop` is called when the union value is dropped, as for a struct. Because the union cannot know which field is valid, the `drop` implementation is `unsafe`-flavoured in spirit: the author must determine from external information which field was last written.

```rust
union IntOrString {
    int: u64,
    string: ManuallyDrop<String>,
}

impl Drop for IntOrString {
    fn drop(&mut self) {
        // We do not know which variant is live, so this impl cannot do
        // anything useful without more context.
    }
}
```

More typically, a union is wrapped inside a struct that tracks the active field:

```rust
struct Tagged {
    tag: bool,
    data: IntOrString,
}

impl Drop for Tagged {
    fn drop(&mut self) {
        if !self.tag {
            unsafe { ManuallyDrop::drop(&mut self.data.string) }
        }
    }
}
```

### Moving out of fields

Fields of a union that are `Copy` can be read freely in `unsafe` code. Fields that are `ManuallyDrop<T>` can be moved out with `ManuallyDrop::take` or, for a field of a union that does not itself implement `Drop`, by a plain move expression:

```rust
let u = IntOrString { string: ManuallyDrop::new(String::new()) };
let s = unsafe { u.string };  // moves the field
```

If the union implements `Drop`, moving a field out is an error, as with structs: `error[E0509]: cannot move out of type IntOrString, which implements the Drop trait`. This restriction is necessary because after the move, the union's `drop` would still run on a partially moved value.

### Assignments

Writing to a union field never drops the old value. Assignment `u.f = v` is equivalent to writing the bits of `v` over the union's storage. This is already the behaviour for `Copy` and `ManuallyDrop` fields, since neither has drop glue. It is stated explicitly here so that it will not change if the field-type restrictions are relaxed.

Assignment to a nested place, such as `u.a.b = 5` where `u.a` is a struct, is permitted without `unsafe` if the struct's fields do not have drop glue, because writing a field of a `Copy` aggregate cannot read uninitialized memory. This matches the stabilised behaviour but adds the requirement that none of the fields being traversed by the place expression implement `Drop` or `Deref`.

### `DerefMut`

Consider:

```rust
union U {
    a: ManuallyDrop<Vec<u8>>,
}

let mut u = U { a: ManuallyDrop::new(Vec::new()) };
u.a.push(1);
```

Here `u.a` is a `ManuallyDrop<Vec<u8>>` and `push` is found by auto-dereferencing through `DerefMut`. This autoderef has an implicit read of `u.a`, which is unsafe, but also would require that the field be initialized. If the code were instead `u.a.0 = ...` where the union was just created, the compiler could treat the write as initializing the field, as it does for struct fields, but a `DerefMut` call on an uninitialized union field would access uninitialized memory.

To avoid this, the RFC specifies that a place expression that requires an overloaded `DerefMut` in order to reach a union field's subplace is treated as a read of the union field and so requires `unsafe`. Writes to nested fields not involving overloaded dereferencing remain safe.

## Reference-level explanation

### Drop of a union

A union value that is not moved is dropped when it goes out of scope. If the union type implements `Drop`, `Drop::drop` is called with a mutable reference to the union. After `drop` returns, no further drop glue runs, since the fields do not have any. The order of `drop` relative to other locals follows the usual rules.

### Partial moves

A union has no notion of partial initialization. Moving out of any field of a union that implements `Drop` is rejected by the borrow checker. For a union that does not implement `Drop`, a move out of a non-`Copy` field leaves the union logically uninitialized, and the union may not be used again except for reassignment of the whole union or writing a field.

### Conditions for implicit drop

Drop elaboration treats a union as a single unit. A union is considered initialized if any of its fields has been written, and moved-out if any field has been moved out. The compiler does not track which field is live. This produces the following behaviour:

```rust
let u = U { a: 1 };
let _x = unsafe { u.b };   // b: ManuallyDrop<String>, moves
// u is now considered moved; no drop of u at end of scope
```

If the union implements `Drop`, the above is a compile error and the union is always dropped.

### Restrictions on `DerefMut`

Any place expression of the form `u.f.g...` where an intermediate step invokes `Deref::deref_mut` on a type reached through a union field is considered to read from the union and requires an `unsafe` block. This does not affect `Box`, which has built-in dereferencing and no user-visible call.

### Interaction with `ManuallyDrop` and `MaybeUninit`

These types are defined as unions or wrappers around them, and the rules above are consistent with their documented behaviour. In particular, `MaybeUninit<T>` has no `Drop` impl, so a `MaybeUninit<String>` that is dropped leaks its contents, which is the intended behaviour.

## Drawbacks

The restriction on moving out of unions implementing `Drop` is conservative. A user may want to move a field out of a union and then forget the remainder, and must instead use `ptr::read` or `ManuallyDrop::take`.

The `DerefMut` rule makes some formerly safe operations unsafe, though this concerns code which was relying on unspecified behaviour. A crater run is advised before stabilization of the exact wording.

Allowing `Drop` on unions at all may encourage patterns that are difficult to review, since the `drop` body cannot be verified locally.

## Rationale and alternatives

**Forbid `Drop` on unions.** This avoids all questions but prevents useful abstractions, for example a union-based small-string optimization that wishes to own its destructor.

**Track the active field in the compiler.** This would be a significant departure from the C-like model of unions, and cannot be done soundly given that unsafe code can write any field at any time.

**Allow moves out of Drop unions, and skip drop.** This would be a surprise to users, who expect `Drop` to always run. It is inconsistent with structs.

**Make `DerefMut` through unions always safe.** This permits a read of uninitialized data through safe code via a user-written `deref_mut` and so is unsound.

## Prior art

C and C++ unions with non-trivial members require explicit user-defined destructors, and C++ calls none of the member destructors automatically. This matches the model here: the programmer is responsible for dropping the live field. The C++ rule that a union's destructor is deleted unless user-provided is analogous to the field restriction in Rust.

## Unresolved questions

* Should `ManuallyDrop` fields be mandatory, or could `Copy` fields only be sufficient for union drop elaboration?
* Is there demand for an attribute to mark a particular field as the one to drop by default?
* Should writes through `&mut` references to union fields be allowed in safe code when the referent is a `Copy` type, as the reference creation itself carries an alignment obligation?

## Future possibilities

Union fields could be allowed to hold arbitrary types with drop glue if a mechanism were added to declare which field is active. This is left to future work, and may be best done as a library over the primitives specified here.
