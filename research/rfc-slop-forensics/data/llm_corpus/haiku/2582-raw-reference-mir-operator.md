# Rust RFC 2582: raw_ref_op

- Feature Name: `raw_ref_op`
- Start Date: 2018-10-01
- RFC PR: rust-lang/rfcs#2582
- Rust Issue: rust-lang/rust#64490

## Summary

This RFC introduces two new variants of the borrow operator. The expression `&raw mut <place>` creates a raw mutable pointer of type `*mut T`, and `&raw const <place>` creates a raw immutable pointer of type `*const T`. In both cases the pointer is produced directly from the place, without first creating an intermediate reference.

The RFC also observes that the existing casts `<term> as *mut T` and `<term> as *const T`, when the term has a reference type, are equivalent to `&raw mut *<term>` and `&raw const *<term>` respectively. Finally, the proposal adds a lint that flags existing code that could be rewritten to use the new operator, so that the migration can happen gradually.

## Motivation

Creating a raw pointer to a place that may be misaligned, uninitialized, or part of a packed structure is an operation that current Rust makes awkward. The common approach is to write `&mut place as *mut _`, which first creates a reference and then casts it to a raw pointer. The intermediate reference is a problem in two ways. First, creating a reference asserts that the referent is valid and properly aligned for its type, and that its contents satisfy the invariants of that type. Code that only wants an address may therefore have undefined behavior even though the pointer itself would be harmless. Second, the reference's lifetime and aliasing rules may be stricter than the programmer intends, which can lead to surprising results under the borrow model.

Examples where this matters include accessing a field of a `#[repr(packed)]` struct, initializing memory that has not yet been written, and interacting with foreign code that expects a pointer into a structure whose invariants are temporarily broken. In each case the programmer wants to name an address without asserting anything about the contents at that address.

The existing workaround for packed fields, which copies the value out or uses `ptr::addr_of!`-style macros, is also not uniform. A direct operator would be more consistent and easier to teach.

## Guide-level explanation

The new operator is written as a borrow with a `raw` keyword in front of the mutability specifier. A raw shared pointer is produced by `&raw const`, and a raw mutable pointer by `&raw mut`. The operand is a place expression, which is an expression that denotes a location in memory, such as a variable, a field, an index, or a dereference.

```rust
let mut value = 0u32;
let p: *mut u32 = &raw mut value;
```

The programmer does not need to think of the result as a reference at all. The pointer refers to the location of `value` and may be used in the usual ways for raw pointers. Creating the pointer does not require that the place be initialized, aligned for a reference, or free of concurrent modification, although using the pointer to read or write will have its own requirements.

For code that already has a reference, the RFC notes that `&raw const *r` and `&raw mut *r` are the natural way to obtain a raw pointer from a reference. These are equivalent to the existing casts when the reference type is involved, so the familiar casts continue to mean what they mean today.

## Reference-level explanation

The grammar is extended so that the borrow operator may be followed by the keyword `raw` and then by either `const` or `mut`. The operand must be a place expression. Applying the operator to a value expression that is not a place is a compile-time error, since the result would have no meaningful address to point to.

The type of `&raw const place` is `*const T`, where `T` is the type of `place`. The type of `&raw mut place` is `*mut T`. Creating either pointer is a safe operation in the sense that it does not itself cause undefined behavior, but the RFC specifies that the operand place must be in bounds of its allocation and must not be the result of an operation that has already produced undefined behavior.

The operator does not create a temporary reference. The compiler must therefore lower it to an address computation that does not introduce a borrow in the intermediate representation. The mid-level intermediate representation gains a new kind of rvalue, which takes a place and a mutability and produces a raw pointer. The borrow checker treats this rvalue as not creating a loan, so that the surrounding code is not restricted by the lifetime of a reference that does not exist.

For the cast forms, the RFC specifies that `<term> as *mut T` where the term has type `&mut U`, with `T` and `U` related as the cast permits, produces a value that is equal to `&raw mut *<term>`. The same holds for shared references and `*const`. The lint triggers when the existing cast pattern appears in a position where the new operator would give the same result without creating a reference.

## Drawbacks

The new syntax adds another form of the borrow operator, and users must learn the distinction between a reference and a raw pointer produced from a place. The distinction is not hard to explain, but it is a new concept in the language surface.

The lint may produce many warnings in code that uses the existing casts widely. The RFC proposes that the lint be off by default in the first release, and that it be enabled in the next edition, so that migration is not forced. Some crates may still prefer the older form for readability.

There is also a risk of confusion about when the new operator is required. Code that works with the old casts is not wrong, but it may be less precise about the validity of its references. The documentation must explain that the new form is a tool for avoiding that imprecision and not a replacement that is always mandatory.

## Rationale and alternatives

The main alternative is to keep the existing cast form and to rely on macros in the standard library that expand to the correct code. Macros such as `addr_of!` already exist for some cases, and the RFC acknowledges their value. The drawback is that macros are not part of the language's core and cannot be used in every context in which an operator can appear. A built-in operator is also easier for the compiler and for tools to reason about, because the intent is visible in the syntax.

A second alternative was to add a method on place types, but the RFC rejects this because places are not values and cannot have methods in the same way. A method would require the operand to be moved or copied, which defeats the purpose.

A third possibility is to make the existing cast form a special case that never creates a reference, without any new syntax. This would change the meaning of code that is already in the wild and would be a breaking change in practice, so it is not proposed.

The RFC therefore adopts the new operator, with the lint and the equivalence to existing casts as a clear migration story.

## Prior art

Other systems languages provide ways to take the address of a location without creating an object that claims validity for its contents. The C language's address-of operator yields a pointer directly from an lvalue and does not have the reference concept that Rust has. Rust's own macros for packed fields and for uninitialized memory were written to approximate this behavior, and the RFC treats the new operator as their natural successor.

## Unresolved questions

The RFC leaves several questions open. The exact set of place expressions that are permitted in unusual positions, such as inside a `static` initializer, needs further specification. The interaction with the planned model of aliasing rules is not yet settled, and the team has asked that the operator's semantics be revisited if that model changes. The lint's exact conditions also need refinement to avoid false positives in macro-generated code.

## Conclusion

The `&raw` operators would let programmers produce raw pointers from places without creating intermediate references, which removes a source of unnecessary undefined-behavior risk and makes intent clearer. The design maps cleanly onto the existing intermediate representation, is compatible with current code, and comes with a migration lint. The RFC recommends that the operators be implemented under a feature gate and stabilized once the open questions are resolved.
