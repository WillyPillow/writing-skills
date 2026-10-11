- Feature Name: `unsafe_no_drop_flag`
- Start Date: 2014-09-02
- RFC PR: [rust-lang/rfcs#320](https://github.com/rust-lang/rfcs/pull/320)
- Rust Issue: (none)

# Summary

Remove drop flags from values that implement `Drop`, and remove the automatic zeroing of memory that accompanies dropping such values. Dynamic drop semantics are preserved. Each function maintains a possibly empty set of compiler-injected boolean flags, one for each drop obligation that must be tracked at runtime. A flag is consulted only when the obligation cannot be resolved statically.

The aim is to make the common case cheaper, with no hidden writes to memory when a value goes out of scope, while keeping the guarantee that a value is dropped exactly once.

# Motivation

The current implementation attaches a drop flag to every value whose type implements `Drop`, and it zeroes the storage of the value after the destructor has run. The flag records whether the value has been moved out of, and the zeroing exists so that a flag check can read a known pattern from a value that has been dropped.

Both mechanisms have costs. Each value of a droppable type carries an extra byte or word of state that must be kept up to date across every move. The zeroing writes memory that the program does not otherwise use after the value is gone. In tight loops and in code that manages many small values, the overhead is measurable, and it also complicates reasoning about the generated code.

Most values do not need a runtime flag at all. The compiler can determine statically whether a value has been moved on every path to its scope exit. Only in the cases where a move happens on some paths but not others does a runtime test become necessary. Limiting flags to those cases removes most of the overhead without changing what programs can express.

The zeroing is also a source of surprise. Programmers do not expect the memory of a dropped value to change after the destructor returns, and the behaviour makes it harder to build custom containers and smart pointers that rely on the storage being left alone.

# Detailed design

The compiler performs a dataflow analysis over the control flow graph of each function. For every local whose type implements `Drop`, the analysis records whether the local is definitely initialized, definitely uninitialized, or maybe initialized at each point. A local that is always initialized or always uninitialized at its scope exit needs no runtime information. The drop is emitted unconditionally, or omitted, respectively.

A local that is maybe initialized at scope exit is a dynamic drop obligation. The compiler allocates one boolean flag for it and sets the flag on initialization and clears it on move. At scope exit, the drop is guarded by a test of the flag. The flag is local to the function frame and is not stored in the value itself.

This split is the key point of the design. The information that the old scheme kept inside each value is moved into a separate piece of state that exists only where it is needed. The value's own storage is not modified by the drop.

Partial moves are handled in the same framework. A struct whose field has been moved out is treated as having one dynamic obligation per field that remains droppable. The compiler records these obligations per field rather than per struct, so that the remaining fields are still dropped correctly.

Zeroing is removed entirely. After a destructor runs, the storage of the value is left as it was. Code that reads memory after a drop is already undefined behaviour under the language's rules, so the removal does not change what safe programs can observe.

# Unsafe code

Some code, particularly code that implements containers, depends on the current behaviour. Such code can observe the difference, because a value that has been dropped may no longer be zeroed. For that reason the proposal introduces an opt-out attribute on types that rely on the old behaviour. The attribute is spelled as an unsafe marker on the type, and it keeps the flag and the zeroing for that type alone.

The attribute is intended for a small set of low-level types, mostly in the standard library. Its use requires an `unsafe` block or an `unsafe` impl, so that the reader is aware that the type has special requirements. Ordinary user code should never need it.

# Drawbacks

The change adds analysis work to the compiler. The dataflow pass must be correct for every control flow construct, including loops, early returns, panics that unwind through a function, and closures that capture by move. A mistake in this pass could cause a value to be dropped twice or not at all, which is a serious bug.

The removal of zeroing makes some debugging situations harder. A developer who inspects memory after a drop will see stale values rather than zeros, and this may be confusing for people who relied on the old behaviour in their tools.

The opt-out attribute adds a second mode to the language. It is small, but it must be documented and it must be maintained.

# Alternatives

One alternative is to keep the drop flags but drop the zeroing. This removes part of the overhead, but it keeps the per-value state, which is the more expensive part in terms of layout and move cost.

A second alternative is to keep everything and document the current behaviour as a guarantee. This is the simplest choice and it avoids the risk of a new analysis. Its disadvantage is that the cost remains, and that the zeroing continues to be a hidden side effect.

A third alternative is to make dynamic drop the rare case by rejecting most programs that need it. This would be too restrictive. Programs that move conditionally out of a local, such as in a loop with a `break`, are common and should continue to compile.

# Unresolved questions

The interaction between the dataflow analysis and panic unwinding needs more work. In particular, the drop flags of a function must be correct when the function unwinds at any point, and the proposal assumes that the landing pads can use the same analysis as normal exit paths.

The naming of the opt-out attribute is not settled. The name in this document is a placeholder, and the final choice should be made with the libraries team.

It is also not clear how much of the existing standard library needs the opt-out. An audit is needed before the change can be scheduled.

# Future work

After the analysis is in place, the compiler could further reduce the number of dynamic flags by using more precise information about borrows. A value that is borrowed but never moved on some path does not need a flag on that path, and a later analysis could take advantage of this.

The attribute for opting out could be replaced by a more general mechanism for controlling drop elaboration, once the design of such a mechanism is clearer. This should be considered after the current change has been tested in real code.
