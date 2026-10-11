# RFC 2996: async_iterator

- Feature Name: `async_iterator`
- Start Date: 2020-09-29
- RFC PR: rust-lang/rfcs#2996
- Rust Issue: rust-lang/rust#79024

## Summary

Introduce the `AsyncIterator` trait into the standard library, using the design from `futures`. Redirect the `Stream` trait definition in the `futures-core` crate (which is "pub-used" by the `futures` crate) to the `AsyncIterator` trait in the standard library.

## Motivation

Async/await allows users to write asynchronous code that looks like synchronous code, and `Future` is the core abstraction beneath it. A `Future` produces exactly one value. Many asynchronous problems, however, are naturally modeled as a sequence of values that arrive over time: network packets on a socket, messages from a channel, lines read from a file, events from a user interface, or items in a paginated API response. The synchronous counterpart of this idea is `Iterator`, and the missing piece is its asynchronous analogue.

The ecosystem has had one for years. The `futures` crate defines `Stream`, and `tokio`, `async-std`, `hyper`, `tonic` and many others build on it. Its de facto status is strong enough that most async code that deals with sequences uses it. But `Stream` lives outside the standard library, and that has several consequences:

- Libraries that want to expose an asynchronous sequence must depend on `futures-core` for the trait. This is a small dependency, but it is a dependency, and the version of the trait becomes part of their public interface.
- The language cannot offer syntax or desugaring for asynchronous sequences until the trait is in `std`. Proposals for `for await` loops and async generators require a trait to target. Without a standard one, the compiler would need to depend on a crate, which it cannot.
- Learners meet `Iterator` in the standard library, `Future` in the standard library, and `Stream` in a third-party crate, with a different naming convention. The asymmetry suggests that it is an optional extra rather than part of the model.
- Runtimes and library authors who want to write generic code over asynchronous sequences cannot rely on a single trait that all of them share without choosing the `futures` crate.

Stabilizing the trait now, in the form the ecosystem already uses, is the smallest step that resolves these problems and that is also low-risk.

## Guide-level explanation

An `AsyncIterator` is a value that can produce a sequence of items asynchronously. Where `Iterator::next` returns `Option<Item>` immediately, `AsyncIterator::poll_next` returns a `Poll<Option<Item>>`:

- `Poll::Pending` means the next item is not ready; the task has been registered to be woken when it is.
- `Poll::Ready(Some(item))` means an item is available.
- `Poll::Ready(None)` means the sequence has ended.

Most users will not call `poll_next` directly. They will use combinators, provided by library crates, and the `next` method:

```rust
use futures::StreamExt;

async fn sum(mut values: impl AsyncIterator<Item = u32> + Unpin) -> u32 {
    let mut total = 0;
    while let Some(v) = values.next().await {
        total += v;
    }
    total
}
```

The `next` method, an extension in `futures`, returns a future that resolves to the next item. Combinators such as `map`, `filter` and `buffered` are provided in extension traits, as they are for `Iterator`.

Implementing the trait by hand is similar to implementing `Future`:

```rust
struct Countdown(u32);

impl AsyncIterator for Countdown {
    type Item = u32;

    fn poll_next(mut self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<Option<u32>> {
        if self.0 == 0 {
            Poll::Ready(None)
        } else {
            self.0 -= 1;
            Poll::Ready(Some(self.0))
        }
    }
}
```

The `Pin<&mut Self>` receiver allows asynchronous sequences that hold self-referential state, as async blocks do.

After this RFC, a crate that currently uses `futures::Stream` keeps working without code changes. The name `Stream` continues to be exported from `futures-core` and refers to the same trait as `std::async_iter::AsyncIterator`. Implementations written for `Stream` become implementations of `AsyncIterator` and vice versa.

## Reference-level explanation

The following trait is added to `core` and re-exported from `std`, in a new module `core::async_iter`:

```rust
pub trait AsyncIterator {
    type Item;

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>>;

    fn size_hint(&self) -> (usize, Option<usize>) {
        (0, None)
    }
}
```

The semantics match those of `Stream`:

- After `poll_next` returns `Poll::Ready(None)`, calling it again may panic, block forever, or return `Poll::Ready(None)` again. Callers must not rely on any particular behavior; an adaptor `fuse` is provided for that purpose in `futures`.
- `Poll::Pending` implies that the context's waker has been stored, and will be woken when more progress can be made, as for `Future::poll`.
- `size_hint` has the same meaning as for `Iterator::size_hint`.

