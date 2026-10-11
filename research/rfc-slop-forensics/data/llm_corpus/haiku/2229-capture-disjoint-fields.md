# Rust RFC 2229: `capture_disjoint_fields`

- Feature Name: `capture_disjoint_fields`
- Start Date: 2019-07-22
- RFC PR: rust-lang/rfcs#2229
- Rust Issue: rust-lang/rust#53488

## Summary

This RFC proposes that closures capture the places they use, not the variables that contain them, and that they capture the minimal set of places needed. Today a closure that mentions one field of a struct captures the whole struct. Under this proposal, the closure captures only the field it uses, and the rules for borrowing and moving disjoint fields apply to closure captures in the same way they apply to ordinary code.

The effect is that code which is rejected today because of an overlapping borrow would compile, and that some moves which previously consumed an entire value would instead move only the fields in use.

## Motivation

Closures in Rust capture their environment by the least demanding mode that still satisfies their body. The unit of capture is the whole variable. A closure that reads `self.count` inside a method that also mutates `self.items` is therefore considered to borrow all of `self`, which conflicts with the mutable access to `self.items` made outside the closure.

Programmers work around this by copying the field into a local variable before creating the closure, or by restructuring the code so that the closure does not need the whole struct. Both workarounds are common, and both are a sign that the language rules do not match the way people reason about their code. A reader sees that the closure touches only one field and expects the compiler to agree.

The mismatch is also a problem for moves. A closure that moves one field out of a struct currently moves the entire struct into its environment. That can drop fields the author did not intend to give away, and it can make a value unusable after a closure that needed only a small part of it.

Minimal capture fixes both problems. It makes the closure's footprint match its actual use, and it allows the borrow checker to reason about closures with the same precision it already applies to direct field access.

## Guide-level explanation

Consider a struct with two fields and a closure that uses only one of them:

```rust
struct Config {
    name: String,
    retries: u32,
}

let mut cfg = Config { name: String::from("worker"), retries: 3 };
let show = || println!("{}", cfg.name);
cfg.retries += 1;
show();
```

Under the current rules, this does not compile, because the closure borrows all of `cfg` and the assignment to `cfg.retries` conflicts with that borrow. Under the proposed rules, the closure captures only `cfg.name` by shared reference. The assignment to `cfg.retries` touches a different place, so there is no conflict, and the program is accepted.

The same reasoning applies to moves. A closure that consumes `cfg.name` moves only that field. The value `cfg.retries` remains available afterward, since it was never part of the closure's environment.

Authors do not need to annotate anything. The compiler infers the places used by each closure, and the programmer continues to write ordinary code.

## Reference-level explanation

A capture is a *place*, meaning a variable followed by a sequence of field projections and dereferences. The compiler collects the places that a closure body uses and computes, for each place, the least demanding capture mode that the body requires: by shared reference, by mutable reference, or by value.

When two captured places overlap, meaning one is a prefix of the other, the compiler captures the shorter place, since it subsumes the longer one. When they are disjoint, each is captured separately. The environment of the closure is a tuple of these captures, and each capture is ordered deterministically so that layout and drop order are predictable.

Captures through a reference are truncated at the point where the reference is dereferenced by value, so that a closure does not reach through a pointer in a way that would change the meaning of the program. Captures through a `Box` may be precise, since the box owns its contents directly.

The rules for move closures are similar, except that every capture is by value. A move closure that uses `cfg.name` moves that field into the environment and leaves the remainder of `cfg` in place. Drop order for the captured places follows the order of the fields in the struct.

Packed structs and unions are excluded from precise capture in the initial implementation, since their field layout imposes constraints that interact poorly with the new rules.

## Drawbacks

Precise capture makes the environment of a closure harder to predict from its source text. A developer who reads a closure that mentions a struct may not realize that the closure captures only one field, unless the tooling makes the capture set visible.

The new rules also change the observable drop order of values in some programs. Most such changes are benign, but code that depends on a whole struct being dropped at a particular point may behave differently.

Finally, the implementation adds complexity to the closure analysis, which is one of the more delicate parts of the compiler.

## Rationale and alternatives

The alternative is to leave the current rule in place and rely on programmers to introduce local bindings. This is a workable pattern, but it is an extra step that the compiler could take on the programmer's behalf, and it leaves the borrow checker's behavior less consistent with the rules for ordinary field access.

A second alternative is to capture the whole variable by default, but allow an explicit annotation that requests precise capture. This avoids changing existing code, but it places a burden on every author who wants the more natural behavior, and it leaves the default at odds with how the rest of the language works.

The proposal chooses precise capture by default because it matches the rules that already govern direct access to fields. A closure is then just another place where the same rules apply.

## Prior art

Other languages with closures that capture by reference have had to decide how precise their captures should be. Some capture whole variables, and some capture individual fields, and the choice affects how easily programs can be reasoned about. The Rust community has discussed this design in the issue tracker and in the internals forum for several years, and the proposal reflects those conversations.

## Unresolved questions

The interaction between precise capture and `async` blocks is not fully settled. The RFC defers that question to a later stage, since async blocks have their own capture machinery that needs separate analysis.

The best way to present captured places in diagnostics is also open. Error messages should name the captured place rather than the variable, but the exact wording needs testing.

## Future possibilities

Once precise capture is in place, tooling could show the capture set of each closure in an editor, which would help programmers understand what their closures borrow. The same analysis could also support lints that warn when a closure captures far more than it uses.
