# RFC 2316: safe_unsafe_trait_methods

## Summary

An `impl` may implement a trait method that the trait marks `unsafe` without marking the method `unsafe` in the `impl`. This RFC calls that *overconstraining* the method. When code calls the method on a concrete type whose `impl` is safe, the call does not need an `unsafe` block.

## Motivation

A trait can declare a method `unsafe` because some implementations need the caller to uphold a condition the compiler cannot check. Another implementation of the same trait may need no such condition. Today, the second implementation still has to declare the method `unsafe`, so every caller needs an `unsafe` block even when the concrete type is known and the call is sound.

The RFC lets the second implementation say so. Callers that use the concrete type skip the `unsafe` block. Callers that go through the trait, for example in generic code, still need it, because they cannot know which implementation they have.

[TODO: author to supply a concrete motivating case. The supplied material gives the rule but no trait, type or call site that suffers from the current behavior. Without one, a reader cannot judge how often the situation arises. This draft does not name any trait or type from the standard library or elsewhere.]

## Guide-level explanation

### An example

The following sketch shows the shape of the feature. The trait and type names are invented for illustration and do not come from the author's material.

```rust
trait Reader {
    unsafe fn read_at(&self, index: usize) -> u8;
}

struct Checked(Vec<u8>);

impl Reader for Checked {
    // Overconstrains the method: safe, because it checks the index.
    fn read_at(&self, index: usize) -> u8 {
        self.0[index]
    }
}

fn demo(c: &Checked) -> u8 {
    c.read_at(0) // no `unsafe` block needed
}

fn generic<R: Reader>(r: &R) -> u8 {
    unsafe { r.read_at(0) } // `unsafe` still required
}
```

In `demo`, the compiler knows the type is `Checked` and that its `read_at` is safe. In `generic`, the compiler knows only that `R` implements `Reader`, and the trait's method is `unsafe`.

[TODO: author to replace this sketch with their own example and to confirm that the two call sites behave as described.]

### Terminology

*Overconstraining* means that the `impl` places a stricter requirement on itself than the trait does. Here the requirement is that the method needs no caller-side precondition. The term comes from the author's material.

### What the reader should expect

A programmer who writes an `impl` can drop the `unsafe` keyword from a method whose trait declaration has it. A programmer who calls the method on a known type no longer writes `unsafe` for that call. A programmer who calls through a trait bound or trait object writes `unsafe` as before. [TODO: author to confirm the trait-object case. The abstract does not mention it.]

## Reference-level explanation

The rule has three parts.

1. An `impl` of a trait may omit `unsafe` on a method that the trait declares `unsafe`.
2. A call that resolves to such an `impl` method on a specific type is a safe call.
3. A call that resolves through the trait declaration is an unsafe call.

The abstract states the first and second parts. The third part follows from them: if the compiler cannot tell which `impl` it is calling, it must use the trait's signature. [TODO: author to confirm the third part, and to say how the compiler tracks the distinction through method resolution, associated types and `dyn Trait`.]

The reverse direction is not part of this RFC. An `impl` cannot mark a method `unsafe` when the trait declares it safe, and the abstract says nothing to change that. [TODO: author to confirm.]

### Interaction with the `unsafe_code` lint and tooling

[TODO: author to describe any effect on lints that report unused `unsafe` blocks, and on tools that read `unsafe` markers from trait declarations. The supplied material does not mention them.]

## Drawbacks

The change gives up a simple reading of the language: today, if a trait method is `unsafe`, every call that mentions it is `unsafe`. After the change, the keyword on a call site depends on which type the compiler sees. A reader who sees `x.read_at(0)` without `unsafe` has to know the type of `x`.

The change also lets an `impl` author weaken a signature without any marker at the call site. If a later edit changes an `impl` from safe to `unsafe`, callers that relied on the safe version stop compiling, which makes the safe signature part of the type's public interface. [TODO: author to say whether this is acceptable and whether it affects semver guidance. This draft does not claim that the effect is small.]

[TODO: author to list any further drawbacks they accept.]

## Rationale and alternatives

**The force.** An `impl` whose method is sound for every caller has no way to say so, and its callers pay for a precondition that does not exist. [TODO: author to describe who pays and how often.]

**Options considered.** The supplied material records only the chosen design. The author has to state what else was considered. [TODO.]

Three alternatives are suggestions for the author to evaluate, not recorded options:

* Do nothing, and let the type provide an inherent method with the same name and a safe signature. Inherent methods take precedence in method resolution, so callers on the concrete type would get the safe method.
* Split the trait into a safe trait and an unsafe trait.
* Require an explicit annotation on the `impl` method, such as an attribute, so the weakening is visible where it happens.

The third option bears on the main drawback above, so it deserves the author's answer. [TODO: deciding reason. Say why implicit overconstraining is preferable to an annotated form, if it is.]

**Reversibility.** Allowing a safe `impl` is a one-way change for libraries: once crates rely on it, removing it breaks them. This is the expensive part of the decision. [TODO: author to address.]

## Prior art

[TODO: author to supply prior art. The material does not mention other languages or earlier Rust proposals, and this draft will not cite any from memory.]

## Unresolved questions

1. How overconstraining interacts with trait objects.
2. How it interacts with default method bodies that call the `unsafe` method.
3. Whether a diagnostic should tell the user that an `unsafe` block around an overconstrained call is unnecessary.
4. Whether the documentation for `unsafe trait` methods needs a statement about overconstraining.
5. The exact set of tools that read the `unsafe` marker.

## Future possibilities

[TODO: author to supply. This draft lists none, because the supplied material proposes only the single rule above.]

## Compatibility

The change allows programs that were previously rejected. Existing programs that compile now continue to compile if the compiler treats every call as before. [TODO: author to confirm. In particular, the `unused_unsafe` lint may begin to fire on code that wrapped a call to a method that is now safe. The material does not say, so this draft makes no claim that no existing program is affected.]
