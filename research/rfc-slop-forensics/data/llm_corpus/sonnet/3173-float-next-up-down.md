# RFC 3173: float_next_up_down

- Feature Name: `float_next_up_down`
- Start Date: 2021-12-10
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

This RFC adds two argumentless methods to `f32` and `f64`, `next_up` and `next_down`. These functions are specified in the IEEE 754 standard and provide the capability to enumerate floating point values in order.

## Motivation

Floating point numbers are a discrete set. Between any two distinct finite values of an `f64` there is a finite number of other representable values, and the values form a total order (ignoring NaN). Programs sometimes need to step through that order one value at a time. Common reasons include:

- **Open versus closed intervals.** Suppose you want the largest value strictly less than `1.0`, so as to sample from the half-open interval `[0, 1)` without ever returning exactly `1.0`. Without `next_down`, the programmer has to write something like `1.0 - f64::EPSILON / 2.0`, which depends on facts about the neighborhood of `1.0` that are easy to get wrong. At a different magnitude, the same trick gives the wrong answer.
- **Exact bounds on rounding error.** Interval arithmetic and numerical verification routinely widen a computed result by one unit in the last place, or ULP, in each direction to guarantee the true value lies inside the interval.
- **Testing.** Property-based tests of numeric code want to probe values immediately adjacent to boundary values, such as either side of a threshold.
- **Enumeration.** Exhaustive tests of a function over every `f32` are feasible, since there are only about four billion of them, but stepping through them requires a way to compute the successor.

Today, users have two options. They can reinterpret the bits as an integer, increment or decrement, and reinterpret back, using `to_bits` and `from_bits`. That works but must treat negative values, zero, infinities, and NaN specially, and many people get at least one of those wrong. Alternatively they can pull in a crate that implements the operation. Since the operation is defined by IEEE 754 and is small, it belongs in the standard library, where it can be implemented once, correctly, and documented.

## Guide-level explanation

Every floating point type has a "next value up" and a "next value down." For example, the number immediately after `1.0_f64` is `1.0000000000000002`, and the number immediately before it is `0.9999999999999999`.

```rust
let x = 1.0_f64;
assert!(x.next_up() > x);
assert!(x.next_down() < x);
assert_eq!(x.next_up().next_down(), x);
```

The two methods are inverses of each other everywhere except at the edges and at NaN.

Use `next_up` to turn a "less than or equal to" bound into a "less than" bound, or to move one step beyond a computed result:

```rust
fn largest_below(x: f64) -> f64 {
    x.next_down()
}

let r = largest_below(1.0);
assert!(r < 1.0);
assert!(r.next_up() == 1.0);
```

The methods handle special values in sensible ways:

```rust
assert_eq!(f64::INFINITY.next_down(), f64::MAX);
assert_eq!(f64::NEG_INFINITY.next_up(), f64::MIN);
assert_eq!(f64::INFINITY.next_up(), f64::INFINITY);
assert_eq!(f64::NEG_INFINITY.next_down(), f64::NEG_INFINITY);
assert!(f64::NAN.next_up().is_nan());
```

Zero deserves a note. Both `0.0` and `-0.0` exist, and they compare equal. The next value above either of them is the smallest positive subnormal number, `f64::from_bits(1)`, and the next value below either is the negative of that:

```rust
let tiny = f64::from_bits(1);
assert_eq!(0.0_f64.next_up(), tiny);
assert_eq!((-0.0_f64).next_up(), tiny);
assert_eq!(0.0_f64.next_down(), -tiny);
```

## Reference-level explanation

The following methods are added to both `f32` and `f64`. They are shown for `f64`:

```rust
impl f64 {
    /// Returns the least number greater than `self`.
    pub const fn next_up(self) -> Self;

    /// Returns the greatest number less than `self`.
    pub const fn next_down(self) -> Self;
}
```

The behavior follows the `nextUp` and `nextDown` operations in IEEE 754-2019, section 5.3.1:

