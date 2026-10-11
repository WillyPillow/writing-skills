- Feature Name: `float_next_up_down`
- Start Date: 2021-09-06
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

This RFC adds two methods with no arguments to `f32` and `f64`: `next_up` and `next_down`. IEEE 754 specifies both operations as `nextUp` and `nextDown`. Together they make it possible to step through floating-point values in order.

```rust
assert_eq!(1.0f32.next_up(), 1.0 + f32::EPSILON);
assert_eq!(0.0f64.next_down(), -f64::from_bits(1));
```

# Motivation

Floating-point numbers are a finite, ordered set. Many algorithms need to step from one value to the next representable value in that order:

- **Interval arithmetic and directed rounding.** To keep a computed interval certain to contain the true result, libraries widen the bounds by one ULP in each direction. Without hardware rounding-mode control, which Rust does not expose, `next_down(lo)` and `next_up(hi)` are the standard tool.
- **Turning closed ranges into half-open ones.** A sampler that returns values in `[a, b)` can produce `[a, b]` by sampling `[a, b.next_up())`. The reverse conversion also comes up in random number generation and in geometric predicates.
- **Testing.** Property tests and numerical test suites often check behavior right at a boundary: "does this function handle the largest value below 1.0 correctly?" Writing `1.0f64.next_down()` is clearer and less error-prone than hand-rolled bit manipulation.
- **Strict comparison with floats.** Turning `x < c` into `x <= c.next_down()` is a common trick in computational geometry and query engines.

Today Rust users have three options, and none of them is good.

1. Reach for `libm`'s `nextafter`, which is not available in `core`, takes a second argument that is almost always infinity, and has awkward semantics around signed zero.
2. Pull in a crate. Several exist, with slightly different handling of edge cases.
3. Write the bit manipulation by hand. This is the most common choice, and it is easy to get wrong for zero, negative values, subnormals, NaN, and infinities.

The operations are small, well-specified, have no dependencies, and are easy to misimplement. That makes them good candidates for `core`.

# Guide-level explanation

`next_up` returns the smallest floating-point value strictly greater than `self`. `next_down` returns the largest floating-point value strictly less than `self`.

```rust
let x = 1.0f64;
let above = x.next_up();
let below = x.next_down();

assert!(below < x && x < above);
// There is no f64 strictly between below and x, or between x and above.
```

They work across the whole range of values, including subnormals:

```rust
// The smallest positive f32 is a subnormal.
let tiny = 0.0f32.next_up();
assert_eq!(tiny, f32::from_bits(1));
assert_eq!(tiny.next_down(), 0.0);
```

The edge cases follow IEEE 754:

- `f64::MAX.next_up()` is `f64::INFINITY`.
- `f64::INFINITY.next_up()` is `f64::INFINITY`.
- `f64::NEG_INFINITY.next_up()` is `-f64::MAX`.
- `(-0.0f64).next_up()` and `0.0f64.next_up()` both return the smallest positive subnormal.
- `f64::NAN.next_up()` returns NaN.

`next_down` mirrors all of these: `x.next_down()` is always equal to `-(-x).next_up()`.

# Reference-level explanation

The following methods are added to `f32`, with identical counterparts on `f64`:

```rust
impl f32 {
    /// Returns the least number greater than `self`.
    ///
    /// Let `TINY` be the smallest representable positive `f32`. Then,
    ///  - if `self.is_nan()`, this returns `self`;
    ///  - if `self` is `NEG_INFINITY`, this returns `-MAX`;
    ///  - if `self` is `-TINY`, this returns -0.0;
    ///  - if `self` is -0.0 or +0.0, this returns `TINY`;
    ///  - if `self` is `MAX` or `INFINITY`, this returns `INFINITY`;
    ///  - otherwise the unique least value greater than `self` is returned.
    pub const fn next_up(self) -> f32;

    /// Returns the greatest number less than `self`.
    ///
    /// The mirror image of `next_up`.
    pub const fn next_down(self) -> f32;
}
```

