- Feature Name: `really_tagged_unions`
- Start Date: 2017-10-30
- RFC PR: rust-lang/rfcs#2195
- Rust Issue: N/A

# Summary

Formally define the memory layout of enums that carry data when they are marked `#[repr(C)]` or with a primitive integer representation such as `#[repr(u8)]`, `#[repr(u32)]` or `#[repr(i8)]`. Today these attributes have a defined meaning only for C-like (fieldless) enums. This RFC specifies a layout for every enum with such an attribute, so that:

1. low-level Rust code can initialize the tag and the payload of an enum separately, through raw pointers, and
2. C and C++ code can safely read, construct and modify these enums through equivalent declarations of tagged unions.

# Motivation

Rust's default enum layout is deliberately unspecified. That freedom lets the compiler pack discriminants into niches (`Option<&T>` is pointer-sized) and reorder fields. It is the right default, but it means there is no way to describe an enum with fields to foreign code, and no way to write unsafe code that relies on where the tag lives.

Two groups of users have hit this wall.

**FFI with C and C++.** Programs that embed Rust into a C++ codebase, such as Firefox's style system, want to share rich data types across the boundary. The natural C++ representation of a Rust enum is a tagged union: an integer tag followed by a union of structs. Without a guaranteed layout, people either duplicate every enum as a hand-written C-compatible struct with conversion functions, or they rely on the current compiler's behaviour and hope it does not change. The first approach is tedious and slow; the second is unsound.

**In-place initialization.** Some code needs to build an enum value field by field in memory it does not own as a Rust value, for example when deserializing directly into a buffer, or when emplacing a large enum into a heap allocation to avoid copying it through the stack. To do that safely the code must know where to write the tag and where each variant's fields go.

Both groups already write `#[repr(C)]` or `#[repr(u8)]` on their enums, and the compiler accepts it, but the attribute's meaning for enums with fields is not documented. This RFC turns the current implementation behaviour into a guarantee, with small adjustments where the implementation was inconsistent.

# Guide-level explanation

Consider:

```rust
#[repr(u8)]
enum Shape {
    Circle(f32),
    Rect { w: f32, h: f32 },
    Empty,
}
```

With this RFC, `Shape` is laid out as if it were the following union of structs, each beginning with the tag:

```rust
#[repr(C)]
union ShapeRepr {
    circle: ShapeCircle,
    rect: ShapeRect,
    empty: ShapeEmpty,
}

#[repr(u8)]
#[derive(Copy, Clone)]
enum ShapeTag { Circle, Rect, Empty }

#[repr(C)] struct ShapeCircle { tag: ShapeTag, r: f32 }
#[repr(C)] struct ShapeRect   { tag: ShapeTag, w: f32, h: f32 }
#[repr(C)] struct ShapeEmpty  { tag: ShapeTag }
```

Because every variant struct starts with the tag, you can always read the first byte to learn which variant is active, and then reinterpret the value as the matching struct.

If instead the enum is marked `#[repr(C)]`:

```rust
#[repr(C)]
enum Shape { Circle(f32), Rect { w: f32, h: f32 }, Empty }
```

it is laid out as a struct with two fields, a tag and a union of the payloads:

```rust
#[repr(C)]
struct ShapeRepr {
    tag: ShapeTag,       // a #[repr(C)] fieldless enum
    payload: ShapePayload,
}

#[repr(C)]
union ShapePayload {
    circle: ShapeCircle,
    rect: ShapeRect,
    empty: ShapeEmpty,
}

#[repr(C)] struct ShapeCircle { r: f32 }
#[repr(C)] struct ShapeRect   { w: f32, h: f32 }
#[repr(C)] struct ShapeEmpty;
```

This matches the idiom most C programmers would write by hand:

```c
enum ShapeTag { Circle, Rect, Empty };
struct Shape {
    enum ShapeTag tag;
    union {
        struct { float r; } circle;
        struct { float w, h; } rect;
    } payload;
};
```

