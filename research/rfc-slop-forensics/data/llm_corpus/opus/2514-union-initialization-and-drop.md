- Feature Name: `untagged_unions`
- Start Date: 2018-08-03
- RFC PR: [rust-lang/rfcs#2514](https://github.com/rust-lang/rfcs/pull/2514)
- Rust Issue: [rust-lang/rust#55149](https://github.com/rust-lang/rust/issues/55149)

# Summary

Unions do not allow fields of types that need drop glue, the code that runs automatically when a value goes out of scope and recursively drops it and its fields. A union may, however, `impl Drop` itself. This RFC specifies when a program may move out of a union field and when the union's own `drop` runs. To prevent unexpected implicit drops, it also restricts the use of `DerefMut` through union fields.

# Motivation

RFC 1444 added `union` to Rust. Unions are needed for FFI with C and for some low-level data structures, such as small-string optimizations and `MaybeUninit`. Since the compiler cannot know which field of a union is active, it cannot know which field to drop. RFC 1444 dealt with this by forbidding fields with drop glue, or at least warning about them, and leaving several questions open:

- When is a union considered initialized, and when moved-from?
- If a union implements `Drop`, when does that `drop` run? What if a field has been moved out?
- Can assigning to a union field run a destructor on the old value?

The current implementation answers some of these questions implicitly and inconsistently. Since unions are on the path to stabilization for non-`Copy` fields, these answers need to be written down.

There is also a hazard with `DerefMut`. Writing `u.f.0 = x` where `u.f` is a `ManuallyDrop<(String, u8)>` goes through `DerefMut::deref_mut` on the `ManuallyDrop`, and assigning to `.0` drops the old `String`. If the union's active field is not `f`, this drops garbage memory. The syntax looks like a plain field write, so it is easy to miss.

# Guide-level explanation

## What fields a union may have

A union field must have a type that does not need drop glue. In practice this means:

- `Copy` types, such as integers and raw pointers,
- `ManuallyDrop<T>` for any `T`,
- references `&T` and `&mut T`,
- tuples and arrays of the above.

If you want a union to hold a `String`, wrap it: `ManuallyDrop<String>`. Then you, not the compiler, decide when and whether to drop it.

## Initialization

A union is either fully initialized or fully uninitialized. Writing any field initializes the whole union. There is no notion of "partially initialized" like there is for structs.

```rust
union U { a: u32, b: ManuallyDrop<String> }

let mut u: U;
u.a = 5;          // u is now initialized
```

Writing a field never drops the previous contents, because no union field has drop glue. That is the point of the restriction.

## Moving out

Reading a non-`Copy` field moves the whole union out:

```rust
let s: ManuallyDrop<String> = unsafe { u.b };
// u is now considered moved-from (uninitialized).
```

After that, the union is treated like any moved-from variable: you cannot read it again until you write to it, and its `Drop` impl, if any, will not run.

## The union's own Drop

If a union implements `Drop`, the compiler calls `drop` when an initialized union goes out of scope, just as it does for a struct. It does not call drop when the union has been moved out of, either directly or by moving out of one of its fields.

```rust
union Either { left: ManuallyDrop<Vec<u8>>, right: u64 }

impl Drop for Either {
    fn drop(&mut self) {
        // Runs when an initialized `Either` is dropped. The impl must
        // know which field is active, typically from context.
    }
}
```

Note that, unlike a struct, after `Drop::drop` returns the compiler does not drop any fields. There is nothing to drop: fields have no drop glue.

## No `DerefMut` through union fields

The compiler rejects writes that go through a `DerefMut` impl on a union field, because those writes can drop the old target:

```rust
union V { f: ManuallyDrop<(String, u8)>, n: u64 }

let mut v = V { n: 0 };
unsafe { v.f.0 = String::new(); }
// error: not automatically applying `DerefMut` on `ManuallyDrop` union field
```

Write the deref explicitly so it is clear what runs:

```rust
unsafe { (*v.f).0 = String::new(); }   // explicit, still drops old .0
unsafe { std::ptr::write(&mut (*v.f).0, String::new()); } // no drop
```

# Reference-level explanation

## Fields

A union field type `T` must satisfy `!needs_drop::<T>()` as determined at definition time, where generic parameters are treated as needing drop unless bounded by `Copy`. A union with a field type that needs drop glue is an error. A union declaring `impl Drop` is permitted.

## Initialization state

For the purposes of borrow checking and move checking, a union is a single place. A write to any field `u.f` (where `u` is a local) initializes `u`. A move out of any field `u.f`, or of any place projected from it, moves out of `u`. A union cannot be partially moved.

Reading a `Copy` field copies and leaves `u` initialized.

## Drop elaboration

When an initialized union `u` of type `U` goes out of scope:

1. If `U: Drop`, call `<U as Drop>::drop(&mut u)`.
2. Otherwise, do nothing.

No field is dropped in either case. If `u` is uninitialized or moved-from at the point it goes out of scope, nothing happens. Where initialization is conditional, a drop flag is used, just as for other types.

## Assignment

`u.f = x` does not drop the old value of `u.f`, regardless of whether `u` was initialized, because `f`'s type has no drop glue. Assignment to the union as a whole, `u = U { .. }`, does drop the old value of `u` first if it is initialized and `U: Drop`.

## DerefMut restriction

When type checking a place expression whose base is a union field, the compiler does not insert implicit `DerefMut::deref_mut` calls on that field. Explicit dereferences (`*u.f`) are allowed. Implicit `Deref::deref` for reads is still permitted, since reading cannot drop anything.

This rule applies only to the first auto-deref step on the union field itself. Places further down are unaffected.

## Pattern matching

Matching a union by field pattern, `let U { f } = u;`, moves or copies `f` according to its type and follows the same rules as a field read.

# Drawbacks

- Users who want a union holding a `Drop` type have to write `ManuallyDrop` everywhere, which is verbose.
- The `DerefMut` restriction is an unusual exception to Rust's auto-deref rules.
- A union with `impl Drop` gets no help from the compiler about which field to drop; its author must track that out of band.

# Rationale and alternatives

**Allow drop-glue fields but never drop them.** This was the original RFC 1444 approach behind a lint. It makes `u.f = x` silently leak or drop depending on interpretation, which is confusing. Requiring `ManuallyDrop` makes the intent explicit at the type level.

**Track initialization per field.** This does not match the memory model: all fields share storage, so writing one invalidates the others.

**Ban `impl Drop` on unions.** This would lose a legitimate use: a union can drop its active field when the active variant can be determined from the contents, as in some small-vector designs.

# Prior art

C and C++ have unions with no automatic destruction. C++11 unrestricted unions require users to call destructors manually, much like `ManuallyDrop`.

# Unresolved questions

- Whether `Copy` bounds on generic union fields should be relaxed to a dedicated "no drop glue" bound in the future.

# Future possibilities

A trait expressing "has no drop glue" could let generic unions accept more field types without requiring `Copy`.
