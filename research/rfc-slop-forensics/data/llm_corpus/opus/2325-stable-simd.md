- Feature Name: `vendor_intrinsics`
- Start Date: 2018-02-04
- RFC PR: rust-lang/rfcs#2325
- Rust Issue: rust-lang/rust#48556

# Summary

This RFC sets out a framework for using SIMD on stable Rust. It proposes stabilizing the x86 and x86_64 vendor intrinsics, the functions Intel and AMD document for their SIMD instruction sets. It also lays down the scaffolding for other platforms and for a future portable SIMD design, which another RFC will cover.

# Motivation

SIMD (single instruction, multiple data) instructions do the same operation on several values at once. Modern CPUs offer hundreds of them across SSE, AVX, AVX2, AVX-512, NEON, and other extensions. Done well, SIMD code can be several times faster than scalar code in compression, hashing, image processing, string searching, linear algebra, and parsing.

Today Rust can only reach these instructions on nightly, through the unstable `platform_intrinsics` and `repr(simd)` features. That leaves a gap:

- Crates that want SIMD, such as `regex`, `memchr`, `encoding_rs`, and `byteorder`, either need nightly, fall back to slower scalar code on stable, or link C code compiled separately.
- C and C++ programmers moving to Rust find they can't port their hand-written SIMD kernels.
- LLVM's auto-vectorizer helps, but it can't express everything and it is fragile. Small source changes can stop it vectorizing.

The goal is to let library authors write SIMD code on stable Rust as soon as possible, without committing to a portable SIMD abstraction whose design isn't settled.

# Guide-level explanation

## The `std::arch` module

A new module, `std::arch` (also available as `core::arch`), holds one submodule per architecture:

```rust
std::arch::x86
std::arch::x86_64
std::arch::arm      // future
std::arch::aarch64  // future
```

Each submodule exposes the vendor's intrinsics with the vendor's names and signatures. For x86 this means Intel's documented names:

```rust
use std::arch::x86_64::*;

unsafe {
    let a = _mm_set1_epi32(1);
    let b = _mm_set1_epi32(2);
    let c = _mm_add_epi32(a, b);
}
```

Using the vendor names means Intel's Intrinsics Guide, existing C code, and Stack Overflow answers all apply directly. Rust doesn't invent a parallel vocabulary.

The vector types are opaque: `__m128`, `__m128i`, `__m128d`, `__m256`, `__m256i`, `__m256d`. They have no arithmetic operators. They are bit containers that intrinsics take and return, as in C.

## Target features

Not every x86 CPU supports AVX2. Executing an AVX2 instruction on a CPU without it is undefined behavior (in practice a crash). Rust therefore needs a way to compile some code for a particular feature and to choose at runtime whether to run it.

**Compile-time enabling.** The existing `-C target-feature=+avx2` flag enables a feature for the whole crate. `cfg!(target_feature = "avx2")` reports whether it is enabled.

**Per-function enabling.** A new attribute, `#[target_feature(enable = "avx2")]`, compiles a single function as if the feature were enabled:

```rust
#[target_feature(enable = "avx2")]
unsafe fn sum_avx2(xs: &[i32]) -> i32 {
    // may use AVX2 intrinsics
}
```

Such functions must be `unsafe fn`. Calling one on a CPU without the feature is undefined behavior, and the compiler can't check that for you.

**Runtime detection.** A new macro, `is_x86_feature_detected!("avx2")`, asks the CPU at runtime:

```rust
pub fn sum(xs: &[i32]) -> i32 {
    #[cfg(any(target_arch = "x86", target_arch = "x86_64"))]
    {
        if is_x86_feature_detected!("avx2") {
            return unsafe { sum_avx2(xs) };
        }
    }
    sum_scalar(xs)
}
```

This lets one binary run on any x86_64 CPU and still use AVX2 where the CPU has it.

## All intrinsics are `unsafe`

