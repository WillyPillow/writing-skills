- Feature Name: `item_like_imports`
- Start Date: 2016-02-09
- RFC PR: [rust-lang/rfcs#1560](https://github.com/rust-lang/rfcs/pull/1560)
- Rust Issue: [rust-lang/rust#35120](https://github.com/rust-lang/rust/issues/35120)

# Summary

Make internal and language-level changes to name resolution.

Internally, split name resolution into two parts: *import resolution* and *name lookup*. Import resolution moves earlier, into the same phase as parsing and macro expansion. Name lookup stays where name resolution happens today, though it can also be performed earlier when required, which matters for future work on resolving macros through the module system.

Import resolution uses a new fixed-point algorithm. The observable language changes are increased flexibility in the resolution rules, especially for glob imports and shadowing. In short: imports behave more like items.

# Motivation

## Imports are not like items

In current Rust, a `use` declaration and an item declaration both introduce a name into a module, but they follow different rules:

- An item can be referenced from anywhere in its module regardless of order. An import is mostly order-independent too, but the resolver has special cases that make some orderings fail.
- A glob import (`use a::*`) cannot import names that are themselves brought in by a glob in `a` in some circumstances, and the rules for when this works are hard to explain.
- An explicit import and a glob import of the same name conflict in some places and not others.
- Private imports are not visible to glob imports in child modules, though private items are, because of how privacy and globs interact in the old resolver.

These inconsistencies show up as confusing errors whose fix is usually to reorder or duplicate imports until the resolver accepts them.

## Globs are too fragile

Globs are a source of breakage between crate versions. If `a` exports `foo` through a glob and `b` exports `foo` through another glob, and a crate imports both `a::*` and `b::*`, the result today is an error as soon as both globs are resolved, even if the crate never uses `foo`. Adding a public item to a library can therefore break downstream crates that never mention it.

## Macros need the module system

Macro names are currently resolved by textual order and `#[macro_use]`, outside the module system. A long-standing goal is to let macros be imported with `use` like other items. That requires knowing what imports resolve to during macro expansion, which means import resolution cannot wait until after expansion finishes. Splitting the resolver is a prerequisite.

# Detailed design

## Two phases

**Import resolution** determines, for every `use` declaration in the crate, which definition each imported name refers to. It runs interleaved with macro expansion: as expansion produces new items and imports, the resolver incorporates them and makes progress.

**Name lookup** resolves every path in expressions, types and patterns to a definition. It runs after expansion as today, but because import resolution has finished, lookup can be done at any point when needed.

## Import resolution algorithm

The resolver maintains, for each module, a set of *bindings*: name and namespace pairs mapped to a definition, with a flag indicating whether the binding is a glob binding. Imports start as *indeterminate*.

The algorithm repeats until a fixed point:

1. For each indeterminate single import `use a::b::c`, try to resolve the module path `a::b`. If it resolves, look up `c` in it. If `c` is *determined* (bound by an item, a resolved explicit import, or a glob that can no longer change), record the binding. If `c` is *determinately absent*, record failure. Otherwise leave it indeterminate.
2. For each glob import `use a::*`, once `a` resolves, add every public (or visible) binding of `a` to the importing module as a glob binding, and arrange for future bindings added to `a` to propagate.
3. Whenever macro expansion produces new items, add them to their modules.

A name in a module is determined once no unresolved import or glob could still add or change a binding for it. When no progress can be made and some imports remain indeterminate, those imports are errors (unresolved or cyclic).

## Shadowing rules

- An item or explicit import shadows a glob import of the same name in the same namespace. No error is reported.
- Two explicit bindings (items or explicit imports) of the same name in the same namespace are an error, as today.
- Two glob imports that bring in *different* definitions for the same name are **not** an error at the point of import. The name is marked *ambiguous*. Only an actual use of an ambiguous name is an error.
- Two glob imports that bring in the *same* definition are not ambiguous.

These rules make adding a public item to an upstream module much less likely to break downstream crates: the new name is either shadowed by an explicit binding or ambiguous but unused.

## Globs and privacy

A glob import brings in every name that is *visible* from the importing module, rather than only `pub` names. In practice this means a glob from a parent module imports the parent's private items and private imports, since those are visible to the child. This makes `use super::*` behave as people expect, which is particularly useful in `mod tests`.

## Re-exports

`pub use` of an import re-exports it as before. A glob re-export (`pub use a::*`) re-exports every binding of `a` that is visible both to the re-exporting module and at the re-export's own visibility level.

## Imports are visible to globs

Imports, like items, are bindings that other globs can see. `use a::*` imports names that `a` itself imported, subject to visibility. Previously this worked only for public imports and only in some orderings.

## Name lookup

Lookup of a path in an expression or type proceeds by resolving each segment in the module bindings computed above, then in the lexical scope (local variables, generics, prelude) as today. Lookup reports an error when it reaches an ambiguous binding.

# Examples

```rust
mod a { pub fn f() {} }
mod b { pub fn f() {} }

mod c {
    use a::*;
    use b::*;     // ok: f is ambiguous but not yet an error
    fn g() {
        f();      // error: `f` is ambiguous
    }
}

mod d {
    use a::*;
    use b::f;     // ok: explicit import shadows glob
    fn g() { f(); }   // refers to b::f
}
```

```rust
mod m {
    fn helper() {}
    #[cfg(test)]
    mod tests {
        use super::*;
        #[test] fn t() { helper(); }   // ok: private item is visible
    }
}
```

# Drawbacks

- The new algorithm is a significant rewrite of the resolver, with risk of regressions.
- Making globs import private names means that adding a private item to a parent module can shadow or create ambiguity in child modules. Because ambiguity errors only fire on use, this is rarely visible in practice.
- Ambiguity being reported lazily means some mistakes are caught later, at the use site rather than the import.

# Alternatives

**Keep the current resolver and patch its edge cases.** The inconsistencies come from the order-dependent design, so patches tend to introduce new edge cases.

**Make glob conflicts always an error.** Simpler, but it preserves the fragility that motivates the change.

**Prefer the first glob on conflict.** Order-dependent and surprising; rejected.

# Unresolved questions

- The exact interaction with macro name resolution is left to a future RFC.
- Whether to warn on unused ambiguous names.

# Backwards compatibility

The changes are almost entirely relaxations: programs that compiled before continue to compile. The exception is that globs now import private items from ancestors, which could in principle create ambiguity in existing code. A crater run will measure this; any breakage can be phased in with warnings.
