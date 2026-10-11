# RFC 2585: unsafe_block_in_unsafe_fn

- Feature Name: `unsafe_block_in_unsafe_fn`
- Start Date: 2018-11-01
- RFC PR: rust-lang/rfcs#2585
- Rust Issue: rust-lang/rust#71668

## Summary

No longer treat the body of an `unsafe fn` as being an `unsafe` block. To avoid a breaking change, this is a warning now and may become an error in a future edition.

## Motivation

The `unsafe` keyword in Rust has two distinct uses. In a function signature, `unsafe fn` declares that the function has preconditions that the compiler cannot check, and that callers must uphold them. In a block, `unsafe { ... }` declares that the code inside performs operations the compiler cannot verify, and that the author has checked that they are sound. The first is a contract placed on callers. The second is an assertion made by the author of the block.

Currently the two are conflated. The body of an `unsafe fn` is implicitly an `unsafe` block, so the whole body can freely call other unsafe functions, dereference raw pointers, and access mutable statics, without any marking. This has several drawbacks.

**The unsafe operations are not visible.** In a long `unsafe fn`, a reader cannot tell which lines are the dangerous ones. A function that contains thirty lines of ordinary safe code and one raw pointer dereference looks the same as a function made entirely of unsafe operations. Code reviewers, who need to focus on the parts that need scrutiny, are left to find them by reading every line and knowing what is unsafe.

**There is no place for a safety comment.** The convention in Rust is that every `unsafe` block is accompanied by a `// SAFETY:` comment explaining why the operation is sound. For an `unsafe fn`, there is a `# Safety` section in the documentation, which describes what the caller must do. There is nowhere to explain why the unsafe operations in the body are valid given those preconditions, because there is no block to attach the comment to. As a result, the reasoning is often never written down.

**Accidental unsafe operations.** A refactoring that adds a call to an unsafe function inside an `unsafe fn` compiles without any acknowledgement. If a safe function is later changed to unsafe, call sites inside `unsafe fn` bodies silently continue to compile. In a regular function, the same change would result in a compile error and force the author to look at each caller.

**The meaning of the signature is lost.** If a function is marked `unsafe` only because its body needs to do something unsafe, then the author has used the keyword as a convenience. That makes its preconditions unclear. The signature should mean "callers must uphold a contract", while the body's operations should be justified separately. Making the two independent makes it easier to ask of every unsafe function: "what is the contract?" and of every unsafe block: "why is this fine?"

Several parts of the Rust ecosystem, including the standard library, have started to adopt the discipline of putting an `unsafe` block around each unsafe operation even inside `unsafe fn`, using the lint to enforce it. The language ought to support this rather than forcing it to be done manually.

## Guide-level explanation

After this change, an `unsafe fn` has the following meaning: calling it requires an `unsafe` block, because it has a contract that the caller must satisfy. The body of the function is checked like any other function body. If it contains an unsafe operation, the operation has to be inside an `unsafe` block.

For example, consider this function in the old style:

```rust
/// # Safety
/// `ptr` must be valid for reads and properly aligned.
pub unsafe fn read_twice(ptr: *const u32) -> (u32, u32) {
    let a = *ptr;
    let b = *ptr;
    (a, b)
}
```

With the new rule, the compiler emits a warning for each dereference, and the author writes:

```rust
pub unsafe fn read_twice(ptr: *const u32) -> (u32, u32) {
    // SAFETY: the caller guarantees `ptr` is valid for reads and aligned.
    let a = unsafe { *ptr };
    // SAFETY: as above.
    let b = unsafe { *ptr };
    (a, b)
}
```

The code is now slightly longer, and the reader sees exactly which two expressions need the contract.

To make the change gradual, a new lint `unsafe_op_in_unsafe_fn` is introduced. It fires when an unsafe operation occurs in an `unsafe fn` outside of an `unsafe` block. In this edition it is allow-by-default, so existing code does not change behavior. Once the ecosystem has had time to adapt, it will be moved to warn-by-default, and it may be a hard error in a future edition.

Authors who want the stricter behavior now can opt in:

```rust
#![warn(unsafe_op_in_unsafe_fn)]
```

or `#![deny(unsafe_op_in_unsafe_fn)]`.

An `unsafe` block inside an `unsafe fn` is no longer reported as "unused" by the `unused_unsafe` lint. Before, such a block was redundant. Now it is the recommended form. The lint is adjusted so that the two lints do not give contradictory advice.

