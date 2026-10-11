# RFC 1040: Duration

- Feature Name: duration
- Start Date: 2015-04-08
- RFC PR: rust-lang/rfcs#1040
- Rust Issue: rust-lang/rust#24874

## Summary

This RFC suggests stabilizing a reduced-scope `Duration` type that is appropriate for interoperating with various system calls that require timeouts. It does not stabilize a large number of conversion methods in `Duration` that have subtle caveats, with the intent of revisiting those conversions more holistically in the future.

## Motivation

Several parts of the standard library need a way to express a span of time. The most pressing are:

- `thread::sleep`, which blocks the current thread for a period;
- `thread::park_timeout`, `Condvar::wait_timeout`, and similar synchronization primitives;
- socket timeouts such as `set_read_timeout` and `set_write_timeout`;
- `Instant::duration_since` and `SystemTime::duration_since`, which return the difference between two points in time.

At present, each of these either takes a raw integer (milliseconds, typically) or uses the unstable `std::time::Duration` type from the old `std::old_io` era. Raw integers are error prone: it is easy to pass seconds where milliseconds are expected, and the unit is communicated only by documentation and naming convention. A dedicated type removes the ambiguity at the call site.

`Duration` has existed in some form since before 1.0, but it has been marked unstable because its API grew organically and includes conversions that hide real hazards. Leaving the type unstable means the stable APIs listed above cannot use it, which in turn means stable code is stuck with integer timeouts. This RFC proposes to stabilize only the part of `Duration` whose design is settled and whose behavior is unsurprising.

## Detailed design

### The type

```rust
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Debug, Default)]
pub struct Duration {
    secs: u64,
    nanos: u32, // always less than 1_000_000_000
}
```

A `Duration` is a span of time with nanosecond resolution and a range of roughly 584 billion years. It is unsigned: a negative span of time is not representable. The fields are private, and the invariant that `nanos` is below one billion is maintained by every constructor and operation.

### Constructors and accessors

The following are stabilized:

```rust
impl Duration {
    pub fn new(secs: u64, nanos: u32) -> Duration;
    pub fn from_secs(secs: u64) -> Duration;
    pub fn from_millis(millis: u64) -> Duration;

    pub fn as_secs(&self) -> u64;
    pub fn subsec_nanos(&self) -> u32;
}
```

`new` normalizes its arguments: if `nanos` is a billion or more, the excess is carried into `secs`. If that carry overflows `secs`, the function panics. `from_secs` and `from_millis` cannot overflow.

`as_secs` returns the whole number of seconds, truncating any fractional part. `subsec_nanos` returns the remaining fractional part, always less than one billion. Together these two accessors expose the full value of the type with no loss of information, which is the property that makes them safe to stabilize.

### Arithmetic

The following operator implementations are stabilized:

```rust
impl Add for Duration { type Output = Duration; }
impl Sub for Duration { type Output = Duration; }
impl Mul<u32> for Duration { type Output = Duration; }
impl Div<u32> for Duration { type Output = Duration; }
```

Addition, subtraction, and multiplication panic on overflow. Subtraction panics if the right operand is larger than the left. This is consistent with integer arithmetic in debug builds, and callers who need non-panicking behavior can compare first. Division by zero panics.

Checked variants (`checked_add`, `checked_sub`, `checked_mul`, `checked_div`) are not stabilized in this RFC. They are straightforward, but they can be added later without any compatibility concern.

### Integration points

With this type stabilized, the following signatures become stable:

```rust
pub fn sleep(dur: Duration);
pub fn park_timeout(dur: Duration);
pub fn wait_timeout<'a, T>(&self, guard: MutexGuard<'a, T>, dur: Duration)
    -> LockResult<(MutexGuard<'a, T>, WaitTimeoutResult)>;
pub fn set_read_timeout(&self, dur: Option<Duration>) -> io::Result<()>;
pub fn set_write_timeout(&self, dur: Option<Duration>) -> io::Result<()>;
```

Socket timeouts take an `Option<Duration>`, where `None` means no timeout. Passing a zero duration to a socket timeout is an error on most platforms, since the underlying system calls interpret zero as "no timeout". The implementation returns an `InvalidInput` error rather than silently disabling the timeout.

### What is deliberately left out

The unstable `Duration` currently has methods such as `num_seconds`, `num_milliseconds`, `num_microseconds`, `num_nanoseconds`, `from_micros`, `from_nanos`, and conversions to and from floating-point seconds. This RFC does not stabilize them. The reasons differ by method:

- **Narrowing conversions** like `num_milliseconds() -> i64` can overflow for large durations. Returning an integer from a type that can hold 584 billion years invites silent truncation or panics. The right signature (a `u128`, a `Result`, or an `Option`) depends on language features not yet available.
- **Sub-millisecond constructors** such as `from_micros` and `from_nanos` raise the question of rounding and overflow behavior for the whole family, and the answer should be uniform.
- **Floating-point conversions** lose precision in ways that depend on magnitude. A duration of several years cannot be represented to the nanosecond in an `f64`, and a naive round trip changes the value.
- **Signed variants.** The old API used signed quantities, which allowed a negative `Duration`. The stabilized type is unsigned. Applications that need signed spans should wrap `Duration` and a sign themselves.

None of these omissions blocks the integration points above. Users who need an integer count of milliseconds can compute it from `as_secs` and `subsec_nanos`, accepting responsibility for the overflow semantics they want.

## Drawbacks

The reduced API is smaller than what many users expect from a time-span type. Someone porting code from another language will want to write `d.as_millis()` and will find it missing. The workaround is a one-line helper, but it is still friction.

Stabilizing the representation now also commits the standard library to a particular range and resolution. Nanosecond resolution is the finest granularity that mainstream operating systems expose, and 64 bits of seconds is more than sufficient, so this seems a safe commitment. The commitment is limited, though: because the fields are private, the internal layout could change without breaking users.

## Alternatives

**Stabilize everything as is.** This would let users have every conversion at once, but it would freeze signatures that are known to be problematic. Removing or changing a stable API requires a major version bump, which the standard library cannot afford.

**Use a signed type.** A signed duration is convenient for computing differences between times in either order. It also makes timeouts ill-defined: what does a negative sleep mean? An unsigned type pushes the question to the point where a difference is computed, where the programmer can choose between an error, a saturated zero, or a flipped order.

**Stabilize raw integer-based APIs and defer `Duration`.** This leaves the integer-unit problem in place indefinitely and risks that the integer APIs become entrenched.

**Use a type alias for `u64` milliseconds.** This offers no type safety, since aliases are interchangeable with their target.

## Unresolved questions

When the language supports 128-bit integers, the narrowing conversions can be revisited with total functions that cannot overflow. The conversion story for floating-point numbers is also left open. A follow-up RFC should propose a coherent set of accessors and constructors, along with checked and saturating arithmetic, and the naming conventions for them.

It is also an open question whether the interaction between `Duration` and the platform-specific clock types should be documented in more detail, especially regarding the granularity of `sleep` on different systems. This RFC takes the position that such details belong in the documentation of each function rather than in the type.
