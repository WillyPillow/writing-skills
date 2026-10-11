# Rust RFC 3173: float_next_up_down

## Summary

This RFC adds two methods to `f32` and `f64`: `next_up` and `next_down`. Neither takes an argument besides the receiver. `x.next_up()` returns the smallest floating point value that compares greater than `x`. `x.next_down()` returns the largest value that compares less than `x`. IEEE 754 specifies both operations (`nextUp` and `nextDown`). With them, a program can walk through the floating point values of a type in order.

## Motivation

Floating point values are a finite, ordered set. Between any two adjacent finite values there is no third value, and the gap between neighbours grows with magnitude. Code that tests, searches or rounds floating point numbers sometimes needs to step from one value to its neighbour. Typical cases are:

- Turning an exclusive bound into an inclusive one. A range `x < y` is the closed range `x.next_up() <= y`.
- Building test inputs that sit just above and just below a boundary, such as the input on each side of a rounding threshold.
- Searching a range of floats by bisection, where the loop must terminate when two bounds are adjacent.

Today a user who needs this writes the bit manipulation by hand. For positive finite values, the next larger float has the next larger bit pattern, so `f64::from_bits(x.to_bits() + 1)` works. The same expression fails for negative values, where increasing the bit pattern moves away from zero. It also fails at the edges: at `f64::MAX` the addition lands on infinity, which happens to be correct, but at positive infinity it lands on a NaN pattern, which is not. Zero needs its own case, because `-0.0` and `+0.0` compare equal but have different bit patterns. These cases are easy to get wrong, and a wrong version passes tests on ordinary inputs.

