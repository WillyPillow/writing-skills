- Start Date: 2014-09-24
- RFC PR: [rust-lang/rfcs#320](https://github.com/rust-lang/rfcs/pull/320)
- Rust Issue: [rust-lang/rust#5016](https://github.com/rust-lang/rust/issues/5016)

# Summary

Remove drop flags from values implementing `Drop`, and remove automatic memory zeroing associated with dropping values. Keep dynamic drop semantics, by having each function maintain a (potentially empty) set of auto-injected boolean flags for the drop obligations for the function that need to be tracked dynamically (which we will call "dynamic drop obligations").

# Motivation

Currently, implementing `Drop` on a struct or enum causes every value of that type to carry a hidden extra byte: the drop flag. The flag records whether the value has already been dropped, so that when a value is moved out of a variable the compiler can avoid running the destructor a second time. To make this work, when a value is moved, its memory is overwritten with zeros, and the destructor is skipped when the flag shows the value is gone.

This design has several costs.

1. **Size.** The drop flag lives inside the value. A type with a destructor that would otherwise be a single pointer takes a second word once alignment is considered. This inflates types like `Box`-like wrappers, `Vec`, `Rc`, and every user-defined smart pointer. It also defeats the niche optimizations that would let `Option<Box<T>>` be the same size as `Box<T>`.

2. **Zeroing.** On every move out of a droppable value, the memory is overwritten. This is redundant work in the common case where the compiler could have statically proven that the value is moved exactly once. The writes also defeat some optimizations by LLVM and pollute the cache.

3. **Semantics.** Because the flag is part of the value, it is visible in the layout. `transmute` between a droppable type and a plain type is not size-preserving. Types cannot be used in `repr(C)` contexts in a sound way if they implement `Drop`. The zeroing also makes it impossible to treat a droppable value as having a fully arbitrary bit pattern, which is a prerequisite for several desirable unsafe patterns.

4. **Correctness hazards.** The zeroing means that a destructor can in principle observe a struct with all-zero fields that did not come from any constructor. Types that rely on an invariant such as "this pointer is never null" can have that invariant violated for values that are about to be dropped, which requires defensive null checks in code such as `Drop for Vec<T>`.

The goal of this RFC is to keep the language-level behaviour that programmers rely on, namely that a value moved conditionally is dropped exactly when it is still owned, while removing the memory-level mechanism that implements it.

# Detailed design

## Overview

The key observation is that the question "does this variable still own a value that needs to be dropped?" is a property of the control flow of a function, not a property of the value itself. The compiler can track it in the function's own stack frame instead of inside the value.

For each local variable, field path, or temporary that may be moved out of or dropped, the compiler already needs to know the drop obligation. Most of the time, the obligation is statically determinable. At every program point the compiler can compute, with a standard dataflow analysis, whether the path is:

- definitely initialized,
- definitely uninitialized (or moved), or
- maybe initialized (initialized along some paths into this point, not along others).

Only in the third case is a runtime check required. This RFC proposes that each such "maybe initialized" path gets an auto-injected boolean flag in the function's stack frame, which we call a *dynamic drop flag*. All other paths need no flag at all.

## Dynamic drop obligations

A *drop obligation* is a path, such as `x`, `x.f`, or `x.f.g`, together with the point at which it must be dropped (typically the end of its scope or an assignment overwriting it). A drop obligation is *dynamic* if, at the point where the drop would occur, the path is maybe-initialized.

For each dynamic drop obligation the compiler adds:

- a boolean local, initialized to `false` at function entry;
- an assignment of `true` at each point where the path becomes initialized (declaration with initializer, assignment, or being the target of a `let`);
- an assignment of `false` at each point where the path is moved out of;
- a conditional drop at the scope exit or overwrite point: `if flag { drop(path) }`.

If the obligation is static, the conditional is omitted: the drop is emitted unconditionally if the path is definitely initialized, and nothing is emitted if it is definitely moved.

The flags are an implementation detail and are never exposed to user code. They can be stored in registers or on the stack, and LLVM can often eliminate them by jump threading.

## Example

```rust
fn f(cond: bool) {
    let x = make_value();
    if cond {
        consume(x);
    }
    // x may or may not have been moved
}   // here x must be dropped iff !cond
```

Under the current scheme, `x` has an embedded drop flag, and the move into `consume` zeroes it. Under this RFC, the compiler synthesizes a local `x_live: bool`, set to `true` after `make_value()`, set to `false` in the branch that calls `consume(x)`, and consulted at the end of the function.

## Partial moves

Moving a field out of a struct is a move of the path `x.f`. If `x` has no `Drop` implementation, the other fields remain individually droppable, so each field becomes its own obligation. If `x` does implement `Drop`, partially moving out of it is already a compile error and nothing changes.

## Loops and breaks

Loops are handled by the same dataflow analysis. A path moved inside a loop body and re-initialized before the end of the body has a static state at the loop head, and no flag is needed. A path moved conditionally in a loop is maybe-initialized and receives a flag. Early exits (`break`, `return`, `?`) are lowered to include the appropriate conditional drops for every obligation in scope.

## Unwinding

During unwinding, the landing pad for a call site must drop every obligation that is live at that call. The dynamic flags are read in the landing pad exactly as they are on a normal exit. Because the flags are on the stack of the same frame, no additional bookkeeping is required.

## Removal of zeroing

Once the dynamic flags are in place, the compiler no longer needs to overwrite moved-from memory. The memory-zeroing code in `trans` is removed, and the extra field is removed from the layout of types that implement `Drop`. The size of such types becomes the size of their fields alone.

## The `unsafe_no_drop_flag` attribute

Currently there exists an attribute `#[unsafe_no_drop_flag]` that opts a type out of the embedded flag, used by a small number of standard library types such as `Vec` and `Rc` which can recognize their own moved-from state via a null or sentinel pointer. This attribute becomes meaningless once the embedded flag is gone. This RFC proposes that it be accepted but ignored for one release cycle with a deprecation warning, and removed thereafter.

Code that depended on the zeroed bit pattern to detect moved-from values, for example `if self.ptr as usize == mem::POST_DROP_USIZE`, must be removed. The constants `POST_DROP_USIZE` and related helpers are deprecated along with the attribute.

# Drawbacks

- The compiler gains complexity: a new dataflow pass, a flag-insertion pass, and changes to the landing pad generation. These are not trivial and must be tested thoroughly, including around `match` guards and nested temporaries.

- Functions with many conditionally moved values pay a small cost in stack space and in branch instructions. Because the flags are in the frame rather than in each value, the overall cost is in practice lower, since the number of dynamic obligations in a function is much smaller than the number of droppable values in the program's heap.

- Unsafe code that relied on the zeroing, for example by reading a value after a move by means of `ptr::read` and assuming it was zeroed, will break. Such code was relying on an unspecified implementation detail, but may exist in the wild.

- Debuggability: a moved-from value now retains its old bits. A stale pointer left behind may be easier to misuse by mistake in unsafe code, although safe code cannot observe it.

# Alternatives

**Keep the status quo.** This leaves all the costs above in place, and makes dynamic drop part of the permanent memory model.

**Make drops static only.** Reject programs whose drop obligations cannot be determined statically. This would break a large amount of existing code and would force awkward patterns such as wrapping values in `Option`. It is more restrictive than the language needs to be.

**Use a single per-function bitmask.** Instead of a boolean per obligation, the compiler could pack flags into a bitset. This is an implementation choice that can be made later; LLVM already performs a similar optimization in many cases.

# Unresolved questions

- Should the language specify that moved-from memory is unspecified, or that it is unchanged? This RFC takes no position, but a future RFC on unsafe code guidelines should.
- How should `mem::forget` and `mem::uninitialized` interact with the flags? The expectation is that `forget` takes ownership and so clears the obligation, and `uninitialized` produces a value without an obligation until it is written.
- Can the flag analysis be reused to produce better diagnostics about use after move in conditional code?
