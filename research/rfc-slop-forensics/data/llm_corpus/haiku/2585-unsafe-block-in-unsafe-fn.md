# Rust RFC 2585: unsafe_block_in_unsafe_fn

- Feature Name: `unsafe_block_in_unsafe_fn`
- Start Date: 2018-09-27
- RFC PR: rust-lang/rfcs#2585
- Rust Issue: rust-lang/rust#71668

## Summary

This RFC proposes that the body of an `unsafe fn` no longer be treated as an `unsafe` block. Under the current rules, the entire body of an unsafe function is implicitly an unsafe context, so that any unsafe operation may be performed anywhere in it without a further marker. The proposal changes this so that each unsafe operation must appear inside an explicit `unsafe` block, even within an unsafe function.

To avoid breaking existing code, the change would initially be introduced as a warning, and it may become an error in a future edition of the language.

## Motivation

The current rule has a cost in clarity. When a function is marked `unsafe`, a reader sees that it has preconditions that its callers must uphold. But the function's body may contain many operations that are unsafe for different reasons, and a reader cannot tell from the signature which lines actually rely on the caller's guarantee and which lines are unsafe for some other reason. Everything in the body looks equally dangerous, and the boundary between the operations that matter and the rest of the function is invisible.

Explicit `unsafe` blocks give the reader that boundary. A block marks the precise place where the programmer takes responsibility for a particular invariant. Requiring such a block inside an unsafe function makes the function easier to audit, because every unsafe operation is accompanied by a marker that can be searched for and reviewed.

The change also makes it easier to find the places where an unsafe function calls safe code that does not in fact need the caller's guarantee. Under the current rules, such code is hidden inside the unsafe context, and it is easy to forget that it is not unsafe at all. Under the proposed rules, the programmer must decide, operation by operation, whether an `unsafe` block is required.

The RFC notes that this is an established practice in other parts of the language and in much of the ecosystem, where careful authors already wrap unsafe operations in small blocks with comments explaining why each one is sound.

## Guide-level explanation

Under the proposal, a function declared `unsafe fn` continues to have the same signature and the same meaning for its callers. A caller must still wrap the call in an `unsafe` block, or call the function from an unsafe context, because the function's preconditions must be upheld by the caller. The change affects only the body of the function.

Within the body, an unsafe operation must be placed inside an explicit `unsafe` block. For example, a function that dereferences a raw pointer would be written as follows.

```rust
unsafe fn read_value(ptr: *const u32) -> u32 {
    unsafe { *ptr }
}
```

Without the inner block, the compiler would warn that the dereference is unsafe but is not inside an unsafe block. The warning is intended to prompt the author to add the block and, where useful, a comment explaining why the operation is sound.

The RFC recommends that authors write a comment at each unsafe block explaining which invariant is being relied upon. This is not required by the language, but it is considered good practice, and tools may later check for the presence of such comments.

## Reference-level explanation

The change modifies the rules for determining whether an operation is in an unsafe context. Currently, the body of an `unsafe fn` is treated as an unsafe context in its entirety. Under the proposal, the body of an unsafe function is a safe context by default, and only operations inside explicit `unsafe` blocks are treated as unsafe.

Operations that require an unsafe context include dereferencing a raw pointer, calling an unsafe function or method, accessing a mutable static, accessing a field of a union, and calling a foreign function. These continue to be classified as they are today. Only the location of the block changes.

For the purposes of the warning, an operation is flagged when it is unsafe and it is not inside an `unsafe` block, even if it appears in the body of an `unsafe fn`. The lint is named `unsafe_op_in_unsafe_fn` and is allow-by-default until the edition change, so that it does not appear in existing code without opt-in.

Macros that expand to unsafe operations must be considered carefully. The RFC specifies that a macro whose expansion contains an unsafe operation should itself contain the necessary block, so that the expansion is correct in any context. Macros defined outside the crate may need to be updated by their authors, and the RFC proposes that the compiler provide a clear message to help them.

### Transition

The change is introduced in two steps. In the first step, the lint is added and is enabled by default as a warning in the current edition. This allows users to see where the new rule applies without breaking their builds. In the second step, which is tied to a future edition, the lint becomes a hard error. The RFC states that the second step should not occur until the ecosystem has had time to update and until tooling to assist the update is available.

## Drawbacks

The change will add visual noise to unsafe functions. Some authors will find that their bodies contain many small blocks, and they may consider the blocks less readable than the original. The RFC acknowledges this and argues that the readability cost is smaller than the benefit of explicit boundaries, especially in functions that mix unsafe and safe operations.

The change also requires many crates to be updated. The migration is mechanical for most code, but it still takes effort, and some crates may be maintained by people who are not active in the project. The RFC proposes an automated fix to reduce the burden, and it argues that the warning period gives authors time to make the change.

Finally, some authors may be tempted to place a single large block around the entire body of a function, which would defeat the purpose of the change. The RFC notes that this is allowed but discourages it in the documentation, and it suggests that code review and linting can help discourage the practice.

## Rationale and alternatives

The main alternative is to leave the current rules unchanged and to rely on documentation and code review to make unsafe operations visible. The RFC rejects this because documentation is easy to ignore and because the compiler is the only tool that can enforce a consistent boundary.

A second alternative is to require a block for each unsafe operation in every context, including unsafe functions, but to make the change without a warning period. This would be simpler to specify but would break a large amount of code immediately, and the authors judged that disruption unacceptable.

A third alternative is to introduce a new keyword or attribute that marks a function as having a safe body inside an unsafe signature. The RFC prefers the lint-based approach, because it uses the existing `unsafe` block syntax and does not introduce new concepts for users to learn.

## Prior art

Other systems languages distinguish between the unsafety of a function's contract and the unsafety of its operations. Some of them require explicit markers at each unsafe site, and the RFC points to these examples as evidence that the approach is workable at scale. Within Rust, the community has long recommended small unsafe blocks as a matter of style, and the RFC formalizes that recommendation.

## Unresolved questions

The RFC leaves several questions for the implementation phase. The exact rules for macros that expand inside unsafe functions need further specification, particularly for macros that are defined in other crates. The interaction with future changes to the aliasing model is also unresolved, since some of the operations that are currently implied by the unsafe context may need their own precise rules. The naming of the lint and the timing of the edition change are provisional.

## Conclusion

Requiring explicit `unsafe` blocks inside `unsafe` functions would make the boundary of each unsafe operation visible and reviewable. The change is introduced as a warning first, which allows the ecosystem to adapt without an immediate break, and it may become an error in a later edition. The RFC recommends that the lint be added with the transition plan described above and that tooling be developed to help crates migrate.
