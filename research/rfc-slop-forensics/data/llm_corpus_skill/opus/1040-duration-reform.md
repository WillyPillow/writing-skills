# RFC 1040: Duration

## Summary

Stabilize a small `Duration` type in `std::time` whose job is to carry timeouts into system calls. Leave unstable the conversion methods whose behavior has caveats (truncation, overflow, floating-point rounding) and revisit them together later.

## Motivation

Several standard library APIs take a timeout. Sleeping a thread, waiting on a condition variable, and setting read or write timeouts on a socket all end in an operating system call that accepts some representation of a time span. [TODO: list the exact std functions that will take `Duration` once this RFC lands, and which of them are already stable with another argument type.]

These APIs cannot be stabilized until the type they take is stable. Today the candidate type is `Duration`, but its unstable surface includes many methods beyond what a timeout needs. Each of those methods would become a permanent public API on stabilization. Stabilizing the whole type therefore means committing to every conversion at once, including the ones whose semantics are not settled.

The goal of this RFC is narrow: make it possible to stabilize timeout-taking APIs without deciding the conversion questions. A reader can check whether it succeeded by asking two things. First, can every timeout-taking API in std be expressed with only the stabilized methods? Second, does any stabilized method lose information silently?

## Which conversions have caveats

The conversions this RFC leaves out share a problem: each maps a value onto a representation that cannot hold every `Duration`, so it must choose between truncating, rounding, saturating and panicking. The right choice depends on the caller, and std cannot make it once for everyone.

Take a conversion to whole milliseconds. A duration of 1.9999 ms becomes 1 ms if the method truncates and 2 ms if it rounds. For a timeout, truncation means waking early, and some callers treat an early wakeup as a spurious one and loop. Rounding up means waking late, which other callers do not expect. Neither answer is wrong. They answer different questions.

Range is the second problem. If `Duration` stores whole seconds as a `u64`, the number of milliseconds in its largest value does not fit in a `u64`, because it is a thousand times larger. A method that returns milliseconds as a `u64` must therefore either panic, saturate, or return an `Option`. Each choice changes the signature or the failure mode, so it cannot be added later without breaking callers.

Floating point is the third. An `f64` has 53 bits of mantissa, so it cannot represent every nanosecond count over the full range of `Duration`. A method returning seconds as `f64` loses precision for large values. Again this is acceptable for some callers and a bug for others.

[TODO: the abstract says these conversions have "subtle caveats". Confirm that the three above are the caveats the author means, and add any others, for example behavior with negative values from external sources.]

## Detailed design

The stabilized type is a span of time with nanosecond resolution. It is not a point in time, and it is never negative. [TODO: confirm non-negativity is decided; it drives the arithmetic semantics below.]

The proposed stable surface is the following sketch. It shows only the parts that bear on the decisions in this RFC.

```rust
pub struct Duration { /* private */ }

impl Duration {
    pub fn new(secs: u64, nanos: u32) -> Duration;
    pub fn from_secs(secs: u64) -> Duration;
    pub fn from_millis(millis: u64) -> Duration;
    pub fn as_secs(&self) -> u64;
    pub fn subsec_nanos(&self) -> u32;
}

impl Add for Duration { /* ... */ }
impl Sub for Duration { /* ... */ }
impl Mul<u32> for Duration { /* ... */ }
impl Div<u32> for Duration { /* ... */ }
```

[TODO: confirm this method list. It is the assistant's reading of "reduced scope", not a list from the author.]

The design rests on one choice: every stabilized accessor is exact. `as_secs` and `subsec_nanos` together return the full value with no rounding, because a `u64` of seconds and a `u32` of nanoseconds are the internal representation. A caller who needs milliseconds, or an `f64`, computes it from these two fields and so makes the rounding decision explicitly.

The constructors follow the same rule in the other direction. `from_secs` and `from_millis` cannot lose information, because every whole number of seconds or milliseconds in a `u64` maps to a representable `Duration`. `new` accepts a nanosecond count of one second or more and carries the excess into the seconds field. [TODO: decide what `new` does when that carry overflows the seconds field: panic, or saturate.]

Arithmetic is where this rule meets its limit. Adding two durations can overflow, and subtracting a larger from a smaller one would produce a negative span. This RFC proposes that both cases panic, matching integer arithmetic in debug builds. [TODO: confirm. The alternative is checked methods such as `checked_add` returning `Option`; the author should state whether those are in scope for this RFC or deferred.]

### How the timeout APIs use it

Each OS call takes its own representation. A POSIX call that takes a `timespec` reads seconds and nanoseconds directly from `as_secs` and `subsec_nanos`, with no rounding. [TODO: confirm what happens when `as_secs` exceeds the range of `time_t` on the target.] A call that takes a millisecond count, such as a Windows wait function, needs a conversion. That conversion lives inside std, next to the call, where the right rounding for that call is known. [TODO: state the rounding and clamping rule std will use for millisecond-based OS calls.]

This is the point of keeping the conversions private for now. Std still performs them, but each one is tied to a specific system call whose needs are known. Only the generic public conversions, whose callers are unknown, are deferred.

## Drawbacks

Users who want milliseconds or floating-point seconds must write the conversion themselves. That is a few lines, but every crate that needs it will write its own version, and some will get the overflow case wrong. [TODO: is there evidence from existing users of the unstable type about how often these conversions are used?]

A small stable surface also means `Duration` will be stabilized in pieces. Each later addition needs its own review. This RFC accepts that cost in exchange for not committing early to semantics that may prove wrong.

## Reversibility

The struct's internal representation is private, so it can change. The public constructors and accessors cannot be removed once stable. In particular, `as_secs` returning `u64` and `subsec_nanos` returning `u32` fix the range and resolution that callers will rely on. These are the decisions in this RFC that are most expensive to reverse, and they deserve the most scrutiny from reviewers.

Leaving conversions unstable is cheap to reverse: any of them can be stabilized later by a separate RFC.

## Alternatives

The status quo is the first alternative: keep all of `Duration` unstable. This blocks stabilization of the timeout APIs that take it, which is the problem the RFC exists to solve.

The second alternative is to stabilize the full current surface. This settles the timeout APIs at once, but commits to the rounding and overflow behavior of every conversion as it is written today.

[TODO: the following are suggestions for the author to evaluate, not options known to have been considered. (1) Have timeout APIs take an integer count of milliseconds or nanoseconds instead of a new type; this avoids a type but fixes one resolution and range for all OS calls. (2) Stabilize conversions with explicit names for the rounding mode, such as `as_millis_floor`; this settles the conversion question now rather than deferring it. The author should state whether either was considered and why it was or was not chosen.]

## Unresolved questions

1. The overflow behavior of `new` and of arithmetic.
2. Whether checked arithmetic belongs in this RFC.
3. The final set of conversions to stabilize later, and the process for deciding their rounding semantics together rather than one at a time.
4. Whether `Duration` should implement `Display` or `Debug` in a particular human-readable format. [TODO: confirm whether formatting is in or out of scope.]