You may also combine the two, writing `#[repr(C, u8)]`, to get the `repr(C)` struct-of-tag-and-union layout while fixing the tag's size to one byte.

The difference between the primitive and `repr(C)` forms is subtle but sometimes matters. With a primitive repr the payload of each variant is placed directly after the tag at whatever offset that variant's own alignment requires, so small variants can be packed tightly. With `repr(C)` all payloads start at the same offset, after padding for the most-aligned variant, which makes the type easier to describe in C but sometimes larger.

# Reference-level explanation

## Primitive representation

For an enum `E` with `#[repr(Int)]`, where `Int` is one of `u8`, `u16`, `u32`, `u64`, `usize`, `i8`, `i16`, `i32`, `i64` or `isize`:

- Let `ETag` be a fieldless `#[repr(Int)]` enum with one variant per variant of `E`, with the same discriminant values.
- For each variant `V` with fields `f1: T1, ..., fn: Tn`, let `EV` be a `#[repr(C)]` struct with fields `tag: ETag, f1: T1, ..., fn: Tn`, in declaration order.
- `E` has the layout of a `#[repr(C)]` union whose fields are each `EV`.

## C representation

For an enum `E` with `#[repr(C)]` and at least one variant with fields:

- Let `ETag` be a fieldless `#[repr(C)]` enum with one variant per variant of `E`.
- For each variant `V`, let `EV` be a `#[repr(C)]` struct containing that variant's fields in declaration order.
- Let `EPayload` be a `#[repr(C)]` union whose fields are each `EV`.
- `E` has the layout of a `#[repr(C)]` struct with fields `tag: ETag, payload: EPayload`.

## Combined representation

`#[repr(C, Int)]` uses the C representation above, except that `ETag` is `#[repr(Int)]`.

## Discriminant values and validity

Explicit discriminants (`A = 3`) are permitted on enums with fields under these representations. It is undefined behaviour for the tag to hold a value that does not correspond to a variant, just as for fieldless enums.

## Niche optimization

Enums with one of these representations do not participate in niche-filling layout optimizations for their own tag. `Option<E>` may still use invalid tag values of `E` as its niche, because the set of valid tag values is known.

## Generic enums

The layout rules apply to generic enums after monomorphization. If a type parameter is instantiated with a zero-sized type, the corresponding fields occupy no space, as in any `repr(C)` struct.

## Interaction with other attributes

`#[repr(packed)]` and `#[repr(align)]` are not permitted on enums by this RFC. `#[repr(transparent)]` is not affected.

# Drawbacks

- This commits the language to specific layouts for these enums forever. Any future improvement to enum layout cannot apply to them. Since users opt in explicitly, this cost falls only on code that asked for it.
- Two layouts with different trade-offs may confuse users. Documentation must explain when each is appropriate.
- Users may write `#[repr(u8)]` to save space without realizing they have also disabled niche optimizations.

# Rationale and alternatives

**Only specify `repr(C)`.** This would serve C interop but not the compact layout that low-level Rust code often wants. The primitive layout also corresponds to how many existing C libraries define tagged unions, with the tag inside each variant struct.

**Introduce new attributes.** A new `#[repr(tagged)]` would avoid giving existing attributes new guarantees. But the current implementation already behaves almost exactly as described, and code in the wild already depends on it. Documenting the existing attribute is less churn.

**Leave it unspecified.** Users would keep duplicating types or relying on unstable behaviour. Tools such as `cbindgen` cannot generate correct headers without a guarantee.

# Prior art

C and C++ tagged unions are the direct model. Swift's `@frozen` enums with C interop and the Itanium layout of `std::variant` were reviewed; neither offers a portable layout guarantee for payload-carrying enums. `cbindgen` already emits C++ declarations matching the primitive layout.

# Unresolved questions

- Should `repr(C)` on an enum with fields warn when the user probably meant a primitive repr, or vice versa?
- Should the language provide a safe way to obtain a pointer to a variant's payload for in-place initialization, rather than requiring users to define the shadow structs themselves?
