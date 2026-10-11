# RFC 2867: isa_attribute

- Feature Name: `isa_attribute`
- Start Date: 2019-09-12
- RFC PR: rust-lang/rfcs#2867
- Rust Issue: rust-lang/rust#74727

## Summary

This RFC proposes a new function attribute, `#[instruction_set(set)]`, which allows you to declare the instruction set to be used when compiling the function. It also proposes two initial allowed values for the ARM architecture (`arm::a32` and `arm::t32`). Other allowed values could be added to the language later.

## Motivation

Some targets support more than one instruction set. The clearest example is 32-bit ARM, where a processor may execute either the "ARM" instruction set (called A32 in recent documentation) or the "Thumb" instruction set (T32). The two sets are not interchangeable. A32 instructions are all four bytes wide and give access to the full set of conditional execution flags and addressing modes. T32 instructions are a mix of two and four bytes, which gives denser code at the cost of some expressiveness. On many chips, particularly small embedded ones, code fetched from slow flash memory benefits from Thumb's density, while hot code copied into fast RAM benefits from ARM's richer instructions.

Today, the instruction set used for a given function is determined by the compilation target. A target such as `thumbv6m-none-eabi` makes every function T32, and a target such as `armv5te-unknown-linux-gnueabi` makes every function A32. A programmer who wants a mix has to either split the program into separate crates compiled for different targets, which is awkward and breaks cross-crate inlining, or reach for assembly.

There are several concrete scenarios where mixing is required:

* On the Game Boy Advance, the CPU is an ARM7TDMI. The cartridge ROM is connected over a narrow 16-bit bus, so executing A32 code directly from ROM is slow because each instruction needs two fetches. The ordinary advice is to compile most code as T32 and to place a small number of hot routines in the internal work RAM, which has a 32-bit bus, compiled as A32.
* Interrupt handlers on some ARM cores are entered in A32 state regardless of which state the interrupted code was in, so the handler's entry point must be A32 even when the rest of the program is T32.
* Some instructions exist only in one set. A function that wants to use the `SWP` instruction or conditional execution of arbitrary instructions needs A32.

C and C++ toolchains have supported this for a long time through function attributes such as GCC's `__attribute__((target("arm")))` and `__attribute__((target("thumb")))`. Rust lacks an equivalent, which is a barrier to using it on these devices.

## Guide-level explanation

The `instruction_set` attribute can be placed on a function to say which instruction set that function should be compiled with. The attribute takes a single path argument naming the set:

```rust
#[instruction_set(arm::a32)]
fn hot_loop(data: &mut [u32]) {
    for x in data {
        *x = x.wrapping_mul(3);
    }
}

#[instruction_set(arm::t32)]
fn cold_setup() {
    // compact code, runs once
}
```

If the attribute is absent, the function is compiled with whatever instruction set is the default for the target. This means that on a target whose default is T32, an `a32` function is the exception, and the reverse is true on an A32 target.

The attribute is only valid when compiling for an ARM family target that actually supports the named set. Using `arm::a32` on a target that has no A32 mode, such as `thumbv6m-none-eabi` (an M-profile core that only runs Thumb), is a compile error. Using the attribute on a non-ARM target is likewise an error. This follows the principle that a request which cannot be honoured should not be silently ignored.

Calling between functions of different instruction sets works as normal from the point of view of the Rust programmer. The compiler and linker take care of the mode switch, using `BX` and `BLX` style interworking calls where necessary. The programmer does not need to change how they write calls.

The attribute is not inherited. A closure defined inside an `a32` function is compiled with the default instruction set unless it is itself annotated. Inlining across instruction set boundaries is not permitted, because the inlined body would then be compiled in the wrong mode.

## Reference-level explanation

### Syntax

The attribute has the form `#[instruction_set(<set>)]`, where `<set>` is a path. The path is intended to be namespaced by architecture so that other architectures can add their own values without collision. The first two accepted values are:

* `arm::a32`: compile the function using the A32 instruction set.
* `arm::t32`: compile the function using the T32 instruction set.

The attribute may be applied to free functions, inherent methods, and trait method implementations that have bodies. It may not be applied to trait method declarations without a body, since there is nothing to compile. Applying it more than once to the same function is an error. Applying it with an unknown value is an error.

