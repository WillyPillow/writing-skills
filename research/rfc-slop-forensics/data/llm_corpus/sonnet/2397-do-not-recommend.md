# RFC: `#[do_not_recommend]`

- Feature Name: `do_not_recommend`
- Start Date: 2018-08-12
- RFC PR: rust-lang/rfcs#2397
- Rust Issue: rust-lang/rust#51992

## Summary

A new attribute can be placed on trait implementations: `#[do_not_recommend]`. This attribute will cause the compiler to never recommend this impl transitively as a way to implement another trait. For example, this would be placed on `impl<T: Iterator> IntoIterator for T`. The result is that when `T: IntoIterator` fails, the error message will only mention `IntoIterator`. It will not say "perhaps `Iterator` should be implemented?".

## Motivation

When a trait bound is unsatisfied, rustc tries to be helpful by explaining why. If the type has no direct implementation of the trait, but there is a blanket impl whose where clauses are not satisfied, the compiler reports the unsatisfied where clauses as the cause of the failure. In most cases this is exactly what the user needs. If you write `Vec<Foo>: Clone` and `Foo` is not `Clone`, being told that `Foo: Clone` is not satisfied is the right thing to say.

There are, however, blanket impls that exist for a very different reason. They are not an invitation to implement the bound they require. They exist as a bridge, so that types which already are something can also be used as something else. The standard library's `impl<I: Iterator> IntoIterator for I` is the classic example. It exists so that an iterator can be passed to a `for` loop or to any function that takes `impl IntoIterator`. It does not mean that a type which wants to be `IntoIterator` should usually become an `Iterator`.

Consider the following code:

```rust
struct Wrapper(Vec<u32>);

fn main() {
    for x in Wrapper(vec![1, 2, 3]) {
        println!("{}", x);
    }
}
```

Today, the error says, among other things, that `Wrapper` is not an iterator, and notes that `Iterator` is required because of the blanket impl of `IntoIterator` for `I: Iterator`. A beginner reading this will frequently conclude that they need to implement `Iterator` for `Wrapper`. Sometimes that is correct. Very often, though, what they wanted was to implement `IntoIterator` directly, handing back the inner `Vec`'s iterator, and the note sends them down a path that requires them to add a cursor field and mutable state.

The same issue arises in the ecosystem. Libraries that use blanket impls as adapters, such as database query builders, web frameworks with extractor traits, and serialization layers, frequently produce errors where the compiler names a deeply nested internal trait that the user has never heard of. Authors of such libraries have repeatedly asked for a way to tell the compiler that a particular impl is an implementation detail whose where clauses should not appear in diagnostics.

The goal of this RFC is to give those authors a small, targeted tool, without changing how trait resolution works.

## Guide-level explanation

Suppose you maintain a library with the following blanket impl:

```rust
pub trait Render {
    fn render(&self) -> String;
}

impl<T: std::fmt::Display> Render for T {
    fn render(&self) -> String {
        self.to_string()
    }
}
```

When a user calls `render` on a type that is not `Display`, they will see an error mentioning both `Render` and `Display`. If this blanket impl is just a convenience, and you would expect most users to implement `Render` by hand, then the note about `Display` is misleading. You can annotate the impl:

```rust
#[do_not_recommend]
impl<T: std::fmt::Display> Render for T {
    fn render(&self) -> String {
        self.to_string()
    }
}
```

With this annotation, the compiler reports that `Foo: Render` is not satisfied, and does not follow the impl to say that `Foo: Display` is the missing piece.

The attribute has no effect on whether code compiles. It does not alter coherence, method resolution, or inference. It only affects which obligations are shown to the user in the explanation of a failed obligation. Removing it will never make a valid program invalid, and adding it will never make an invalid program valid.

The attribute is accepted only on trait impls. Placing it on any other item is an error. It takes no arguments.

## Reference-level explanation

The attribute `#[do_not_recommend]` is added to the set of built-in attributes. It is valid only on `impl Trait for Type` items. On any other item, the compiler emits an error.

