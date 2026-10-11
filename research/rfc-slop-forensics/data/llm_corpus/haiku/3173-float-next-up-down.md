# Rust RFC 3173: float_next_up_down

- Feature Name: `float_next_up_down`
- Start Date: 2021-06-02
- Status: Accepted

## Summary

This RFC adds two methods to the primitive floating-point types `f32` and `f64`: `next_up` and `next_down`. Given a floating-point value, `next_up` returns the least representable value that is strictly greater than it, and `next_down` returns the greatest representable value that is strictly less than it. Both methods take no arguments other than the receiver and follow the behavior specified for the corresponding operations in the IEEE 754 standard. Together they make it possible to step through the ordered set of finite floating-point values in either direction.

## Motivation

Floating-point numbers are not spaced evenly. Between any two powers of two the representable values are equally spaced, but the spacing doubles at each power of two. Code that needs to reason about the exact neighbors of a value currently has to manipulate the bit representation directly, reinterpreting the value as an integer, adding or subtracting one, and reinterpreting it back. This works, but it requires careful handling of the sign bit, of zero, of infinities, and of NaN, and it is easy to get wrong.

Several common algorithms depend on stepping to a neighboring value. Interval arithmetic uses the neighbors of a computed bound to ensure that rounding errors cannot make an interval exclude the true result. Tests of numerical routines often compare results against the nearest representable values on either side of an expected answer. Iterators over ranges of floating-point values need to know where the next value lies. Each of these cases would benefit from a direct, correct operation.

The IEEE 754 standard already specifies these operations under the names nextUp and nextDown. Other languages expose them, and the C standard library provides a related function, nextafter, that takes a direction argument. Rust has no equivalent in its standard library, so users must either write the bit manipulation themselves or depend on an external crate.

## Guide-level explanation

After this change, a programmer can write the following.

```rust
let x: f64 = 1.0;
assert!(x.next_up() > x);
assert!(x.next_down() < x);
assert_eq!(x.next_up().next_down(), x);
```

The values returned are the immediate neighbors of the receiver among all finite values and the infinities. Zero is a special case: `next_up` applied to positive or negative zero returns the smallest positive subnormal value, and `next_down` applied to either zero returns the negative subnormal value of the same magnitude. Applied to the largest finite value, `next_up` returns positive infinity. Applied to negative infinity, `next_up` returns the most negative finite value.

NaN is returned unchanged. Positive infinity is returned unchanged by `next_up`, and negative infinity is returned unchanged by `next_down`.

Users who want to step through a range of values can write a loop that calls `next_up` until a bound is reached. The methods are not intended to replace arithmetic on values that are well separated, but they give a clear answer in the edge cases where arithmetic is ambiguous.

## Reference-level explanation

The methods are added as inherent methods on `f32` and `f64`, with the following signatures.

```rust
pub fn next_up(self) -> Self;
pub fn next_down(self) -> Self;
```

The implementation may be written in terms of the bit representation. For a finite non-zero value, the next value upward has the same sign and a magnitude one unit greater in the last place when the value is positive, and a magnitude one unit smaller when the value is negative. The special cases for zero, infinities, and NaN follow from the ordering of the bit patterns once the sign is handled correctly.

The results must agree with the IEEE 754 definitions for all inputs. Because the operations do not round, they are exact. No floating-point exception is raised by either method, though a signaling NaN input should be quieted as is conventional for operations that return NaN.

The methods are `const fn` if the compiler supports the necessary operations in constant evaluation at the time of stabilization. Otherwise they are plain functions and can be made `const` later without breaking changes.

Documentation for each method should include examples showing the behavior at zero and at the largest finite value, so that readers do not need to consult the standard to understand the edge cases.

## Drawbacks

Adding methods to the primitive types expands the public surface of the standard library, and every addition carries a maintenance cost. The operations are simple, but they are not common, so their benefit must be weighed against the space they occupy in documentation and autocompletion.

Some users may mistake `next_up` for an approximation of addition by a small epsilon. The documentation must make clear that the result is the exact neighbor in the ordered set of representable values, which differs from adding a fixed amount when the value is large or small.

## Rationale and alternatives

The main alternative is to leave these operations to external crates, which already implement them. That keeps the standard library smaller but forces a dependency for a fundamental operation that the standard specifies. The methods are short enough that the cost of including them is low, while the benefit to correctness is significant.

Another alternative is to provide a single function that takes a direction, in the style of the C library's nextafter. That design is compact but makes the direction a runtime value, which is less convenient in the common case where the direction is known. Two named methods read more clearly and match the names used in the standard.

A third alternative is to add the operations to a separate module rather than to the primitive types. This would avoid cluttering the methods on the types, but it would make the operations harder to discover, and the methods are closely related to other floating-point methods that already live on the types.

## Prior art

The IEEE 754 standard defines nextUp and nextDown as part of its required operations. Java provides Math.nextUp and Math.nextDown, which behave the same way for double and float. The C standard provides nextafter, and the C++ standard library provides std::nextafter in the same header. Each of these has been used in numerical libraries for decades, and their behavior at the edges has been stable. The proposed Rust methods follow these precedents closely so that programmers familiar with other languages will find them predictable.

## Unresolved questions

The RFC does not decide whether the methods should be `const` at stabilization. This depends on the state of compile-time floating-point support at the time, and the decision can be made during stabilization.

It is also open whether the documentation should recommend specific uses for the methods. The authors propose a short section with examples from interval arithmetic and testing, but the wording is left to the stabilization report.

## Future possibilities

If these methods are stabilized, the standard library could add helpers built on them, such as an iterator over a half-open range of floating-point values. Interval types in the ecosystem could rely on the methods directly rather than reimplementing them. The methods also make it easier to write portable tests of numerical code, because the expected neighbors of a result can be computed without bit manipulation.
