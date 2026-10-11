# Rust RFC 3173: float_next_up_down

## Summary

This RFC adds two methods to `f32` and `f64`: `next_up` and `next_down`. Neither takes an argument besides `self`. The IEEE 754 standard specifies both operations. Together they let a program step through floating point values in order, one representable value at a time.

## Motivation

Floating point numbers are a finite, ordered set. Between two adjacent values there is no other value, and the gap between neighbours grows with the magnitude of the number. Some programs need to move from a value to its neighbour. Examples are a test that checks a function at the value just below a boundary, a range check that turns a closed bound into an open one, and a search over all floats in an interval.

Today a Rust program has no method for this step. The standard library offers `to_bits` and `from_bits`, so a program can reach the neighbour by reading the bit pattern, adding or subtracting one, and converting back. That works for positive finite numbers. It fails for the cases where the sign, zero, infinities and NaN interact with the integer representation:

- For a negative number, adding one to the bit pattern moves the value away from zero, which means down, not up.
- For positive zero and negative zero, the bit patterns differ, but both values must step to the same smallest positive subnormal number when moving up.
- For the largest finite value, adding one to the bit pattern produces infinity, which is correct, but for infinity itself it produces a NaN pattern, which is not.

Each of these cases is easy to get wrong in a hand-written helper, and a wrong helper fails only on the rare inputs. [TODO: the author should supply concrete incidents, crates or issues where programs hand-rolled this step and got it wrong, or state that none are known.]

IEEE 754 defines the two operations as `nextUp` and `nextDown`. Naming and semantics therefore come from the standard and do not need a new design.

## Guide-level explanation

`x.next_up()` returns the smallest floating point value of the same type that is greater than `x`. `x.next_down()` returns the largest value that is less than `x`. In both calls, "value" means a member of the type, not a real number.

The example below shows the gap between neighbours for `1.0_f32`.

```rust
let x = 1.0_f32;
assert!(x.next_up() > x);
assert_eq!(x.next_up(), 1.0 + f32::EPSILON);
assert_eq!(x.next_up().next_down(), x);
```

`f32::EPSILON` is the distance from `1.0` to the next larger `f32`, so the second assertion states the definition of that constant in terms of the new method. Below `1.0` the neighbours are closer together, so `x.next_down()` differs from `x` by half of `f32::EPSILON`. The two methods are inverses on finite values, as the third assertion shows, with exceptions at the ends of the range listed in the next section.

A program that wants every `f32` in ascending order can start at `f32::NEG_INFINITY` and call `next_up` until it reaches `f32::INFINITY`. Such a loop is a way to test a function on every input, though it runs about four billion iterations for `f32`. [TODO: the author should confirm whether the RFC wants to mention exhaustive testing as a use case.]

## Reference-level explanation

The methods are inherent methods on `f32` and `f64`.

```rust
impl f64 {
    pub fn next_up(self) -> Self;
    pub fn next_down(self) -> Self;
}
```

The same two signatures apply to `f32`. [TODO: the author should state whether the methods are `const fn` and whether they are stabilized together with the feature gate named `float_next_up_down`.]

The behaviour follows the `nextUp` and `nextDown` operations in IEEE 754. [TODO: check the cases below against the standard text before merging; they are written here from the definition of the operations, not from the standard.]

| Input | `next_up` | `next_down` |
|---|---|---|
| finite, not zero | the next greater representable value | the next smaller representable value |
| `+0.0` or `-0.0` | smallest positive subnormal | smallest negative subnormal |
| largest finite value | `+infinity` | the next smaller finite value |
| `+infinity` | `+infinity` | largest finite value |
| `-infinity` | smallest-magnitude finite negative step from `-infinity`, that is `-MAX` | `-infinity` |
| NaN | NaN | NaN |

The zero row means that the two zeros are not distinguished: `(-0.0).next_up()` and `(0.0).next_up()` return the same value, and so do `next_down` calls. The table implies that `next_up` of `-MIN_POSITIVE_SUBNORMAL` is `-0.0`. The sign of that zero is a detail the standard fixes, and the RFC adopts it unchanged. [TODO: confirm this entry against the standard.]

A direct implementation works on the bit pattern. For a positive finite `x`, `next_up` adds one to the bits. For a negative finite `x`, it subtracts one from the bits, which reduces the magnitude. Zero and the non-finite values are handled before this step. `next_down(x)` is `-next_up(-x)`. [TODO: the author should say whether the RFC specifies the implementation or only the results, and whether the NaN payload is preserved.]

The methods do not change the floating point environment, raise no exceptions in the IEEE sense and do not panic. [TODO: confirm. The standard signals underflow or overflow in some cases for `nextUp`; the RFC should state what Rust does about that.]

## Drawbacks

The RFC adds two names to the public API of two primitive types, and that API cannot be removed after stabilization. Every addition to `f32` and `f64` also takes the name away from user traits that define a method with the same name. A user trait implemented for floats with a `next_up` method would become ambiguous at call sites in the way the compiler already reports for other inherent-versus-trait clashes. [TODO: the author should estimate how common such traits are, for example by searching published crates. No data was supplied for this draft.]

The methods offer a small convenience for the programs that need them. The bit-twiddling alternative exists, so the cost of rejecting the RFC is that those programs keep writing their own helpers.

## Rationale and alternatives

The deciding reason in the abstract is that IEEE 754 already specifies these operations. Adopting the standard's names and semantics means that a reader who knows `nextUp` from C, or from another language, knows what the method does. [TODO: the author should say what other languages and libraries expose these operations, and under what names. This draft knows only the standard.]

The following alternatives are suggestions for the author to evaluate. They are not options the author has recorded as considered.

- A single method `next_after(self, toward: Self)`, in the style of the C function `nextafter`. It covers both directions with one name. It takes an argument where the abstract specifies none.
- A method that returns the gap to the neighbour (the unit in the last place) and leaves the arithmetic to the caller. It answers a different question and does not give the neighbour at the boundaries where the gap changes.
- No change to `std`, with the helper left to an external crate. This is the status quo, and the Motivation section argues against it only for programs that cannot afford a dependency or want standard semantics. [TODO: the author should supply the reason the helper belongs in `core`.]

The choice of two methods with no extra arguments is reversible only before stabilization. After that, the names and the NaN, zero and infinity behaviour are fixed.

## Prior art

The RFC takes the operations from IEEE 754. [TODO: citation of the standard revision and the section number. Other implementations, such as libm functions in C or equivalents in other language libraries, need to be cited by the author; none were supplied.]

## Unresolved questions

- Should the methods be `const fn` at the time of stabilization? [TODO: depends on whether `to_bits` and `from_bits` are usable in const contexts at that time.]
- Should the RFC also add `next_up` and `next_down` for `f16` and `f128` if those types exist in the language at the time of writing? [TODO]
- Should NaN payload and sign be preserved or canonicalized? [TODO]

## Future possibilities

The author may later want an iterator over a closed interval of floats, built on `next_up`. This RFC does not propose one, and nothing in it depends on one.
