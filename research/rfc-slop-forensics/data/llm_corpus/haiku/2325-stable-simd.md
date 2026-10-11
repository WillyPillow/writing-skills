# Rust RFC 2325: `vendor_intrinsics`

- Feature Name: `vendor_intrinsics`
- Start Date: 2018-07-05
- RFC PR: rust-lang/rfcs#2325
- Rust Issue: rust-lang/rust#48556

## Summary

This RFC provides a framework for using SIMD on stable Rust. It proposes stabilizing the x86 and x86-64 vendor intrinsics, which are the functions that expose a processor's vector instructions directly. It also sets out the scaffolding that other platforms will use to add their own vendor intrinsics, and it describes the intended shape of a portable SIMD design. The portable design itself is left to a separate RFC.

## Motivation

Vector instructions are among the most effective tools for speeding up numerical and byte-oriented code. Modern processors provide wide registers and instructions that operate on many values at once, and programs that use them can run several times faster than scalar code. Rust programmers have been able to reach these instructions only through nightly features, which means that a library depending on them cannot be used on the stable toolchain.

The vendor intrinsics are the most direct route to these instructions. Each one corresponds to a single machine operation or a small sequence, and each is named by the vendor in its documentation. Exposing them on stable gives library authors a dependable base on which to build. It also lets application programmers use SIMD when they need it, without waiting for a higher-level design to settle.

The RFC is motivated by the observation that the intrinsics are already widely used in the ecosystem, through crates that depend on nightly. Stabilizing them removes a barrier that has pushed authors toward workarounds, including inline assembly and fragile code that depends on compiler behavior.

## Guide-level explanation

The intrinsics appear in the `std::arch` module. On x86 and x86-64, each intrinsic is a function with a name that matches the vendor's documentation, such as an addition of packed integers or a comparison of packed floats. Programmers call these functions inside an `unsafe` block, because many of them require the processor to support a particular feature set.

Support for a feature set is detected at runtime with a macro that checks the processor's capabilities. A program that chooses between a SIMD path and a scalar path uses the detection macro to decide which one to run. The detection is cheap, and the result may be cached by the caller.

Programmers who write code for a particular target can also enable features at compile time. This removes the need for runtime checks, but it limits the resulting binary to processors that support the chosen features.

The RFC does not expect most programmers to write intrinsics directly. It expects that many will use them through libraries, and that the intrinsics will serve as the common foundation those libraries depend on.

## Reference-level explanation

The stabilized surface covers the x86 and x86-64 intrinsics that are already implemented in the compiler and the standard library, grouped by the feature sets that introduced them. Each group is stabilized with the feature name that the processor vendor uses for it, so that detection and documentation match.

The vector types are defined in the same module. They are plain data types with a fixed size and alignment, and they carry no hidden state. Conversions between vector types and arrays are provided through standard traits, so that code can move data in and out of vectors without unsafe operations beyond the intrinsics themselves.

The scaffolding for other platforms defines the module layout and the naming convention. A platform that wishes to expose intrinsics places them in a module named after the architecture, and it uses the same detection and documentation rules. The RFC does not stabilize intrinsics for other architectures, but it fixes the structure so that later additions will not change the shape of the API.

The intrinsics are marked as unsafe where the underlying instruction has a precondition, such as alignment for certain memory operations. Where no precondition exists, the function is safe to call once the feature has been confirmed as available.

The compiler continues to be responsible for the code generated for each intrinsic. The RFC does not change how the compiler lowers the intrinsics to machine instructions.

## Drawbacks

Stabilizing a large set of intrinsics adds a substantial API surface that must be maintained as the compiler evolves. The intrinsics are numerous, and some are rarely used, so the cost of carrying them may be disproportionate to their value.

The intrinsics are also tied to specific processors. Code written against them is less portable than code that uses a higher-level abstraction, and it requires careful testing on each target it supports.

Finally, the unsafe nature of many intrinsics places a burden on programmers, who must verify the preconditions themselves.

## Rationale and alternatives

The main alternative is to wait for a portable SIMD design and stabilize only that. This would give a single, uniform interface, but it would delay the availability of SIMD on stable for an uncertain period, and it could not expose the full range of instructions that vendor intrinsics provide.

A second alternative is to stabilize only a small subset of intrinsics, chosen for their general usefulness. This would reduce the maintenance burden, but it would still leave many programmers without the instructions they need, and the choice of subset would itself be contentious.

The RFC chooses a middle course. It stabilizes the vendor intrinsics as a group, because they share a common model and a common documentation source, and it defines the scaffolding so that the portable design can build on them without disruption.

## Prior art

Other languages expose vendor intrinsics through their standard libraries or through C-compatible headers, and their programmers commonly use them for performance-sensitive code. The C intrinsics headers defined by processor vendors are the closest analogue, and the RFC follows their naming conventions so that existing documentation remains useful.

Several libraries in the Rust ecosystem already wrap the intrinsics for stable use, and their experience informed the choice of which groups to stabilize first.

## Unresolved questions

The exact set of intrinsics to stabilize in the first release is still being finalized. The RFC lists the groups that are ready, and it leaves the others for later stabilization once their tests and documentation are complete.

The detection macro's behavior on platforms without a runtime feature query is not fully specified. This should be settled before the scaffolding is extended to other architectures.

## Future possibilities

A portable SIMD design, built on the intrinsics and the scaffolding described here, would give programmers a single interface that compiles efficiently across targets. Such a design would be the subject of a later RFC. The vendor intrinsics stabilized by this proposal would remain available as an escape hatch for code that needs exact control over the instructions it uses.
