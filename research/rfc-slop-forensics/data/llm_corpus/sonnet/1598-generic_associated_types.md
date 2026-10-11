# Rust RFC 1598: Generic Associated Types

- Feature Name: `generic_associated_types`
- Start Date: 2016-04-29
- RFC PR: rust-lang/rfcs#1598
- Rust Issue: rust-lang/rust#44265

## Summary
[summary]: #summary

Allow type constructors to be associated with traits. This is an incremental step toward a more general feature commonly called "higher-kinded types," which is often ranked highly as a requested feature by Rust users. This specific feature (associated type constructors) resolves one of the most common use cases for higher-kindedness, is a relatively simple extension to the type system compared to other forms of higher-kinded polymorphism, and is forward compatible with more complex forms of higher-kinded polymorphism that may be introduced in the future.

## Motivation
[motivation]: #motivation

Rust traits can have associated types, which let a trait refer to a type chosen by each implementor. For example, `Iterator` has an `Item` type. But an associated type is a single, fixed type for each implementation. It cannot be parameterized: there is no way to say "for every lifetime `'a`, there is a type `Item<'a>`," nor "for every type `T`, there is a type `Pointer<T>`."

Two families of problems follow from this limitation.

### Streaming iterators

The standard `Iterator` trait cannot express an iterator whose items borrow from the iterator itself. Consider an iterator that reads lines from a file into a reused buffer, handing out a slice of the buffer on each call:

```rust
trait StreamingIterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
}
```

With this definition, `Item` must be a single type. For a buffer-backed implementation, the natural item is `&'a str`, where `'a` is the lifetime of the borrow of `&mut self` in the call to `next`. But `'a` differs on every call, and there is no way to name it in the trait: `Self::Item` cannot depend on the lifetime of the `&mut self` argument. The trait as written forces `Item` to borrow from something with a fixed lifetime, and so cannot express this pattern.

What we want to write is:

```rust
trait StreamingIterator {
    type Item<'a>;
    fn next<'a>(&'a mut self) -> Option<Self::Item<'a>>;
}
```

Here, `Item` is a type constructor that takes a lifetime. An implementation can supply a different type for each lifetime:

```rust
impl<'buf> StreamingIterator for Lines<'buf> {
    type Item<'a> = &'a str;
    fn next<'a>(&'a mut self) -> Option<&'a str> { ... }
}
```

This pattern is the single most commonly cited example. The inability to write it is a well-known limitation in Rust's standard library, where `Iterator` cannot support windows over mutable slices, or lending iterators over buffers.

### Pointer families and abstraction over containers

The second family involves abstraction over type constructors with type parameters. A library wishing to be generic over reference-counted pointers, `Rc` and `Arc`, cannot write a trait to describe "a pointer type constructor," since `Rc` and `Arc` are not types but type constructors.

With associated type constructors:

```rust
trait PointerFamily {
    type Pointer<T>: Deref<Target = T>;
    fn new<T>(value: T) -> Self::Pointer<T>;
}

struct RcFamily;
struct ArcFamily;

impl PointerFamily for RcFamily {
    type Pointer<T> = Rc<T>;
    fn new<T>(value: T) -> Rc<T> { Rc::new(value) }
}

impl PointerFamily for ArcFamily {
    type Pointer<T> = Arc<T>;
    fn new<T>(value: T) -> Arc<T> { Arc::new(value) }
}
```

A data structure can then be written once and parameterized by `P: PointerFamily`, so that a persistent collection can be backed by either `Rc` or `Arc` depending on whether thread safety is required.

Similarly, a trait for collections can describe the collection type with a different element type:

```rust
trait Collection {
    type Of<T>;
    fn empty<T>() -> Self::Of<T>;
    fn push<T>(c: &mut Self::Of<T>, t: T);
}
```

## Detailed design
[design]: #detailed-design

### Syntax

