# RFC 1040: Duration

## Summary

Stabilize a small `Duration` type in `std::time`: enough to pass a timeout to the standard library's blocking operations and, through them, to the system calls those operations make. Leave the many conversion methods that `Duration` currently has unstable, because several of them have edge cases that need a more careful design than this RFC can give them. Those conversions will be revisited together in a later RFC.

## Motivation

Several standard library APIs need a timeout. Sleeping a thread, waiting on a condition variable with a deadline, and setting read and write timeouts on a socket all take an amount of time from the caller and hand it to the operating system. Until a duration type is stable, these APIs either stay unstable themselves or take a raw integer whose unit the caller has to remember. [TODO: list the specific APIs blocked on a stable `Duration` at the time of writing, and whether any shipped with integer-millisecond parameters that this RFC would replace.]

The operating systems these APIs call expect time in a few fixed shapes. POSIX `nanosleep` and `pthread_cond_timedwait` take a `timespec`, which is a count of seconds plus a count of nanoseconds. `setsockopt` with `SO_RCVTIMEO` takes a `timeval`, which is seconds plus microseconds. Windows APIs such as `Sleep` and `SleepConditionVariableSRW` take milliseconds in a 32-bit integer. A duration type for timeouts has to convert to each of these shapes without surprising the caller. [TODO: confirm the set of target platforms and system calls the design was checked against.]

The current unstable `Duration` does more than this. It carries a range of constructors and accessors for weeks, days, hours, minutes, seconds, milliseconds and microseconds, signed values, and conversions whose results depend on rounding and overflow rules that are not written down. [TODO: name the conversion methods with known caveats, and give one concrete case for each, such as a value that overflows or rounds in a way a caller would not expect.] Stabilizing all of it now would commit the standard library to those rules. Stabilizing none of it keeps the timeout APIs unstable. This RFC takes the subset that the timeout APIs need.

## Detailed design

### Representation

A `Duration` is a non-negative span of time made of a whole number of seconds and a number of nanoseconds below one second:

```rust
pub struct Duration {
    secs: u64,
    nanos: u32, // always less than 1_000_000_000
}
```

The fields are private. The invariant on `nanos` is maintained by every constructor and every arithmetic operation.

This layout matches `timespec`, which is the most precise of the system-call formats listed above. Converting to `timespec` copies the two fields. Converting to `timeval` or to milliseconds discards precision, and the rounding direction for that loss is a decision for each call site (see "Conversion at the system boundary" below). [TODO: confirm that matching `timespec` is the reason for this layout, and say whether a single integer count of nanoseconds was considered. A `u64` of nanoseconds covers about 584 years, which may or may not have been judged enough.]

Durations are unsigned. A timeout cannot be negative, and none of the target system calls accept a negative value. [TODO: confirm that signed durations were deliberately excluded, and say where a caller who needs the difference of two instants is expected to get a signed result, if anywhere.]

### Stable API

The proposed stable surface is:

```rust
impl Duration {
    pub fn new(secs: u64, nanos: u32) -> Duration;
    pub fn from_secs(secs: u64) -> Duration;
    pub fn from_millis(millis: u64) -> Duration;

    pub fn as_secs(&self) -> u64;
    pub fn subsec_nanos(&self) -> u32;
}
```

