# RFC 2229: capture_disjoint_fields

- Feature Name: `capture_disjoint_fields`
- Start Date: 2018-04-05
- RFC PR: rust-lang/rfcs#2229
- Rust Issue: rust-lang/rust#53488

## Summary

This RFC proposes that closure capturing should be minimal rather than maximal. Conceptually, the existing rules regarding borrowing and moving disjoint fields should be applied to capturing. If implemented, the following code examples would become valid:

```rust
let a = SomeStruct::new();
drop(a.x);
let c = || println!("{}", a.y); // Error: cannot borrow `a` in its entirety, since `a.x` was moved
c();
```

```rust
let mut a = SomeStruct::new();
let c = || a.y += 1;
a.x += 1; // Error: cannot use `a.x` while `a` is mutably borrowed by the closure
c();
```

Note that some discussion of this has already taken place:

- rust-lang/rust#19004
- Rust internals forum

## Motivation

Today, a closure that mentions `a.y` captures all of `a`. The compiler computes the set of captured *variables*, not the set of captured *places*. This is simple to explain and to implement, but it is surprising, because the rest of the borrow checker is precise about disjoint fields. This works:

```rust
let mut a = SomeStruct::new();
let x = &mut a.x;
let y = &mut a.y;
*x += 1;
*y += 1;
```

but this does not:

```rust
let mut a = SomeStruct::new();
let mut incr_x = || a.x += 1;
let mut incr_y = || a.y += 1; // Error: `a` already mutably borrowed
incr_x();
incr_y();
```

The two forms are semantically equivalent: each borrows a different field. The closure form fails only because of an implementation detail.

### Real-world friction

The problem shows up in several common patterns.

**Methods that take `&mut self` and use closures.** A method holds `self.items` and `self.counter`, and iterates over the first while updating the second:

```rust
impl Tracker {
    fn process(&mut self) {
        self.items.iter().for_each(|item| {
            self.counter += item.weight; // Error: `self` is already borrowed
        });
    }
}
```

The expression `self.items.iter()` borrows `self.items` immutably, but the closure captures `self` in its entirety by mutable reference, so the two borrows conflict. Programmers work around this by destructuring `self` into local references before the call, which is noisy and hides the real intent.

**Move closures and partial moves.** With `move`, a closure that mentions only `a.name` currently moves all of `a`. The programmer who wanted to move the `String` and keep using a `Copy` field must clone or copy fields into locals first.

**Threading.** When spawning a thread with a `move` closure, large structs are moved wholesale even when the thread needs one field. This obscures ownership and can force needless clones.

### Why it matters now

Closures are pervasive in idiomatic Rust: iterator adaptors, callbacks, thread spawns, and `async` blocks. The mismatch between the precision of ordinary borrow checking and the coarseness of capture is one of the more common "why does the compiler reject this?" questions, and it is a barrier for newcomers who reasonably expect disjoint fields to behave independently.

## Guide-level explanation

Closures capture the *places* they use, not the entire variables that contain them. If a closure body mentions `a.y`, it captures `a.y`. If it mentions `a.x.z`, it captures `a.x.z`, not `a.x` and not `a`.

Take the earlier example again:

```rust
let mut a = SomeStruct::new();
let mut incr_x = || a.x += 1; // captures `a.x` by mutable reference
let mut incr_y = || a.y += 1; // captures `a.y` by mutable reference
incr_x();
incr_y();
```

Now this compiles, for the same reason that taking `&mut a.x` and `&mut a.y` does.

### Capture modes

Each captured place is captured in the least restrictive mode that the closure body needs, as at present: by shared reference, by mutable reference, or by value. For `move` closures, every captured place is moved.

```rust
let a = SomeStruct::new();
drop(a.x);
let c = || println!("{}", a.y); // OK: captures only `a.y`
c();
```

After `a.x` is moved out of `a`, the remaining fields are still usable, and the closure captures `a.y` by reference.

### Rules at a glance

1. The closure captures every place expression it uses, in the form of a path from a local variable through field accesses (and dereferences where applicable).
2. If one place is a prefix of another, only the shorter is captured. If the closure uses both `a.x` and `a.x.z`, it captures `a.x`, in the stronger of the two modes.
3. Captures stop at dereferences of raw pointers, at fields of `repr(packed)` structs, and at indexing operations. For example, using `v[0]` captures `v`.
4. Captures stop at the field of a type that implements `Drop`, if capturing deeper would require moving out of it. A value of a type with a destructor cannot be partially moved.

### Effect on drop order