- If `self` is NaN, the result is NaN. The payload and sign are unspecified, as for other arithmetic on NaN.
- `next_up` returns the smallest representable value strictly greater than `self`, with these edge cases:
  - `NEG_INFINITY.next_up()` is `MIN`.
  - `INFINITY.next_up()` is `INFINITY`.
  - `-0.0.next_up()` and `0.0.next_up()` are both the smallest positive subnormal.
  - `-MIN_POSITIVE_SUBNORMAL.next_up()` is `-0.0`.
- `next_down` is defined symmetrically, and satisfies `x.next_down() == -(-x).next_up()` for all non-NaN `x`.

A reference implementation for `f64`, written in terms of the bit representation:

```rust
pub const fn next_up(self) -> Self {
    const TINY_BITS: u64 = 0x1;
    const CLEAR_SIGN_MASK: u64 = 0x7fff_ffff_ffff_ffff;

    let bits = self.to_bits();
    if self.is_nan() || bits == Self::INFINITY.to_bits() {
        return self;
    }

    let abs = bits & CLEAR_SIGN_MASK;
    let next_bits = if abs == 0 {
        TINY_BITS
    } else if bits == abs {
        bits + 1
    } else {
        bits - 1
    };
    Self::from_bits(next_bits)
}

pub const fn next_down(self) -> Self {
    -((-self).next_up())
}
```

The implementation relies on the fact that, within each sign, the ordering of the bit patterns matches the ordering of the values. For positive numbers, adding one to the bits yields the next larger value, including the transition from the largest finite number to infinity. For negative numbers, subtracting one moves toward zero, which is upward. Zero is handled explicitly since both zero encodings map to the same successor.

Whether `to_bits` and `from_bits` are usable in `const` contexts is governed by their own stabilization. The new methods are marked `const` once those are available, otherwise they are introduced as non-const functions and made `const` later. Neither choice is observable to existing code.

Both methods behave identically on all platforms because they operate on the bit pattern and do not depend on the floating point environment, rounding mode, or flush-to-zero settings.

## Drawbacks

This adds two methods to the surface of each float type. The methods are small, well specified, and cheap to maintain, so the cost is modest.

There is a small risk that users will reach for these methods where an epsilon comparison would be more appropriate. Documentation should point out that one ULP is not a general error tolerance, and that the distance between adjacent floats varies with magnitude.

## Rationale and alternatives

**Follow IEEE 754 names.** IEEE 754 calls the operations `nextUp` and `nextDown`. The snake-case forms `next_up` and `next_down` follow Rust naming conventions and are discoverable beside methods such as `is_nan` and `copysign`.

**Provide `next_after(self, other)`.** The C library offers `nextafter(x, y)`, which steps from `x` toward `y`. This is more general but also more awkward, since one of the arguments only supplies a direction. IEEE 754 itself chose to deprecate that form in favor of the two argumentless operations. `next_after` could be added later if the need arises without conflicting with this proposal.

**Leave it to crates.** Third-party crates provide this today. The functionality is nonetheless foundational and defined by a standard the language already follows for its arithmetic, and a single implementation in `core` removes a common source of subtle bugs.

**Different zero semantics.** One could have `next_up` of `-0.0` return `0.0`, which would preserve the property that zeros are adjacent in the bit ordering. IEEE 754 says otherwise, and treating the two zeros as one value for stepping purposes is more useful in practice.

**Methods on a separate trait.** Placing these on an extension trait would avoid growing the inherent impls, but inherent methods are the established convention for float functionality in `core`.

## Prior art

- IEEE 754-2008 and 2019 specify `nextUp` and `nextDown`.
- C99 offers `nextafter`, `nextafterf`, and, in C23, `nextup` and `nextdown`.
- Java provides `Math.nextUp`, `Math.nextDown`, and `Math.nextAfter`.
- Python's `math.nextafter` was added in 3.9, and `math.ulp` gives the size of one step.
- Numerous Rust crates implement the same functionality, including `float_next_after` and parts of `num-traits` extensions.

## Unresolved questions

- Should the methods be `const` immediately, or only once the bit conversion functions are usable in constant evaluation?
- Should a companion `ulp` method, returning the distance to the next value, be proposed separately?

## Future possibilities

A `next_after` method and a `ulp` method could be added later. Support for the new `f16` and `f128` types would follow the same pattern.
