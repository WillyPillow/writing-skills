- Feature Name: `union`
- Start Date: 2015-12-29
- RFC PR: rust-lang/rfcs#1444
- Rust Issue: rust-lang/rust#32836

**Note:** This RFC has been partially superseded by `unions-and-drop`.

# Summary
[summary]: #summary

Provide native support for C-compatible unions, defined via a new "contextual keyword" `union`, without breaking any existing code that uses `union` as an identifier.

# Motivation
[motivation]: #motivation

Many FFI interfaces include unions. Operating system headers, graphics APIs, network protocol definitions and hardware register descriptions all rely on them. A union is a type whose fields all occupy the same storage; writing one field and reading another reinterprets the bytes.

Rust currently has no direct way to declare such a type. The workarounds all have drawbacks.

**Use a struct of the largest size.** One can declare a struct with a byte array of the right size and cast pointers into it. This is verbose and error-prone. The alignment of the array may be wrong, the size must be computed by hand and must be updated if a field changes, and every access needs an unsafe pointer cast.

**Use an enum.** Rust enums are tagged, so they carry a discriminant and have a layout that does not match a C union.

**Use `mem::transmute`.** This copies the whole value and requires the user to keep types and sizes in sync.

**Generate bindings that hide the union.** The bindgen tool presently emits a struct with accessor methods that cast the storage. That is a workable approximation, but the output is harder to read and use than a real union, and the approach cannot be used for hand-written code without much boilerplate.

Besides FFI, unions are useful in unsafe code that wants to implement space-efficient data structures: a value that is either a pointer or an integer, a small-string optimization, or a manually managed tagged union with a tag stored elsewhere. Rust's standard library implements some of these with raw pointers and casts, which a union would express more directly.

# Detailed design
[design]: #detailed-design

## Declaring a union

A union is declared with the contextual keyword `union`:

```rust
#[repr(C)]
union MyUnion {
    f1: u32,
    f2: f32,
}
```

The syntax mirrors that of a struct with named fields. Tuple unions and unit unions are not supported. Generic parameters, lifetimes and where clauses are accepted as with structs. Fields are private by default, and visibility modifiers may be placed on them.

## Contextual keyword

`union` is not reserved. It is treated as a keyword only when it appears at the start of an item and is followed by an identifier and then either `<` or `{`:

```rust
union Foo { ... }     // a union declaration
union Foo<T> { ... }  // a union declaration
let union = 3;        // an ordinary identifier
fn union() {}         // an ordinary identifier
union::path();        // a path
```

In all other contexts, `union` is an ordinary identifier, so existing code is unaffected. The parser needs a one-token lookahead past `union` to determine whether a declaration follows. This is a form of lookahead already used for other contextual keywords, such as `default` and `auto`.

## Layout

A union must be marked `#[repr(C)]` to have a defined layout. The union has the size of its largest field, rounded up to the alignment of the field with the greatest alignment, and all fields start at offset 0. Without `#[repr(C)]` the layout is unspecified, except that all fields are at offset 0 and the size is at least that of the largest field.

## Construction

A union value is created by specifying exactly one field:

```rust
let u = MyUnion { f1: 1 };
```

Specifying zero or more than one field is an error. Construction is safe, since writing to a field cannot cause undefined behaviour in itself.

## Field access

Reading a field is unsafe, because the compiler cannot know which field was last written, and the bytes may not be a valid value of the field's type:

```rust
let u = MyUnion { f1: 1 };
let f = unsafe { u.f2 };
```

Writing a field of a `Copy` type is safe, as in `u.f1 = 2;`, because it overwrites the storage and no previous value is dropped. Taking a reference to a field is unsafe like reading, since the reference could be used to read.

## Pattern matching

Unions may be matched with a pattern naming exactly one field:

```rust
unsafe {
    match u {
        MyUnion { f1: 10 } => { ... }
        MyUnion { f2 } => { ... }
    }
}
```

The match must be in an unsafe block, since it reads a field. Fields may be matched with literals or bindings. Exhaustiveness checking treats a pattern naming one field with an irrefutable subpattern as exhaustive.

## Field types

For this RFC, the fields of a union are restricted to `Copy` types, references, and tuples and arrays of those. Types with destructors, such as `String` or `Box<T>`, are not permitted, because the compiler cannot know which field is active when the union is dropped, and so cannot run the right destructor.

Unions of `Copy` types are themselves `Copy` if all fields are, and `Clone` may be derived.

## Drop

A union with only `Copy` fields has no drop glue. A union cannot implement `Drop`; this RFC says nothing about relaxing that. (This part has been superseded by a later RFC which allows `ManuallyDrop` fields.)

## Other traits

Derives for `Debug`, `PartialEq` and so on are not available, since they would have to read fields. Users may implement these traits by hand.

# How We Teach This
[how-we-teach-this]: #how-we-teach-this

Unions should be introduced in the section on FFI and in the Nomicon, as an unsafe feature intended for interoperating with C and writing low-level data structures. The documentation should stress that reading from a union field is the programmer's responsibility, and should compare it with `mem::transmute`. Examples showing the translation of a C union to a Rust union will help C programmers.

# Drawbacks
[drawbacks]: #drawbacks

**Another kind of item.** Unions add to the surface area of the language, and the parser and the compiler must be extended. Tools such as rustfmt, rustdoc and IDEs need updates.

**Contextual keywords add parser complexity.** Although the rule is simple, it makes the grammar slightly less regular.

**Potential misuse.** Some programmers may reach for unions to reinterpret data where safe alternatives exist. Documentation and lints can guide against this.

# Alternatives
[alternatives]: #alternatives

**Do nothing, and rely on bindgen.** This leaves hand-written FFI and low-level structures awkward.

**Reserve `union` as a keyword.** This would break existing code that uses `union` as a name, such as `HashSet::union`, which is a method in the standard library. A contextual keyword avoids the breakage.

**A macro-based approach.** A macro could generate a struct with accessors, but this cannot be as ergonomic or give pattern matching.

**Allow non-Copy fields now.** This needs a decision on drop semantics. Restricting to `Copy` types leaves room for a later extension.

# Unresolved questions
[unresolved]: #unresolved-questions

- Should field writes of non-Copy types be allowed in the future?
- Should the compiler offer a lint for unions without `#[repr(C)]`?
- How should debuginfo describe unions?
