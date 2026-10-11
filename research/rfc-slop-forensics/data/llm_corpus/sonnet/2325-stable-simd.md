# RFC 2325: vendor_intrinsics

- Feature Name: `stable_simd`
- Start Date: 2018-02-20
- RFC PR: rust-lang/rfcs#2325
- Rust Issue: rust-lang/rust#48556

## Summary

The purpose of this RFC is to provide a framework for SIMD to be used on stable Rust. It proposes stabilizing x86-specific vendor intrinsics, but includes the scaffolding for other platforms as well as a future portable SIMD design (to be fleshed out in another RFC).

## Motivation

SIMD (single instruction, multiple data) lets a processor apply one operation to several values at once. Modern CPUs expose it through wide registers and dedicated instructions, such as SSE and AVX on x86, NEON on ARM, and AltiVec on PowerPC. For workloads like image processing, cryptography, compression, text search and numeric kernels, SIMD can make code several times faster than scalar code.

Rust has had unstable access to SIMD since before 1.0, through the `simd_ffi` and platform intrinsics features, and the `stdsimd` crate has since provided a more complete, in-tree implementation. But none of it is available on the stable channel. Programmers who need SIMD today must either use nightly, write assembly through `build.rs` and FFI, or rely on the compiler's auto-vectorizer, which is unpredictable and often cannot exploit the instructions that matter most.

This is a notable gap. Rust competes with C and C++ for performance-sensitive work, and in those languages vendor intrinsics are available out of the box, via `<immintrin.h>` and similar headers. A language that claims zero-cost abstractions should let users access the hardware.

The existing popular crates (`memchr`, `regex`, `ripgrep` and various hashing libraries) have already shown the value of SIMD, and several have had to maintain nightly-only code paths or limit themselves to what LLVM happens to vectorize.

### Why vendor intrinsics first

There are two broad approaches to SIMD in a language: portable abstractions (`f32x4`, `u8x16` with operations that map to whatever the target supports) and vendor-specific intrinsics that map one-to-one onto machine instructions. Portable SIMD is the better long-term interface, but its design is large and involves hard questions about masks, lane counts, and performance portability. Vendor intrinsics are mostly mechanical: the vendors have already specified them, and C programmers have used them for two decades.

By stabilizing intrinsics first, we unblock real users now and obtain experience that informs the portable design.

## Guide-level explanation

### Using intrinsics

The standard library gains a module `std::arch` (and `core::arch`), containing a submodule for each supported architecture. For x86 and x86-64, these are `std::arch::x86` and `std::arch::x86_64`.

```rust
#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

#[cfg(target_arch = "x86_64")]
unsafe fn add_lanes(a: [i32; 4], b: [i32; 4]) -> [i32; 4] {
    let va = _mm_loadu_si128(a.as_ptr() as *const __m128i);
    let vb = _mm_loadu_si128(b.as_ptr() as *const __m128i);
    let sum = _mm_add_epi32(va, vb);
    let mut out = [0i32; 4];
    _mm_storeu_si128(out.as_mut_ptr() as *mut __m128i, sum);
    out
}
```

Each function carries the same name as its C counterpart, so documentation, tutorials and examples written for C transfer directly.

### Feature detection

Not every CPU supports every instruction set. Executing an AVX2 instruction on a machine without it causes undefined behaviour. Intrinsics that require a particular feature are therefore `unsafe` to call, and the caller must ensure the feature is present.

There are two ways to arrange this.

**Compile-time.** If the program is compiled with `-C target-feature=+avx2` or `-C target-cpu=native`, the feature is statically known and `cfg!(target_feature = "avx2")` is true.

**Runtime.** The macro `is_x86_feature_detected!` performs a runtime check, cached after the first call:

```rust
fn sum(data: &[f32]) -> f32 {
    #[cfg(any(target_arch = "x86", target_arch = "x86_64"))]
    {
        if is_x86_feature_detected!("avx2") {
            return unsafe { sum_avx2(data) };
        }
    }
    sum_scalar(data)
}
```

### The `target_feature` attribute

To make the compiler generate AVX2 code inside one function without enabling it for the whole crate, the function is annotated:

```rust
#[target_feature(enable = "avx2")]
unsafe fn sum_avx2(data: &[f32]) -> f32 {
    // intrinsics from std::arch::x86_64 can be used here
}
```

The attribute causes the function to be compiled with the feature enabled. Calling such a function is `unsafe`, since the compiler cannot prove that the CPU supports it. Functions with `#[target_feature]` cannot be inlined into callers lacking the feature, since that would put the instructions where they might not be supported.

