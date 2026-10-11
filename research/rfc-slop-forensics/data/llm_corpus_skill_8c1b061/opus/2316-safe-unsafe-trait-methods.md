- Feature Name: `safe_unsafe_trait_methods`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

# Summary

This RFC allows an `impl` to implement an `unsafe` method of a trait with a method that is not marked `unsafe`. We call this *overconstraining* the method in the `impl`. When the method is called on a type whose `impl` is known to be safe, the call does not need an `unsafe` block.

# Motivation

A trait method is marked `unsafe fn` when some implementations require the caller to uphold a precondition that the compiler cannot check. The marker applies to every implementation, because generic code calling the method through the trait cannot know which implementation it will reach.

Some implementations have no such precondition. Today, such an implementation must still be declared `unsafe fn`, and every call to it needs an `unsafe` block, even where the caller names the concrete type and the method cannot cause undefined behaviour for any input.

The following trait is a hypothetical illustration:

```rust
trait RawBuffer {
    /// # Safety
    /// `i` must be less than `self.len()`.
    unsafe fn get_unchecked(&self, i: usize) -> u8;
    fn len(&self) -> usize;
}

struct Checked(Vec<u8>);

impl RawBuffer for Checked {
    unsafe fn get_unchecked(&self, i: usize) -> u8 {
        self.0[i] // bounds-checked; panics instead of reading out of bounds
    }
    fn len(&self) -> usize { self.0.len() }
}
```

`Checked::get_unchecked` never has undefined behaviour, whatever `i` is, because indexing a `Vec` is checked. Even so, a caller holding a `Checked` must write:

```rust
let b = Checked(vec![1, 2, 3]);
let x = unsafe { b.get_unchecked(1) };
```

This `unsafe` block costs more than the keystrokes. Every `unsafe` block in a codebase is a place an auditor must inspect, and the block above tells the auditor that something here could be unsound when nothing could. A codebase full of such blocks makes the necessary ones harder to find.

[TODO: real traits and crates where this situation arises, with the number of unnecessary `unsafe` blocks it causes if known. A hypothetical example shows the shape of the problem but not its frequency.]

# Guide-level explanation

An `unsafe fn` in a trait declares that callers must uphold a contract. An implementation may choose not to need that contract. It does so by omitting `unsafe` from its method:

```rust
impl RawBuffer for Checked {
    fn get_unchecked(&self, i: usize) -> u8 {
        self.0[i]
    }
    fn len(&self) -> usize { self.0.len() }
}
```

The implementation now promises more than the trait requires: it is safe to call with any arguments. Code that calls the method on a value of type `Checked` can rely on that promise and needs no `unsafe` block:

```rust
let b = Checked(vec![1, 2, 3]);
let x = b.get_unchecked(1); // no `unsafe` needed
```

Code that calls the method through the trait still needs `unsafe`, because it may reach an implementation that does have a precondition:

```rust
fn first<T: RawBuffer>(t: &T) -> u8 {
    unsafe { t.get_unchecked(0) } // still required
}
```

The same holds for calls through `dyn RawBuffer` and through the fully qualified form `<Checked as RawBuffer>::get_unchecked`. [TODO: confirm that the fully qualified form is meant to require `unsafe`. One could argue that naming the concrete type is enough.]

The rule a reader needs to remember is this: whether a call needs `unsafe` depends on the method the compiler resolves the call to. If it resolves to the `impl`'s method, the `impl`'s signature decides. If it resolves to the trait's method, the trait's signature decides.

This RFC concerns `unsafe` methods, not `unsafe` traits. An `unsafe trait` is one whose implementations must uphold a contract that callers rely on, and it is implemented with `unsafe impl`. Overconstraining a method does not change whether its trait or its `impl` is `unsafe`.

# Reference-level explanation

The rules are as follows.

1. In an `impl` of a trait, a method that implements a trait method declared `unsafe fn` may be declared without `unsafe`. All other parts of its signature must match the trait method as they do today.
2. A method declared `unsafe fn` in an `impl` must still correspond to a trait method declared `unsafe fn`. This RFC does not allow the reverse, which would let an implementation add a precondition that generic callers cannot know about.
3. A call whose receiver type is known to be the implementing type resolves to the `impl`'s method, and follows the safety of the `impl`'s signature.
4. Calls through a generic parameter, a trait object, or a path naming the trait follow the safety of the trait's signature.

[TODO: the precise definition of when a call "resolves to the `impl`'s method", in terms of the compiler's method resolution. In particular, whether a method call on a concrete type whose trait is in scope counts, as in the guide example, and whether autoderef through a smart pointer to the concrete type counts.]

[TODO: whether function pointers obtained from the method, as in `let f = Checked::get_unchecked;`, have type `fn(&Checked, usize) -> u8` or `unsafe fn(&Checked, usize) -> u8`.]

[TODO: the interaction with default method bodies in the trait. A default body is part of the trait, so it remains `unsafe` for all implementors who do not override it. Confirm that this is intended.]

# Drawbacks

Removing `unsafe` from an `impl` method becomes a public promise. Downstream code that calls the method on the concrete type will drop its `unsafe` blocks. If a later version of the crate restores `unsafe` on the method, those calls stop compiling. Library authors must treat the safety of an overconstrained method as part of their semver contract. [TODO: whether the RFC proposes any lint or documentation to make this visible to library authors.]

The reverse change creates warnings in downstream code. When a library overconstrains a method that was `unsafe` before, the existing `unsafe` blocks around calls to it on the concrete type become unnecessary, and the `unused_unsafe` lint fires on each of them. This is noise for downstream maintainers, although each warning points at a block that can be removed.

The rule makes the safety of a call depend on how the call resolves. Two calls that look alike in source, one on a concrete type and one on a generic parameter bound by the same trait, need different treatment. [TODO: whether the author considers this a source of confusion worth addressing in diagnostics, for example an error message that explains why `unsafe` is required in the generic case.]

# Rationale and alternatives

The proposal treats safety the way the language already treats the rest of a method's contract: an implementation may promise more to callers who know which implementation they have. [TODO: whether the author wants to cite existing cases in Rust where an `impl` may be more permissive than its trait, and which ones. Without a confirmed precedent, this paragraph should state the principle without claiming the language already follows it.]

[TODO: the alternatives considered, with the reason each lost. Two to ask about are (a) leaving the language as it is and having library authors add an inherent safe method with the same behaviour alongside the trait method, and (b) a separate attribute on the `impl` method instead of omitting `unsafe`. Option (a) works today, so the RFC needs to say why it is not enough; one candidate reason is that the inherent method and the trait method can drift apart.]

The decision is expensive to reverse once stabilised. Libraries will publish safe implementations of `unsafe` trait methods, and downstream code will call them without `unsafe` blocks. Withdrawing the feature would break that code.

# Prior art

[TODO: prior art in other languages, if any, and in earlier Rust discussions.]

# Unresolved questions

1. Exactly which forms of call count as resolving to the `impl`'s method.
2. The type of a function pointer taken from an overconstrained method.
3. Whether rustdoc should show that an `impl` method is overconstrained, so that downstream authors can see the promise they are relying on.