## Reference-level explanation

The unsafety checker, which currently starts in an unsafe context for the body of an `unsafe fn`, is changed so that it starts in a safe context when the lint `unsafe_op_in_unsafe_fn` is enabled at the function. An unsafe operation found outside of an `unsafe` block is then reported as the lint, instead of the hard error E0133 that is used in safe functions.

The following operations are covered, since they are those currently permitted only in unsafe contexts:

- Calling an unsafe function or method.
- Dereferencing a raw pointer.
- Accessing or modifying a mutable static variable.
- Accessing a field of a `union`.
- Calling an unsafe function through a foreign function interface declaration.
- Implementing or using other operations the compiler designates as unsafe.

The unused-unsafe analysis is updated so that a block is considered used if it contains an unsafe operation, or if it is within an `unsafe fn` where the lint is enabled. When the lint is not enabled, the `unused_unsafe` lint continues to fire for an `unsafe` block nested in an `unsafe fn`, as it does at present; with this RFC the warning would be misleading if the lint were turned on later, so the message links to the lint.

A machine-applicable suggestion is provided with the warning: wrap the offending expression in `unsafe { ... }`. This allows `cargo fix` to do the bulk of the migration. For blocks with many unsafe operations, the user is expected to restructure by hand and write a safety comment.

### Macros

Macros that expand to unsafe operations inside an `unsafe fn` are handled as they are in safe functions: the macro definition must contain the `unsafe` block, or the call site must wrap the macro invocation. Macros from external crates that do not contain an `unsafe` block, and which relied on being expanded in an unsafe context, will trigger the lint. The span of the diagnostic points to the macro call, and the suggestion is to wrap the call in `unsafe`. Macros in the standard library, such as `ptr::addr_of!`, are reviewed and updated.

### Edition plan

The lint is allow-by-default in all editions at first. In a later edition, it is anticipated to be warn-by-default, and then deny-by-default in a still later one, subject to experience with how much existing code is affected. A decision about this is deferred until usage data from the ecosystem is available, for example from a crater run.

## Drawbacks

This adds noise to existing `unsafe fn`s, which will gain many nested `unsafe` blocks. Some functions are entirely about performing unsafe operations, such as thin wrappers around system calls, and in those functions the extra blocks add no information. In these cases the blocks can be consolidated, but a function whose body is one large unsafe block is no better than the status quo.

There is a cost in migration. Large crates with many `unsafe fn`s will need a significant amount of edits to silence the lint, and the lint will be noisy for crates that have not opted in. Making the lint allow-by-default limits the pain, but also limits the benefit.

Some will argue that the contract in the signature is enough, and the extra blocks do not add safety, since the author could just write `unsafe { ... }` around the whole body. This is true, and the RFC does not prevent that. It does make the choice explicit, and visible during review.

## Rationale and alternatives

**Do nothing.** The conflation of the two meanings persists, and the safety reasoning stays undocumented in most unsafe functions.

**Make it an error immediately.** This would break much existing code, and would require a new edition. A lint provides the same signal without breakage.

**Introduce a new syntax for unsafe-contract functions.** For example, one could separate the keyword that marks a function as having a contract from the keyword that marks it as having an unsafe body. This was considered and rejected as too heavy for a change that can be accomplished with the existing keyword in two positions.

**Make the lint warn-by-default now.** The standard library and large crates need time to migrate, and the diagnostics need to prove accurate. A staged approach is safer.

**Use a clippy lint instead of a compiler lint.** The compiler's unsafety checker already has the information and a clippy lint would duplicate that work. A compiler lint also benefits from `cargo fix`.

## Prior art

Few other languages have a distinction similar to this one. C# has `unsafe` as a modifier that can be applied to a type, a member or a block, and a method marked `unsafe` has an unsafe body entirely, which is the same as Rust today. Swift's `unsafe` pointer types are marked by name rather than a keyword. Within the Rust ecosystem, the `unsafe_code` lint and several crates' style guides recommend one `unsafe` block per operation, with a safety comment, which is the practice this RFC supports.

## Unresolved questions

Should the lint be warn-by-default in the next edition, or later? The answer depends on measurements of how much code would be affected.

Should there be a mechanism to say that a particular function's entire body is an unsafe context, as an explicit annotation, for functions where the extra blocks are noise?

How should the lint handle operations that are only unsafe in some contexts, such as `static mut` references in newer rules, and will it be extended to those uniformly?
