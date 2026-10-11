- Feature Name: `stable_drop_order`
- Start Date: 2017-01-19
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary
[summary]: #summary

I propose we specify and stabilize drop order in Rust, instead of treating it as an implementation detail. The stable drop order should be based on the current implementation. This results in avoiding breakage and still allows alternative, opt-in, drop orders to be introduced in the future.

# Motivation
[motivation]: #motivation

Today, the order in which values are dropped in Rust is observable but not documented. Programs can and do depend on it. A `Drop` implementation might release a lock, flush a buffer, close a socket, or print a message, and whether one of these happens before another can be the difference between a correct program and a deadlock.

The reference does not say what the order is. The language team has, on several occasions, said that it is "unspecified," while the compiler has behaved the same way for years. Users reasonably read the lack of documentation as a lack of guarantee, and this leaves them in an uncomfortable spot: either they write code that works today but may break tomorrow, or they add contortions such as explicit `drop` calls and nested scopes to make the order evident.

Three concrete problems follow from the lack of specification.

1. **Unsafe code cannot rely on it.** A type that owns raw resources may require its fields to be released in a particular sequence. If the sequence is not guaranteed, `unsafe` code is forced to use `ManuallyDrop` or `Option` wrappers merely to be safe against a change that has never happened.
2. **Silent breakage.** If a future compiler version, for the sake of optimization or from a refactor, changes the order, programs will break in subtle ways. Because drop order rarely appears in test assertions, the breakage may be discovered in production.
3. **Learning and teaching.** Newcomers ask the question, and the answer, "it's whatever the compiler does," is unsatisfying.

Other languages with deterministic destruction, like C++, define destruction order precisely, and it is part of how people reason about resource management. Rust's ownership model makes the same kind of reasoning natural, and giving it a firm footing would be welcome.

# Detailed design
[design]: #detailed-design

The proposal is to document, as normative, the order the compiler currently implements. I summarize the rules here; the exact text should go into the reference.

## Local variables

Local variables are dropped in the reverse order of their declaration when the scope ends.

```rust
fn main() {
    let a = Noisy("a");
    let b = Noisy("b");
    let c = Noisy("c");
}
// drops c, then b, then a
```

Function parameters are dropped after the function's local variables, in reverse order of their position in the parameter list.

## Temporaries

Temporaries are dropped at the end of the enclosing statement, in reverse order of their creation. There are well-known exceptions:

- In the tail expression of a block, temporaries live until the end of the enclosing statement of the block, not of the tail expression itself.
- In a `let` statement, a temporary whose reference is bound by `ref` or by a `let x = &temp;` is extended to the end of the enclosing block.
- In the scrutinee of `match`, `if let` and `while let`, temporaries live until the end of the entire expression.

The current rules for temporary lifetime extension are specified by the existing reference text and are not changed by this RFC.

## Fields of structs, tuples, and arrays

When a value is dropped, its own `Drop::drop` is run first, if it implements `Drop`. Afterwards, its fields are dropped in declaration order.

```rust
struct Pair { first: Noisy, second: Noisy }
// dropping a Pair drops `first`, then `second`.
```

Tuples are dropped in order from the first element to the last. Arrays and slices, and therefore `Vec<T>`, drop their elements from the first to the last.

Note that this order, which is front-to-back for fields, is opposite to that of local variables. This asymmetry is deliberate; it is the existing behavior, and reversing it would break code.

## Enums

An enum value drops the fields of the active variant, in declaration order, after any `Drop` implementation on the enum.

## Closures

A closure drops its captured variables in the order in which they are first used in the closure body (the order of capture). This follows the current implementation. Because capture order is an implementation detail of how the compiler analyzes the closure, I propose to leave it documented as unspecified, and only specify that all captured variables are dropped when the closure value is dropped.

## Panics and unwinding

If a panic unwinds through a scope, the values in that scope are dropped in the same order as for normal exit. If a destructor panics while the thread is already unwinding, the process aborts, as today.

## Partial moves

When a value has been partially moved out of, the remaining fields are dropped at the point where the whole would have been dropped, in declaration order. The moved-out fields are not dropped by the original owner.

## What this RFC does not do

This RFC does not stabilize the order of destruction for:

- elements of a `HashMap`, `HashSet` or other containers with unspecified iteration order;
- the order of statics, which are never dropped;
- the order of thread-local destructors relative to one another.

These are properties of the library types and platform and could be addressed separately.

# How We Teach This
[how-we-teach-this]: #how-we-teach-this

The reference gains a chapter, "Destructors," that lays out the rules in this RFC with examples. The book's discussion of `Drop` in the chapter on smart pointers points to it. A short table summarizing the directions (locals reversed, fields forward) would be a useful teaching aid.

A recurring tip for users: when an order matters and is not obvious from the rules above, make it obvious in the code by using an explicit `drop()` call or an inner block, regardless of the guarantee.

# Drawbacks
[drawbacks]: #drawbacks

- The existing order has inconsistencies, such as locals being reversed while fields are forward. Locking this in forever means these inconsistencies stay.
- Specifying the order restricts the optimizer. For example, a future compiler could otherwise reorder independent drops for better code or for smaller stack frames.
- Closure capture order is not obvious to a reader of the code, and users could still be surprised.

# Alternatives
[alternatives]: #alternatives

## Keep it unspecified

The simplest alternative is to continue saying the order is unspecified. This defers the problem but does not fix it. Programs depend on the present behavior regardless, and the compiler team has been reluctant to change it for just this reason, so the order is effectively stable. It would be better to be honest about it.

## Choose a different order and migrate

We could change fields to be dropped in reverse order of declaration, to match locals. That is a more consistent design, but it would break existing programs and would need an edition boundary or a long deprecation. Given the cost to the ecosystem, I do not think the gain justifies it.

## Make the order configurable

An attribute such as `#[drop_order(reverse)]` could be added later for structs that want the alternative. Stabilizing the current order is compatible with that addition. This RFC makes room for such opt-in variants but does not propose them.

# Unresolved questions
[unresolved]: #unresolved-questions

- Should the closure capture order be fixed, or documented as unspecified?
- Should the reference make explicit that the order of drop for temporaries in `match` guards is as currently implemented?
- Are there any cases where the present compiler is inconsistent with the rules above, and if so, should those be treated as bugs or be adopted into the specification?
