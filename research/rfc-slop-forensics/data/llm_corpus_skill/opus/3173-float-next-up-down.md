# RFC 3173: `float_next_up_down`

- Feature Name: `float_next_up_down`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

## Summary

Add two methods without arguments, `next_up` and `next_down`, to `f32` and `f64`. For a value `x`, `x.next_up()` returns the least floating-point value that compares greater than `x`, and `x.next_down()` returns the greatest value that compares less than `x`. IEEE 754 specifies both operations, under the names nextUp and nextDown. With them, a program can step through the floating-point values of a type in order, one value at a time.

## Motivation

Floating-point values are not evenly spaced. The gap between an `f64` and its neighbor is 2^-52 just above 1.0, 1.0 just above 2^52, and 2^-1074 between the smallest subnormals. No fixed increment therefore reaches "the next value". A common attempt is to add `EPSILON`:

```rust
let x = 4.0_f64;
assert_eq!(x + f64::EPSILON, x); // the addition rounds back to x
```

`f64::EPSILON` is the gap above 1.0. For any `x` of at least 4.0 the gap is at least four times larger, so `x + f64::EPSILON` rounds back to `x`. Near zero the same addition skips almost all of the values between `x` and `x + EPSILON`.

Rust programs can already compute the neighbor today by reinterpreting the bits. The obvious version is short:

```rust
fn next_up_naive(x: f64) -> f64 {
    f64::from_bits(x.to_bits() + 1)
}
```

This function is correct only for positive finite values below `f64::MAX`. It is wrong in four other cases:

1. For negative `x`, adding one to the bit pattern increases the magnitude, so the result moves toward negative infinity instead of up.
2. For `-0.0`, whose bit pattern is the sign bit alone, adding one produces the smallest negative subnormal, which is less than `-0.0`.
3. For `f64::INFINITY`, adding one produces a NaN bit pattern.
4. For `f64::MAX`, the result is infinity, which is correct, but only because of how the exponent field happens to overflow. A reader of the code cannot tell this case was considered.

A correct version has to branch on the sign, on zero, on infinity and on NaN. The method is small, but each case is easy to get wrong, and a mistake shows up only at the edges of the value range, where tests seldom look. That is the argument for providing it in the standard library rather than leaving each program to write its own.

Programs that need the operation include those that enumerate every `f32` in a range to test a function exhaustively, and those that need the nearest value strictly above or below a bound, for example to turn a closed interval into an open one. [TODO: author to list the concrete uses that prompted this RFC, with links to crates or issues that implement the operation by hand.]

## Guide-level explanation

`next_up` moves one step toward positive infinity, and `next_down` moves one step toward negative infinity:

```rust
let x = 1.0_f32;
assert_eq!(x.next_up(), 1.0 + f32::EPSILON);
assert_eq!(x.next_down(), 1.0 - f32::EPSILON / 2.0);
```

The step below 1.0 is half the step above it, because 1.0 is the first value with its exponent. The two methods are therefore not inverses of a fixed increment. They are inverses of each other for every finite value: `x.next_up().next_down() == x`, with the zero case noted in the reference section.

"Up" means toward positive infinity, not away from zero. For a negative value, `next_up` moves toward zero:

```rust
assert!((-1.0_f64).next_up() > -1.0);
```

To visit every `f32` in a closed range `[lo, hi]` in increasing order:

```rust
let mut x = lo;
loop {
    check(x);
    if x == hi { break; }
    x = x.next_up();
}
```

The loop compares with `hi` before stepping rather than testing `x <= hi` at the top. With `hi == f32::INFINITY`, the version with the test at the top never terminates, because `f32::INFINITY.next_up()` is infinity.

## Reference-level explanation

The following methods are added to `f32`, and the same methods with `f64` in place of `f32` are added to `f64`:

```rust
impl f32 {
    pub fn next_up(self) -> f32;
    pub fn next_down(self) -> f32;
}
```

`next_up` returns the least value of the type that compares greater than `self`. The special cases are:

| Input | `next_up` result |
|---|---|
| NaN | NaN |
| negative infinity | `-MAX` |
| `-tiny`, the negative subnormal of least magnitude | `-0.0` |
| `-0.0` or `+0.0` | `tiny`, the positive subnormal of least magnitude |
| `MAX` | positive infinity |
| positive infinity | positive infinity |

`tiny` is 2^-149 for `f32` and 2^-1074 for `f64`. [TODO: check each row of the table against the text of IEEE 754-2008 section 5.3.1, in particular the result for `-tiny` and whether the result for a signaling NaN must be quiet.]

`next_down(x)` is defined as `-(-x).next_up()`. The table for `next_down` is therefore the table above with every sign flipped.

The zero row of the table shows the one place where the two methods do not invert each other. Both zeros step up to `tiny`, and `tiny.next_down()` is `+0.0`, so `(-0.0).next_up().next_down()` returns `+0.0`, not `-0.0`. The two compare equal, so the identity above holds under `==` but not bit for bit.

For NaN input, the result is a NaN. This RFC does not specify its payload or sign. [TODO: decide whether the result must be the input NaN unchanged, and make the decision consistent with the NaN guarantees of other `f32` methods.]

The implementation works on the bit pattern, as in the motivation, with explicit branches for the cases in the table. It uses no floating-point arithmetic. Its result therefore does not depend on the rounding mode or on whether the target flushes subnormals to zero. [TODO: confirm that no supported target changes the bit pattern of a subnormal on `from_bits`.]

## Drawbacks

The methods add two items to the API of each float type. Each item has to be documented, tested on every target, and kept forever.

The name "up" can mislead. A reader who thinks of floating-point steps in terms of magnitude may expect `(-1.0).next_up()` to return a value further from zero. The documentation has to state the direction, and the guide-level example above exists for that reason.

Code that uses these methods in a loop without care for infinity loops forever, as the guide shows. This hazard comes with any enumeration of floats, but putting the method in the standard library makes such loops easier to write.

## Rationale and alternatives

The status quo is that each program writes the bit manipulation itself or uses a crate. The motivation section shows why a hand-written version is easy to get wrong. [TODO: author to say whether a crate that provides these operations exists and why depending on it is not enough.]

The method names follow the IEEE 754 operation names nextUp and nextDown. A reader who knows the standard can find the specification of the edge cases from the names.

The following alternatives are suggestions for the author to evaluate. They are not options this RFC has recorded as considered and rejected.

- A single method with a direction argument, such as `next_toward(self, target)`, returning the neighbor of `self` in the direction of `target`. It covers both directions with one item. It also needs rules for a NaN target and for `target == self`, and it is not one of the IEEE 754 operations named in this RFC. [TODO: author to say whether this form was considered and, if so, why it lost.]
- A method that returns the gap between `x` and its neighbor (the unit in the last place) instead of the neighbor itself. Programs that want the neighbor would then add the gap, which rounds correctly but needs its own handling of the edge cases. [TODO: author to evaluate.]

Adding these methods does not prevent adding either alternative later.

## Prior art

[TODO: author to supply prior art, for example the equivalent operations in other languages' standard libraries, with a sentence on how each relates to this proposal.]

## Unresolved questions

- Should the methods be `const fn`? The bit-pattern implementation uses no floating-point arithmetic, so the usual concerns about floating-point evaluation in const contexts may not apply. [TODO: author or the const evaluation team to decide.]
- What NaN, with what payload and sign, should the methods return for NaN input? See the reference-level section.

## Future possibilities

If Rust adds further float types, these methods would apply to them with the same definition. [TODO: author to decide whether to say anything here.]