`Duration` also implements `Clone`, `Copy`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash`, `Debug` and `Default`.

`new` accepts a `nanos` value of one second or more and carries the excess into `secs`. If the carry overflows `secs`, `new` panics. [TODO: confirm panic rather than saturation on overflow in `new`.]

`from_secs` and `from_millis` cover the two units in which timeouts are most often written by hand. `from_millis` also gives Windows code a direct path from a millisecond value. [TODO: say whether `from_micros` and `from_nanos` were left out on purpose, and why.]

The accessors return the two stored fields. `subsec_nanos` returns only the fractional part, so code that wants a total in some unit has to compute it, and so sees the overflow cases in its own code. This choice is the main way the RFC avoids stabilizing a conversion with a hidden caveat. A method such as `as_millis` would need to say what happens when the total does not fit in its return type, and that question is deferred.

### Arithmetic

`Duration` implements `Add`, `Sub`, `Mul<u32>` and `Div<u32>`. Each operation keeps the `nanos` invariant. `Add` and `Mul` panic on overflow of `secs`. `Sub` panics if the result would be negative. `Div` truncates toward zero. [TODO: confirm that arithmetic is in scope for this RFC. It is not needed to pass a timeout, but a caller computing a remaining timeout after a spurious wakeup needs `Sub`.]

Checked variants (`checked_add`, `checked_sub` and so on) are left out of this RFC and can be added later without changing the behavior above.

### Conversion at the system boundary

Each standard library API that takes a `Duration` converts it to the form its system call needs. Two problems arise.

The first is precision. A `Duration` of 1 nanosecond passed to a millisecond API rounds to 0 if truncated, and a timeout of 0 often means "return immediately" or, for socket options, "no timeout". Code that asked for a short wait could get no wait or an infinite one. The conversion for timeouts should therefore round up to the next representable unit, except that a zero `Duration` stays zero. [TODO: confirm round-up as the rule for all timeout conversions, and decide what a zero `Duration` means for `set_read_timeout`, where zero has a special meaning at the OS level.]

The second is range. `secs` is a `u64`, but `time_t` is 32 bits on some platforms and Windows millisecond arguments are 32 bits. A conversion that overflows should clamp to the largest value the system call accepts, so that a very long timeout becomes the longest possible wait rather than a short one after wraparound. [TODO: confirm clamping as the overflow rule, and check whether any target API reserves its maximum value to mean "infinite", as Windows does with `INFINITE`.]

These rules live inside the standard library's platform code. They are not part of the public `Duration` API, which is what lets this RFC stabilize the type without stabilizing a general conversion policy.

## Drawbacks

The reduced API is awkward for callers who think in milliseconds. Getting a total millisecond count requires `d.as_secs() * 1000 + (d.subsec_nanos() / 1_000_000) as u64`, which is longer than a method call and has its own overflow case. Some of these callers will write the arithmetic incorrectly.

Fixing the representation as seconds plus nanoseconds is hard to undo once the type is stable. The fields are private, so the layout itself can change, but `new(secs, nanos)`, `as_secs` and `subsec_nanos` assume it. A later change to a different internal unit would have to keep those methods behaving the same.

Choosing unsigned durations means a future signed type, if one is wanted, has to be a separate type. [TODO: check whether this is acceptable to the people who use the current signed `Duration` outside timeouts.]

Leaving conversions unstable for now means a second round of design and review. Users on stable Rust will write their own conversion helpers in the meantime, and those helpers may disagree with whatever the later RFC chooses.

## Alternatives

[TODO: record which of the following were considered, and why each was not chosen. None of them is presented here as having been evaluated.]

[TODO: Was stabilizing the existing `Duration` with its full API considered? If so, which caveats ruled it out?]

[TODO: Was taking timeouts as an integer count of milliseconds in each API considered, with no `Duration` type at all? This would avoid stabilizing a type, at the cost of a fixed precision.]

[TODO: Was a single `u64` of nanoseconds considered as the representation?]

[TODO: Was leaving the timeout APIs unstable until the full conversion design is settled considered? This option keeps everything reversible and delays the APIs.]

## Unresolved questions

Which conversions to add next, and what each one does at the edges, is the main open question. The later RFC needs to decide at least these points:

1. Whether whole-unit accessors such as `as_millis` return a truncated value, a rounded value, or an `Option`.
2. Whether floating-point constructors and accessors (`from_secs_f64`, `as_secs_f64`) belong on `Duration`, given their rounding behavior.
3. Whether constructors for minutes, hours and days belong on `Duration` at all, since they invite questions about calendars and leap seconds that a timeout type does not need to answer.

[TODO: confirm this list and add any conversion questions the author already knows to be contentious.]

Whether `Duration` should implement `Display`, and in what format, is also open. [TODO: decide or defer.]
