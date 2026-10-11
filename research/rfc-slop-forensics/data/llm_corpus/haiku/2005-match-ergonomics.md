# RFC 2005: Default Binding Modes for Pattern Matching

- Feature Name: `match_default_bindings`
- Start Date: 2017-02-14
- Status: Proposed

## Summary

This RFC improves the ergonomics of pattern matching when the value being matched is a reference. Today, a program that matches on a reference must spell out the reference structure in the pattern, using `&` patterns to dereference and `ref` or `ref mut` to bind by reference. This is correct but verbose, and it forces the reader to track the reference layers by hand. Under this proposal, a pattern written against the underlying type can be matched against a reference to that type. The compiler inserts the dereferences automatically and switches the binding mode from move to reference as it passes through each reference layer. The existing explicit forms continue to compile with the same meaning.

## Motivation

Consider a common case: iterating over a slice of pairs and destructuring each pair.

```rust
let pairs: Vec<(String, u32)> = load();
for &(ref name, count) in pairs.iter() {
    // ...
}
```

Here the `&` pattern strips the reference produced by `iter()`, and the `ref` keyword is needed because `name` would otherwise try to move a `String` out of a borrowed tuple, which is not allowed. The programmer must hold two rules in their head at once: the outer reference is peeled by `&`, and the inner binding must be a `ref`. Beginners find this confusing, and experienced users find it noisy.

The same problem appears in `match` expressions over `Option<&T>`, in `if let` chains, and in closures that receive references. Each of these sites repeats the same pattern of `&` and `ref` tokens, and the repetition obscures the logic of the match.

The desired form is simpler. The programmer writes the pattern that describes the data they care about, and the compiler figures out how to access it:

```rust
for (name, count) in pairs.iter() {
    // name: &String, count: &u32
}
```

Here the tuple pattern matches through the reference. Because the default binding mode is now "ref", each binding receives a reference to the corresponding field, and no `ref` keyword is needed.

## Guide-level explanation

When a non-reference pattern is matched against a reference value, the compiler automatically dereferences the value and applies the pattern to the referent. This is called default binding mode. The binding mode starts as "move" and changes as the compiler peels reference layers:

- When the compiler dereferences a shared reference, the binding mode becomes "ref".
- When it dereferences a mutable reference, the binding mode becomes "ref mut", unless the mode is already "ref", in which case it stays "ref".
- Bindings made while the mode is "ref" or "ref mut" receive references to the matched data, rather than moving or copying it.

Explicit `&` and `ref` remain legal. A pattern that spells out the reference structure continues to behave exactly as before. Mixing explicit and default forms is permitted at the level of individual sub-patterns, but the rule for each binding is the same: explicit `ref` or `ref mut` on a binding overrides the default mode for that binding, and an explicit `&` pattern must match a reference type.

To help readers, the compiler's lints recommend the simpler form where the explicit one is redundant, but no existing program is rejected.

## Reference-level explanation

Matching proceeds through a sequence of steps. When the pattern is a non-reference pattern (a struct, tuple, tuple struct, slice, or literal pattern other than a string literal in some positions) and the scrutinee type is `&T` or `&mut T`, the compiler inserts a dereference of the scrutinee and updates the default binding mode as described above. The process repeats for nested references.

Literal patterns and range patterns are not auto-dereferenced in the same way, because their type is determined by the literal. The string literal pattern `"abc"` already has type `&str`, so it matches a `&str` scrutinee directly.

Binding patterns with explicit `ref` or `ref mut` ignore the default binding mode for their own binding and bind by reference regardless. A binding pattern written without `ref` under the "ref" mode produces a reference. Under the "move" mode, it produces a value, as before.

The checker must ensure that a `mut` binding under the "ref" mode is rejected, since it would otherwise create an ambiguous mutable alias. The rule is that `mut x` resets the binding mode to "move", which is the only way to request a move out of a borrowed structure, and this request is an error when the data is behind a shared reference.

## Drawbacks

The proposal adds a second, implicit way to write patterns, and readers must learn that a pattern's meaning can depend on the type it is matched against. A pattern such as `Some(x)` binds differently depending on whether the scrutinee is `Option<T>` or `&Option<T>`. Critics argue this hides information that was previously visible in the source text.

The rules for binding modes interact with `mut` in subtle ways, and some programs that compiled under the old rules now require careful reading to predict. The compiler team considers these cases rare in practice, but the risk is real.

## Rationale and alternatives

The simplest alternative is to do nothing. The explicit forms are sound, and the cost is only verbosity. This option keeps the language smaller, but it leaves a steady source of friction in code that matches on references, which is common in iterator chains.

A second alternative is to adopt auto-dereferencing without changing binding modes. This is insufficient, because binding a non-Copy field through a reference would still need a `ref` keyword, and the result would be a syntax rule with exceptions. Changing the binding mode together with the dereference keeps the rule uniform.

A third alternative is a lint-only approach, in which the compiler accepts only the explicit forms but suggests simplifications. This was rejected because it does not remove the verbosity from code that is written by hand, and it does not help readers of existing code.

The chosen design follows a principle already present in the language: a pattern describes the shape of the data, and the matching machinery should handle the mechanical parts of accessing that shape. The design also preserves backward compatibility, since every program that compiled before still compiles with the same meaning.

## Prior art

Other languages with pattern matching on references have adopted similar rules. The design here is narrower, focusing only on the reference layers that the type system already tracks, and it does not introduce any new syntax.

## Unresolved questions

- The exact interaction between default binding modes and `box` patterns is not settled and should be resolved during implementation.
- The lint that recommends simplification needs a precise definition, so that it does not fire on code where the explicit form is clearer for a specific reason.
- Whether the "ref mut" mode should be further restricted in closure parameter positions remains open.

## Future possibilities

If this RFC is accepted, the team can extend the same mechanism to other forms of implicit access, such as pattern matching through smart pointers that implement deref. That extension is out of scope here, but the mental model introduced by default binding modes would carry over without modification.
