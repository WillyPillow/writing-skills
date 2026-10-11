- Feature Name: `safe_unsafe_trait_methods`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

# Summary

This RFC allows a safe implementation of an `unsafe` trait method. An `impl` may implement a trait whose methods are marked `unsafe` without marking those methods `unsafe` in the `impl`. We call this *overconstraining* the method in the `impl`. When such a method is called on a specific type for which the `impl` is known to be safe, the call does not need an `unsafe` block.

# Motivation

A trait method is marked `unsafe` when some implementations require the caller to uphold a condition that the compiler cannot check. The caller states that it upholds the condition by writing an `unsafe` block. Today every implementation must repeat the `unsafe` marker, even an implementation that requires nothing of its caller.

Consider a trait for reading a byte at an index:

```rust
trait ReadAt {
    /// # Safety
    /// `i` must be less than `self.len()`.
    unsafe fn read_at(&self, i: usize) -> u8;
    fn len(&self) -> usize;
}
```

An implementation backed by a raw pointer needs the precondition. An implementation backed by a `Vec<u8>` can check the index itself:

```rust
struct Checked(Vec<u8>);

impl ReadAt for Checked {
    unsafe fn read_at(&self, i: usize) -> u8 {
        self.0[i] // panics on an out-of-bounds index; never undefined behavior
    }
    fn len(&self) -> usize { self.0.len() }
}
```

The body of `Checked::read_at` contains no unsafe operation and is safe to call with any index. Yet the signature says `unsafe fn`, and every caller who holds a `Checked` must write

```rust
let b = unsafe { c.read_at(3) };
```

That `unsafe` block has two costs. It asks the caller to reason about a precondition that does not apply. It also adds an `unsafe` block to code that a reviewer or an audit tool must then inspect, although the block guards nothing. A codebase that counts its `unsafe` blocks, or forbids them in some modules, cannot call `Checked::read_at` at all from those modules.

The workaround today is an inherent method with a different name that the trait method forwards to. This duplicates the API surface, and the caller must know to use the inherent method instead of the trait method.

[TODO: the author should give one or two real crates or APIs where this situation occurs. This draft uses a constructed example only.]

# Guide-level explanation

When you implement a trait that has an `unsafe fn` method, you may leave off `unsafe` if your implementation is safe to call with any arguments:

```rust
impl ReadAt for Checked {
    fn read_at(&self, i: usize) -> u8 {
        self.0[i]
    }
    fn len(&self) -> usize { self.0.len() }
}
```

By leaving off `unsafe`, you promise that callers of `Checked::read_at` do not need to uphold the trait's safety precondition. The compiler holds you to that promise in the same way it holds any safe function to it: the body of a safe function may not perform unsafe operations outside an `unsafe` block.

Code that knows it has a `Checked` can then call the method without an `unsafe` block:

```rust
let c = Checked(vec![1, 2, 3]);
let b = c.read_at(1); // no unsafe block
```

Generic code does not know which implementation it has, so it still sees the trait's signature:

```rust
fn first<T: ReadAt>(t: &T) -> u8 {
    unsafe { t.read_at(0) } // still required
}
```

# Reference-level explanation

## Rule for `impl` items

For a trait method declared `unsafe fn`, an `impl` of that trait may declare the method either `unsafe fn` or `fn`. All other parts of the signature must match the trait as they do today. The reverse is not allowed: if the trait declares a safe `fn`, an `impl` may not declare it `unsafe fn`, because generic callers rely on being able to call it without an `unsafe` block.

## Rule for calls

Whether a method call needs an `unsafe` block depends on which signature the call resolves to:

1. If the call resolves to a known `impl`, because the receiver's type is concrete or the path names the `impl`'s type (for example `<Checked as ReadAt>::read_at(&c, 1)`), the compiler uses the signature written in the `impl`. A safe signature in the `impl` means no `unsafe` block is needed.
2. If the call is made through a type parameter, an associated type that has not been normalized, or a trait object, the compiler uses the signature in the trait. An `unsafe fn` in the trait means an `unsafe` block is needed.

[TODO: the author should specify the behavior for a trait object such as `&dyn ReadAt` whose concrete type is not known at compile time. This draft assumes rule 2 applies, because the compiler cannot know which `impl` will run.]

## Function pointers and `Fn` traits

Naming the method as a value, as in `<Checked as ReadAt>::read_at`, gives a function item. [TODO: the author should decide whether that item is a safe `fn` item, which coerces to `fn(&Checked, usize) -> u8`, or an `unsafe fn` item. Rule 1 suggests the former. The author should also say whether the item implements the `Fn` traits, which only safe functions do today.]

# Drawbacks

An implementation's safety becomes part of its public API. Once a crate publishes `impl ReadAt for Checked` with a safe `read_at`, downstream code calls it without `unsafe`. If the crate later changes the `impl` to `unsafe fn`, that downstream code stops compiling. Authors must therefore treat the choice to overconstrain as a semver commitment, which is a new consideration when writing an `impl`.

The signature of a trait method is no longer the whole story. A reader who looks up `ReadAt::read_at` sees `unsafe fn`, but the call `c.read_at(1)` compiles without an `unsafe` block. The reader must find the specific `impl` to understand why. [TODO: the author should say how rustdoc should display an overconstrained method, so that readers can see it without reading the source.]

The rule adds a case to method call checking. [TODO: the author should describe the implementation cost in the compiler, if known. This draft makes no claim about it.]

# Rationale and alternatives

The deciding reason for this design is that the information needed already exists in the `impl`: the implementor knows whether their body needs the precondition. Allowing them to say so in the signature lets callers who know the concrete type benefit, and does not weaken the guarantee for generic callers, who still see the trait's signature.

The following are alternatives suggested by this draft for the author to evaluate. They are not options that were recorded as considered.

- Keep the status quo, with a forwarding inherent method. This works today and needs no language change. Its cost is the duplicated API surface described in the motivation, and the caller must know the inherent method exists.
- Use an attribute instead of a signature change, for example marking the `impl` method so that a lint suppresses the "unnecessary unsafe" warning. This would not remove the `unsafe` block, which is the problem for codebases that restrict `unsafe`.
- Allow overconstraining more generally, for example letting an `impl` declare fewer `where` clauses than the trait. This RFC covers only `unsafe`. [TODO: the author should say whether a broader rule was discussed and why this RFC is limited to `unsafe`.]

[TODO: the author should record which alternatives were actually discussed and why each lost.]

# Prior art

[TODO: the author should supply prior art, such as other languages in which an override may have a narrower effect or contract than the method it overrides. This draft adds no references.]

# Unresolved questions

- How the rule applies to trait objects and to function items, as noted above.
- How rustdoc shows an overconstrained method.
- Whether a lint should suggest overconstraining when an `unsafe fn` in an `impl` contains no unsafe operations. Such a lint would also push authors into the semver commitment described under "Drawbacks", so its default level needs discussion.
- Whether the same rule should later apply to `unsafe trait` declarations or to other qualifiers on `fn`, such as `const`. This RFC does not propose either.
