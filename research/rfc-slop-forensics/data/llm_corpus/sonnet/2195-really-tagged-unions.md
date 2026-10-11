# RFC: Really Tagged Unions

- Feature Name: `really_tagged_unions`
- Start Date: 2017-09-25
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

Formally define the enum `#[repr(u32, i8, etc..)]` and `#[repr(C)]` attributes to force a non-C-like enum to have a defined layout. This serves two purposes: allowing low-level Rust code to independently initialize the tag and payload, and allowing C(++) to safely manipulate these types.

## Motivation

Rust's `enum` type is a tagged union. Any value of an enum has a discriminant (the tag) identifying which variant is active, and a payload holding that variant's fields. For enums without fields, the `repr` attribute already pins the discriminant to a given integer type:

```rust
#[repr(u8)]
enum Color { Red, Green, Blue }
```

For enums with fields, however, `#[repr]` today is accepted in some positions but its meaning is not nailed down. The compiler is free to choose the placement of the tag, the layout of each variant, niche optimizations, and padding. This is the correct default: it lets `Option<&T>` occupy a single pointer and lets the optimizer reorder fields. But it also means that Rust code cannot do two things that systems programmers regularly need.

### Interop with C and C++

Consider a C library that exposes a tagged union:

```c
typedef enum { TAG_NONE, TAG_INT, TAG_FLOAT } Tag;

typedef struct {
    Tag tag;
    union {
        int32_t i;
        float f;
    } payload;
} Value;
```

There is no way to write a Rust type that is guaranteed to have this layout while still enjoying the safety and expressiveness of an `enum`. Users today write a `#[repr(C)]` struct holding a `#[repr(C)]` union, and then re-implement the discriminated access by hand, with `unsafe` and without the compiler checking exhaustiveness. Bindings generators such as `bindgen` and `cbindgen` also cannot translate Rust data-carrying enums to a C header with any confidence, since the layout is unspecified.

### Initializing the tag and payload independently

Low-level code sometimes needs to build a value in pieces. Examples include writing directly into memory-mapped buffers, deserializing from a wire format where the tag arrives first, and implementing custom allocators or arena builders. Without a defined layout, there is no sound way to write the tag and then write the payload separately, because the offset of each is unknown.

This RFC defines the layout of such enums so that both use cases become possible and sound.

## Guide-level explanation

You may put a `repr` attribute naming an integer type on an enum that has fields:

```rust
#[repr(u8)]
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
}
```

This tells the compiler that the discriminant is stored as a `u8`, located at the start of the value, and that each variant's fields follow it in a layout that is described precisely below. As a consequence, you can write code that treats the enum as a union of structs, each beginning with the tag.

You can also use `#[repr(C)]`:

```rust
#[repr(C)]
enum Message { /* same variants */ }
```

This gives the enum the layout that a C compiler would give to the equivalent tagged union, with the tag being a C `enum` sized as the target's default C integer, and the payload a `union` of the variants' structs.

Both attributes also work together, as `#[repr(C, u8)]`, which selects a C-style layout using an explicitly sized tag.

For C interop you use `repr(C)` or `repr(C, u8)`; for packing a tag tightly in a Rust-only context you use `repr(u8)`.

## Reference-level explanation

### Primitive representation: `repr(Int)`

Given an enum with `#[repr(Int)]` where `Int` is one of `u8`, `u16`, `u32`, `u64`, `usize`, `i8`, `i16`, `i32`, `i64`, or `isize`, the layout is defined as that of a `union` of `repr(C)` structs, one per variant. Each struct has, as its first field, the tag of type `Int`, followed by the fields of the variant in declaration order, laid out as `repr(C)`.

For the `Message` example above, the layout is equivalent to:

```rust
#[repr(C)]
union MessageRepr {
    quit: MessageQuit,
    mv: MessageMove,
    write: MessageWrite,
}

#[repr(C)] struct MessageQuit  { tag: u8 }
#[repr(C)] struct MessageMove  { tag: u8, x: i32, y: i32 }
#[repr(C)] struct MessageWrite { tag: u8, s: String }
```

