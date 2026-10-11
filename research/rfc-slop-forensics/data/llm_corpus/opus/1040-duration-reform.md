- Feature Name: `duration`
- Start Date: 2015-04-10
- RFC PR: rust-lang/rfcs#1040
- Rust Issue: rust-lang/rust#24874

# Summary

Stabilize a reduced-scope `Duration` type in `std::time` that is suitable for passing timeouts to system calls. Leave out, for now, the many conversion methods on `Duration` that have subtle caveats, with the intent of revisiting conversions as a whole once the rest of the time story (instants, wall-clock time, time zones) is designed.

# Motivation

Several APIs that are already stable, or are about to become stable, need a way to express a span of time:

- `std::thread::sleep`
- `Condvar::wait_timeout`
- socket read and write timeouts in `std::net`
- `std::sync::mpsc::Receiver::recv_timeout` and similar channel operations
- `thread::park_timeout`

At the moment these APIs either take a raw number of milliseconds as a `u32`, or they take the unstable `Duration` type that lives in `std::time`. Neither is a good long-term answer.

Millisecond integers are ambiguous at the call site. Reading `sleep_ms(1500)` requires the reader to know the unit by name, and every API would need a suffix or documentation to make the unit clear. Milliseconds are also too coarse for some uses. Operating systems happily accept microsecond or nanosecond timeouts, and some programs, such as audio software and benchmarks, need them.

The existing unstable `Duration` was ported from an older time library. It supports negative durations, stores its value as seconds plus nanoseconds in signed integers, and exposes a large surface: `weeks`, `days`, `hours`, `minutes`, `num_milliseconds`, `num_microseconds`, arithmetic with overflow panics, and so on. Several of these methods are questionable:

- Negative durations do not make sense as timeouts. Every system call that takes a timeout either rejects a negative value or treats it as zero, and the type does not prevent callers from producing one.
- `Duration::days(1)` suggests that a day is always 86 400 seconds, which is false in the presence of leap seconds and is a common source of bugs in calendar code. Wall-clock concepts do not belong on a type intended for elapsed time.
- `num_milliseconds` and friends silently truncate. Whether they should round, truncate, or saturate depends on the use, and the right choice is not obvious.

We do not want to commit to all of this surface area in 1.0. We do want a type that the timeout APIs can share.

# Detailed design

The stabilized type is:

```rust
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug, Default)]
pub struct Duration {
    secs: u64,
    nanos: u32, // always < 1_000_000_000
}
```

The representation is private. A `Duration` is always non-negative. It can represent spans up to `u64::MAX` seconds, which is far longer than the age of the universe, with nanosecond precision.

## Construction

```rust
impl Duration {
    pub fn new(secs: u64, nanos: u32) -> Duration;
    pub fn from_secs(secs: u64) -> Duration;
    pub fn from_millis(millis: u64) -> Duration;
}
```

`new` normalizes its arguments: if `nanos` is one second or more, the excess is carried into `secs`. If that carry overflows `secs`, `new` panics.

`from_millis` is included because a large amount of existing code thinks in milliseconds, and because it can be implemented without loss. Constructors for minutes, hours, and days are deliberately omitted. For minutes and hours there is no correctness problem, but they invite the next step of adding days and weeks, which do have one. Callers who want an hour can write `Duration::from_secs(60 * 60)`, which makes the arithmetic visible.

## Accessors

```rust
impl Duration {
    pub fn as_secs(&self) -> u64;
    pub fn subsec_nanos(&self) -> u32;
}
```

These return the two components of the representation directly and never lose information. Together they are enough to convert a `Duration` into any platform's timeout structure, such as `timespec` on Unix or a millisecond `DWORD` on Windows, with whatever rounding the platform layer chooses.

Methods such as `as_millis` or `as_secs_f64` are not stabilized by this RFC. Each of them must make a decision about truncation, rounding, or overflow, and we would prefer to make those decisions together, after we know what the rest of the time API looks like.

## Arithmetic

`Duration` implements `Add`, `Sub`, `Mul<u32>`, and `Div<u32>`, each returning `Duration`. `Add` and `Mul` panic on overflow. `Sub` panics if the result would be negative. `Div` truncates toward zero at nanosecond precision.

Panicking on underflow is a departure from the old type, where subtraction could produce a negative duration. We expect underflow to be a logic error far more often than an intended result. Checked variants (`checked_add`, `checked_sub`, and so on) can be added later in an unstable form if demand appears.

## Display

`Duration` implements `Debug`. It does not implement `Display` at this time, since the right human-readable format (for example `1.5s` versus `1s 500ms` versus `00:00:01.500`) is a matter of taste that a library can provide.

## Migration of existing APIs

APIs that currently take milliseconds will gain `Duration`-taking counterparts. For example, `thread::sleep(dur: Duration)` is added and `thread::sleep_ms(ms: u32)` is deprecated. The same pattern applies to `Condvar::wait_timeout_ms`, `thread::park_timeout_ms`, and the socket timeout setters.

Platform code converting a `Duration` to a system timeout should round up rather than down when the platform granularity is coarser than a nanosecond, so that a requested timeout is never cut short. A timeout too large for the platform type should saturate to the platform's maximum rather than wrap.

# Drawbacks

Leaving out convenient constructors and accessors means some code will be wordier. `Duration::from_secs(5 * 60)` is less pleasant than `Duration::minutes(5)`. Some users will write their own extension traits in the meantime, and those may diverge from what the standard library eventually adopts.

Committing to an unsigned representation rules out using `Duration` for signed differences between times. Those uses will need a different type or an explicit pair of a sign and a `Duration`. We believe this is correct: the difference between two points in time is better represented by an API on the time-point type that can report which point came first.

# Alternatives

**Keep milliseconds.** This avoids designing a type at all, but bakes an arbitrary unit into stable APIs and limits precision.

**Stabilize the existing `Duration` unchanged.** This is the fastest path but commits to negative durations and calendar-flavoured constructors that we think are mistakes.

**Use a single `u64` of nanoseconds.** This is simpler and makes arithmetic cheap. It limits the range to about 584 years, which is enough for timeouts but may not be enough for other uses of the type, and it makes conversion to `timespec`-style structures require a division. The two-field representation keeps both the range and the conversion simple.

**Use floating-point seconds.** Floats are convenient but lose precision for large values and make equality comparisons unreliable. They are a poor fit for a type that will be used as a hash key and compared for ordering.

# Unresolved questions

- Should `from_millis` take `u64` or `u32`? `u64` is chosen here for consistency with `from_secs`.
- What is the plan for `Instant` and `SystemTime`, and how should `Duration` interact with them? This RFC intentionally leaves that for a follow-up.
- Should conversions to floating-point seconds be added soon, given how common they are in games and simulations?