## Reference-level explanation

### Types

The vector types are defined in `std::arch::<arch>`: for x86, `__m128`, `__m128i`, `__m128d`, `__m256`, `__m256i`, `__m256d`, and so on. These are opaque, `Copy` types. They are deliberately not given arithmetic operators, nor are their lane contents exposed, since that is the job of portable SIMD. They implement `Debug` for convenience but this is not a stable representation.

The types are `repr(simd)` internally. Their layout is the natural layout of the vector register, with the size and alignment of the corresponding C type. They are `Send` and `Sync`.

### Functions

Each intrinsic is a function that is `unsafe`, `#[inline]`, and annotated with `#[target_feature(enable = "...")]` for the feature it needs. Where a C intrinsic takes an immediate operand (like `_mm_shuffle_epi32(a, imm8)`), the Rust function uses a const generic parameter or a `#[rustc_args_required_const]` attribute so the argument is guaranteed to be a constant at the call site.

The set of stabilized functions is the subset of Intel's intrinsics guide for SSE through AVX2, plus a handful of other extensions like BMI, POPCNT and LZCNT, whose specification is stable and widely deployed. AVX-512 is not stabilized, since support is still limited and the instruction set is in flux.

### Naming

Names match Intel's C names exactly, including the leading underscore and `mm` prefix. This is deliberate. A search for `_mm_add_epi32` should find both the C and Rust documentation, and code ported from C should differ only syntactically.

### Detection macro

`is_x86_feature_detected!` expands to a check that reads a cached bitmask populated using `cpuid` on the first use. It is available in `std`, but not `core`, since the implementation needs operating system support for some features, e.g. checking whether the OS saves AVX state. `core::arch` provides the intrinsics themselves, so `no_std` programs can use them given compile-time knowledge.

### Other architectures

The module layout reserves `arm`, `aarch64`, `wasm32`, `powerpc`, `powerpc64`, `mips` and `mips64` for the same treatment. Each follows its vendor's naming conventions. Only x86 and x86-64 are stabilized in this RFC. Others remain unstable until a follow-up RFC or stabilization PR confirms their types and function lists.

### Future portable SIMD

This RFC deliberately does not specify portable vector types such as `f32x4`. The `stdsimd` repository contains a prototype `std::simd`, but its design involves open questions (bounds, mask types, interaction with const generics) that are better answered once intrinsics are in widespread use. The intrinsic types in `std::arch` should be convertible to and from portable types when those are added.

## Drawbacks

- **Large API surface.** Thousands of functions are being added to the standard library. Maintenance burden is real, although most are mechanical and generated from Intel's XML specification.
- **`unsafe` everywhere.** Every intrinsic is unsafe, which makes simple code noisy. Safe wrappers are possible in third-party crates.
- **Stability of vendor names.** If Intel deprecates or renames an intrinsic, Rust inherits the cruft.
- **Architecture-specific code.** Programs written with intrinsics are not portable, and each additional architecture multiplies the work for library authors.
- **Compile times.** Large modules of inlined functions can slow compilation of the standard library, though not of user code that does not import them.

## Rationale and alternatives

### Stabilize portable SIMD first

This is the cleaner interface but takes longer and its design is contested. Waiting would leave users without any solution. Intrinsics are a pragmatic floor on which libraries can build portable abstractions.

### Rely on auto-vectorization

LLVM's auto-vectorizer is improving, but it cannot be relied upon for algorithms like string search or shuffle-heavy parsing, and its output changes between versions.

### Inline assembly

Inline assembly is also unstable and is much harder to get right: register allocation, clobbers and instruction scheduling are all left to the programmer. Intrinsics let the compiler optimize across them.

### Third-party crates only

Crates like `simd` and `faster` exist but depend on nightly compilers. Stable support requires compiler and standard library changes.

## Prior art

C and C++ expose intrinsics through compiler-provided headers. GCC, Clang, MSVC and ICC agree on names and semantics. Go uses assembly files for hand-tuned routines. Java's Vector API incubator offers a portable approach. .NET has `System.Runtime.Intrinsics`, which divides the world into a portable `Vector128<T>` and platform-specific classes such as `Sse2` with `IsSupported` properties, strongly resembling this design.

## Unresolved questions

- How should `#[target_feature]` interact with safe functions in the future? A mechanism for making such functions safe to call from matching contexts is plausible.
- Should `is_x86_feature_detected!` be accessible from `core` with an operating-system provided hook?
- When should AVX-512 stabilize, and under what feature names?
- What is the right representation for ARM's scalable vector extensions, whose size is unknown at compile time?
