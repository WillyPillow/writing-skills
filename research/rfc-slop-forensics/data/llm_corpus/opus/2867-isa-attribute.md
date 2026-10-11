- Feature Name: `isa_attribute`
- Start Date: 2020-02-16
- RFC PR: [rust-lang/rfcs#2867](https://github.com/rust-lang/rfcs/pull/2867)
- Rust Issue: N/A

# Summary

This RFC adds a function attribute, `#[instruction_set(set)]`, which declares the instruction set a function should be compiled for. Two initial values are proposed for the ARM architecture: `arm::a32` and `arm::t32`. More values, for ARM or for other architectures, can be added later through the normal process.

```rust
#[instruction_set(arm::t32)]
fn compact_helper(x: u32) -> u32 {
    x.wrapping_mul(3).rotate_left(5)
}

#[instruction_set(arm::a32)]
unsafe extern "C" fn irq_entry() {
    // ...
}
```

# Motivation

Many ARM processors can execute more than one instruction set. Older and embedded cores in the ARMv4T through ARMv7 families support both A32 (the original 32-bit fixed-width encoding, historically called "ARM") and T32 (the mixed 16/32-bit encoding, historically called "Thumb"). The core switches between them at runtime: a branch-and-exchange instruction (`BX` or `BLX`) to an address with the low bit set enters T32 mode, and one with the low bit clear enters A32 mode.

The two encodings have different strengths. T32 code is usually 25 to 35 percent smaller, which matters when the code lives in a few kilobytes of flash or must fit in a fast but tiny cache. A32 code can be faster for some inner loops, has access to some instructions that T32 lacks on certain cores, and is sometimes required outright. On the ARM7TDMI, for instance, exception vectors are always entered in A32 mode, so the first instructions of an interrupt handler must be A32 code.

Today Rust only lets a crate choose one instruction set, and only for the whole compilation, through the target. `armv4t-none-eabi` produces A32 code and `thumbv4t-none-eabi` produces T32 code. A project that wants mostly T32 code with a handful of A32 functions has no good options:

- It can write the A32 parts in assembly, in a separate file, and link them in. This is what most Game Boy Advance and similar projects do today. It works, but it throws away the reason for using Rust in the first place for that code.
- It can split the program into several crates and build some with one target and some with another, then link them together. Cargo does not support this well, the standard library and `core` would need to be built twice, and generic code cannot cross the boundary in any useful way.
- It can use a nightly-only `target_feature` that LLVM happens to accept, such as `+thumb-mode`. This is not stable, not documented, and mixes "what the hardware supports" with "which encoding to emit", which are different questions.

C compilers solved this long ago. GCC and Clang both accept `__attribute__((target("arm")))` and `__attribute__((target("thumb")))` on individual functions, and the linker inserts the interworking veneers needed when an A32 function calls a T32 function or the other way round. Rust code should be able to do the same.

# Guide-level explanation

The `instruction_set` attribute can be placed on a function definition. It takes a single path naming an instruction set:

```rust
#[instruction_set(arm::a32)]
fn this_is_a32() { /* ... */ }
```

The compiler generates the body of that function using the named instruction set, regardless of the default for the target. Callers do not need to know or care; calling `this_is_a32()` from T32 code works like any other call. The toolchain handles the mode switch.

The attribute is only accepted on targets where the named instruction set is meaningful. Using `arm::t32` on an x86_64 target, or on an AArch64 target running in 64-bit state, is a compile error:

```text
error[E0779]: target does not support `#[instruction_set]`
 --> src/lib.rs:1:1
  |
1 | #[instruction_set(arm::t32)]
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

Programs that need to support several targets can combine the attribute with `cfg_attr`:

```rust
#[cfg_attr(target_arch = "arm", instruction_set(arm::a32))]
fn hot_loop(buf: &mut [u32]) { /* ... */ }
```

The attribute is a hint about code generation, not a change to the function's type or signature. A function pointer to an `arm::a32` function has the same type as a function pointer to an `arm::t32` function, and the two can be stored in the same variable. The low bit of the address carries the mode information at runtime, exactly as it does in C.

# Reference-level explanation

## Syntax

```text
InstructionSetAttribute :
    `instruction_set` `(` SimplePath `)`
```

The path is resolved against a fixed, compiler-known namespace. It is not looked up through the normal name resolution of the crate, so a user cannot shadow `arm::a32` by defining a module called `arm`.

At most one `instruction_set` attribute may appear on a function. Applying it to anything other than a function or method with a body (a struct, a trait method without a default body, an `extern` block declaration) is an error.

## Initial values

| Value      | Meaning                                                     |
|------------|-------------------------------------------------------------|
| `arm::a32` | Generate A32 code (the "ARM" instruction set).              |
| `arm::t32` | Generate T32 code (the "Thumb" or "Thumb-2" instruction set). |

These are accepted when `target_arch = "arm"`. Whether a particular target actually supports both modes depends on the CPU; for example, Cortex-M targets only support T32. Asking for `arm::a32` on a T32-only target is an error.

## Interaction with inlining

A function with an `instruction_set` attribute cannot be inlined into a function compiled for a different instruction set, since the result would mix two encodings in one body. When the instruction sets differ, the compiler treats the call as not inlinable. `#[inline(always)]` on such a function produces a warning when it cannot be honored, rather than a hard error, because the call site may be generic or behind another layer of inlining that the user cannot see.

Inlining a function into a caller with the *same* instruction set is allowed as normal.

## Interaction with `target_feature`

`instruction_set` and `target_feature` answer separate questions. `target_feature` says which optional hardware features the code may assume. `instruction_set` says which encoding the code is emitted in. Both can appear on the same function.

## Closures and nested items

The attribute applies to the function it is placed on. It does not propagate to closures defined inside that function, nor to nested `fn` items. A closure can be given its own attribute once attributes on closures are stable for this purpose; until then, users who need a specific mode for a closure can write a named function.

# Drawbacks

- This adds an architecture-specific attribute to the language. Rust has tried to keep such things inside `core::arch` and `target_feature`. The counterargument is that the decision of which encoding to emit cannot be expressed as a library function; it has to be a property of code generation.
- Some of the knowledge needed to use this correctly (which exception handlers must be A32, which instructions are missing from T32 on a given core) lives in vendor manuals, not in the compiler. The attribute does not protect against those mistakes.
- It increases the surface area that alternative backends, such as Cranelift or GCC, need to support.

# Rationale and alternatives

**Use `target_feature(enable = "thumb-mode")`.** This reuses an existing attribute, but `target_feature` is designed for features that can be detected and are additive. Thumb mode is neither: enabling it does not add capability, it changes encoding. Overloading `target_feature` would also make `is_arm_feature_detected!("thumb-mode")` a confusing question.

**Use a string argument like C does.** `#[instruction_set("thumb")]` would be familiar to C programmers, but paths give a clear namespace per architecture and room for future additions without collisions, for example if a different architecture also had a mode called "compact".

**Do nothing.** Users can keep writing the relevant functions in assembly. This works, but it is the status quo that motivated the RFC, and it is a real barrier for the retro-console and microcontroller communities.

# Prior art

- GCC and Clang: `__attribute__((target("arm")))` and `__attribute__((target("thumb")))`, plus `#pragma GCC target`.
- ARM's own compiler (armcc) used `#pragma arm` and `#pragma thumb`.
- MIPS compilers support `__attribute__((mips16))` and `__attribute__((micromips))` for the same reason, which is one of the likely future additions to this attribute.

# Unresolved questions

- Should the attribute be allowed on closures directly?
- What should happen when the attribute is applied to a function marked `#[naked]`? The naked function's body is assembly, so the attribute arguably only affects the symbol's low bit.
- Exact error codes and wording.

# Future possibilities

- `mips::mips16` and `mips::micromips` for MIPS targets.
- `riscv::compressed` or similar, if a meaningful per-function control for RISC-V's C extension is ever wanted.
- A module-level or crate-level form of the attribute, so large parts of a crate can opt into one mode without annotating every function.