The trait is implemented for `Pin<P>` where `P: DerefMut` and `P::Target: AsyncIterator`, for `&mut S where S: AsyncIterator + Unpin + ?Sized`, and for `Box<S>` under the same conditions as `Future`. There is also a blanket implementation for `AssertUnwindSafe<S>`.

The trait is *dyn-compatible*, so `Pin<Box<dyn AsyncIterator<Item = T>>>` can be used as a type-erased sequence.

### Relationship with `futures-core`

`futures-core` 0.3 currently defines `pub trait Stream`. To preserve compatibility, a future release will replace this definition with `pub use core::async_iter::AsyncIterator as Stream`, once the standard library trait is stable. Because the two traits are identical in methods and associated types, existing implementations and bounds continue to work. This depends on the library's minimum supported Rust version being raised to the one in which the trait is stabilized; until then, `futures-core` may use a conditional build script to select either definition. The `futures` crate's combinators remain in `StreamExt`, which are bounded on the same trait.

### What this RFC does not include

Only the core trait is included. This RFC does not add:

- Any combinators or extension methods, such as `next`, `map` or `collect`. These continue to be provided by libraries. A later RFC may add selected methods.
- Syntax such as `for await` loops or async generator blocks.
- Async fn in traits as part of the interface, such as an `async fn next(&mut self)` signature. Using `poll_next` avoids a dependency on that feature and leaves the door open for it.
- A `FromAsyncIterator` or `IntoAsyncIterator` trait. These may follow once their design is settled.

## Drawbacks

Standardizing a trait fixes its shape. If better designs emerge, for example one that uses `async fn next` directly or a lending variant that yields items borrowed from the iterator, the standard library will have a trait that is less than ideal. Because it would be difficult to change `AsyncIterator` once stabilized, any future improvement would have to be an additional trait. This is also true of `Iterator`, which has had no major change in its signature since 1.0.

The name is a departure from `Stream`, which is the established term in the ecosystem and in other languages. Having two names for one trait could confuse users, particularly as documentation and tutorials mix the two.

Poll-based interfaces are low-level and difficult to implement correctly by hand, and manually written `poll_next` implementations are a frequent source of bugs. Without generators, which are not part of this RFC, the burden falls on the combinator libraries and on `async-stream`-style macros.

## Rationale and alternatives

**Why this design?** It is the one that is in use. Choosing it means no migration for the ecosystem and gives the language a stable foundation for generators and `for await`. It has been exercised across several years of production use.

**Why `AsyncIterator` rather than `Stream`?** The name connects the trait to its synchronous counterpart, as with `Read` and `AsyncRead`. In keeping with the language's naming of related concepts, it makes the relationship clear to learners. The `Stream` name remains available as an alias in `futures-core`, so no code breaks.

**Alternative: wait for async fn in traits and lending iterators.** A trait defined as `async fn next(&mut self) -> Option<Self::Item>` is simple to read and write. It would, however, block on language features that are not yet stable, and it could not express the polling behavior needed for manual combinators and for use with `select!`. A later `async fn`-based trait can be layered on top of `poll_next`.

**Alternative: do nothing.** The ecosystem continues to work, but the language remains unable to provide syntax for asynchronous iteration, and the divide between `Iterator` and `Stream` persists in teaching.

**Alternative: include the combinators now.** This would increase the size of the commitment and the review burden. The decision to add them is better made after real experience with the trait in std.

## Prior art

Python's `async for` and `__aiter__`/`__anext__` protocol, JavaScript's async iterators and `for await...of`, C#'s `IAsyncEnumerable<T>`, and Kotlin's `Flow` all provide an asynchronous sequence abstraction with language syntax. In Rust, the `futures` crate's `Stream`, along with `tokio-stream` and `async-std`'s extensions, form the existing implementation. Earlier versions of `futures` (0.1) defined `Stream` with an associated `Error` type, later dropped in favor of `Result` items. The current design is the result of that experience.

## Unresolved questions

Should the module be called `async_iter` or `stream`, and should `core::stream` be reserved for something else?

Should `size_hint` be included in the initial trait, given that it was not on the first versions of `Stream`?

Should the trait have an `IntoAsyncIterator` companion at the same time so that `for await` can be defined directly in terms of it?

How should the trait interact with a future lending variant that yields references into its own state?
