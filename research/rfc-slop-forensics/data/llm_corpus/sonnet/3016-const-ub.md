# RFC: Undefined behavior in const evaluation

- Feature Name: `const_ub`
- Start Date: 2020-07-15
- RFC PR: rust-lang/rfcs#3016
- Rust Issue: N/A

## Summary

Define UB during const evaluation to lead to an unspecified result or hard error for the affected CTFE query, but not otherwise infect the compilation process.

## Motivation

Const evaluation, also known as compile-time function evaluation (CTFE), runs Rust code inside the compiler. The code is executed by the Miri-based interpreter that lives in rustc. As more of the language becomes available in `const fn`, including raw pointers, `unsafe` blocks, `transmute`, and references, it becomes possible to write const code that has undefined behavior in the sense of the Rust abstract machine.

The language reference states that undefined behavior is a bug in the program, and that the compiler may assume it never happens. For runtime code this has an obvious meaning: the program may do anything. For compile-time code, the question is subtler. What can go wrong when a `const` initializer contains UB? Several answers have been informally given:

1. "Anything may happen at compile time, including miscompilation of unrelated code." This is the most literal reading of "UB is UB".
2. "The interpreter detects it and reports an error." This is what happens in many cases today, since Miri checks many kinds of UB, such as out-of-bounds accesses and invalid values.
3. "The result of the const is arbitrary but the compiler continues to work." This is what some users expect.

Because there is no written policy, library authors writing `const fn` do not know how careful they have to be, compiler developers do not know which behaviors they must preserve, and the unsafe code guidelines working group cannot say whether const evaluation needs to match runtime semantics bit for bit.

This RFC picks an answer. It aims to be conservative enough to avoid committing the project to detecting all UB, while strong enough to keep the compiler sound and predictable.

## Guide-level explanation

Writing UB in a `const` or `const fn` is still a bug in your program. The Rust compiler does not promise that every instance of UB will be caught, and the fact that your code compiles does not mean it is correct.

What the compiler does promise is that UB in const evaluation is contained. If evaluation of a particular constant hits UB, then one of two things happens:

- Compilation reports an error pointing at the constant, or
- The constant takes on some unspecified value of its type, and compilation proceeds.

In neither case does the rest of the compiler misbehave. A bug in one constant cannot cause the compiler to crash, to emit invalid machine code for unrelated functions, or to produce a different result for another constant that does not depend on it.

For example:

```rust
const BAD: u32 = unsafe { *(0x1000 as *const u32) };
```

Here, dereferencing an integer-derived pointer inside const evaluation is detected and reported as a hard error. In other cases the interpreter may not notice that UB has occurred:

```rust
const WORSE: u8 = unsafe { std::mem::transmute::<u8, bool>(2) } as u8;
```

Depending on the compiler version, this may fail with an error about an invalid boolean, or yield some value. Either outcome is allowed. What is not allowed is for this one constant to cause an unrelated function to be compiled incorrectly.

The practical advice for authors is unchanged: avoid UB, test `const fn` in both const and runtime contexts, and run Miri on code that uses `unsafe`.

## Reference-level explanation

We define the following terms.

A **CTFE query** is one evaluation of a const item, static initializer, array length expression, enum discriminant, const generic argument, or `const` block, performed by the compiler.

A **UB-affected query** is a CTFE query in which the interpreter executes an operation that would be undefined behavior in the Rust abstract machine, whether or not the interpreter detects this.

For a UB-affected query, the compiler must behave in one of two ways:

1. It reports a hard error for this query, and every item that depends on it fails to evaluate. Compilation as a whole fails, as it does for any other const evaluation error.
2. It produces an unspecified value for the query result, subject to the following constraints: the value is a valid value of the type of the constant, in the sense of the type's validity invariant; and the value is the same every time the query is evaluated within one compilation.

In both cases, the effects are limited to the UB-affected query and to queries that transitively depend on its result. Queries that do not depend on it behave as if the UB-affected query did not exist.

The compiler must not use UB in a const as justification to assume anything else about the program, must not skip type checking or borrow checking, and must not otherwise treat its own state as corrupted. The interpreter itself is a safe Rust program; interpreting UB code must not trigger UB in the compiler.

### Result validity and promotion

For a constant whose type has a validity invariant that the produced value would violate, such as a `bool` holding the value 2, the compiler must either produce an error or normalize the value. The choice is unspecified. Existing behavior, where such constants produce an error "it is undefined behavior to use this value", is permitted and expected to remain.

### Interaction with runtime behavior

This RFC says nothing new about UB at runtime. If a `const fn` is called at runtime and has UB, then the usual rules apply. If a `const fn` is called at compile time and not at runtime, only the rules above apply. A `const fn` that is UB-free at runtime but whose const evaluation differs, for example because of pointer-to-integer casts that Miri cannot support, is a separate issue and handled by const-specific errors, not by this RFC.

### Non-determinism across versions

Because the set of UB that gets detected is not specified, a program that compiles on one compiler version might fail on a later one when the interpreter's checks become stricter. This is already the case for other categories of compile-time errors that were previously accepted. Such changes are treated as acceptable fixes for soundness bugs, subject to a crater run and the usual future-compatibility lint process.

## Drawbacks

This RFC allows the compiler to produce different results for the same incorrect program, which can be surprising. A constant might hold one value in a debug build and a different value in release builds if optimization-related changes alter the interpreter's behavior. We believe this is unlikely, since CTFE does not depend on optimization level, but it is not forbidden by the text.

Another drawback is that it promises very little to users who hope for hard errors. Some developers will want a guarantee that all UB in constants is detected. This is not achievable in general: some UB, such as data races on statics, or violations of aliasing rules that the interpreter does not track, cannot be detected without a full model.

## Rationale and alternatives

**Full UB semantics.** The alternative is to say UB in const evaluation is exactly as at runtime: the whole compilation has UB. This is simple to state but unhelpful, because it prevents the compiler from giving any guarantee in the presence of a buggy constant. It also contradicts existing practice, where Miri-style checks produce errors.

**Guarantee detection.** Another alternative is to promise that all UB is detected and turned into an error. This would force the interpreter to track every aspect of the abstract machine, including aliasing models that are still under discussion, and it would make the language specification hostage to the interpreter's capabilities.

**Treat const-evaluated UB as a runtime panic.** One could treat UB as a panic, which is deterministic and recoverable. However, in const contexts panics are already hard errors, so this collapses into the error option while adding nothing.

The chosen design leaves room for the interpreter to grow stricter without a language change, protects the compiler, and gives unsafe code authors a clear statement of what they can rely on.

## Prior art

C++ `constexpr` requires that a constant expression not exhibit UB, and compilers are required to diagnose it, since evaluation containing UB is not a constant expression. The result is that compilers reject programs at compile time, but this rule works because C++ constant evaluation is restricted to a smaller set of operations. Rust's const evaluation is increasingly permissive, which makes full diagnosis harder.

Zig's `comptime` detects many forms of illegal behavior at compile time and reports them as errors, with the rest left unspecified.

## Unresolved questions

- Should the "same value every time" requirement be weakened to "some valid value" for cases where the query is evaluated more than once, for example during incremental compilation?
- Should the compiler be required to emit a lint when it can prove a constant is UB-affected but chooses the unspecified-value path?
- How should this interact with `const_eval_select` and intrinsics whose compile-time and run-time behaviors differ?

## Future possibilities

As the aliasing model stabilizes, the interpreter may implement it and turn more UB into hard errors. Some UB checks could be gated behind a lint level, so that users can opt into stricter diagnostics. The specification of const evaluation could eventually be integrated into the Rust reference.
