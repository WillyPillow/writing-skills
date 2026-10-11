# Rust RFC 1040: Stabilize a reduced `Duration` type

- Start Date: (draft)
- RFC PR: (pending)
- Rust Issue: (pending)

## Summary

This RFC suggests stabilizing a reduced-scope `Duration` type that is appropriate for interoperating with various system calls that require timeouts. It does not stabilize a large number of conversion methods in `Duration` that have subtle caveats, with the intent of revisiting those conversions more holistically in the future.

## Motivation

`std::time::Duration` represents a span of time as a count of seconds and a count of nanoseconds. It is the type that the standard library uses to express timeouts for operations such as `thread::sleep`, `Condvar::wait_timeout`, and socket read and write deadlines. A stable and unambiguous representation is therefore important for any program that interacts with the operating system.

The current unstable version of the type exposes a large surface area. It includes conversions to and from floating point seconds, methods for checked, saturating, and wrapping arithmetic at several granularities, and constructors for many units. Each of these methods carries design questions. Converting a floating point value to an integer count of nanoseconds involves rounding and overflow behavior that is easy to get wrong. Multiplying a duration by a float raises questions about precision. Some methods have names that are not yet agreed upon.

The breadth of this surface has held back stabilization. Stabilizing everything at once would lock in decisions that the community has not finished discussing. At the same time, the core need is narrow: a program must be able to construct a duration from seconds and nanoseconds, read those components back, add and subtract durations, and pass a duration to an operating system call. This subset is uncontroversial and is already exercised heavily by the standard library itself.

The motivation of this RFC is therefore to separate the minimal and well-understood part of the API from the rest, stabilize that part now, and leave the remainder unstable so that it can be designed carefully.

## Guide-level explanation

After this RFC, a user can write code like the following.

```rust
use std::time::Duration;

let timeout = Duration::new(5, 500_000_000);
assert_eq!(timeout.as_secs(), 5);
assert_eq!(timeout.subsec_nanos(), 500_000_000);
```

The user can also construct a duration from whole seconds with `Duration::from_secs` and from whole milliseconds with `Duration::from_millis`. Both of these take integer arguments and cannot produce a value out of range, because the seconds field is a `u64` and the largest millisecond count that the constructor accepts is also bounded by that representation.

Arithmetic is available through the standard operator traits for addition and subtraction between two durations. Subtraction that would produce a negative result panics, matching the behavior of unsigned integers, and the stabilized API provides `checked_sub` for callers who need to test for underflow without panicking.

The user can pass a `Duration` to functions that take a timeout. The stabilized surface does not include floating point conversion, so code that needs fractional seconds must compute the nanosecond count itself, or wait for a later RFC.

## Reference-level explanation

The stabilized items are the following. The constructor `Duration::new(secs: u64, nanos: u32)` panics if `nanos` is 1,000,000,000 or greater, because the nanosecond field must be a valid sub-second component. The constructors `from_secs` and `from_millis` are provided because they are the most common forms and cannot overflow in a way that surprises a caller.

The accessor methods `as_secs`, `subsec_millis`, `subsec_micros`, and `subsec_nanos` return the components. The method `as_secs` returns a `u64` and the sub-second accessors return the appropriate unsigned integer type. These are pure reads and do not allocate.

The trait implementations `Add`, `Sub`, `AddAssign`, and `SubAssign` are stabilized for `Duration` with `Duration` on the right side. `Add` panics on overflow, consistent with integer addition in debug builds. `checked_add` and `checked_sub` return an `Option` and are also stabilized, since they are needed for any code that must handle a clock that could move backwards or a timeout computed from user input.

The constant `Duration::ZERO` is stabilized, along with `is_zero`. The `Default` implementation returns zero, and `Duration` implements `Copy`, `Clone`, `Eq`, `Ord`, and `Hash`.

The following are explicitly not stabilized by this RFC. Conversions from and to `f32` and `f64` remain unstable. Multiplication and division by integers and floats remain unstable, as do the saturating and wrapping variants. The methods that convert to and from units such as minutes or hours are not included. These items may be stabilized by a follow-up RFC once their semantics are settled.

## Drawbacks

Stabilizing a subset means that some users will find the stable API insufficient and will need to use the unstable surface through a feature gate, which they cannot do on a stable compiler. This is a real cost. However, the features left out are ones where a bad choice would be expensive to undo, so the trade is judged acceptable.

A second drawback is that a narrow API may encourage ad hoc conversion code in user programs, each with its own rounding behavior. The RFC argues that this is less harmful than a standard conversion with a subtle flaw, which would be used everywhere once stabilized.

## Rationale and alternatives

The main alternative is to stabilize the full current API. The authors rejected this because several methods carry unresolved questions about rounding, overflow, and naming, and because stabilizing them would commit the project to answers before the design discussion had matured.

A second alternative is to stabilize nothing until the design is complete. The authors rejected this because the core constructors and accessors are needed now, and because delaying them would block libraries that wish to expose timeout parameters in stable interfaces.

The chosen middle path follows the general principle that a stabilization should be as small as the use cases require. It also matches the practice of other standard library types, which tend to stabilize a constructor and a few accessors first and extend the API over time.

## Prior art

Other languages handle durations in different ways. Some represent a duration as a single floating point number of seconds, which is convenient but imprecise for large spans. Others use a fixed integer count of a smallest unit, which is exact but limits range. The representation chosen here, a pair of integers for whole seconds and nanoseconds, is exact across the full range and avoids floating point error. The RFC does not change this representation.

## Unresolved questions

Several questions are left for the follow-up work. The first is whether the floating point conversions should round toward zero, toward nearest, or in a way selected by the caller. The second is whether the names of the multiplication methods should follow the convention used for integers or a new convention. The third is whether `Duration` should gain a method that converts to a platform-specific timeout representation, which some operating system bindings would find useful.

The RFC also asks whether the panicking behavior of `Duration::new` on out-of-range nanoseconds should be replaced with a checked constructor that returns an error. The authors intend to leave the panicking form in place for the stable release and to add a checked form later if demand appears.

## Future possibilities

Once the core is stable, the library can add conversions to and from floating point seconds with a documented rounding rule. It can add saturating arithmetic for use in timeout computations that should clamp rather than fail. It can also add units beyond seconds for code that deals with long intervals. Each of these can be proposed separately, with its own rationale, so that the reasoning for each choice is recorded alongside the choice itself.

The reduced stabilization also gives the standard library room to change internal details, such as the width of the nanosecond field, without breaking public code, since the stable surface does not expose that detail beyond the accessors.
