# RFC 3173: `float_next_up_down`

- Status: [TODO: status and tracking issue link]
- Affects: `f32` and `f64` in the standard library

## Summary

This RFC adds two argument-free methods to `f32` and `f64`, `next_up` and `next_down`. Each returns the floating-point value adjacent to `self` in the direction its name gives. The operations are specified in IEEE 754, and they give programs a direct way to step through the floating-point values in order.

## Motivation

Floating-point values are not evenly spaced. Between any two adjacent representable values there is a gap, and the size of that gap changes with the magnitude of the value. A program that needs to walk the set of finite values in order, for example to test a function at every neighbor of a boundary point, has to know where the next value is. [TODO: state how users currently obtain the adjacent value, and what they must assume about the representation to do so.]

The obstacle is that the next value cannot be computed reliably by ordinary arithmetic. Adding the smallest step to a value does not produce the next value when the step is below the gap at that magnitude, and the gap itself changes across powers of two. [TODO: add a concrete case from the material where a naive approach returns the wrong neighbor, or a user request that needed this operation.]

## Design

The proposal adds `next_up(self) -> Self` and `next_down(self) -> Self` to both float types. [TODO: confirm the signatures and return types, and whether the methods are `const`.]

The methods follow the IEEE 754 definitions, so their results are fixed by the standard and do not depend on the platform. The force behind this choice is the goal of enumerating values in order: an enumeration is only useful if every implementation returns the same neighbor. A method with a looser definition would give different answers on different targets.

Several cases decide the result, and the RFC must say what they are:

- The result for NaN. [TODO: state the result for NaN input.]
- The result for the infinities and for the largest finite value. [TODO: state whether `next_up` on the largest finite value returns infinity.]
- The result for zero, where positive and negative zero are adjacent to the smallest subnormal values. [TODO: state the result for both signed zeros.]
- The result for subnormal values. [TODO: confirm that subnormals step by the subnormal spacing, not the normal spacing.]

The authors should say which of these follow from the standard and which are choices the RFC makes.

## Alternatives considered

[TODO: list the alternatives the authors considered, for example leaving enumeration to external crates, or exposing bit-level conversions for users to build the neighbors themselves. These are not recorded in the material, so they are not presented here as considered or rejected. Each one needs the reason it lost.]

## Cost accepted

Adding methods to a primitive type expands its public surface on every target that supports it. Once stabilized, the names and the exact behavior at the edge cases become part of the public API, and changing either is a breaking change. [TODO: state any cost the authors accept beyond this, such as the number of methods added to a type that already has many, or interaction with future operations of the same family.]

## Reversibility

Stabilization is the expensive step. Before stabilization the names can change. After it, the methods can be deprecated but not removed without a breaking change, and the edge-case behavior should be fixed by then. [TODO: confirm the stabilization plan and whether any part of the behavior is expected to change.]

## Drawbacks

[TODO: state the drawbacks the authors see, or state that none apply and why.]

## Unresolved questions

- [TODO: name the questions still open at the time of this draft, and the input each one needs.]
- [TODO: decide whether the edge-case results are settled or still under discussion.]