Notably, under this scheme the payload of a variant begins at a position that depends on the alignment of that variant's fields, which can leave padding between the tag and the first field. This is intentional and is the same as in the C layout of a struct whose first member is the tag.

The size of the whole enum is the size of the largest variant struct, rounded up to the maximum alignment.

### C-compatible representation: `repr(C)`

With `#[repr(C)]` on a data-carrying enum, the layout is that of a `repr(C)` struct with two fields: the tag, whose type is an `enum` with the same discriminants as the Rust enum and sized as a C compiler would size it for the target, and a `repr(C)` union of `repr(C)` structs, one per variant, each containing that variant's fields. For the earlier example this yields:

```rust
#[repr(C)]
struct MessageRepr {
    tag: MessageTag,
    payload: MessagePayload,
}
```

The difference from `repr(Int)` is that the tag and the payload are separated, so that the payload's offset is the same for every variant, and equal to the alignment-rounded size of the tag. This matches the common C idiom.

### `repr(C, Int)`

This combines the two: the layout is that of `repr(C)` above, but with the tag type fixed as `Int` rather than the target default.

### Discriminant values

Explicit discriminants work as before. When a data-carrying enum specifies a primitive representation, explicit discriminant expressions are permitted on variants with fields, which they are not at present. The values must fit within `Int`.

### Niche optimization

Enums with any of these representations do not participate in niche optimization for their own layout: a `repr(u8)` enum always has a distinct tag byte. However, a *containing* type may still use invalid tag values as niches, if the compiler can determine them. For example, `Option<Message>` may use a tag value that no variant takes. This is not guaranteed, however, and should not be relied upon for FFI.

### Validity

Producing a value of such an enum whose tag does not correspond to any variant is undefined behavior, as is a payload that is invalid for the variant the tag claims. Code that initializes the tag and payload independently must therefore ensure both are written before the value is read as the enum type, and must use `MaybeUninit` or raw pointers during construction.

### Pattern matching and transmute

The defined layout allows sound `transmute` and pointer casts between the enum and its equivalent union, provided validity holds.

## Drawbacks

- This commits the language to a layout for a new class of types. Changes to the layout of `repr(Int)` enums would henceforth be breaking.
- It permits more unsafe code with subtle validity requirements.
- Having both `repr(C)` and `repr(Int)` produce different layouts could confuse some users. Documentation must explain this clearly.
- Defining the layout in terms of unions of structs may not match what some existing C++ compilers do for `std::variant`, which is unspecified; this RFC makes no promises about C++ types beyond what a C union of structs gives.

## Rationale and alternatives

**Do nothing.** Users continue to hand-write unions. The ecosystem has already done so many times, and each reinvents the design with inconsistent results.

**Only provide `repr(C)`.** This addresses FFI but not the use case of Rust-only low-level construction, where it is desirable to avoid the extra space the C layout may need.

**Only provide `repr(Int)`.** The union-of-structs layout does not match the C idiom, so C code cannot easily read it without declaring structs that repeat the tag.

**A new attribute** instead of reusing `repr`. The meaning of `repr` for field-less enums is already "this controls representation", so extending it is consistent and discoverable.

**Leaving the discriminant location implicit.** Rejected, as the entire point is for programmers to be able to rely on it.

## Prior art

C and C++ programmers write tagged unions manually. Swift has `indirect enum` but no stable layout. Zig's `union(enum)` has a similarly explicit tag-and-payload representation, with an `extern` form for C compatibility. Several Rust crates, including those for protocol buffers and Lua bindings, define unions by hand.

## Unresolved questions

- Should `repr(C)` be permitted on enums that contain no fields? It already is, so the answer is to preserve the current behavior.
- Should we allow `#[repr(packed)]` combinations? This RFC leaves them out.
- What should the tag size be for `repr(C)` on targets where C's default `enum` size varies by flags? The RFC proposes to follow the target's default.
