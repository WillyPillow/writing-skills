# Rust RFC 1040: duration

## Summary

Stabilize a reduced `Duration` type: enough to pass a timeout to a system call, and nothing more. Leave unstable the conversion methods whose behavior has subtle caveats, and revisit them together in a later RFC.

## Motivation

Standard library APIs that block on the operating system need a way to say "give up after this long". Sockets, thread parking, condition variables, and process waits all take a timeout. Until `Duration` is stable, a stable signature cannot name its timeout parameter, so each of these APIs either stays unstable or takes a raw integer whose unit the caller must guess.

The type itself is small. A caller builds a `Duration` from a count of seconds, milliseconds or nanoseconds, passes it to a blocking call, and the library hands it to the OS. That path needs a constructor, a way to read the value back, and a few arithmetic operations. It does not need the full set of conversions to and from other numeric types and other clocks that the unstable `Duration` currently carries.

Those conversions are the reason stabilization has stalled. A conversion from a `Duration` to a floating-point number of seconds loses precision at large values. A conversion to an integer number of milliseconds has to choose between truncating and rounding the sub-millisecond part. A conversion from a signed integer has to decide what a negative span means. Each of these has more than one defensible answer, and the answers interact: a method that rounds in one direction makes a round trip through another method lossy.

[TODO: list the exact methods currently on the unstable `Duration`, grouped into the ones this RFC stabilizes and the ones it defers.]

Stabilizing a method fixes its behavior for every later release of the language. A wrong choice in a conversion would be visible to every user who relied on it, and it could not be changed without breaking them. That cost is the reason this RFC proposes to stabilize less than the type currently offers.

## Detailed design

### What becomes stable

The type `Duration` becomes stable, along with the operations a timeout API needs:

1. A constructor taking whole seconds and a constructor taking whole milliseconds.
2. [TODO: confirm whether a nanosecond constructor is in scope.]
3. Accessors that return the whole-seconds part and the sub-second part separately.
4. Addition and subtraction, with the behavior on overflow and underflow stated in the documentation.
5. The comparison and copy traits that let a `Duration` be stored in a struct and checked against a deadline.

The accessors return the two parts separately on purpose. A caller who needs one number can combine them with the rounding rule the caller wants. The library never has to pick a rule on the caller's behalf.

[TODO: state the panic or saturation behavior of subtraction when the result would be negative, and name the existing precedent in the standard library that this follows.]

### What stays unstable

The following groups remain behind the feature gate:

- Conversions to and from floating-point seconds.
- Conversions to a single integer count of milliseconds, microseconds or nanoseconds.
- Multiplication and division of a `Duration` by a scalar.
- Any conversion that depends on the platform's clock representation.

[TODO: confirm which of these groups exist on the unstable type today, and add any that are missing from this list.]

Each group has at least one open question about rounding, range or sign. The RFC does not try to answer them. A follow-up RFC takes up the whole set at once, so that the methods in it agree with each other.

### Interaction with system calls

A timeout passed to the OS usually has a fixed unit and a fixed integer width. The standard library converts a `Duration` into that unit inside the implementation of the blocking call. When the value does not fit, the implementation clamps to the largest value the OS accepts, which is a longer wait than the caller asked for only if the caller asked for something the OS cannot express.

[TODO: confirm the clamping rule and whether it matches what the existing unstable timeout APIs do.]

The conversion lives inside the library, not in `Duration`, so the public type does not need an integer-milliseconds method for this purpose. Stabilizing the narrow type therefore does not block the timeout APIs.

## Drawbacks

Users who want the omitted conversions will write their own. Because the accessors return seconds and sub-second nanoseconds separately, the arithmetic is short, but every user writes it again, and different users will round differently. That duplication continues until the follow-up RFC lands.

The split also creates a period in which the stable `Duration` is visibly incomplete. Documentation has to say so, and a user who reads the unstable method list will find methods they cannot call on stable.

Finally, a partial stabilization makes the follow-up RFC a commitment. If it stalls, the type stays incomplete. [TODO: ask the author whether an owner or a timeline exists for the follow-up.]

## Alternatives

**Stabilize everything as it stands.** This gives users the full set at once. It also commits the language to the conversions whose behavior this RFC calls unsettled. The cost of a mistake falls on every user and cannot be recovered, which outweighs the convenience of having the methods now.

**Keep `Duration` unstable until the whole design is settled.** This avoids a period of incompleteness. It leaves every timeout API without a stable signature for as long as the conversion questions stay open, and the questions have no deadline. [TODO: ask the author whether this was discussed, and what the expected delay would have been.]

**Take timeouts as plain integers.** An API like `set_timeout(ms: u64)` needs no new type. It fixes one unit into every signature, loses the unit in the type, and gives up the ability to express a span finer than the chosen unit. [TODO: ask the author whether this alternative was considered.]

**Stabilize only the constructors.** This is smaller still. It would leave a caller unable to read a `Duration` back, so a function that receives one could not inspect it. [TODO: ask the author whether this was considered.]

## Unresolved questions

- Which of the deferred groups should the follow-up RFC take first, and does any group have a clear default that could be stabilized sooner?
- Should the follow-up use the same rounding direction across all integer conversions? The deferred methods currently differ, and the RFC does not say which behavior is intended. [TODO: confirm with the author.]
- Is the negative-result behavior of subtraction acceptable for timeouts, or would a checked variant serve those callers better? [TODO: confirm.]

## Testing and documentation

Each stabilized method needs a doctest that shows a typical timeout use. The documentation for the type states which conversions are absent and links to the tracking issue for the follow-up. [TODO: add the issue number.]

The overflow behavior of addition is documented where the method is described. A caller who adds two large spans should find the result in the documentation of `+`, not in the source.

## Migration

Code that compiles today on a nightly toolchain with the feature gate enabled keeps compiling for the stabilized methods. Code that uses a deferred method keeps the gate and stays on nightly. [TODO: confirm that no stabilized method changes signature or behavior relative to the current unstable version; this RFC has no evidence either way.]
