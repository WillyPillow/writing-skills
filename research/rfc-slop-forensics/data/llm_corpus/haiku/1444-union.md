# Rust RFC 1444: union

- Start Date: 2016-07-20
- RFC PR: (placeholder)
- Rust Issue: (placeholder)

## Summary

This RFC proposes native support for C-compatible unions in Rust. A union is a type whose fields occupy the same memory, so that at any moment the value is interpreted through one of the fields. The RFC introduces the keyword `union` as a contextual keyword, so that existing code which uses `union` as an identifier continues to compile. Reading a field of a union is an unsafe operation, because the compiler cannot know which field was most recently written. Writing a field is safe, because the write replaces the contents of the union with a value of a known type.

Note that parts of this design have since been superseded by a later RFC that addresses drop behavior for unions. The present document describes the original proposal as it was written, with the understanding that the drop rules are discussed elsewhere.

## Motivation

Foreign function interfaces frequently use unions. A C library may define a structure whose payload is one of several types, selected by a tag field, and the Rust code that calls into it must represent the same layout. Without a native union type, the Rust programmer has two choices. One is to use a byte array of the correct size and alignment and to cast pointers into it, which is error prone and hard to read. The other is to use an enum, which has a different layout and cannot be passed to C with the same meaning.

Unions are also useful inside Rust code, for example to reinterpret the bits of a value, to implement tagged data structures with a known layout, or to build types whose size must be exact. The standard library currently implements some of these uses with compiler intrinsics and with private unsafe code, which is harder to audit than a language feature would be.

The proposal therefore aims to provide the feature directly, with a syntax that matches the rest of the language and with rules that make the common uses safe where possible and clearly marked where they are not.

## Guide-level explanation

A union is declared in the same way as a struct, using the keyword `union` in place of `struct`. Each field has its own type, and all fields share the same storage. The size of the union is the size of its largest field, rounded up to the alignment of its most strictly aligned field.

```rust
#[repr(C)]
union IntOrFloat {
    i: u32,
    f: f32,
}
```

A value of this type is created by naming one field. The other fields are not initialized. Writing to a field is safe, because the write produces a value of the field's type, and the compiler does not need to know anything else about the contents. Reading a field is unsafe, because the program may be reading a value that was written through a different field. The programmer must ensure that the bits stored in the union are valid for the type being read.

```rust
let mut u = IntOrFloat { i: 0x3f80_0000 };
let f = unsafe { u.f };
```

Pattern matching on a union is allowed, but it is also unsafe, because the match reads the contents of the union through one of its fields. The RFC does not propose any safe way to inspect a union without knowing which field is active, because that information is not available to the compiler.

The keyword `union` is recognized only in the position where a type declaration can begin. In other positions, it remains an ordinary identifier. This means that a program that defines a variable or function called `union` is not affected by the change.

## Reference-level explanation

A union declaration consists of a name, optional generic parameters and a set of named fields. The fields may have any type that is sized, and they may be declared with visibility modifiers in the same way as struct fields. The union does not have a discriminant, and the compiler does not track which field is active.

The layout of a union is defined by the `repr` attribute. Without an attribute, the compiler may choose any layout that satisfies the size and alignment requirements of the fields. With `repr(C)`, the layout is the one a C compiler would use for the same declaration, which means that every field starts at offset zero and the size is the maximum of the field sizes, padded as required by the alignment.

The compiler enforces that fields of a union do not require drop glue in the original proposal. A union whose fields have destructors cannot be defined, because the compiler would not know which destructor to run. This restriction is one of the parts that the later RFC relaxes under specific conditions.

Each field read is an unsafe operation. The compiler does not attempt to determine whether the bits are valid for the requested type, and it inserts no checks. The programmer is responsible for ensuring that the read produces a valid value.

Writing a field is safe for types that do not require drop. The write overwrites the contents of the union, and the previous contents are not dropped because the union was defined not to require it.

## Interaction with existing code

The contextual keyword is chosen so that the change does not break existing programs. A name such as `union` may appear as a variable, a function, a module or a field in existing code, and the parser must continue to accept those uses. The parser recognizes the keyword only when it appears at the start of an item declaration and is followed by an identifier and an opening brace or generic list. Any other use of the word is treated as an identifier.

The change does not affect the `std` crate, although the standard library may later use unions in its implementation. Crates that define their own type called `union` are not affected, because the name is scoped to its module.

## Drawbacks

A union with an unchecked read is a source of unsoundness if the programmer makes a mistake. The safety of the feature depends on the discipline of the programmer, and the compiler cannot help with it. Some critics have argued that the feature should be restricted to foreign declarations, where the layout is needed, and should not be available for general Rust code.

The feature also introduces a second way to represent data that overlaps with enums and structs. Programmers may be tempted to use unions where an enum would be more appropriate, because a union avoids the cost of a tag. This is a legitimate concern, but the RFC judges that the benefit for foreign code outweighs the risk of misuse.

## Rationale and alternatives

The design is driven by the need to match C layouts. Alternatives that rely on byte arrays and casts are workable, but they move the layout logic into user code, which is where errors come from. A native union makes the intent clear and allows the compiler to check the declaration.

One alternative is to make the union tagged, so that the compiler records which field was written and checks reads against it. This would make the feature safe, but it would require a discriminant, which conflicts with the C layout. A tagged union is better represented by an enum, which the language already supports.

Another alternative is to make reads safe for types that are valid for every bit pattern, such as integers. This is a useful refinement, but it requires a notion of valid bit patterns that the language does not yet have, and it is better left to a later proposal.

## Prior art

C and C++ provide unions with similar semantics, and many other languages provide variants of them for foreign interfaces. The design in this RFC follows the C model closely, with the main difference that reads are marked unsafe in Rust, which reflects the language's emphasis on explicit unsafety.

## Unresolved questions

The exact rules for pattern matching on unions are not settled. The RFC proposes that matching be permitted in unsafe blocks only, but it leaves open the precise syntax and whether a match may bind fields by reference.

It is also unresolved whether unions should be allowed to have fields with destructors, and how such fields should be dropped when the union goes out of scope. This question is taken up in the later RFC.

## Future possibilities

If unions are accepted, the standard library can use them in its implementation of certain types, which may reduce the amount of unsafe code. A later extension could allow reads of certain fields to be safe when the field type accepts every bit pattern, which would reduce the number of unsafe blocks that users need to write for simple reinterpretation.
