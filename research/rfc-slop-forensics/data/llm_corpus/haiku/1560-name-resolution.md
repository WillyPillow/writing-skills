- Feature Name: `item_like_imports`
- Start Date: 2016-03-20
- RFC PR: [rust-lang/rfcs#1560](https://github.com/rust-lang/rfcs/pull/1560)
- Rust Issue: [rust-lang/rust#35120](https://github.com/rust-lang/rust/issues/35120)

# Summary

This RFC makes two kinds of change to name resolution. Internally, name resolution is split into two parts: import resolution and name lookup. Import resolution moves earlier in the compilation pipeline, so that it happens in the same phase as parsing and macro expansion. Name lookup stays where name resolution takes place today.

The observable effect on the language is a more flexible set of rules for imports, especially around glob imports and shadowing. Imports become more like ordinary items. A `use` declaration can name a function, a type, a module, or a macro in the same way, and its position in a module no longer determines whether it can be seen.

# Motivation

The current rules for name resolution were written for a compiler that handled imports in a single late pass. That pass has to deal with cycles, with glob imports that shadow each other, and with macros whose expansion depends on names that have not yet been resolved. The implementation has grown complicated, and the rules that describe it are hard to state precisely.

A user encounters the consequences of this in several ways. A glob import may be silently shadowed by a name that happens to be defined later in the same module. An import may be rejected in one position and accepted in another, for reasons that are not obvious from the code. Macros that want to use the module system cannot do so, because the module system is not ready when macros are expanded.

The proposal addresses these problems by separating the two parts of name resolution and by giving import resolution a clear algorithm. The change to the rules is modest, but it makes the language easier to explain and easier to extend.

# Guide-level explanation

An import is a declaration that brings a name from another module into the current scope. Under the new rules, an import is treated as an item in its own right. It can be used before it appears in the source, and its effect does not depend on where it is written inside a module.

Consider a module that imports a function from a sibling and then defines a local function with a different name. Under the current rules the order of declarations can matter when the two names collide. Under the proposal, a collision between an explicit import and a local item is an error, regardless of order, and the error message points to both declarations.

Glob imports behave in a more predictable way. A glob import brings in every public name from a module, but it does not override a name that was imported explicitly or defined locally. When two glob imports supply the same name, the name is ambiguous, and it is an error to use it. The programmer must resolve the ambiguity with an explicit import.

These rules match the intuition that most programmers already have. The difference is that the compiler now enforces them consistently, rather than applying a special case depending on the order of the source text.

# Reference-level explanation

Name resolution is divided into two passes. The first pass resolves imports. It runs during the expansion phase, after parsing and before most macros are expanded. Each import is recorded as a binding that maps a name in the current module to a definition in another module, or to a pending definition that is not yet known.

Import resolution uses a fixed-point algorithm. Each import is attempted repeatedly until no further progress is made. An import that depends on a glob import that has not yet been resolved is deferred. When no import can make progress, the remaining imports are either errors or are reported as indeterminate, depending on whether their target exists.

The second pass is name lookup. It takes place where name resolution takes place today, during the later stages of compilation. It consults the bindings produced by the first pass, together with the items defined in each module, to find the definition that a path refers to.

The rules for shadowing are the central change. A binding introduced by an explicit import shadows a binding introduced by a glob import in the same module. A local item shadows a glob import. An explicit import that conflicts with a local item is an error. These rules are chosen so that the result of a lookup does not depend on the order of the source code.

Macros are affected in a positive way. Because import resolution happens during expansion, a macro can refer to items through the module system. This is outside the scope of the present RFC, but the design is chosen so that it can be added later without a further restructuring.

# Drawbacks

The change is substantial. The new algorithm must be implemented carefully, and the interaction with macro expansion must be tested extensively. A mistake in the fixed-point iteration could cause the compiler to loop, or to report an error for a program that is valid.

Some existing programs will be rejected. In particular, a program that relies on a local item silently shadowing a glob import will need to be changed, although the change is usually a simple one. The migration cost is real, and the project must provide clear diagnostics to help users make the change.

The rules are more uniform, but they are also more explicit. Some users may find that they have to write more imports than before in order to make their intentions clear.

# Rationale and alternatives

The alternative is to keep the existing rules and to fix specific bugs as they are reported. This has been the approach for several years, and it has produced a collection of special cases that are difficult to reason about. The proposal aims to replace these special cases with a single algorithm.

A second alternative is to make all imports ordered, so that an import can only refer to names that appear before it in the source. This is simple to state but unnatural for programmers, who expect declarations in a module to be order independent. It is rejected.

A third alternative is to keep import resolution late and to allow macros to see the result only after a separate pass. This preserves the current structure but does not solve the problem that macros cannot use the module system. It would also leave the rules for glob imports as complicated as they are now.

# Prior art

Many languages with a module system handle imports as declarations that are independent of position. The rules in those languages are usually expressed as a single resolution algorithm, which the proposal follows in outline. The treatment of glob imports and shadowing is one area where the designs differ, and the proposal chooses the rules that are easiest to explain to a programmer.

# Unresolved questions

The exact diagnostic for an ambiguous glob import needs to be designed. The message should name both sources of the ambiguity and should suggest the explicit import that resolves it.

The treatment of re-exports through glob imports needs more study. A public glob import that re-exports names from a private module raises questions about visibility that the RFC does not fully answer.

# Future possibilities

Once import resolution is complete, macros can refer to items through the module system. This would allow a macro to be defined in terms of paths rather than through a fixed set of names, which would make macro libraries easier to write and to compose.

The fixed-point algorithm could later be extended to handle more complicated cases, such as imports that depend on the results of macro expansion. The present design leaves room for this, but it does not attempt it.
