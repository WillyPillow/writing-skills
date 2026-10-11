# RFC 3173: float_next_up_down

- Feature name: `float_next_up_down`
- Start date: [TODO: date]
- RFC PR: [TODO: link]
- Tracking issue: [TODO: link]

## Summary

Add two methods to `f32` and `f64`:

```rust
impl f64 {
    pub fn next_up(self) -> f64;
    pub fn next_down(self) -> f64;
}
```

`x.next_up()` returns the smallest floating point value greater than `x`, and `x.next_down()` returns the largest value less than `x`. IEEE 754 specifies both operations under the names nextUp and nextDown [TODO: check the clause number in IEEE 754-2008 and IEEE 754-2019]. With them, a program can step through the floating point values in order, one representable value at a time.

## Motivation

Rust has no direct way to get the neighbor of a float. A programmer who needs one today usually writes the bit-level version by hand:

```rust
fn next_up_naive(x: f32) -> f32 {
    f32::from_bits(x.to_bits() + 1)
}
```

This function is correct for positive finite values below `f32::MAX` and wrong for every other class of input. Floats use a sign-magnitude encoding, so adding one to the bits of a negative number makes its magnitude larger, which moves the value down instead of up. `(-1.0f32).to_bits() + 1` decodes to a number slightly below `-1.0`. The function also fails at the special values:

1. For `-0.0`, whose bits are `0x8000_0000`, adding one gives the negative subnormal closest to zero, which is less than `-0.0`.
2. For `f32::INFINITY`, adding one produces a NaN bit pattern.
3. For `f32::MAX`, adding one gives infinity, which is the right answer, but only by accident of the encoding.
4. For a NaN input, adding one may produce a different NaN payload or, for the largest payload, overflow into the sign bit.

A correct version handles the sign, both zeros, infinities and NaN separately. That is short but easy to get wrong, and the errors show up only for inputs that tests often skip. Putting the operation in the standard library gives one implementation that is checked against the IEEE 754 definition.

[TODO: list the concrete use cases that motivated this RFC, for example crates or issues that implement this by hand, and any bugs caused by the naive version.]

Two kinds of code need the operation. The first enumerates floats: exhaustive tests over a range of inputs, and searches that need the next candidate value. The second converts between strict and non-strict bounds. For a finite float `b`, the condition `x < b` holds exactly when `x <= b.next_down()`. That identity lets code that accepts only closed intervals express an open one. [TODO: confirm these two uses are the ones the author intends to cite.]

## Guide-level explanation

Every finite float except the largest has a successor, the next larger representable value. `next_up` returns it:

```rust
let x = 1.0f32;
let y = x.next_up();
assert!(y > x);
assert_eq!(y - x, f32::EPSILON);
```

Between 1.0 and 2.0 the spacing of `f32` values is `f32::EPSILON`, so the successor of 1.0 is `1.0 + f32::EPSILON`. The spacing changes with the exponent, so code should not assume the step is constant. `next_up` and `next_down` take the encoding into account and return the neighbor for any input.

To visit every `f32` in a closed range, step with `next_up` until the upper bound is reached:

```rust
let mut x = 0.5f32;
while x <= 0.5000001 {
    check(x);
    x = x.next_up();
}
```

The two methods are inverses on finite values that are neither zero nor at the ends of the range: `x.next_up().next_down() == x`. The zero case is described below.

## Reference-level explanation

The methods follow the IEEE 754 definitions. For `next_up`:

| Input `x`                        | `x.next_up()`                         |
|----------------------------------|---------------------------------------|
| NaN                              | NaN                                   |
| `-INFINITY`                      | `-MAX`                                |
| negative finite, not the closest to zero | the next value toward zero    |
| largest negative subnormal (`-0x1p-149` for `f32`) | `-0.0`              |
| `-0.0` or `+0.0`                 | smallest positive subnormal           |
| positive finite below `MAX`      | the next larger value                 |
| `MAX`                            | `INFINITY`                            |
| `INFINITY`                       | `INFINITY`                            |

`next_down(x)` is defined as `-(-x).next_up()`. So `next_down` of either zero returns the negative subnormal closest to zero, and `next_down(-INFINITY)` is `-INFINITY`.

The table shows why `next_up` and `next_down` are not exact inverses at zero. Both zeros step up to the same subnormal, and that subnormal steps down to `+0.0`. So `(-0.0).next_up().next_down()` is `+0.0`, and by symmetry `(0.0).next_down().next_up()` is `-0.0`. [TODO: check these zero results against the IEEE 754 text.] The two zeros compare equal, so `==` hides the difference, but `is_sign_negative` and `to_bits` show it.

For NaN input, the methods return a NaN. This RFC does not specify the payload or sign of the returned NaN, which matches how other float operations in the standard library treat NaN. [TODO: confirm whether the RFC should promise to return the input NaN unchanged.]

The methods must not depend on the current floating point environment. Rust does not expose rounding modes, and neither operation rounds, since the result is always representable. The implementation can therefore work on the bit pattern:

1. If `x` is NaN, return `x`.
2. If `x` is `+INFINITY`, return `x`.
3. If `x` is either zero, return the smallest positive subnormal.
4. If `x` is positive, return `from_bits(x.to_bits() + 1)`.
5. Otherwise `x` is negative and nonzero, so return `from_bits(x.to_bits() - 1)`.

Step 5 covers `-INFINITY`, whose bits minus one decode to `-MAX`, and the largest negative subnormal, whose bits minus one decode to `-0.0`. The same steps apply to `f64` with 64-bit integers.

[TODO: decide whether the methods are `const fn`. The bit-level implementation uses only operations that are allowed in `const` contexts once `to_bits` and `from_bits` are `const`, but the RFC should state the decision.]

Both methods are added as inherent methods in `core`, so they are available in `no_std` code. They do not depend on a math library.

## Drawbacks

The methods add two items to the public API of each float type. That cost is small, but the API cannot be removed once stabilized.

New inherent methods can change which method a call resolves to. A crate that defines a trait with a method named `next_up` or `next_down`, implements it for `f32` or `f64`, and calls it with method syntax would start calling the inherent method after this change, since inherent methods take precedence. If the trait method had different behavior at the edge cases above, the result would change without a compile error. [TODO: check crates.io for traits that define `next_up` or `next_down` on floats, and state how many are affected and whether their behavior matches.]

The zero case is a small trap. A user who expects `next_up` and `next_down` to be exact inverses will be surprised by the sign of zero. The documentation should show the case explicitly.

## Rationale and alternatives

The names `next_up` and `next_down` come from IEEE 754's nextUp and nextDown, converted to Rust's snake case. Using the standard's names lets a reader who knows the standard find the operation and its definition.

The methods take no argument. Each one moves in a fixed direction, so the caller states the direction in the method name, and no comparison against a target is needed.

[TODO: Was a C-style `nextafter(x, y)`, which moves `x` one step toward `y`, considered? If so, record why the RFC prefers two fixed-direction methods. If `nextafter` is wanted as well, say whether it belongs in this RFC or a later one.]

[TODO: Was leaving this to a crate on crates.io considered? If so, record why the operation belongs in `core`.]

## Prior art

IEEE 754 defines nextUp and nextDown as required operations. C99 provides `nextafter` and `nexttoward`, which take a direction argument. [TODO: add other languages the author wants to compare against, with links, and describe each from its documentation.]

## Unresolved questions

- Whether the methods are `const fn` (see the reference-level explanation).
- Whether the documentation promises anything about the NaN that is returned.
- Whether to add a two-argument `next_after` in the same feature or later.
