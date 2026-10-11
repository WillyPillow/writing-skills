- Feature Name: `async_iterator`
- Start Date: 2020-09-29
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Add an `AsyncIterator` trait to the standard library, using the design of the `Stream` trait from the `futures` crate. Then change the `futures-core` crate, which `futures` re-exports, so that its `Stream` trait is a re-export of the standard library's `AsyncIterator`.

# Motivation

`Iterator` is one of the most widely used traits in Rust. It gives a common interface for "a sequence of values", and a large set of adapters and consumers is built on top of it. Asynchronous code needs the same thing for sequences whose values arrive over time: lines from a socket, messages from a channel, rows from a database cursor, events from a UI.

The ecosystem already has an answer. The `Stream` trait in `futures-core` has been in use for years, and almost every async library either implements it or consumes it. But because it lives outside the standard library:

- **It cannot be used by `std` itself.** Async-related types that may land in `std`, such as channels or a future `async fn` in traits, have no common trait for "async sequence" to implement.
- **It cannot get language support.** Proposals for `for await` loops and async generators need a trait the compiler knows about. That trait has to live in `core`.
- **It splits the ecosystem.** Some runtimes define their own similar traits, partly to avoid depending on `futures`. Users then write adapters between them.

Putting the trait in `core` gives everyone a single, stable definition to build on. Starting with the trait alone, and leaving adapters and syntax to later RFCs, keeps this step small enough to land and stabilize.

# Guide-level explanation

An async iterator is like an iterator, except that asking for the next item may need to wait. Instead of `next` returning `Option<Item>`, `poll_next` returns `Poll<Option<Item>>`:

- `Poll::Ready(Some(item))`: here is the next item.
- `Poll::Ready(None)`: the sequence is finished.
- `Poll::Pending`: no item yet. The iterator has arranged for the task to be woken when it should be polled again.

Most users will not call `poll_next` directly. Libraries such as `futures` provide a `next()` method that returns a future, so you can write:

```rust
use futures::stream::StreamExt;

while let Some(line) = lines.next().await {
    println!("{}", line?);
}
```

Implementing the trait looks like implementing a future that can complete many times:

```rust
use core::async_iter::AsyncIterator;
use core::pin::Pin;
use core::task::{Context, Poll};

struct Countdown(u32);

impl AsyncIterator for Countdown {
    type Item = u32;

    fn poll_next(mut self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<Option<u32>> {
        if self.0 == 0 {
            Poll::Ready(None)
        } else {
            self.0 -= 1;
            Poll::Ready(Some(self.0 + 1))
        }
    }
}
```

Existing code that implements or uses `futures::Stream` does not change. After `futures-core` re-exports the standard trait, `Stream` and `AsyncIterator` are the same trait under two names.

# Reference-level explanation

## The trait

```rust
// core::async_iter
pub trait AsyncIterator {
    type Item;

    fn poll_next(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>>;

    #[inline]
    fn size_hint(&self) -> (usize, Option<usize>) {
        (0, None)
    }
}
```

`size_hint` has the same meaning as on `Iterator`: a lower bound and optional upper bound on the number of remaining items. It is a hint only and must not be relied on for safety.

After `poll_next` returns `Ready(None)`, further calls may do anything except cause undefined behavior, as with `Iterator::next`. A separate fused marker can be added later.

## Blanket implementations

```rust
impl<S: ?Sized + AsyncIterator + Unpin> AsyncIterator for &mut S { ... }
impl<P> AsyncIterator for Pin<P>
where P: DerefMut + Unpin, P::Target: AsyncIterator { ... }
```

In `alloc`:

```rust
impl<S: ?Sized + AsyncIterator + Unpin> AsyncIterator for Box<S> { ... }
```

These match the implementations `futures-core` provides today, so that moving the trait does not remove any impls users rely on.

## Migration of futures-core

Once the trait is stable, `futures-core` will, behind a version check, replace its trait definition with:

```rust
pub use core::async_iter::AsyncIterator as Stream;
```

Because the trait has the same methods, signatures and blanket impls, this is not a breaking change for implementers or consumers. The `futures` maintainers have agreed to this plan. Extension traits such as `StreamExt` stay in `futures` and keep working, since they are implemented for all `T: Stream`.

## Naming

The trait is named `AsyncIterator`, not `Stream`. "Stream" is overloaded: `std::io` already uses it informally for byte streams, and `TcpStream` is not a `Stream` in this sense. `AsyncIterator` says what the trait is, and it lines up with planned names such as `async_iter::from_iter` and a future `IntoAsyncIterator`.

# Drawbacks

- The `poll_next` design may not be the final shape of async iteration in Rust. Once `async fn` in traits is available, a design based on `async fn next(&mut self)` might be preferable. Stabilizing `poll_next` now commits `core` to supporting it permanently, even if a different interface becomes the preferred one.
- Adding the trait without adapters leaves it awkward to use from `std` alone. Users will still reach for `futures` or a runtime crate for combinators.
- Two names for one trait (`Stream` in the ecosystem, `AsyncIterator` in `std`) may confuse people for a while.

# Rationale and alternatives

**Wait for `async fn` in traits.** A trait with `async fn next(&mut self) -> Option<Item>` would be friendlier to implement. But that feature is years away and has open design questions, especially around object safety and `Send` bounds. The poll-based design is what the ecosystem uses today, and it is the lowest-level form; an `async fn next` layer can be provided on top of it later.

**Add adapters now.** `map`, `filter`, `buffer_unordered` and friends are useful but raise many questions: which ones, how they handle concurrency, and how they interact with cancellation. Keeping them out lets the trait land without settling those questions.

**Keep the name `Stream`.** Rejected for the reasons above, though the alias in `futures-core` keeps existing code readable.

**Do nothing.** The ecosystem keeps working, but `for await`, async generators and any `std` async types stay blocked.

# Prior art

- The `futures` crate's `Stream`, on which this design is based.
- JavaScript's async iterators and `for await...of`.
- C#'s `IAsyncEnumerable<T>` and `await foreach`.
- Python's `__aiter__`/`__anext__` and `async for`.

All of them pair an async sequence trait with dedicated loop syntax, which supports putting the trait in the core library first.

# Unresolved questions

- Should `poll_next` be the only required method, or should a provided `next()` returning a future be added now?
- Should `AsyncIterator` and `Iterator` be connected, for example with a blanket impl for `Iterator` types wrapped in an adapter?

# Future possibilities

`for await` loops, async generator syntax, an `IntoAsyncIterator` trait, and a standard set of combinators.
