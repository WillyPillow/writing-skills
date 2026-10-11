- Feature Name: `const_ub`
- Start Date: 2020-10-10
- RFC PR: rust-lang/rfcs#3016
- Rust Issue: (none yet)

# Summary

Define what happens when Undefined Behavior occurs during compile-time function evaluation (CTFE). A const evaluation that encounters UB produces either an unspecified result or a hard error for that particular CTFE query. The UB does not otherwise "infect" compilation: rustc continues to compile the rest of the crate correctly, and the compiler itself does not exhibit undefined behaviour.

# Motivation

Rust is steadily expanding what can be computed at compile time. `const fn` can now contain loops, branches, and, behind feature gates, raw pointer operations and unions. As soon as unsafe code is allowed in const contexts, programs can do things in a const that would be Undefined Behavior at runtime: read uninitialized memory, transmute an invalid bit pattern into a `bool`, dereference a dangling pointer, and so on.

At runtime, UB means that the language makes no promises about the behaviour of the entire program. We need to decide what it means at compile time. If we simply say "UB in a const is UB", a literal reading would imply that the compiler itself may misbehave: miscompile unrelated functions, crash, or produce any output at all. That is unacceptable for several reasons:

- The compiler is a program that users run on untrusted or semi-trusted inputs, such as dependencies they have not audited. We do not want a bug in someone's `const fn` to make rustc do arbitrary things.
- Miri, which powers CTFE, already detects a large fraction of UB and reports it as an error. It would be odd to define the semantics in a way that ignores this.
- On the other hand, Miri does not detect *all* UB, and checking everything would be expensive. We need room to skip checks, especially for performance reasons in large const computations.

This RFC picks a definition that preserves the integrity of the compiler while leaving the implementation free to detect as much or as little UB as is practical.

# Guide-level explanation

When you write unsafe code in a `const` or `static` initializer, or in a `const fn` called from one, the usual rules about Undefined Behavior apply: you must not cause it. If you do, here is what can happen:

1. The compiler may notice and stop with an error, pointing at the offending operation. This is the common case today for things like reading uninitialized memory or out-of-bounds pointer arithmetic.
2. The compiler may not notice, in which case the constant ends up with some value. That value is unspecified: it could be what you "expected", or it could be something else. It is not guaranteed to be stable across compiler versions or even across compilations.

Importantly, neither outcome affects anything *other* than the const whose evaluation hit the UB. The rest of your crate is compiled normally. If the bad constant is then used at runtime, the program's runtime behaviour is determined by whatever value the constant received — which may itself violate validity invariants, so runtime UB may follow. But the compiler will not, for example, decide to delete an unrelated function because some const somewhere was ill-formed.

As an example:

```rust
const BAD: bool = unsafe { std::mem::transmute::<u8, bool>(3) };
```

The compiler may reject this with an error about an invalid value for `bool`. If it accepts it, `BAD` has some unspecified value; using it in `if BAD { ... }` at runtime is then UB at runtime, just as if you had performed the transmute at runtime.

# Reference-level explanation

A *CTFE query* is a single request to evaluate a constant, static initializer, array length, enum discriminant, const generic argument, or promoted expression.

If evaluation of a CTFE query performs an operation that would be Undefined Behavior at runtime, then the result of that query is one of:

- a hard compile-time error, or
- an arbitrary value of the query's type (which need not satisfy that type's validity invariant).

Which one is chosen is unspecified and may vary between compiler versions, target platforms, and compilation flags. No other part of compilation is affected: other queries evaluate as specified, code generation for non-const code is unaffected, and the compiler process itself remains well-behaved.

Some clarifications:

**Determinism within a compilation.** Within a single compilation session, a given query yields a single result. If the same constant is used twice, both uses see the same value. This follows from the query system caching results and is needed for type-system soundness: `[u8; N]` must mean the same type everywhere.

**Interaction with the type system.** If a const generic argument or array length is produced by a UB-containing evaluation and the compiler chooses to return a value, the resulting types are well-formed with that value. Type checking remains sound in the sense that the compiler will not accept two different values as equal.

**Values that violate validity.** CTFE already performs a validity check on the final value of each constant. This check is not required by this RFC, but where it is performed, a failed check is reported as a hard error. The RFC does not require this check to be complete.

**Lints.** Today some UB-detection outcomes in CTFE are reported as the deny-by-default `const_err` lint rather than as hard errors. This RFC allows such cases to be lints in the meantime, but the long-term intent is that UB detected in a const that is actually used is a hard error.

# Drawbacks

- Programs that accidentally trigger UB in a const may compile on one version of rustc and fail on the next, as Miri learns to detect more UB. This is consistent with the general stance that UB is never part of the stability guarantee, but it may still surprise users.
- "Unspecified value" may make some bugs harder to find than an outright error would. The alternative, requiring detection of all UB, has costs described below.

# Rationale and alternatives

**Require detection of all UB.** We could mandate that every instance of UB during CTFE is reported as an error. This would make CTFE an exact UB checker, which is attractive but expensive. Some checks, such as full validity checks on every typed copy or precise tracking of Stacked Borrows, slow evaluation significantly. More importantly, the definition of UB in Rust is not finished; requiring complete detection would tie CTFE to a specification that does not yet exist.

**Treat UB in CTFE as UB in the whole program.** This is the "do nothing special" option. It allows the compiler to miscompile unrelated code, which would make debugging miserable and would mean a bug in a dependency's constant could corrupt any part of a binary. It also does not reflect how the implementation actually works.

**Make UB in CTFE always produce a value.** Forbidding errors would prevent the compiler from reporting UB it detects. That is strictly less helpful.

The chosen definition is the weakest that still protects the compiler's integrity, which gives the implementation maximum freedom to trade off detection against speed.

# Prior art

C++ requires that a core constant expression not contain an operation with undefined behavior; an expression that would is not a constant expression, and the program is ill-formed. In practice compilers detect many but not all such cases, so the actual behaviour resembles what this RFC proposes, though the C++ standard states it as a stronger requirement.

Zig's comptime execution checks many forms of illegal behaviour and reports them as compile errors, consistent with the "hard error" branch here.

# Unresolved questions

- Should promoted expressions, which the user did not explicitly request to be evaluated at compile time, be treated differently? Arguably UB in a promoted should be treated as if it happened at runtime.
- What exactly should happen when a `const` that triggered UB is never used? Today it may still be evaluated and produce an error; whether that should remain the case is a separate question.
