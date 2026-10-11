# RFC 2867: `isa_attribute`

- Feature Name: `isa_attribute`
- Start Date: 2018-03-14
- Tracking Issue: (to be assigned)
- Status: Proposed

## Summary

This RFC proposes a new function attribute, `#[instruction_set(set)]`, which lets a programmer declare the instruction set that the compiler should use when generating code for a particular function. It also proposes two initial allowed values for the ARM architecture: `arm::a32` and `arm::t32`. Other allowed values may be added to the language later, without changing the design of the attribute itself.

## Motivation

ARM processors have supported more than one instruction encoding for a long time. The A32 encoding uses fixed 32-bit instructions, while the T32 (Thumb) encoding uses a mix of 16-bit and 32-bit instructions. Many ARM cores can switch between the two at runtime, and the choice affects code size, performance, and which operations are available.

Today, Rust has no way to express this choice at the level of a single function. The target triple determines the instruction set for an entire crate, and the only available control is through codegen flags or target features that apply to the whole build. This is a poor fit for embedded projects, where a small number of hot routines might benefit from one encoding while the rest of the firmware is best compiled with another. It is also a poor fit for projects that need to interoperate with existing assembly or C code built for a specific instruction set.

The existing workarounds are not satisfactory. Developers can write the affected functions in assembly and link them in, which loses the type checking and optimization available to Rust code. They can split the code into separate crates and compile each with different flags, which is cumbersome and cannot be applied at the granularity of a single function. A function-level attribute gives the programmer direct control while keeping the code in one place and under the normal compiler pipeline.

## Guide-level explanation

The attribute is written on a function item:

```rust
#[instruction_set(arm::t32)]
fn fast_checksum(data: &[u8]) -> u32 {
    // ...
}
```

When the compiler generates code for `fast_checksum`, it uses the T32 encoding. Other functions in the same crate are compiled according to the crate's default. The attribute does not change the signature of the function, its calling convention as seen from Rust, or its behavior as observed by the caller. It only changes how the body is encoded.

Two values are accepted on the ARM architecture:

- `arm::a32` selects the 32-bit fixed-width ARM encoding.
- `arm::t32` selects the Thumb encoding.

Using the attribute on a target that does not support instruction set selection is a compile-time error. The error message names the target and lists the sets that the target does support, so that the programmer can remove the attribute or change the target.

Calls between functions that use different instruction sets are ordinary calls. The compiler inserts whatever interworking code the target requires, which on ARM means the branch-exchange sequence needed to change state. Programmers do not need to write this code by hand.

## Reference-level explanation

The attribute takes exactly one argument, which must be a path naming one of the accepted values. Any other form is rejected with an error. The attribute may appear only on free functions and inherent or trait methods that have a body. It may not appear on declarations without a body, on closures, or on items inside `extern` blocks.

The compiler maps each accepted value to a codegen setting for the function. For `arm::a32` and `arm::t32`, this setting selects the corresponding encoding in the backend. Functions without the attribute continue to use the default for the current target.

The attribute does not affect type checking, borrow checking, or the set of items that are visible to the compiler. It is applied during code generation, after those phases have completed. This keeps the feature orthogonal to the rest of the language.

Inlining across instruction sets is not permitted by default. A function marked with one instruction set is not inlined into a function that uses another, because doing so would require the compiler to re-encode the body. The compiler may still inline functions that share the same set. Programmers who require a specific inlining decision should use the existing inlining attributes together with this one, and the interaction should be documented in the reference.

Symbols are not decorated with the instruction set. A caller links against the symbol name as usual. The linker and the backend handle the state transition at the call site.

## Drawbacks

The attribute adds a new concept that some programmers will need to understand, and it introduces a per-function setting that interacts with inlining and with the target. Teams that are not working on ARM will see an attribute that does nothing useful for them, which may be confusing. There is also a maintenance cost: every new backend that supports instruction set selection must implement the mapping and document it.

There is a risk of misuse. A programmer who mixes encodings carelessly may find that the performance benefit is outweighed by the cost of frequent state transitions. The documentation should warn about this, and the compiler should not attempt to second-guess the choice.

## Rationale and alternatives

An alternative is a target-wide setting controlled by a flag, which is what most compilers offer today. This is simple, but it is too coarse for the cases described above. Another alternative is a new target triple for each combination of settings, which multiplies the number of targets and complicates distribution of the standard library. A third is to leave the matter to inline assembly, which is available but gives up most of the benefits of writing Rust.

The proposed design chooses a function attribute because the choice is naturally made per function, and because attributes are already the language's mechanism for expressing per-item codegen settings. Restricting the initial set of values to two ARM encodings keeps the scope small. The set of values is open to extension, so that other architectures with alternative encodings can be supported later without redesigning the attribute.

Naming the values with paths, such as `arm::t32`, rather than with strings, keeps them checked by the compiler and avoids typos being discovered only at link time.

## Prior art

Several C and C++ compilers support function-level attributes or pragmas that select between ARM and Thumb code generation. These mechanisms are widely used in embedded toolchains. The experience from those systems suggests that per-function selection is practical and that the main difficulties lie in interworking and inlining, both of which are addressed in this proposal.

## Unresolved questions

- Whether the attribute should be stabilized together with the two ARM values, or whether the values should remain unstable until more experience is gained.
- How the attribute interacts with link-time optimization, in particular whether the linker may merge functions that differ only in instruction set.
- Whether a future version should allow the attribute on closures, which would require a decision about how closure bodies are lowered.
- The precise wording of the diagnostic for unsupported targets, which will be settled during implementation review.

## Future possibilities

Future RFCs could add instruction set values for other architectures, such as those with alternative encodings for specialized processors. They could also add a crate-level default that individual functions may override, which would reduce the annotation burden in projects that mostly use one set. A later design could integrate the attribute with target feature detection, so that code can select an instruction set based on what the running processor supports. None of these extensions is required for the present proposal, and each would be considered in its own right.
