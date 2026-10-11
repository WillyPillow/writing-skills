## id: pep-0296
Document type: Python Enhancement Proposal (PEP)
Title: PEP 296: Adding a bytes Object Type
Abstract: This PEP proposes the creation of a new standard type and builtin constructor called 'bytes'. The bytes object is an efficiently stored array of bytes with some additional characteristics that set it apart from several implementations that are similar.

## id: pep-3141
Document type: Python Enhancement Proposal (PEP)
Title: PEP 3141: A Type Hierarchy for Numbers
Abstract: This proposal defines a hierarchy of Abstract Base Classes (ABCs) (PEP 3119) to represent number-like classes. It proposes a hierarchy of ``Number :> Complex :> Real :> Rational :> Integral`` where ``A :> B`` means "A is a supertype of B". The hierarchy is inspired by Scheme's numeric tower [#schemetower]_.

## id: 2115-argument-lifetimes
Document type: Rust language/tooling RFC
Title: Rust RFC 2115: argument_lifetimes
Abstract: Eliminate the need for separately binding lifetime parameters in `fn` definitions and `impl` headers, so that instead of writing: you can write: Lint against leaving off lifetime parameters in structs (like `Ref` or `Iter`), instead nudging people to use explicit lifetimes in this case (but leveraging the other improvements to make it ergonomic to do so). The changes, in summary, are: - A signature is taken to bind any lifetimes it mentions that are not already bound. - A style lint checks that lifetimes bound in `impl` headers are multiple characters long, to reduce potential confusion with lifetimes bound within functions. (There are some additional, less important lints proposed as well.) - You can write `'_` to explicitly elide a lifetime, and it is deprecated to entirely leave off lifetime ...

## id: pep-0223
Document type: Python Enhancement Proposal (PEP)
Title: PEP 223: Change the Meaning of ``\x`` Escapes
Abstract: Change ``\x`` escapes, in both 8-bit and Unicode strings, to consume exactly the two hex digits following. The proposal views this as correcting an original design flaw, leading to clearer expression in all flavors of string, a cleaner Unicode story, better compatibility with Perl regular expressions, and with minimal risk to existing code.

## id: 1445-restrict-constants-in-patterns
Document type: Rust language/tooling RFC
Title: Rust RFC 1445: structural_match
Abstract: The current compiler implements a more expansive semantics for pattern matching than was originally intended. This RFC introduces several mechanisms to reign in these semantics without actually breaking (much, if any) extant code: - Introduce a feature-gated attribute `#[structural_match]` which can be applied to a struct or enum `T` to indicate that constants of type `T` can be used within patterns. - Have `#[derive(Eq)]` automatically apply this attribute to the struct or enum that it decorates. **Automatically inserted attributes do not require use of feature-gate.** - When expanding constants of struct or enum type into equivalent patterns, require that the struct or enum type is decorated with `#[structural_match]`. Constants of builtin types are always expanded. The practical effect of these changes will be to prevent the use of constants in ...

## id: pep-0520
Document type: Python Enhancement Proposal (PEP)
Title: PEP 520: Preserving Class Attribute Definition Order
Abstract: The class definition syntax is ordered by its very nature. Class attributes defined there are thus ordered. Aside from helping with readability, that ordering is sometimes significant. If it were automatically available outside the class definition then the attribute order could be used without the need for extra boilerplate (such as metaclasses or manually enumerating the attribute order). Given that this information already exists, access to the definition order of attributes is a reasonable expectation. However, currently Python does not preserve the attribute order from the class definition. This PEP changes that by preserving the order in which attributes are introduced in the class definition body. That order will now be preserved in the ``__definition_order__`` attribute of the class. This allows introspection of the original definition order, e.g. by class ...

## id: 2008-non-exhaustive
Document type: Rust language/tooling RFC
Title: Rust RFC 2008: non_exhaustive
Abstract: This RFC introduces the `#[non_exhaustive]` attribute for enums and structs, which indicates that more variants/fields may be added to an enum/struct in the future. Adding this hint to enums will force downstream crates to add a wildcard arm to `match` statements, ensuring that adding new variants is not a breaking change. Adding this hint to structs or enum variants will prevent downstream crates from constructing or exhaustively matching, to ensure that adding new fields is not a breaking change. This is a post-1.0 version of [RFC 757], with some additions.

## id: pep-0590
Document type: Python Enhancement Proposal (PEP)
Title: PEP 590: Vectorcall: a fast calling protocol for CPython
Abstract: This PEP introduces a new C API to optimize calls of objects. It introduces a new "vectorcall" protocol and calling convention. This is based on the "fastcall" convention, which is already used internally by CPython. The new features can be used by any user-defined extension class. Most of the new API is private in CPython 3.8. The plan is to finalize semantics and make it public in Python 3.9. **NOTE**: This PEP deals only with the Python/C API, it does not affect the Python language or standard library.

## id: 2845-supertrait-item-shadowing
Document type: Rust language/tooling RFC
Title: Rust RFC 2845: supertrait_item_shadowing
Abstract: Change item resolution for generics and trait objects so that a trait bound does not bring its supertraits' items into scope if the subtrait defines an item with this name itself.

## id: pep-0651
Document type: Python Enhancement Proposal (PEP)
Title: PEP 651: Robust Stack Overflow Handling
Abstract: This PEP proposes that Python should treat machine stack overflow differently from runaway recursion. This would allow programs to set the maximum recursion depth to fit their needs and provide additional safety guarantees. If this PEP is accepted, then the following program will run safely to completion:: sys.setrecursionlimit(1_000_000) def f(n): if n: f(n-1) f(500_000) and the following program will raise a ``StackOverflow``, without causing a VM crash:: sys.setrecursionlimit(1_000_000) class X: def __add__(self, other): return self + other X() + 1

