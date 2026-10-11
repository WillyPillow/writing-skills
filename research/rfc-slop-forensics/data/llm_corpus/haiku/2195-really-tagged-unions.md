# RFC 2195: Defined Layout for Enums with Explicit Representation

- Feature Name: `really_tagged_unions`
- Start Date: 2017-05-03
- Status: Proposed

## Summary

This RFC gives a precise, documented memory layout to enums that carry an explicit representation attribute. Today, `#[repr(u32)]`, `#[repr(i8)]`, and similar attributes are accepted on enums that have data-carrying variants, but the layout that results is not fully specified. The compiler is free to choose the placement of the tag and the payload as long as the tag has the requested integer type, and as a result, unsafe code cannot rely on the arrangement. This proposal defines the layout as a `repr(C)` struct containing a tag followed by a union of the variant payloads, for both `repr(C)` and integer-tagged forms. With this definition, low-level code can write the tag and the payload independently, and C or C++ code can read and write the same values safely.

## Motivation

Rust programs frequently need to exchange data with code written in other languages. A common pattern in C is the tagged union: a struct containing an integer tag and a union of payloads, where the tag says which member of the union is valid. Many APIs expose values in this shape, including message formats, event systems, and foreign function interfaces that return variant data.

Rust's enums are a natural fit for this pattern, but the current guarantees are too weak for interoperability. Consider an enum with two variants:

```rust
#[repr(u32)]
enum Message {
    Ping,
    Data(u64),
}
```

The programmer expects the tag to be a four-byte integer and the payload to follow it. Under the present rules, the tag is a `u32` as requested, but the offset of the payload is not guaranteed to match what a C compiler would compute for the equivalent struct. A C function that receives a pointer to this value, or that constructs one, can therefore disagree with Rust about where the payload lives.

Two use cases are especially affected. The first is low-level Rust code that initializes the tag and the payload in separate steps, for example when filling a buffer received from a device. The second is C or C++ code that must examine or build these values without going through a Rust function call. In both cases, the programmer needs a layout that is written down and stable.

## Guide-level explanation

An enum annotated with an integer representation, such as `#[repr(u8)]`, `#[repr(i32)]`, or `#[repr(u64)]`, has a layout that is equivalent to the following C-style definition:

```rust
#[repr(C)]
struct Enum {
    tag: u32,      // the integer type given in the attribute
    payload: Union, // a union of the variant payloads
}
```

Each variant corresponds to a field of the union, with a struct layout that begins with its own fields. The tag holds the discriminant value of the active variant. Fieldless variants have no payload storage, but the union still exists to keep the size and alignment consistent across all variants.

The same definition applies when the enum is annotated with `#[repr(C)]`, except that the tag has the type that a C compiler would choose for an enum of the same variant count.

Programmers who need to write the tag and payload separately can do so by taking a pointer to the enum, casting it to the layout above, and writing each part. The RFC does not add new syntax for this; it only fixes the layout so that the cast is valid.

## Reference-level explanation

For an enum `E` with `#[repr(T)]`, where `T` is an integer type, the layout of `E` is defined as a `repr(C)` struct with two fields. The first field has type `T` and holds the discriminant. The second field has type `union { V1, V2, ... }`, where each `Vi` is a `repr(C)` struct containing the fields of the i-th variant. The union has the alignment and size required to hold the largest variant payload. The overall alignment of `E` is the maximum of the alignment of `T` and the alignment of the union.

For an enum `E` with `#[repr(C)]`, the same structure applies, with `T` set to the integer type that the C compiler selects for enumerations of the same size. The discriminant values are assigned in declaration order, starting at zero, unless the programmer assigns explicit values.

Fieldless enums with an integer representation keep their existing layout, since their values are fully determined by the tag. Enums with no representation attribute retain the unspecified layout, and the compiler may continue to optimize them freely, including by using niche values.

Safety considerations apply. Writing an invalid tag value produces undefined behavior when the enum is later read. Writing a payload that does not match the tag has the same effect. The RFC does not make these operations safe. It makes them meaningful, so that code which performs them deliberately has a defined effect.

## Drawbacks

The defined layout prevents some optimizations that the compiler currently applies. In particular, the niche optimization that stores a discriminant inside an unused bit pattern of a payload is not available for enums with explicit representation, which can increase the size of some types. Programs that depend on the current, smaller sizes will change behavior.

The rule also adds a constraint to future language evolution. Any change to the layout of data-carrying enums must now respect this definition, which limits some design choices.

## Rationale and alternatives

One alternative is to leave the layout unspecified and provide a separate attribute, such as `#[repr(tagged)]`, that opts into the defined layout. This keeps the existing behavior unchanged, but it creates two families of enum with different guarantees, and programmers must remember which attribute they need. The proposal instead attaches the guarantee to the existing representation attributes, since programmers who write `repr(u32)` already expect a specific tag size and would reasonably expect a predictable layout.

A second alternative is to define only the tag and leave the payload position to the compiler. This is insufficient, because the payload offset is the value that C code most needs to agree on.

A third alternative is to generate bindings or helper functions that hide the layout. This works for some uses, but it does not help code that operates on raw memory, and it adds a layer that library authors must maintain.

## Prior art

The C standard does not define a tagged union, but the pattern is common in practice, and most C compilers lay out the structures in the way this RFC describes. Several systems languages have adopted similar guarantees for enums with explicit representations, which gives this proposal a track record to build on.

## Unresolved questions

- The treatment of variants with zero-sized payloads needs to be specified precisely, including whether the union member for such a variant is present.
- The interaction with `#[repr(packed)]` is not fully settled and may need a separate rule.
- The exact wording of the safety requirements for writing the tag must be reviewed by the unsafe code working group.

## Future possibilities

Once the layout is defined, the language can offer safe helper types that build and inspect these enums without exposing raw pointers. Such helpers are outside the scope of this RFC, but they would rest on the guarantee introduced here.