A `move` closure that captures `a.x` moves just `a.x`. The remaining fields of `a` stay in place and are dropped when `a` goes out of scope. This is already the behaviour when moving a field manually, so there is nothing new to learn, but it can change when a given field is dropped compared with today. This is discussed under Drawbacks.

## Reference-level explanation

### Capture analysis

The compiler's upvar analysis currently records, for each closure, a list of captured local variables, each with a mode. Under this RFC, it records a list of captured places. A *place* is a local variable followed by zero or more projections: field accesses and dereferences of references and boxes.

The analysis proceeds as follows.

1. Walk the closure body and collect every place expression that refers to a variable defined outside the closure, together with the mode in which it is used (by copy or move, by shared borrow, by mutable borrow).
2. Truncate each place at the first projection that cannot be captured precisely: an index operation, a dereference of a raw pointer, a field of a packed struct, a field of a union, or any projection that would move out of a value whose type implements `Drop`.
3. For `move` closures, truncate each place at the first dereference of a reference, since moving out of a reference is not possible. The reference itself is captured by value, preserving existing semantics.
4. Merge places such that if one is an ancestor of another, only the ancestor remains, with the mode set to the stronger of the two.
5. Assign a mode to each remaining place.

### Closure layout

A closure is a struct whose fields correspond to the captures. After this change, the number and types of fields may differ. The layout is not guaranteed and nothing public should depend on it, but `size_of` of a closure may shrink, which is generally beneficial.

### Auto traits

Whether a closure is `Send`, `Sync` or `Clone` depends on the types of the captured places. Capturing less can make a closure `Send` when it was previously not, because it no longer captures a non-`Send` field. The reverse is not possible, but capturing different values could change behaviour for `Clone`.

### Drop order

For non-`move` closures, there is no change, since they hold references. For `move` closures, fields moved into the closure are dropped when the closure is dropped; fields not captured are dropped with their parent variable. This may change the order in which destructors run compared with the previous behaviour, where the whole variable was moved into the closure. The compiler should provide a migration lint, under the edition mechanism, to flag closures in which the order of drop could change in a way that matters, namely where a captured field's type or a non-captured sibling has a significant destructor.

### Edition considerations

Because of the drop order and auto trait changes, the new capture rules would be applied in a new edition, with a migration lint that rewrites closures to preserve existing behaviour by inserting a `let _ = &a;` statement at the top of the closure body, forcing capture of the whole variable.

## Drawbacks

- **Observable changes in drop order.** Code that relies on destructors running when a closure is dropped may behave differently. Such code is rare, but when it exists, such as with guards, the effect can be subtle. The migration lint addresses the common cases.
- **Compiler complexity.** Capture analysis becomes more intricate, as do the data structures that represent captures. MIR building for closures must handle places rather than variables.
- **Harder mental model of closure size.** Programmers may be surprised that a closure's size depends on which paths it uses.
- **Diagnostics.** Error messages must describe captures at the level of places, for example "closure captures `a.x`", and be precise about why a particular capture was truncated.
- **Cross-version differences.** The same source may compile differently under different editions, which adds to the cognitive load of the edition story.

## Rationale and alternatives

### Why minimal capture

Minimal capture matches the model users already hold of how borrowing works. The borrow checker is already field-sensitive, and closures are the one place where that precision is lost. Removing the exception makes the language more uniform.

### Alternative: keep the status quo

Programmers can destructure into locals before creating the closure. This works but is verbose, obscures intent, and is not discoverable. It also does not help with `move` closures when the reordering needed is non-trivial.

### Alternative: explicit capture lists

C++ and other languages let the programmer name captures explicitly, as in `[&a.x]`. This is flexible but heavy, and it would add syntax to a language where the compiler can infer the same information.

### Alternative: field-level capture only for non-move closures

This limits the change to borrowing closures, avoiding the drop order issue. But it creates an inconsistency between `move` and non-`move` closures that is hard to explain. The edition-gated approach is preferable.

## Prior art

C++ lambdas capture variables, not subobjects, though C++20 allows capturing structured bindings in limited ways and init-captures such as `[x = a.x]` let the user pick a subobject. Swift closures capture variables whole. Go closures capture variables by reference. In languages with garbage collection the question rarely arises, since aliasing is not restricted.

## Unresolved questions

- Should the lint suggest the `let _ = &a;` workaround or a more targeted fix?
- How should captures interact with `async` blocks, which also capture upvars and have layout implications?
- Should capture precision extend through `Box` dereferences for `move` closures?
- How precisely should diagnostics describe truncation of a captured path?
