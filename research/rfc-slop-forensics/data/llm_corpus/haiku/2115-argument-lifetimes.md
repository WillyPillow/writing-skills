# Rust RFC 2115: argument_lifetimes

- Feature Name: `argument_lifetimes`
- Start Date: 2016-07-29
- RFC PR: (to be assigned)
- Rust Issue: (to be assigned)

## Summary

This RFC removes the need to declare lifetime parameters separately in function definitions and `impl` headers when the lifetimes can be inferred from the signature. A function signature is taken to bind any lifetime it mentions that is not already bound, so the author no longer needs to write a parameter list for each lifetime. The RFC also adds a style lint that encourages explicit lifetimes on structs that hold references, and it introduces the `'_` form for explicitly eliding a lifetime.

## Motivation

Lifetimes are a central part of Rust's safety guarantees, but the syntax for declaring them is verbose in common cases. A function that takes two references and returns one of them must currently declare each lifetime in angle brackets before the parameter list, even though the relationship between the lifetimes is already evident from the signature. The declaration repeats information that the rest of the signature conveys.

The same verbosity appears in `impl` headers. An implementation block for a type with a lifetime parameter must name that parameter at the top of the block, and it must repeat the name wherever the type appears inside. In large implementations this produces a great deal of repetition that adds no meaning.

Verbosity is not the only cost. Beginners find the declaration step confusing, because it requires them to understand a distinction that the language could infer. Experienced programmers find it tedious. A design that infers the obvious case while keeping explicit declarations available for the unusual case would reduce friction for everyone.

At the same time, the inference must not hide information that matters. Readers of a struct that holds a reference should be able to see that a lifetime is involved, so the RFC pairs the inference with a lint that asks for explicit lifetimes on such structs.

## Guide-level explanation

Consider a function that returns the longer of two string slices. Under this proposal, the signature can be written as follows:

```rust
fn longest(x: &str, y: &str) -> &str
```

Here the elided lifetimes are bound by the signature itself, and the function returns a reference that is tied to one of its inputs. Writing the lifetime explicitly is still permitted when the relationship needs to be stated clearly:

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str
```

For an `impl` block, the lifetime may be introduced in the header and used throughout, or it may be left to the compiler. The RFC asks the author to choose a lifetime name that is more than one character long when it is introduced in an `impl` header, so that it is easy to distinguish from the short names that appear inside function bodies.

When a struct holds a reference, the RFC recommends naming its lifetime explicitly. A struct such as `Iter` that wraps a borrowed collection hides the borrow in its definition, and a reader who sees only the type name may not realize that it borrows. The lint encourages the author to write the lifetime, which makes the borrow visible.

The form `'_` allows a lifetime to be elided explicitly at a point where the compiler would otherwise infer it. Writing `'_` signals to the reader that a lifetime exists at that position, even though its name is not given. Leaving the lifetime off entirely remains valid for functions, but for structs it is deprecated.

## Reference-level explanation

### Binding rules

A function signature binds every lifetime that it mentions and that is not already in scope. Lifetimes already in scope come from an enclosing `impl` header or from an explicit declaration on the function. Any new lifetime name appearing in the parameter list or return type is treated as a parameter of the function, and it is introduced without a separate declaration.

The rules for elision in function signatures are unchanged for the cases that are already covered. The new rule adds only the ability to name a lifetime in a signature without declaring it first. Elision still assigns a fresh lifetime to each elided reference in the parameters, and it ties the return lifetime to the input when exactly one lifetime appears among the parameters.

### Impl headers

An `impl` header may mention lifetimes, and those lifetimes are bound for the entire block. A style lint checks that such lifetimes have names longer than one character. The lint is a warning rather than an error, because the names are a matter of style and not of correctness. Less important lints are proposed for related situations, such as unused lifetimes in headers.

### Explicit elision

The `'_` form is permitted wherever a lifetime may be elided. It has the same meaning as the elided lifetime at that position. Its purpose is to make the elision visible to readers, so that a reference with an unnamed lifetime is recognized as such. The form is accepted in function signatures, in types inside function bodies, and in `impl` headers.

### Struct lint

A lint is added that warns when a struct has a lifetime parameter that is implicit in a field type. The lint asks the author to write the lifetime explicitly in the field declaration. The lint is warn-by-default, and it can be allowed by a crate that prefers the older style. Deprecation of the fully elided form in structs is planned for a later edition.

## Drawbacks

The inference rules add a small amount of complexity to the language. Readers must learn that a lifetime which is not declared may still be bound by a signature, and the rules for when a lifetime is bound must be stated clearly. A careless reader may not notice that a new lifetime has been introduced.

The style lints also introduce judgment. Some authors will find them intrusive, and the boundary between a lifetime that deserves explicit mention and one that does not is not always sharp. The RFC accepts this cost in exchange for clearer code in the cases that matter most.

## Rationale and alternatives

The main alternative is to leave the language as it is and rely on documentation to explain the verbosity. That choice preserves the current rules but does nothing for the friction that the proposal addresses. It also leaves the struct case unaddressed, where elision hides information from readers.

A second alternative is to infer lifetimes everywhere, including in structs. This would reduce the number of annotations further, but it would make the borrows in struct definitions invisible, which is the outcome the struct lint is designed to prevent. The RFC keeps the struct case explicit for that reason.

## Prior art

The elision rules already in the language were a major step toward reducing lifetime annotations, and this RFC continues in the same direction. The proposal is also consistent with the way the language treats generic type parameters, which may be introduced in a signature without a separate declaration in some positions.

## Unresolved questions

The exact set of lints for `impl` headers has not been finalized. Contributors have asked whether the length rule should apply to all lifetimes or only to those introduced in headers. The RFC proposes the narrower rule but leaves the question open for review.

It is also unsettled how the `'_` form should interact with future features that extend elision. The current design is intended to be forward compatible, but the details will depend on the implementation.

## Future possibilities

Once the binding rules are in place, the language may be able to infer more lifetimes in closures and in trait bounds. These extensions would build on the same principle, that a lifetime mentioned in a signature is bound by the signature, and they would reduce annotation further without hiding the relationships that matter to readers.
