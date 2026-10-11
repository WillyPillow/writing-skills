- Feature Name: `capture_disjoint_fields`
- Start Date: 2017-11-28
- RFC PR: rust-lang/rfcs#2229
- Rust Issue: rust-lang/rust#53488

# Summary

This RFC proposes that closures capture as little as they need rather than as much. The borrow checker already lets code borrow or move disjoint fields of a struct independently. Closure captures should follow the same rules. A closure that uses `self.a` should capture `self.a`, not all of `self`.

With this change the following code would compile:

```rust
struct Foo { a: String, b: String }

impl Foo {
    fn update(&mut self) {
        let a = &mut self.a;
        let f = || println!("{}", self.b);
        a.push_str("!");
        f();
    }
}
```

```rust
let mut point = (1, 2);
let c = || point.0 += 1;
println!("{}", point.1);
```

There has already been some discussion of this in rust-lang/rust#19004 and on the Rust internals forum.

# Motivation

Today a closure captures every variable it mentions as a whole. If a closure body refers to `self.b`, the closure captures `self`. If it refers to `x.0.field`, it captures `x`. That is simple to describe, but it doesn't match how Rust treats borrows elsewhere.

Outside closures, the borrow checker tracks borrows by *place*, meaning a path like `self.a` or `x.0.field`. Two borrows conflict only if their places overlap. This compiles:

```rust
let a = &mut self.a;
let b = &self.b;
a.push_str(&b);
```

Wrap the second borrow in a closure and it fails:

```rust
let a = &mut self.a;
let print_b = || println!("{}", self.b);
//            ^^ error: cannot borrow `self` as immutable because
//               `self.a` is also borrowed as mutable
a.push_str("!");
print_b();
```

The two programs ask for the same thing. Whether the read of `self.b` sits inside a closure shouldn't decide whether the program compiles.

This shows up all the time:

- **Methods on `&mut self`.** Building an iterator chain or callback that reads one field while another field is being mutated is a common pattern, and today it needs a temporary binding.
- **Struct destructuring as a workaround.** Users write `let Foo { a, b } = self;` (or `let b = &self.b;`) before the closure, just to give the closure a narrower variable to capture. It's boilerplate that hides what the code is doing.
- **`move` closures.** A `move` closure that uses `self.config` moves all of `self` when the user only wanted that one field. In async code and threaded code, where `move` closures are everywhere, this means extra clones or awkward restructuring.

Newcomers in particular get confused by the inconsistency. The error says `self` is borrowed while the closure only mentions `self.b`, and the usual answer, "closures capture whole variables", is an implementation detail with nothing to do with what the program means.

# Guide-level explanation

A closure captures the *places* it uses, not the variables those places start from.

```rust
let mut s = State { counter: 0, name: String::from("x") };

let mut inc = || s.counter += 1;   // captures `s.counter` by mutable reference
println!("{}", s.name);            // fine: `s.name` is a different place
inc();
```

Before this change, `inc` would capture `s` by mutable reference and the `println!` would be rejected.

The same goes for `move` closures:

```rust
let s = State { counter: 0, name: String::from("x") };
let c = move || println!("{}", s.name);  // moves `s.name` into the closure
println!("{}", s.counter);               // fine: `s.counter` was not moved
```

The rule is the one users already know from ordinary borrows: if the paths don't overlap, the captures don't conflict.

## Mode of capture

Each captured place keeps the existing capture mode rules. A place is captured by shared reference if it is only read, by mutable reference if it is mutated, and by value if it is moved out of or the closure is `move`. These are worked out per place, not per variable.

If a closure uses both a place and one of its ancestors, for example `s` and `s.name`, it captures the ancestor, using the strongest mode required.

# Reference-level explanation

## Capture analysis

For each closure, the compiler collects the set of places the body uses, together with how each is used (read, mutate, move). A place is a local variable followed by zero or more projections. This RFC deals with field projections (`.f`, `.0`). The following rules are then applied.

1. **Truncate at dereferences of raw pointers.** Unsafe pointer dereferences are captured at the pointer, as today.
2. **Truncate at a move through a reference.** A by-value capture can't move out of something behind `&` or `&mut`, so the place is cut back to the reference.
3. **Truncate at union fields.** Reading a union field is unsafe and its disjointness rules differ, so unions are captured whole.
4. **Truncate at `#[repr(packed)]` fields** when the capture would create a reference to an unaligned field.
5. **Merge ancestors.** If a place and one of its prefixes are both captured, keep only the prefix, using the strongest mode.

The result is the closure's capture list. The closure's generated struct has one field per captured place, not one per variable.

## Borrow checking

Captured places become ordinary borrows or moves at the point the closure is created. The borrow checker checks them exactly as it checks any other borrow of a place, so it needs no new rules.

## Drop order

This change is observable. Today, a `move` closure that captures `s` owns all of `s`, and `s` is dropped when the closure is dropped. With precise capture, a closure that only moves `s.name` owns only `s.name`. The rest of `s` is dropped at the end of the enclosing scope, which may be earlier or later than before.

```rust
{
    let s = State { counter: Noisy(1), name: Noisy(2) };
    let c = move || drop(&s.name);
    // Before: both fields dropped when `c` drops.
    // After: `s.counter` dropped at end of scope; `s.name` when `c` drops.
}
```

Programs whose correctness depends on drop timing (locks, guards, files) could change behavior silently.

## Migration

Because the drop order changes, this should land at an edition boundary. For crates on the older edition, a migration lint will find closures whose drop order or auto-trait implementations (`Send`, `Sync`, `Clone`, `UnwindSafe`) would change. It will then suggest inserting `let _ = &s;` at the top of the closure body, which forces the whole variable to be captured and keeps the old behavior.

The auto-trait point matters. A closure that used to capture a `Send` struct might now capture just a non-`Send` field of that struct, or the other way round. The migration lint covers both cases.

# Drawbacks

- **Larger closures.** A closure that uses five fields of `self` by reference now holds five references instead of one. That can make closures bigger and could affect performance in tight loops. Optimizations can sometimes merge the references when no disjointness is needed, but this RFC doesn't require that.
- **Harder to explain drop order.** "Dropped with the closure" now applies to individual fields, not whole variables.
- **Migration cost.** Even with an automatic lint, an edition change that touches closure semantics adds churn.

# Rationale and alternatives

## Keep whole-variable capture

Users would keep writing the workarounds described above. The inconsistency with ordinary borrowing would remain.

## Capture minimally only for non-`move` closures

This keeps `move` drop semantics the same, but leaves out the cases where precise capture helps most: async blocks and spawned threads.

## Explicit capture lists

C++-style capture clauses (`[&a, b]`) would let users pick exactly what is captured. That adds syntax and still leaves the default unintuitive. Explicit capture lists could be proposed separately and would work fine alongside this RFC.

# Prior art

- **C++ lambdas** capture variables, not members. Capturing `this` captures the whole object, which is a common source of lifetime bugs.
- **Swift closures** capture variables by reference unless a capture list says otherwise. There is no field-level capture.
- Field-sensitive analyses for closures and lambdas appear in the escape-analysis literature, but most languages with garbage collection gain little from them. Rust's ownership model is what makes the precision matter.

# Unresolved questions

- How should captures through `Box` dereferences be handled? `Box` is special to the borrow checker and allows moving out of a dereference. Capturing through it is attractive but complicates the truncation rules.
- Should the compiler optimize multiple shared captures from the same root into a single reference when that can be shown safe?
- Exactly which diagnostics should the migration lint emit, and how should it handle macro-generated closures?
