- Feature Name: item_like_imports
- Start Date: 2016-02-09
- RFC PR: [rust-lang/rfcs#1560](https://github.com/rust-lang/rfcs/pull/1560)
- Rust Issue: [rust-lang/rust#35120](https://github.com/rust-lang/rust/issues/35120)

# Summary

Some internal and language-level changes to name resolution.

Internally, name resolution will be split into two parts - import resolution and name lookup. Import resolution is moved forward in time to happen in the same phase as parsing and macro expansion. Name lookup remains where name resolution currently takes place (that may change in the future, but is outside the scope of this RFC). However, name lookup can be done earlier if required (importantly it can be done during macro expansion to allow using the module system for macros, also outside the scope of this RFC). Import resolution will use a new algorithm.

The observable effects of this RFC (i.e., language changes) are some increased flexibility in the name resolution rules, especially around globs and shadowing.

There is an implementation of the proposed algorithm in the form of a prototype branch, and it passes the existing test suite with small modifications.

# Motivation

Name resolution in Rustc is currently a single pass over the AST that happens after macro expansion. This has a number of consequences.

First, macros cannot take part in the module system. A macro cannot be imported by name using `use`, because at the time macros are expanded, imports have not yet been resolved. Instead, a separate `#[macro_use]` mechanism exists with its own, textual, scoping rules. To make macros first-class citizens, imports must be resolvable while expansion is still happening.

Second, the existing algorithm for resolving imports is an iterative fixed-point computation with ad-hoc rules about what is permitted. Its behaviour is hard to describe, and in some cases it depends on the order in which items appear in a file. For example, a glob import that brings a name into scope may or may not conflict with an explicit item with the same name depending on how far resolution has progressed. Users see this as surprising errors in apparently valid code. Implementers see it as a source of bugs and a barrier to improving the compiler.

Third, the current rules about shadowing by globs are more restrictive than they need to be. Two globs that import the same name from the same underlying definition are reported as ambiguity errors in some cases, although both refer to the same item. This hurts the common "prelude" pattern, where a crate re-exports many things through several paths.

The aim of this RFC is to define a clean, order-independent algorithm for import resolution that fits into the expansion phase, and to state the rules that this algorithm implements so they can be documented.

# Detailed design

## Terminology

An *import* is a `use` declaration; a *single import* names one item (`use a::b;`) and a *glob import* names every public item in a module (`use a::*;`). A *name binding* associates a name in a given namespace (types, values, macros) with a definition. A *module* contains a set of bindings: those *defined* by items in it, and those *imported* into it. *Visibility* of a binding determines which modules may see it.

## Rules for bindings

The following are the rules, in order of priority, for the set of bindings visible in a module.

1. **Items and single imports take priority over globs.** If a module has an item or a single import binding a name, and a glob import also provides that name, the item or single import wins. This is already the case today and is retained.
2. **Globs may shadow each other only if they agree.** If two globs provide the same name in the same namespace, and both refer to the same definition, there is no ambiguity and the name is bound to that definition. If they refer to different definitions, the name is ambiguous. An ambiguity is an error only if the name is actually used; merely having conflicting globs is not an error. This differs from the existing behaviour for some cases, where conflicts were reported eagerly.
3. **Explicit definitions may not duplicate.** Two items, or two single imports, or an item and a single import, binding the same name in the same namespace within a module remain an error.
4. **Imports are not allowed to shadow macro-expanded names in a way that depends on order.** If the expansion of a macro could introduce a name that would conflict with an import, the conflict is an error, regardless of whether expansion has yet occurred. This is necessary to ensure determinacy.

The observable consequence is that adding or removing a glob import, or reordering items, never changes the meaning of a program that compiles, except by turning a name use into an ambiguity error.

## The algorithm

Import resolution takes place on a *module graph*, where each module has a list of unresolved imports. The algorithm maintains, for each module, a map from `(name, namespace)` to a *resolution*. A resolution holds an optional binding and a list of the glob imports that may still contribute to it. It proceeds in rounds.

1. Initialize each module with the bindings of its items. Each import is placed in a worklist of its containing module.
2. For each import in the worklist, attempt to resolve the path of the import. Resolution of a path segment requires the previous segment to be a module whose relevant name is *determined*. A name is determined in a module when no unresolved import or glob in that module could still produce a binding with that name.
3. When a single import resolves, add the corresponding binding to the importing module. If the module already has a binding for the name from a glob, replace it, as explicit imports shadow globs. If it has one from an item or another single import, report a duplicate-definition error.
4. When a glob import resolves, record it as an edge from the imported module to the importing module. Then, for each public binding in the imported module, add it to the importing module, unless shadowed. Subsequent bindings that appear in the imported module are propagated along the edges.
5. Repeat until no progress is made. If imports remain unresolved, report an error for each, distinguishing "cannot find" from "indeterminate" (a cycle of globs that never settles).

Termination follows because the number of bindings is finite and each step only adds bindings or replaces a glob binding with a more specific one; a binding is never removed, and a replacement strictly increases specificity.

### Determinacy

The principal subtlety is deciding when a lookup can be answered "not found". Because a glob may later add a name, a negative answer is only safe once all globs that could provide the name in the module have themselves been fully resolved. The algorithm records for each module a count of unresolved globs, and treats a negative lookup as *indeterminate* while that count is nonzero. The lookup is deferred and retried in a later round.

This is sufficient to guarantee that results do not depend on the order in which imports are processed, as every successful resolution is a monotone fact: once a name is bound, it can be rebound only to a more specific binding, and anything that has been resolved through the less specific binding is re-validated at the end of the process.

### Validation

After the fixed point is reached, a pass visits all resolved imports and checks that the final binding for each is the one used when it was resolved. If an import resolved to a glob binding that was later shadowed, the shadowing is an error, which prevents the order-dependence that exists today.

## Interaction with macro expansion

Resolution is interleaved with expansion. Whenever expansion produces new items or imports, they are added to the module graph and the algorithm continues. Name lookups issued during expansion, for example to find a macro, use the same determinacy rules: if the lookup is indeterminate, expansion of the macro invocation is deferred in favour of other work.

## Language changes

For users, the following program was previously rejected and is accepted:

```rust
mod a { pub fn f() {} }
mod b { pub use a::f; }
mod c { pub use a::f; }

use b::*;
use c::*;

fn main() { f(); }
```

Both globs bring `f` into scope and both refer to `a::f`, so there is no ambiguity.

The following continues to be an error only on use:

```rust
mod x { pub fn g() {} }
mod y { pub fn g() {} }
use x::*;
use y::*;
fn main() { g(); } // error: `g` is ambiguous
```

Without the call to `g`, the program compiles.

Shadowing an item by a glob continues to be disallowed in the sense that the item wins silently; this is existing behaviour.

# Drawbacks

- The rules around glob ambiguity are more subtle than the current ones, since an error may appear only when a name is used.
- The new algorithm is more complex than the old, and it needs to be maintained. Compile-time performance on very large crates must be measured; prototype numbers suggest no regression.
- Some currently accepted programs will be rejected because the validation step flags a glob shadowing that was previously tolerated by accident of ordering. A crater run on the prototype found a handful of such cases, all easily fixed.

# Alternatives

- Leave the algorithm in place and tackle macros separately. This leaves macro scoping as a special case indefinitely.
- Make all glob conflicts errors, regardless of use. This is simpler but breaks the prelude pattern and is less backwards compatible.
- Disallow globs altogether in certain positions. Too disruptive.

# Unresolved questions

- The precise error messages for indeterminate imports. The prototype reports a generic "import resolution is stuck" message that should be improved.
- Whether visibility restrictions on globs (`pub(crate) use`) require additional rules in the validation pass.
- The relationship to a future RFC on macro imports via `use`.
