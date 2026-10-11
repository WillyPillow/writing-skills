- Feature Name: `untagged_unions`
- Start Date: 2015-12-29
- RFC PR: [rust-lang/rfcs#1444](https://github.com/rust-lang/rfcs/pull/1444)
- Rust Issue: [rust-lang/rust#32836](https://github.com/rust-lang/rust/issues/32836)

**Note:** This RFC has been partially superseded by `unions-and-drop`.

# Summary
[summary]: #summary

Provide native support for C-compatible unions, defined with a new contextual keyword `union`, without breaking any existing code that uses `union` as an identifier.

# Motivation
[motivation]: #motivation

Rust aims to interoperate with C without overhead. Most C types have a direct Rust equivalent: structs map to `#[repr(C)] struct`, enums of integers map to integer types or `#[repr(C)] enum`, pointers map to raw pointers. Unions do not.

Unions are common in C APIs. Some examples:

- Windows APIs use unions extensively, for example `LARGE_INTEGER` and many structures in the input and networking APIs.
- POSIX `sigaction` contains a union of handler function pointers; `epoll_event` contains `epoll_data_t`, a union of a pointer and integers.
- Many hardware register descriptions and binary file formats overlay several interpretations on the same bytes.
- Tagged unions written by hand in C, where a separate field records which variant is active.

Today, Rust code binding to these APIs uses workarounds:

- Declare a struct containing the largest member, and transmute to other members. This gets the size right but not necessarily the alignment, and it is easy to get wrong when the "largest" member differs between platforms.
- Use a byte array with an explicit alignment attribute, plus accessor methods using pointer casts. This is verbose, and the alignment attribute was not available on stable for a long time.
- Generate per-platform definitions with `bindgen`, which then has to emit the workarounds above.

None of these let the compiler know that a type is a union, so none of them work correctly when the union is passed by value across an FFI boundary on ABIs where unions have their own calling convention rules.

Beyond FFI, unions are also useful within Rust for space-efficient data structures where an external tag indicates which field is live, for example in small-string optimizations or in implementations of `Option`-like types with niche tricks that the compiler cannot infer.

# Detailed design
[design]: #detailed-design

## Declaring a union

A union declaration uses the same syntax as a struct, with `union` in place of `struct`:

```rust
#[repr(C)]
union IntOrFloat {
    i: u32,
    f: f32,
}
```

`union` is a contextual keyword. It is treated as a keyword only when it appears at the start of an item followed by an identifier and then a `{` or generic parameters. Everywhere else, including `let union = ...;` and `fn union() {}`, it remains an ordinary identifier. This means no existing code breaks, and in particular `std::collections::HashSet::union` continues to work.

Unions may be generic and may have where clauses, attributes, and visibility modifiers on the type and its fields, exactly as structs can. Tuple-style unions (`union U(u32, f32);`) are not supported, since unnamed fields would make accesses unreadable. Unit-style unions with no fields are also not supported.

## Layout

All fields of a union start at offset zero. The size of a union is at least the size of its largest field, rounded up to its alignment, which is the maximum alignment of its fields.

With `#[repr(C)]`, the layout matches what the platform C compiler would produce for the corresponding C union, and the union is passed to and returned from `extern "C"` functions following the C ABI rules for unions.

Without `#[repr(C)]`, the layout is unspecified beyond the guarantee above, but in practice the same.

## Constructing a union

A union is constructed with struct expression syntax naming exactly one field:

```rust
let u = IntOrFloat { f: 1.0 };
```

Naming zero fields, or more than one, is an error. Functional record update syntax (`..base`) is not permitted. Construction is safe.

## Reading and writing fields

Writing to a union field is safe, as long as the field type does not implement `Drop` (see below). Writing does not drop the previous contents.

```rust
let mut u = IntOrFloat { i: 0 };
u.f = 2.5;
```

Reading a field is `unsafe`, because the compiler cannot know which field was last written, and reinterpreting bytes as another type may produce an invalid value (for example, a `bool` that is neither 0 nor 1, or an invalid reference):

```rust
let bits = unsafe { u.i };
```

Taking a reference to a field is likewise `unsafe`. Borrowing one field borrows the whole union for the borrow checker, since all fields overlap.

## Pattern matching

Unions may be matched with a struct pattern naming exactly one field. Such a match is unsafe:

```rust
unsafe {
    match u {
        IntOrFloat { i: 10 } => println!("ten"),
        IntOrFloat { f } => println!("{}", f),
    }
}
```

A pattern does not check which field is active; it only reinterprets the bytes. Each arm simply reads the named field and tests the sub-pattern.

## Drop

A union does not know which of its fields is active, so it cannot drop its contents. Unions therefore never run destructors for their fields automatically. A union may implement `Drop` itself, in which case the implementation must determine the active field from external information.

This RFC allows fields of any type, including types that implement `Drop`. The `unions-and-drop` follow-up revisits this: allowing `Drop` fields makes field assignment surprising (it does not drop the old value) and complicates generics. Under that later design, union fields are restricted to `Copy` types and `ManuallyDrop<T>`, which makes the non-dropping behaviour explicit at the type level. Readers should consult that RFC for the current rules.

## Traits

Unions do not automatically implement any traits. `#[derive(Clone, Copy)]` is permitted when all fields are `Copy`, and is implemented as a bitwise copy. Deriving `Debug`, `PartialEq`, `Hash` and similar traits is an error, since they would need to know the active field.

## Unions and `unsafe` code guidelines

Reading a field other than the one last written is defined to reinterpret the bytes, like `transmute`. It is undefined behaviour only if the resulting value is invalid for the field's type. Reading a field whose bytes were partly uninitialized (because a smaller field was written) is undefined behaviour unless the field's type tolerates uninitialized bytes.

# Drawbacks
[drawbacks]: #drawbacks

- Adds a new kind of type with unsafe field access to the language, increasing the surface area of `unsafe` code.
- Contextual keywords complicate the parser slightly.
- Some uses are already served, if awkwardly, by `transmute` and careful layout. Making unions easy may encourage their use where an `enum` would be safer.

# Alternatives
[alternatives]: #alternatives

**A `#[repr(union)]` attribute on structs.** This was considered. It avoids a new keyword, but it changes the meaning of field access and construction drastically based on an attribute, which is surprising, and it reads poorly.

**Make `union` a full keyword in a future edition.** This would avoid contextual parsing but breaks existing identifiers. A contextual keyword is enough.

**Library-level emulation via macros.** Macros can generate accessor methods over a byte array, but cannot convey union-ness to the ABI, which is a central requirement.

**Safe access with runtime tags.** That is what `enum` already provides. Unions exist precisely for the case where the tag is external or absent.

# Unresolved questions
[unresolved]: #unresolved-questions

- Should unions be allowed in `const` contexts, and with what restrictions on reading fields?
- Should the compiler lint when a non-`repr(C)` union is used in an `extern` function signature?
- How should unions interact with the "uninhabited type" analysis, for example a union whose only field is `!`?
