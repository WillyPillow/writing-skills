# Stabilize a reduced-scope `Duration`

## Summary

This RFC proposes to stabilize a reduced version of the `Duration` type. The reduced type covers one job: passing timeouts to system calls and to APIs that wrap them. The RFC leaves the larger set of conversion methods on `Duration` unstable. Those methods have subtle caveats, and the RFC defers them so that a later proposal can design all conversions together.

[TODO: the author's material is only the title and abstract. The method list, the representation, and the list of unstable methods below are marked wherever they are a suggestion and not part of the supplied material.]

## Context

Operating system interfaces that block, wait or poll take a timeout. The programs that call them need a value type that expresses "wait at most this long" and that can be handed to the standard library's blocking APIs. `Duration` is that type.

The type also grew a large surface of conversion methods, such as methods that turn a `Duration` into a count of some unit or build one from a count of some unit. The abstract states that these methods "have subtle caveats". The caveats are not described in the supplied material.

[TODO: list the specific caveats of the conversion methods, with one concrete example for each. Candidate topics are rounding, overflow and loss of precision, but the author must confirm which apply. They are not stated in the abstract.]

[TODO: list which standard-library APIs currently accept a `Duration` and would be affected by stabilization.]

## Goals and non-goals

Goals:

1. Users of stable Rust can express a timeout and pass it to system-call wrappers. [TODO: name the first stable APIs that need this, so a reviewer can check the goal.]
2. The stabilized surface is small enough that every method in it has no known caveat. [TODO: confirm this criterion with the author.]

Non-goals:

1. This RFC does not stabilize the conversion methods with caveats. The abstract states the intent to revisit them "more holistically in the future".
2. This RFC does not design a general-purpose time library. [TODO: confirm. A reader could reasonably expect a `Duration` to support calendar arithmetic, and the author should say whether that is excluded.]

## Design

### What is stabilized

The type stabilized is the `Duration` type itself, plus the minimum set of methods that let a program create a value, read it back and use it as a timeout.

A suggested minimum, for the author to evaluate:

- a constructor that takes whole seconds and a sub-second part;
- accessors that return those two parts;
- the standard traits that a plain value type needs, such as `Copy`, `Clone`, `Eq` and `Ord`. [TODO: confirm trait list.]

[TODO: replace the suggestion above with the actual list of stabilized items, with signatures. Show only the signatures that bear on a trade-off.]

### What stays unstable

Every conversion method that has a caveat remains behind a feature gate. The RFC does not list them here because the list belongs to the author. [TODO: enumerate the methods that remain unstable and the caveat for each.]

Keeping these methods unstable has one effect on users: code that needs them must use a nightly compiler until the follow-up proposal lands. [TODO: state whether the author considers that acceptable, and for whom.]

### Why a small stable core is the decision

The force behind the decision is that stabilization is hard to undo. A method that ships stable stays in the language's compatibility promise. Stabilizing a method whose semantics are in doubt would commit the project to semantics it may want to change.

Options:

- *Stabilize the whole type as it stands.* This gives users the full surface at once. It also commits the project to every caveat. [TODO: the author must confirm whether this option was considered and why it lost. This document does not claim that it was.]
- *Stabilize nothing and wait.* This keeps every option open. It leaves stable Rust without a timeout type. [TODO: confirm.]
- *Stabilize a reduced core, as this RFC does.* The deciding reason, based on the abstract, is that the core serves the system-call use case and carries no caveat. [TODO: confirm that this is the deciding reason and add the author's reasoning on why the conversions cannot simply be fixed in this RFC.]

### Reversibility

Stabilizing the type name and its constructor is expensive to undo, because downstream code will name the type. Leaving the conversions unstable is cheap to undo: they can be stabilized later, changed, or removed. This asymmetry supports the split. [TODO: confirm that the stabilized methods are the ones the author considers settled.]

## Drawbacks

The main cost is that users get an incomplete type. Anyone who needs a unit conversion either writes the arithmetic by hand or waits for the follow-up work. Hand-written arithmetic is the place where the caveats mentioned in the abstract would appear, so the cost may fall on exactly the users who are most exposed to them. [TODO: author to confirm or correct this reading.]

A second cost is that "revisit in the future" has no date. If the follow-up never arrives, the type stays small. [TODO: state whether the author proposes a tracking issue, an owner or a deadline.]

## Alternatives

The alternatives described under "Why a small stable core is the decision" are the whole-design alternatives. [TODO: add any other alternative the author considered, in its strongest form, with the reason it lost. For example, a different type name or a type that avoids the unit conversions entirely. These are suggestions, not recorded history.]

## Compatibility

[TODO: the supplied material makes no compatibility claim. The author should state whether stabilizing the reduced type changes any existing stable API, and whether any currently stable code calls a method that will stay unstable.]

## Rollout

1. Stabilize the items listed under "What is stabilized".
2. Leave the feature gate in place for the remaining methods.
3. Open a tracking issue for the conversion design. [TODO: confirm this step.]

Rollback: removing a stabilized item is a breaking change and is not planned. This is why the stabilized set is small.

## Unresolved questions

1. Which conversions go into the follow-up proposal, and in what order? [TODO]
2. Should the follow-up proposal change the representation, or only the method set? [TODO]
3. Which caveats can be fixed by documentation, and which need a different design? [TODO]
4. Does any platform restrict the range of timeouts it accepts, and should `Duration` say so? [TODO: the abstract speaks of "various system calls", and the author should name them.]

## Evidence

The supplied material includes no benchmark, prototype or incident. This RFC therefore rests on one argument: a smaller stable surface lowers the risk of committing to the wrong semantics. [TODO: add a concrete instance, such as a specific bug or a surprising result from one of the caveated methods, so reviewers can test the argument against a case.]

## Review notes

The disagreement test for this RFC: a reviewer who disagrees should be able to name a specific method and argue that it belongs in the stable set, or that it should be removed from it. The RFC cannot support that until the method list exists. [TODO: fill in the list.]
