- Start Date: 2014-09-24
- RFC PR: [rust-lang/rfcs#320](https://github.com/rust-lang/rfcs/pull/320)
- Rust Issue: [rust-lang/rust#5016](https://github.com/rust-lang/rust/issues/5016)
- Feature Name: (none for the bulk of RFC); `unsafe_no_drop_flag`

# Summary

Remove drop flags from values that implement `Drop`, and remove the automatic memory zeroing that happens when such values are dropped or moved. Keep dynamic drop semantics by having each function maintain a set of compiler-inserted boolean flags, one for each drop obligation whose status cannot be determined statically. We call these *dynamic drop obligations*. For most functions the set is empty.

# Motivation

## How drop works today

When a type implements `Drop`, the compiler adds a hidden one-byte *drop flag* to its representation. The flag is set when the value is initialized. When the value goes out of scope, the destructor runs only if the flag is set. When a value is moved out of a location, the source memory is overwritten with zeroes, which clears the flag, so the destructor will not run again at the original location.

This scheme supports *dynamic drop*: code like

```rust
let x = make_resource();
if condition() {
    consume(x);
}
// is x dropped here?
```

does the right thing. If `consume` took `x`, the source was zeroed and nothing happens at the end of scope. Otherwise `x`'s destructor runs.

## What it costs

The drop flag and zeroing have real costs.

1. **Size.** Every `Drop` type grows by a byte, and usually by a full word after alignment. A `Vec<T>` is four words instead of three. Arrays of droppable structs pay this per element. Because the flag lives inside the value, it also appears in every enum variant, every `Box`, and every collection.

2. **Time.** Every move of a droppable value writes zeroes over the source. For large values this is a `memset` in the middle of otherwise straight-line code. Optimizers can sometimes remove it, but often cannot prove it dead because the destructor check reads it later.

3. **Representation.** Types that implement `Drop` cannot have the same layout as the corresponding C struct. Code doing FFI has to avoid `Drop` or use `#[unsafe_no_drop_flag]`, an undocumented and unsound attribute.

4. **Semantics.** Zeroing on move means that a moved-from location contains a valid-looking all-zeroes value. Unsafe code that reads moved-from memory sees data that happens to be "dropped" rather than undefined. Destructors also have to tolerate being called on zeroed values in certain edge cases, which complicates writing them correctly.

Almost all of this is paid for a feature most functions do not use. In the common case, the compiler knows statically whether a value has been moved at each scope exit.

# Detailed design

## Drop obligations

At each program point, a local variable (or a field path within one, such as `x.a.b`) is either *initialized*, *uninitialized*, or *maybe initialized*. This is exactly the information the borrow checker's move analysis already computes.

At a scope exit, the compiler must run the destructor for each variable that holds a `Drop` value. We call this a *drop obligation*.

- If the variable is initialized at the exit on all paths, the obligation is *static*: emit an unconditional destructor call.
- If the variable is uninitialized on all paths, emit nothing.
- If the variable is maybe initialized, the obligation is *dynamic*.

## Stack-local drop flags

For each dynamic drop obligation, the compiler allocates a boolean in the function's stack frame. The flag is:

- set to `true` when the corresponding path is initialized,
- set to `false` when it is moved out of,
- tested at scope exit, with the destructor running only if it is `true`.

In the example from the motivation, `x` gets a flag that is set after `make_resource()` returns, cleared on the `consume(x)` branch, and checked at the end of scope.

Flags are per-path. If a struct `s` with `Drop` fields `a` and `b` has only `s.a` moved conditionally, then `s.a` gets a flag and `s.b` is dropped statically. If `s` itself implements `Drop`, moving out of its fields is already forbidden, so the question does not arise.

Flags are function-local. They never appear in the type's representation, never cross function boundaries, and never touch the heap.

## No zeroing

With flags held outside the value, nothing needs to know whether a moved-from location still contains a live value. The compiler stops writing zeroes on move. Moved-from memory is logically uninitialized and its contents are unspecified.

## Removal of the embedded drop flag

Types implementing `Drop` no longer contain a hidden flag. Their layout is the same as the same type without a `Drop` implementation. `#[unsafe_no_drop_flag]` becomes a no-op and is deprecated.

## Heap-allocated and container values

Values inside a `Box`, `Vec`, or other container are dropped by the container's destructor. The container already knows which elements are live: a `Vec` knows its length, and a `Box` owns exactly one value. Neither ever relied on the drop flag for correctness. They relied on it only incidentally, through zeroing behaviour in their unsafe code, which must be audited (see below).

## Interaction with `mem::forget`, `ptr::read` and friends

Unsafe code that moves a value out with `ptr::read` and later lets the original location go out of scope would, today, run the destructor a second time on a zeroed value, which for most types happens to be harmless. Under this RFC, the original location is not tracked by any flag and its destructor will run on stale data. Such code must use `mem::forget` or `ManuallyDrop`-style wrappers to suppress the original destructor. This was already the documented contract; the change removes the accidental safety net.

To ease the transition, the standard library will provide `mem::forget` as a safe function and audit its own use of `ptr::read`.

# Example lowering

```rust
fn f(c: bool) {
    let a = Thing::new();
    let b = Thing::new();
    if c {
        take(a);
    }
    take(b);
}
```

lowers conceptually to

```rust
fn f(c: bool) {
    let a_flag: bool;
    let a = Thing::new();
    a_flag = true;
    let b = Thing::new();
    if c {
        a_flag = false;
        take(a);
    }
    take(b);
    if a_flag { drop_in_place(&mut a); }
}
```

`b` is moved on all paths, so it needs no flag and no destructor call. Only `a` gets a flag.

# Drawbacks

- Unsafe code that depended on zeroing semantics will break, sometimes silently. A destructor running on stale memory is undefined behaviour, which is worse than a crash.
- The compiler becomes responsible for a dataflow analysis in code generation that previously lived only in the borrow checker. This must be correct; bugs here produce double drops or leaks.
- Debugging moved-from memory becomes harder, because it no longer contains a recognizable pattern.

# Alternatives

**Static drop semantics.** Earlier drafts proposed eliminating dynamic drop entirely: a value that is maybe-moved at scope exit would be dropped at the point where control flow merges, or the program would be rejected. This simplifies codegen but changes observable behaviour (destructors run earlier, which matters for locks and guards) and rejects some reasonable programs. Keeping dynamic semantics with local flags avoids both problems.

**Keep embedded flags but stop zeroing.** This removes the time cost but keeps the size cost and the layout incompatibility, which are the larger problems.

**Do nothing.** Every `Drop` type continues to pay a word of overhead and every move continues to pay for zeroing.

# Unresolved questions

- How much of the flag analysis should be shared with the borrow checker, and how much reimplemented in translation?
- Should the compiler warn when a function requires dynamic drop flags, to help performance-sensitive code avoid them?
- Exactly which standard library functions need auditing for reliance on zeroed memory.

# Implementation plan

1. Implement stack-local flags alongside the existing embedded flags, using them for drop decisions, and verify behaviour on the test suite.
2. Audit the standard library for reliance on zeroing.
3. Stop zeroing on move.
4. Remove the embedded drop flag from type layout and deprecate `#[unsafe_no_drop_flag]`.