An associated type declaration in a trait may be followed by a list of generic parameters, which may be lifetimes, types, or both, with optional bounds and a `where` clause:

```rust
trait Foo {
    type Bar<'a, T>: Display where T: Clone;
}
```

An implementation provides a matching definition:

```rust
impl Foo for Baz {
    type Bar<'a, T> = &'a T where T: Clone;
}
```

The parameters on the implementation's declaration must match the trait's in number and kind. Bounds in the impl must be no stricter than the trait's declaration.

Uses of the associated type supply arguments:

```rust
fn f<F: Foo>(x: F::Bar<'static, u32>) { }
```

### Type equality and projection

An associated type constructor application `<T as Trait>::Assoc<Args>` is a projection type, a generalization of today's projections. It normalizes to the type given in the implementation, substituting the arguments, when `T` is known to be an implementation.

Bounds may mention the constructor:

```rust
fn g<I>(iter: I) where I: for<'a> StreamingIterator<Item<'a> = &'a str> { }
```

The equality constraint `Item<'a> = &'a str` is allowed and means the projection is equal to `&'a str` for every `'a`. Because the quantification over `'a` is higher-ranked, this syntax requires `for<'a>` in most positions.

### Well-formedness

A declaration `type Bar<'a>` introduces an infinite family of types, one per lifetime. The compiler must be able to determine, for each use, whether it is well-formed. A use `Self::Bar<'x>` is well-formed whenever `Self: Trait` and the arguments satisfy the declared bounds and `where` clauses. In the impl, the definition's right-hand side must be well-formed for every instantiation allowed by the clauses.

### Object safety

A trait with an associated type constructor is not object safe, as the type constructor cannot be fixed by a trait object. This restriction can be relaxed later.

### Defaults

Associated type defaults remain unstable and are not extended in this RFC.

### Interaction with the trait system

The central implementation work is in the trait solver. Projection normalization must handle bound variables and substitutions, and the solver must treat `Assoc<'a>` for distinct `'a` as potentially different types. Lifetimes are erased after type checking, so they do not affect code generation, and in the lifetime-only case no new monomorphization issues arise. The type-parameter case has no new codegen issues either, since each application is substituted at monomorphization.

## How We Teach This
[how-we-teach-this]: #how-we-teach-this

Introduce the feature as "associated types that take parameters." Lead with the lending iterator example, since it is concrete and motivates the lifetime form, then show the pointer family as the type-parameter case.

The Rust reference gains a section documenting the syntax and well-formedness rules. The error messages for mismatched parameters between trait and impl should name both declarations.

## Drawbacks
[drawbacks]: #drawbacks

- Increased complexity in the trait solver, with the risk of compile-time cost and subtle inference limitations, in particular around higher-ranked bounds.
- The feature adds a surface area of syntax and rules that learners must understand. Most users will not need it, but library authors will encounter it through APIs that use it.
- There is pressure toward further generalization, such as full higher-kinded types, and some worry that a partial feature will constrain future design. The RFC argues that it is forward compatible.

## Alternatives
[alternatives]: #alternatives

**Full higher-kinded types.** A more general mechanism would let traits abstract over arbitrary type constructors, such as `trait Functor<F<_>>`. This is considerably more complex to implement and interacts with inference in difficult ways. Associated type constructors cover the most common cases with much less machinery.

**Workarounds with extra traits.** Programmers can emulate lending iterators using a helper trait with a lifetime parameter on the trait itself, `trait StreamingIterator<'a>`, and a higher-ranked bound `for<'a> StreamingIterator<'a>`. This works in limited cases but is verbose, leaks into every signature, and fails to compose.

**Do nothing.** Libraries continue to avoid the patterns or use unsafe code.

## Unresolved questions
[unresolved]: #unresolved-questions

- How should `where` clauses on associated type constructors be checked when a trait is used generically?
- Should type constructors be allowed to be partially applied?
- What is the best way to relax object safety for traits whose type constructors have defaults?