Every intrinsic in `std::arch` is an `unsafe fn`. Most of them are memory-safe in themselves (`_mm_add_epi32` touches no memory), but they are only defined on CPUs with the right feature. Marking them all `unsafe` puts the responsibility in one clear place, the caller who checked the feature. Safe wrappers are left to libraries.

# Reference-level explanation

## Stabilized items

For `x86` and `x86_64`, this RFC stabilizes:

- the vector types `__m128`, `__m128d`, `__m128i`, `__m256`, `__m256d`, `__m256i`;
- all intrinsics for SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX, AVX2, FMA, BMI1, BMI2, LZCNT, POPCNT, ABM, TBM, and related extensions, with Intel's names and signatures;
- `#[target_feature(enable = "...")]` with the feature names those extensions use;
- `is_x86_feature_detected!`;
- `cfg(target_feature = "...")` for those features.

AVX-512 is left out because its API surface is very large and its mask types need more design.

Other architectures will be stabilized in follow-up work, using the same structure: an `std::arch::<arch>` module, vendor names, and an `is_<arch>_feature_detected!` macro.

## Signatures

Intrinsics that take immediate operands (compile-time constants encoded in the instruction) are declared with ordinary integer parameters. Passing a non-constant value is a compile error. The `rustc_args_required_const` attribute is used internally to enforce this. A later version could switch to const generics without breaking callers who pass literals.

Pointer arguments use `*const T` and `*mut T` of the element type, matching the C signatures as closely as Rust's type system allows.

## Implementation

The intrinsics live in the `stdsimd` repository, which `libcore` includes. Most are thin wrappers over LLVM intrinsics or over generic `simd_*` platform intrinsics. An automated test suite checks every intrinsic's signature against Intel's XML specification and checks that it compiles to the expected instruction.

## Inlining and `target_feature`

A function with `#[target_feature]` can't be inlined into a caller that lacks the feature, because the inlined code could run on hardware without it. LLVM already enforces this. As a result, intrinsics only become single instructions when called from functions with the matching features. Otherwise they become calls, which is correct but slow. The documentation will explain this.

# Drawbacks

- **The API is enormous.** Stabilizing thousands of functions in one go is unprecedented for `std`. Reviewing each one isn't practical, so the RFC relies on mechanical checks against the vendor specification.
- **It is unsafe and unidiomatic.** The intrinsics are hard to use and easy to misuse. Most users should wait for a portable SIMD API or use a crate.
- **The names are ugly.** `_mm256_shuffle_epi8` is not what Rust names usually look like. That is intentional, but it may surprise people.

# Rationale and alternatives

## Portable SIMD first

A portable API, in which `u32x4` and similar types support `+` and `*` and compile to whatever instructions the target has, is the better long-term design. The design questions there (types, masks, shuffles, reductions, and what to do about missing instructions) are still open, though, and holding vendor intrinsics back for it would leave stable users waiting for years. Vendor intrinsics are also a foundation on which portable abstractions can be built in libraries and tried out on stable.

## Rust-style names

Renaming intrinsics to `add_i32x4` and so on was rejected. It would cut Rust off from the existing documentation, and a full rename would be a large design effort with little benefit.

## Leave it to crates

Without compiler support for `target_feature` and the intrinsics themselves, crates can't do this on stable. The language has to provide the foundation.

# Prior art

- **C and C++** expose the same intrinsics through `<immintrin.h>` and `<arm_neon.h>`, with `__attribute__((target("avx2")))` and `__builtin_cpu_supports`. This RFC follows that model closely.
- **Go** has no intrinsics and uses hand-written assembly for SIMD.
- **C#/.NET** added hardware intrinsics in `System.Runtime.Intrinsics.X86` with similar names and an `IsSupported` property per instruction set.

# Unresolved questions

- Should `#[target_feature]` functions eventually be callable safely from contexts that already have the feature enabled?
- How should AVX-512 and ARM's SVE, with their scalable vectors and mask registers, be exposed?
- The design of portable SIMD is left to a separate RFC.