When the compiler reports an unsatisfied obligation, it walks the chain of nested obligations that led to the failure. This chain is built from the impl candidates considered during selection. When it reaches a candidate that corresponds to an impl carrying `#[do_not_recommend]`, it stops. The obligation attached to that impl is treated as the reported root cause, and the nested where clauses of that impl are neither displayed in the primary message nor in the notes of the form "required because of the requirements on the impl of ...".

Concretely, the following changes are made to error reporting:

1. When suggesting candidate impls for an unsatisfied obligation `T: Trait`, impls with the attribute are excluded from the list of "the following implementations were found".
2. When computing the "root obligation" used to report a failure, the traversal does not descend past an impl with the attribute.
3. Where the compiler would otherwise say `the trait bound X: Bound is not satisfied ... required because of the requirements on the impl of Trait for X`, it instead reports `the trait bound X: Trait is not satisfied`.

The attribute is a hint. The compiler is permitted to ignore it where honoring it would require significant complexity, and the precise wording of diagnostics is not stable. Tools such as rust-analyzer may choose to display the omitted information on demand.

### Interaction with other features

The attribute does not interact with specialization, negative impls, or auto traits. It is not inherited by other impls, and it is not meaningful on impls with no where clauses, though applying it there is not an error, to simplify macro-generated code.

If multiple impls could apply and only some carry the attribute, the compiler reports only the impls that do not carry it. If all candidates carry the attribute, the compiler reports the plain failure of the trait without further explanation.

## Drawbacks

The principal drawback is that it adds another attribute to the language, and it is one that most users will never write. Each such attribute carries documentation and maintenance cost.

There is also a risk of over-application. A library author who finds an error message noisy may apply the attribute broadly, thereby hiding information that would have been useful. Someone whose type is one trait away from the blanket impl would then get less guidance than before. The attribute shifts judgment about diagnostics from the compiler to the library author, who may not have the same view of all use cases.

Finally, because the attribute only affects diagnostics, it makes the language slightly harder to reason about from the outside: two crates with identical semantics can produce different messages.

## Rationale and alternatives

**Do nothing.** Compiler diagnostics could be improved by heuristics alone, for instance by hard-coding the `IntoIterator` impl. This works for the standard library but cannot help third-party crates, and hard-coded special cases tend to accumulate.

**Use `#[rustc_on_unimplemented]`.** This existing attribute lets a trait author customize the message displayed when the trait is not implemented. It is useful, but it operates on the trait, not on the impl. It cannot suppress a note that arises from a different trait's blanket impl, which is the case here, since the note is generated from the `Iterator` side of the chain.

**A general-purpose diagnostic namespace.** A more flexible design would introduce a namespace of diagnostic attributes, with `do_not_recommend` as the first member. This RFC does not preclude such a namespace. In fact, it is a plausible future direction, in which case this attribute could be moved there with the old spelling kept as an alias.

**A negated form on the where clause.** One could instead annotate individual where clauses so that they are skipped in diagnostics. This is more granular but considerably more complicated to specify, and the use cases we know of apply to the impl as a whole.

## Prior art

Several compilers provide ways to tune diagnostics. GHC offers `TypeError` custom type errors, which let a library author substitute their own message for a failed instance lookup. Scala has `@implicitNotFound` and `@implicitAmbiguous`, which customize messages for missing implicits. Rust's `rustc_on_unimplemented` is itself descended from similar ideas. What is distinctive here is that the annotation is placed on the impl and works by suppression.

## Unresolved questions

- Should the attribute accept an optional reason string, for documentation purposes only?
- Should the attribute be permitted on traits to mean "do not recommend any impl of this trait"?
- What is the right behavior for rustdoc, if any? The current proposal is that rustdoc ignores the attribute entirely.

## Future possibilities

A stable diagnostic namespace, with attributes covering message customization, label customization, and suppression, would be a natural extension. The attribute could also be consumed by IDE tooling to rank code actions, preferring suggestions that do not pass through annotated impls.
