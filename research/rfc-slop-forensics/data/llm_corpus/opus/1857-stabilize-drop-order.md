- Feature Name: stable_drop_order
- Start Date: 2017-01-19
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

I propose we specify and stabilize drop order in Rust, instead of treating it as an implementation detail. The stable drop order should be based on the current implementation. This results in avoiding breakage and still allows alternative, opt-in, drop orders to be introduced in the future.

# Motivation

The order in which values are dropped is observable. Any `Drop` implementation with a side effect, whether it prints a message, releases a lock, flushes a buffer, or frees memory that another value points into, can tell which value was dropped first. In practice, a great deal of real Rust code depends on drop order:

- RAII guards. A `MutexGuard` stored next to data that must be written while the lock is held depends on the guard being dropped after the write is complete.
- Self-referential structures built with `unsafe`. A struct that holds both an arena and references into that arena must drop the references before the arena.
- FFI wrappers. A struct holding a library context and a handle obtained from it must close the handle before destroying the context.
- Tests that assert on the order of logged events.

The Reference currently says that drop order is unspecified, and some documentation has described it as subject to change. Despite this, the order has not changed since before 1.0, and people rely on it, often without knowing they are doing so. A change would cause silent misbehaviour, sometimes memory unsafety in `unsafe` code, and would not be detected by the compiler. In other words, the order is already de facto stable. Specifying it acknowledges reality and lets people reason about their code with confidence.

There have been proposals to change the order of struct field drops to reverse declaration order, to match how local variables are dropped. Whatever the merits of that order, changing it now would break code silently. This RFC argues that the cost of such a change outweighs the benefit of consistency, and that the right path is to document the current behaviour.

# Detailed design

The following rules describe the current behaviour of rustc. This RFC proposes that they become part of the language specification.

## Local variables

Local variables are dropped in reverse order of declaration when they go out of scope.

```rust
let a = Noisy("a");
let b = Noisy("b");
// at end of scope: drops b, then a
```

Function arguments are treated as locals declared in order, and are dropped in reverse order after all locals in the function body.

Temporaries are dropped at the end of the enclosing statement, in reverse order of creation, except where temporary lifetime extension applies, in which case they are dropped as if they were locals declared at that point.

## Struct fields

The fields of a struct are dropped in declaration order, first to last, after the struct's own `Drop::drop` has run (if it implements `Drop`).

```rust
struct Pair {
    first: Noisy,
    second: Noisy,
}
// dropping a Pair drops `first`, then `second`
```

Note that this is the opposite of local variables. The asymmetry is historical, and this RFC preserves it.

## Tuples

Tuple elements are dropped in order, first to last, like struct fields.

## Enum variants

The fields of the active variant of an enum are dropped in declaration order, like a struct.

## Arrays and slices

Elements of an array `[T; N]` are dropped in order, from index 0 to index N-1. Owned slices such as `Box<[T]>` and `Vec<T>` drop their elements in index order. For `Vec`, this is a property of its `Drop` implementation, which this RFC also proposes to document as stable.

## Closures

Variables captured by a closure are dropped in an order that is currently determined by the order in which they appear in the closure body. This order is less obvious to users and depends on capture analysis. This RFC proposes to specify it as the order of first mention in the closure body, matching the current implementation, but notes that future changes to capture analysis (for example capturing disjoint fields) would need to consider this.

## Partial moves

If some fields of a struct or tuple have been moved out, only the remaining fields are dropped, in their usual relative order.

## Panics during drop

If a destructor panics while a value is being dropped, the remaining fields of the value are still dropped, in their usual order, during unwinding. If a second panic occurs during that unwinding, the process aborts, as it does today.

# How we teach this

The Reference should gain a section on destructors that lists the rules above. The Book's chapter on `Drop` should mention that locals are dropped in reverse order and fields in forward order, and should show an example where the order matters, such as a guard and the data it protects.

A useful rule of thumb for users: "the thing you declared last in a scope goes away first; the fields of a struct go away top to bottom." Users who need a particular order between fields should either declare the fields in that order, or, for clarity, wrap them in `ManuallyDrop` and drop them explicitly in the struct's `Drop` implementation.

# Drawbacks

- The resulting rules are inconsistent: locals drop in reverse, fields drop forward. Locking this in means newcomers will always have to learn both.
- Specifying the order removes freedom from the compiler. An optimizing compiler might in principle want to reorder drops of values with trivial or independent destructors. In practice the compiler can still do so when it can prove there is no observable difference, as with any other optimization.
- The closure capture order is somewhat arbitrary, and specifying it may constrain future work on closure capture.

# Alternatives

## Change field drop order to reverse declaration order

This would make fields consistent with locals, and would match C++, where members are destroyed in reverse order of construction. However, it would silently change the behaviour of existing programs. Because drop order is not checked by the type system, there is no reliable way for the compiler to warn about code that would be affected. A crater run can find tests that fail, but not programs that merely leak or corrupt memory in production.

One could imagine a migration path with an attribute such as `#[drop_order(reverse)]` to opt in, followed by a lint encouraging its use, followed by a flip of the default. This is a lot of churn for a cosmetic benefit, and every step requires authors to audit their types.

## Leave drop order unspecified

This is the status quo. It forces careful authors to write defensive code (often with `ManuallyDrop` or `Option` plus manual `take()`), and leaves careless authors with code that works only by accident. It also does not, in practice, give the compiler any freedom, because changing the order would break too much.

## Specify only some cases

For example, specify locals but leave fields unspecified. This would not help the most common unsafe patterns, which involve fields.

# Future possibilities

Specifying the default does not prevent future opt-in mechanisms for other orders. An attribute on a struct requesting reverse-order drop, or a derive that generates a custom `Drop`, could be added later without affecting code that does not use it. Because the default is fixed, such additions are purely additive.

# Unresolved questions

- Should the order of captured variables in closures be specified now, or deferred until the design of disjoint-field capture is settled?
- Should `Vec`, `VecDeque` and other standard collections have their element drop order documented as part of this RFC, or separately by the libs team?