A reference implementation of `next_up` for `f32`:

```rust
pub const fn next_up(self) -> f32 {
    const TINY_BITS: u32 = 0x1;          // smallest positive subnormal
    const CLEAR_SIGN_MASK: u32 = 0x7fff_ffff;

    let bits = self.to_bits();
    if self.is_nan() || bits == f32::INFINITY.to_bits() {
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
    f32::from_bits(next_bits)
}
```

This works because, for finite values of a given sign, IEEE 754 binary formats order the bit patterns the same way as the values they represent. Adding one to the bits of a positive number moves to the next larger value. Subtracting one from the bits of a negative number moves toward zero, which is also the next larger value. Zero of either sign is handled separately, and so are infinity and NaN.

`next_down` is implemented symmetrically.

## NaN handling

IEEE 754 says `nextUp(NaN)` returns a quiet NaN. This RFC specifies only that the result is a NaN. Whether its payload is preserved or the NaN is quieted follows the general rules for NaN payloads in Rust and is not guaranteed by this API. The reference implementation simply returns `self`.

## `const`

Both methods are `const fn`. They use only bit operations and comparisons, so they can be evaluated at compile time once the floating-point bit conversions they rely on are const-stable. If those conversions are not const-stable when this RFC is implemented, the methods may start out non-const and gain `const` later.

## Signaling exceptions

Unlike some C library implementations, these methods do not raise floating-point exceptions such as overflow or inexact. Rust does not expose the floating-point environment, so this matches the rest of the standard library.

# Drawbacks

- It adds two methods to every float type, and the float API surface is already large.
- Users may confuse these methods with `nextafter` and expect a two-argument form. The documentation should point out that `x.next_up()` is equivalent to `nextafter(x, INFINITY)` and that the other direction is `next_down`.

# Rationale and alternatives

## Why `next_up` and `next_down` rather than `nextafter`?

C's `nextafter(x, y)` takes a direction argument. In practice that argument is almost always `INFINITY` or `NEG_INFINITY`, and the two-argument form adds edge cases of its own: what happens when `x == y`, or when `y` is NaN? IEEE 754-2008 added `nextUp` and `nextDown` precisely because they are the primitive operations. `nextafter` is easy to build from them if anyone needs it.

## Why the names?

The names follow IEEE 754 and use Rust's snake_case convention. Other options were considered:

- `succ` and `pred`: short, but obscure to anyone not familiar with Haskell or Peano arithmetic, and they suggest integer-like stepping.
- `next` and `prev`: easy to confuse with iterator methods.
- `next_representable` and `prev_representable`: precise but long.
- `next_after` with a direction enum: more machinery for no gain.

## Why not an iterator?

A `RangeInclusive<f64>` that iterates over every representable float would be convenient for exhaustive testing of `f32`, but it raises more design questions than it answers, such as how to handle signed zeros and NaN bounds. It can be built on top of these methods later.

## Doing nothing

Users can continue to rely on crates. But these functions are tiny, widely needed, and part of IEEE 754's list of required operations. That they are easy to get wrong is the strongest reason to provide one correct version.

# Prior art

- IEEE 754-2008, section 5.3.1, defines `nextUp` and `nextDown`.
- C99 and C++11 provide `nextafter` and `nexttoward`.
- Java provides `Math.nextUp`, `Math.nextDown`, and `Math.nextAfter`.
- Julia provides `nextfloat` and `prevfloat`.
- Python 3.9 added `math.nextafter`.
- Go provides `math.Nextafter`.

# Unresolved questions

- Should the methods also appear on future types such as `f16` and `f128` as those are added? (Likely yes, for consistency.)
- Should NaN payload behavior be specified more tightly?

# Future possibilities

- An `ulp` method returning the gap between `self` and the next representable value.
- Stepping by `n` representable values at once.
