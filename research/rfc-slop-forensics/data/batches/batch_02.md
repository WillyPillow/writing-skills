## id: 2008-non-exhaustive
Document type: Rust language/tooling RFC
Title: Rust RFC 2008: non_exhaustive
Abstract: This RFC introduces the `#[non_exhaustive]` attribute for enums and structs, which indicates that more variants/fields may be added to an enum/struct in the future. Adding this hint to enums will force downstream crates to add a wildcard arm to `match` statements, ensuring that adding new variants is not a breaking change. Adding this hint to structs or enum variants will prevent downstream crates from constructing or exhaustively matching, to ensure that adding new fields is not a breaking change. This is a post-1.0 version of [RFC 757], with some additions.

## id: 2333-prior-art
Document type: Rust language/tooling RFC
Title: Rust RFC 2333: prior_art
Abstract: Adds a *Prior art* section to the RFC template where RFC authors may discuss the experience of other programming languages and their communities with respect to what is being proposed. This section may also discuss theoretical work such as papers.

## id: 2229-capture-disjoint-fields
Document type: Rust language/tooling RFC
Title: Rust RFC 2229: capture_disjoint_fields
Abstract: This RFC proposes that closure capturing should be minimal rather than maximal. Conceptually, existing rules regarding borrowing and moving disjoint fields should be applied to capturing. If implemented, the following code examples would become valid: Note that some discussion of this has already taken place: - rust-lang/rust#19004 - Rust internals forum

## id: pep-0590
Document type: Python Enhancement Proposal (PEP)
Title: PEP 590: Vectorcall: a fast calling protocol for CPython
Abstract: This PEP introduces a new C API to optimize calls of objects. It introduces a new "vectorcall" protocol and calling convention. This is based on the "fastcall" convention, which is already used internally by CPython. The new features can be used by any user-defined extension class. Most of the new API is private in CPython 3.8. The plan is to finalize semantics and make it public in Python 3.9. **NOTE**: This PEP deals only with the Python/C API, it does not affect the Python language or standard library.

## id: pep-0359
Document type: Python Enhancement Proposal (PEP)
Title: PEP 359: The "make" Statement
Abstract: This PEP proposes a generalization of the class-declaration syntax, the ``make`` statement. The proposed syntax and semantics parallel the syntax for class definition, and so:: make <callable> <name> <tuple>: <block> is translated into the assignment:: <name> = <callable>("<name>", <tuple>, <namespace>) where ``<namespace>`` is the dict created by executing ``<block>``. This is mostly syntactic sugar for:: class <name> <tuple>: __metaclass__ = <callable> <block> and is intended to help more clearly express the intent of the statement when something other than a class is being created. Of course, other syntax for such a statement is possible, but it is hoped that by keeping a strong parallel to the class statement, an understanding of how classes and metaclasses work will translate into an understanding of how the make-statement works as well. The PEP ...

## id: 2325-stable-simd
Document type: Rust language/tooling RFC
Title: Rust RFC 2325: vendor_intrinsics
Abstract: The purpose of this RFC is to provide a framework for SIMD to be used on stable Rust. It proposes stabilizing x86-specific vendor intrinsics, but includes the scaffolding for other platforms as well as a future portable SIMD design (to be fleshed out in another RFC).

## id: 2845-supertrait-item-shadowing
Document type: Rust language/tooling RFC
Title: Rust RFC 2845: supertrait_item_shadowing
Abstract: Change item resolution for generics and trait objects so that a trait bound does not bring its supertraits' items into scope if the subtrait defines an item with this name itself.

## id: pep-0639
Document type: Python Enhancement Proposal (PEP)
Title: PEP 639: Improving License Clarity with Better Package Metadata
Abstract: This PEP defines a specification how licenses are documented in the Python projects. To achieve that, it: - Adopts the `SPDX license expression syntax <639-spdx_>`__ as a means of expressing the license for a Python project. - Defines how to include license files within the projects, source and built distributions. - Specifies the necessary changes to :term:`Core Metadata` and the corresponding :term:`Pyproject Metadata key`\s - Describes the necessary changes to the `source distribution (sdist) <sdistspec_>`__, `built distribution (wheel) <wheelspec_>`__ and `installed project <installedspec_>`__ standards. This will make license declaration simpler and less ambiguous for package authors to create, end users to understand, and tools to programmatically process. The changes will update the `Core Metadata specification <coremetadataspec_>`__ to version 2.4. .. _639-goals:

## id: 1733-trait-alias
Document type: Rust language/tooling RFC
Title: Rust RFC 1733: Trait alias
Abstract: Traits can be aliased with the `trait TraitAlias = …;` construct. Currently, the right hand side is a bound – a single trait, a combination with `+` traits and lifetimes. Type parameters and lifetimes can be added to the *trait alias* if needed.

## id: pep-0651
Document type: Python Enhancement Proposal (PEP)
Title: PEP 651: Robust Stack Overflow Handling
Abstract: This PEP proposes that Python should treat machine stack overflow differently from runaway recursion. This would allow programs to set the maximum recursion depth to fit their needs and provide additional safety guarantees. If this PEP is accepted, then the following program will run safely to completion:: sys.setrecursionlimit(1_000_000) def f(n): if n: f(n-1) f(500_000) and the following program will raise a ``StackOverflow``, without causing a VM crash:: sys.setrecursionlimit(1_000_000) class X: def __add__(self, other): return self + other X() + 1

