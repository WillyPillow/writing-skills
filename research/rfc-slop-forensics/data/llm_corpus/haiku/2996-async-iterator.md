# Rust RFC 2996: async_iterator

- Feature Name: `async_iterator`
- Start Date: 2019-07-09
- RFC PR: rust-lang/rfcs#2996
- Rust Issue: rust-lang/rust#79024

## Summary

This RFC proposes introducing an `AsyncIterator` trait into the standard library, using the design that has been developed in the `futures` crate. It also proposes redirecting the `Stream` trait definition in the `futures-core` crate, which the `futures` crate re-exports, so that it refers to the standard library's `AsyncIterator` instead of defining its own.

The goal is to give asynchronous sequences of values a common, stable interface in the standard library, so that libraries can depend on that interface without depending on a particular async runtime or on a particular third-party crate.

## Motivation

Synchronous iteration is a core part of Rust. The `Iterator` trait, with its `next` method, is the basis for `for` loops and for a large family of adapter methods. Asynchronous code needs a similar abstraction for sequences whose elements become available over time, such as network messages, timer ticks, or the lines of a file read without blocking.

Today the ecosystem provides this abstraction through the `Stream` trait in the `futures` family of crates. The trait is widely used, and many libraries expose streams in their public APIs. However, because the trait is defined outside the standard library, libraries that want to offer an asynchronous sequence must choose a dependency on that crate, and users must agree to that choice. A library that wants to be runtime-agnostic has to rely on a crate that was not designed by the language team.

Standardizing the trait would remove this dependency. It would let libraries expose asynchronous sequences using a type the language itself defines, and it would let the crates in the ecosystem build their adapters on the same foundation. The RFC argues that this is the natural next step after the stabilization of `async` and `await` syntax, since those features make it possible to write asynchronous iteration in a way that is pleasant to read.

## Guide-level explanation

An asynchronous iterator is a value that can produce a sequence of items, one at a time, where producing each item may require waiting. The trait has an associated type for the item, and a method that attempts to produce the next item. Because the method may need to wait, it returns a future that resolves to an optional item. A `None` result signals that the sequence has ended.

A user who has written synchronous iteration will find the shape familiar. A function that returns an asynchronous sequence of lines might be written like this:

```rust
async fn read_lines(path: &str) -> impl AsyncIterator<Item = String> {
    // a stream of lines produced as the file is read
}
```

Consumers can then loop over the sequence with a dedicated syntax, or they can call adapter methods such as `map`, `filter`, and `take`, in the same way they would for a synchronous iterator. The details of the loop syntax are outside the scope of this RFC and are being discussed separately.

## Reference-level explanation

The trait is defined with an associated type `Item`, and a single required method that takes a pinned mutable reference to the iterator and a context for waking, and returns a poll result. The poll result indicates whether an item is ready, whether the sequence has ended, or whether the caller must wait. The design follows the `Stream` trait in `futures-core` so that existing implementations can be carried over with minimal change.

The RFC specifies that the trait should be object-safe where the design allows it, so that asynchronous iterators can be stored behind a trait object. It also specifies that the trait should provide a provided method, sometimes called `next`, that returns a future for the next item, so that most callers do not need to deal with the lower-level polling interface directly.

Implementations must respect the usual rules for pinning and waking. An implementation that returns `Pending` must arrange for the task to be woken when the item may be ready, and it must not return `Ready` with an item unless the item is actually available. The RFC notes that these rules are the same as those for futures and that they are documented in the existing async chapter of the standard library documentation.

### Standard library changes

The trait is added to a new module in the standard library and is exported through the appropriate public path. The `futures-core` crate is updated so that its `Stream` trait is a re-export of the standard library's `AsyncIterator`, or so that the two are otherwise unified. The RFC states that this change should be done in a way that preserves the existing public names, so that code that refers to `Stream` continues to compile.

The RFC does not add adapter methods to the standard library in this step. Adapters are left to the ecosystem, with the expectation that the most common ones will be considered for standardization later.

## Drawbacks

The main drawback is that the standard library would take on a trait whose design has not yet been exercised in all of the situations that the ecosystem has explored. Once stabilized, changes to the trait would be difficult, and any mistake in its shape would be visible to all users.

A second drawback is that the RFC commits the project to a particular interpretation of the pinning and waking rules before some of the related language features are finished. If the language later provides a more ergonomic way to write asynchronous iteration, the trait may need to be used differently or may be overshadowed.

A third concern is that the trait's name may cause confusion with the `Stream` name that many users already know. The RFC addresses this by keeping `Stream` as a re-export for compatibility, but users will need to learn that the two names refer to the same concept.

## Rationale and alternatives

The main alternative is to leave the trait in the ecosystem and to rely on the `futures` crates indefinitely. This keeps the standard library smaller and avoids premature standardization, but it leaves libraries dependent on an external crate for a basic abstraction, and it complicates the design of runtime-agnostic code.

A second alternative is to standardize a different trait, designed from scratch to fit the language's newer features. The RFC rejects this because the `futures` design is already widely used and tested, and because a new design would fragment the ecosystem for a long period while the two competed.

A third alternative is to wait for the language to provide a general mechanism for asynchronous iteration, such as a generator syntax, before standardizing the trait. The authors considered this but argued that the trait is useful on its own, and that the language mechanism can be built on top of it.

## Prior art

Many languages provide a sequence abstraction whose elements are produced asynchronously, often under a name that reflects the idea of a stream of values. The `futures` crate's design is informed by those examples and by the experience of building asynchronous network services in Rust. The RFC relies on the ecosystem's experience as its main evidence that the design is workable.

## Unresolved questions

The RFC leaves several details open. The exact name of the trait is one of them, since the RFC proposes `AsyncIterator` but acknowledges that the name is still under discussion. The precise set of provided methods is another, since the RFC proposes only the minimum needed for basic use. The interaction with the planned syntax for consuming asynchronous sequences in loops is also deferred, because that syntax is being designed in a separate effort.

## Future possibilities

If the trait is stabilized, the next step would be to consider standard adapters such as `map`, `filter`, and `fold`, and to consider whether a dedicated loop syntax should be provided. The RFC notes that these additions would be additive and would not change the basic trait. It also notes that a general mechanism for writing asynchronous sequences with ordinary control flow would make many hand-written implementations unnecessary.

## Conclusion

Introducing `AsyncIterator` into the standard library would give asynchronous sequences a common, stable definition, and would let libraries expose them without depending on an external crate. The design follows the `futures` ecosystem's established `Stream` trait, which keeps migration simple. The RFC recommends that the trait be added with the minimal set of methods, that the `Stream` name be kept as a re-export, and that the adapter and syntax questions be handled in follow-up work.
