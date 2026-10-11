- Feature Name: `unsafe_block_in_unsafe_fn`
- Start Date: 2018-11-04
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Stop treating the body of an `unsafe fn` as an `unsafe` block. Unsafe operations inside an `unsafe fn` will need their own `unsafe { }` block, just as they do in a safe function. To avoid a breaking change, the new requirement starts out as a lint, `unsafe_op_in_unsafe_fn`, that is allow-by-default. It may be made warn-by-default, and the behavior may become a hard error in a future edition.

# Motivation

The keyword `unsafe` does two different jobs in Rust.

1. **On a function, it states a requirement.** `unsafe fn` says: "this function has preconditions the compiler cannot check, and callers must uphold them." It is a promise the caller has to keep.
2. **On a block, it discharges a requirement.** `unsafe { ... }` says: "I have checked that the preconditions of the unsafe operations in here are met." It is a promise the author of the block keeps.

Today, writing `unsafe fn` also does the second job for the whole function body. The body behaves as if it were wrapped in `unsafe { }`. So declaring that callers have obligations also, silently, lets the function body perform any unsafe operation without marking it.

This hurts in practice.

**Unsafe operations are hidden.** In a long `unsafe fn`, nothing distinguishes the one line that dereferences a raw pointer from the twenty lines of ordinary arithmetic around it. Reviewers have to read the whole function looking for operations that might be unsafe. In a safe function, `unsafe` blocks tell reviewers exactly where to look.

**Mistakes go unnoticed.** Consider:

```rust
/// # Safety
/// `idx` must be less than `self.len()`.
pub unsafe fn get_unchecked(&self, idx: usize) -> &T {
    let ptr = self.ptr.add(idx);
    &*ptr
}
```

Suppose a later change adds a call to another unsafe function with different preconditions. The compiler says nothing, because the body is already an unsafe context. The author may not even notice the new call is unsafe, and certainly is not prompted to document why it is sound.

**Safety comments have no anchor.** The convention is to put a `// SAFETY:` comment on each `unsafe` block, explaining why it is sound. Inside an `unsafe fn` there are no blocks to attach these comments to, so the reasoning either goes undocumented or sits in a single paragraph far from the code it covers.

**It is confusing to learn.** Learners are taught that `unsafe` blocks mark the places where the programmer takes responsibility. Then they find that `unsafe fn` bodies are a large exception, and that the same keyword means "caller's responsibility" in one position and "my responsibility" in another, but also both at once when on a function.

Separating the two meanings makes `unsafe fn` mean only "this function has preconditions", and makes `unsafe { }` the only way to perform an unsafe operation, everywhere.

# Guide-level explanation

With the lint enabled, the example above is written as:

```rust
/// # Safety
/// `idx` must be less than `self.len()`.
pub unsafe fn get_unchecked(&self, idx: usize) -> &T {
    // SAFETY: the caller guarantees `idx < self.len()`, so the offset
    // stays inside the allocation.
    let ptr = unsafe { self.ptr.add(idx) };
    // SAFETY: `ptr` is in bounds and points to an initialized `T`.
    unsafe { &*ptr }
}
```

Each unsafe operation is marked, and each one has its own justification, which can rely on the function's documented preconditions.

To turn the check on in a crate:

```rust
#![warn(unsafe_op_in_unsafe_fn)]
```

Without the lint, existing code compiles exactly as before. With the lint enabled, an unsafe operation in an `unsafe fn` body outside an `unsafe` block produces a warning that points at the operation and suggests wrapping it.

An `unsafe` block directly inside an `unsafe fn` currently triggers the `unused_unsafe` lint, because it is redundant. With this change, such blocks are no longer redundant when `unsafe_op_in_unsafe_fn` is enabled, and `unused_unsafe` will not fire on them.

# Reference-level explanation

## The lint

A new lint, `unsafe_op_in_unsafe_fn`, is added. It is allow-by-default. When enabled, the unsafety checker treats the body of an `unsafe fn` as a safe context: any unsafe operation in it that is not inside an `unsafe` block triggers the lint. Unsafe operations are the same as elsewhere:

- dereferencing a raw pointer;
- calling an `unsafe fn` or unsafe trait method;
- accessing or modifying a mutable `static`;
- accessing a field of a `union`;
- using inline assembly;
- implementing an `unsafe trait` (not affected, since this is not in a function body).

Because it is a lint, it obeys `allow`, `warn`, `deny` and `forbid`, and can be set per crate, module or function.

## Interaction with unused_unsafe

When `unsafe_op_in_unsafe_fn` is `allow` at the location of an `unsafe` block nested directly in an `unsafe fn`, the block is reported as unused, as today. When the lint is at any other level, the block is not reported as unused if it contains an unsafe operation.

## Closures and nested items

Closures inside an `unsafe fn` already inherit the unsafe context today. Under the lint, they inherit the safe context, so unsafe operations in them also need a block. Nested `fn` items are unaffected; they never inherited the context.

## Edition plan

This RFC does not change any edition. It proposes the following path, to be confirmed by later decisions:

1. Introduce the lint as allow-by-default.
2. Once the ecosystem has had time to adapt, make it warn-by-default.
3. In a future edition, consider making it deny-by-default or a hard error in that edition, with `cargo fix` able to insert the needed blocks automatically.

The automatic fix is simple: wrap each flagged operation, or the whole body, in `unsafe { }`. Wrapping the whole body reproduces today's behavior exactly, so migration is never forced to be more than mechanical.

# Drawbacks

- More `unsafe` blocks mean more lines and more nesting in code that is already heavy with unsafety, such as low-level allocators and FFI wrappers.
- Code where nearly every line is unsafe gains little from per-operation blocks, and authors may wrap the whole body anyway.
- Two lints (`unused_unsafe` and the new one) now interact, which adds some complexity to the compiler and to the documentation.

# Rationale and alternatives

**Do nothing.** The confusion and the hidden unsafe operations remain.

**Change it immediately in the next edition** without an intermediate lint. This gives users no time to try the style and report problems. Starting with a lint is cheap and reversible.

**New syntax** such as `unsafe(caller) fn` was suggested to separate the two meanings. That introduces a new spelling for a concept that already has one. Changing what the body means is enough.

# Prior art

Some large Rust codebases, including parts of the standard library, already avoid long `unsafe fn` bodies by delegating to small helper functions, to get the same effect by convention.

# Unresolved questions

- The timeline for moving the lint to warn-by-default.
- Whether the edition change should make it a hard error or a deny-by-default lint.