[TODO: the author's material gives no concrete user report, crate or bug where a hand-written version went wrong. Add one if it exists.]

The standard library already exposes the neighbouring operations. `to_bits` and `from_bits` give the representation, and `total_cmp` gives the IEEE 754 total order. `next_up` and `next_down` fill the gap between them: the total order says which of two values is larger, and these methods give the successor.

## Guide-level explanation

`next_up` moves one step toward positive infinity, and `next_down` moves one step toward negative infinity. A step is one representable value, not a fixed distance.

```rust
let x = 1.0_f32;
let y = x.next_up();
assert!(y > x);
// No f32 lies strictly between x and y.
assert_eq!(y, f32::from_bits(x.to_bits() + 1));
assert_eq!(y.next_down(), x);
```

The distance between `x` and `x.next_up()` depends on `x`. Near `1.0` it is `f32::EPSILON`. Near `1.0e10` it is much larger. A caller who wants "a slightly larger number" in a way that is independent of scale should use these methods instead of adding a constant.

Walking through every value in a range works as a loop:

```rust
let mut x = 0.0_f32;
while x < 1.0 {
    // use x
    x = x.next_up();
}
```

The behaviour at special values follows IEEE 754:

| Receiver | `next_up` | `next_down` |
|---|---|---|
| a finite value | next larger finite value, or `+inf` after `MAX` | next smaller finite value, or `-inf` below `MIN` |
| `+inf` | `+inf` | `MAX` |
| `-inf` | `MIN` | `-inf` |
| `+0.0` or `-0.0` | smallest positive subnormal | smallest negative subnormal |
| NaN | NaN | NaN |

Zero deserves a sentence. `0.0.next_up()` and `(-0.0).next_up()` both return the smallest positive subnormal, because the two zeros are one point on the number line. Neither call returns the other zero. For the same reason, `next_down` of the smallest positive subnormal is `+0.0`, and `next_up` of the smallest negative subnormal is `-0.0`.

Subnormal values are not skipped. Stepping up from `0.0` visits every subnormal before it reaches `f32::MIN_POSITIVE`.

## Reference-level explanation

The methods are added to `impl f32` and `impl f64` with these signatures:

```rust
pub const fn next_up(self) -> Self;
pub const fn next_down(self) -> Self;
```

[TODO: the author's material does not say whether the methods are `const`, or whether they are stabilized together with `const` evaluation. Decide and state it here.]

`next_up` is defined by the following cases, applied in order.

1. If `self` is NaN, return `self`. A signalling NaN may be quieted, as with other arithmetic operations. [TODO: confirm the intended NaN payload and signalling behaviour.]
2. If `self` is positive infinity, return `self`.
3. If `self` is zero of either sign, return the smallest positive subnormal.
4. If `self` is positive, return the value whose bit pattern is one larger. Since the largest finite value has the pattern just below infinity, `MAX.next_up()` is `+inf`.
5. If `self` is negative, return the value whose bit pattern is one smaller. For `-inf` this gives `MIN`, because the pattern after the sign bit and the all-ones exponent minus one is the largest-magnitude finite value.

`next_down` is defined by symmetry: `x.next_down()` equals `-((-x).next_up())` for every `x`, NaN included. An implementation may use this identity or write its own cases.

A sketch of the implementation in terms of bits:

```rust
fn next_up(self) -> f64 {
    let bits = self.to_bits();
    if self.is_nan() || bits == f64::INFINITY.to_bits() {
        return self;
    }
    let abs = bits & !SIGN_MASK;
    let next = if abs == 0 {
        TINY_BITS            // smallest positive subnormal
    } else if bits == abs {
        bits + 1             // positive: larger magnitude is larger value
    } else {
        bits - 1             // negative: smaller magnitude is larger value
    };
    f64::from_bits(next)
}
```

The sketch is illustrative. The behaviour is the specification, and the code is not.

The methods must give the same result on every platform. They need no floating point arithmetic and no rounding mode, so they do not depend on the hardware's floating point environment. [TODO: check this claim against the intended implementation, which may use intrinsics on some targets.]

### Properties

For every non-NaN `x` other than the end points, the following hold, and the tests for the implementation should check them:

- `x.next_up() > x` and `x.next_down() < x`.
- `x.next_up().next_down() == x`, and likewise in the other order.
- No float `z` satisfies `x < z < x.next_up()`.

At the end points the first two properties weaken: `f64::INFINITY.next_up()` equals `f64::INFINITY`, so the strict inequality does not hold there.

## Drawbacks

The methods enlarge the surface of `f32` and `f64` by two names each. The functionality can be written by users, as the Motivation shows, so the case for inclusion rests on how often the hand-written version is wrong and on how easy it is to write incorrectly. The material for this RFC does not include a measurement of either. [TODO: add evidence of demand, such as uses in existing crates.]

The names could collide with methods that user traits already add to `f32` and `f64`. Inherent methods take priority over trait methods, so a collision silently changes which method a call resolves to. [TODO: the author should state whether a crater run or other check was done and what it found.]

## Rationale and alternatives

The names `next_up` and `next_down` follow the IEEE 754 operations `nextUp` and `nextDown`, which gives readers who know the standard a direct mapping.

The standard also defines `nextAfter(x, y)`, which steps from `x` toward `y`. [TODO: ask the author whether `next_after` was considered, and why the two argumentless methods were chosen over it.] Two further options a reviewer may ask about are a free function in a crate outside `std`, and an iterator over a range of floats. [TODO: ask the author whether either was considered, and what decided against it.]

Leaving the status quo in place has a known cost: every user who needs the operation writes the bit manipulation themselves, including the sign and zero cases.

## Prior art

IEEE 754 defines `nextUp` and `nextDown` as required operations in its 2008 revision. [TODO: the author should supply references to other languages and libraries that expose the operations, and to the standard's section numbers. None are listed here because none were supplied.]

## Unresolved questions

- Whether the methods are `const` at stabilization.
- The NaN behaviour for signalling NaNs and payloads.
- Whether a `next_after`-style method belongs in a later RFC.

## Future possibilities

A later RFC could add an iterator that yields every float in a range. That would build on these two methods. This RFC does not propose it.