### Interaction with the target

The compiler must reject the attribute if the target does not support the requested set. In terms of the LLVM backend, `arm::a32` corresponds to disabling the `thumb-mode` target feature on the function, and `arm::t32` corresponds to enabling it. Targets that lack the `thumb-mode` feature, or that lack support for ARM mode entirely, produce an error at attribute resolution time.

### Interaction with other attributes

The `instruction_set` attribute is compatible with `#[inline]`, `#[inline(never)]`, `#[cold]`, `#[no_mangle]`, `#[link_section]` and `#[naked]`. For `#[inline(always)]`, a function with an explicit instruction set may not be inlined into a caller with a different set, and the compiler should emit a warning if `#[inline(always)]` cannot be honoured for this reason. The `#[target_feature]` attribute is orthogonal; its features are applied in addition to the mode selection.

Function pointers to `instruction_set` functions have the same type as any other function pointer. The low bit of the address, which the ARM architecture uses to encode the target state for interworking branches, is set appropriately by the compiler and linker. No change to the type system is required.

### Interaction with `const fn`

A `const fn` may carry the attribute. Evaluation at compile time does not depend on the instruction set, so the attribute has no effect on const evaluation.

### Generic and monomorphized code

A generic function with the attribute is compiled with the specified set for every monomorphization. The attribute is part of the function item, not of its instantiation.

## Drawbacks

This adds a new attribute to the language, which has a maintenance and teaching cost. It is also specific to a small number of targets, and the semantic space of "instruction set" is broader than the two ARM modes proposed here. Early stabilization risks committing to a design that fits ARM but not others.

The restriction that functions of differing sets may not be inlined into each other can surprise users, since it may pessimize code that looks trivially inlinable.

Finally, the feature increases the chance of subtle mistakes. A programmer who places an `a32` function in a section that is mapped to a region with a 16-bit bus will see poor performance but no diagnostic.

## Rationale and alternatives

### Why an attribute rather than a `target_feature`?

The existing `#[target_feature(enable = "...")]` mechanism is intended for optional extensions to an instruction set, such as AVX2, where enabling the feature allows the compiler to emit additional instructions. It is `unsafe` to call such functions without checking support. Switching between A32 and T32 is different in kind: it changes the encoding of every instruction in the function. Calling an `a32` function from a `t32` function is not unsafe in the same way, because the hardware on a given ARM core either supports both states or the target is rejected at compile time. Using `target_feature` would conflate these two concerns and would impose `unsafe` calls on code where no safety invariant exists.

### Why not a separate crate per mode?

Splitting by crate works but defeats cross-crate inlining and forces build system complexity onto projects that need only a handful of A32 functions. It also does not compose with generics, which are instantiated in the caller's crate.

### Why a namespaced path?

A bare identifier such as `arm` or `thumb` would pin the design to ARM vocabulary. The `arch::set` path leaves room for, for example, `mips::mips16` or `riscv::compressed` without further syntax.

### Do nothing

Without this attribute, users can write the hot function in an assembly file or `global_asm!`. This loses type checking, makes the function opaque to the optimizer, and is significantly more work than adding an attribute.

## Prior art

GCC and Clang support `__attribute__((target("arm")))` and `__attribute__((target("thumb")))` on ARM, and `__attribute__((mips16))` and `__attribute__((nomips16))` on MIPS. The Rust community around Game Boy Advance development has requested this capability repeatedly, and existing projects work around its absence with custom linker scripts and assembly stubs.

## Unresolved questions

* Should additional architectures be specified in this RFC or deferred? This RFC defers them.
* Should there be a way to query the current function's set at compile time, for example through `cfg`? This RFC does not propose one, since `cfg` is evaluated per crate and not per function.
* How should `#[naked]` functions interact when their body is written in inline assembly that assumes a specific set? The current text leaves this to the author, with the attribute simply setting the assembler mode directive.

## Future possibilities

Future RFCs may add values for other architectures. A `#[instruction_set]` default could also be allowed at the module or crate level, so that a project could say "everything in this module is A32" without annotating each function. Finally, a lint could warn when an `a32` function is placed in a section known to reside on a narrow bus.
