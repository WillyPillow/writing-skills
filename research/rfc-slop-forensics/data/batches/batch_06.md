## id: 1728-north-star
Document type: Rust language/tooling RFC
Title: Rust RFC 1728: north_star
Abstract: A refinement of the Rust planning and reporting process, to establish a shared vision of the project among contributors, to make clear the roadmap toward that vision, and to celebrate our achievements. Rust's roadmap will be established in year-long cycles, where we identify up front - together, as a project - the most critical problems facing the language and its ecosystem, along with the story we want to be able to tell the world about Rust. Work toward solving those problems, our short-term goals, will be decided by the individual teams, as they see fit, and regularly re-triaged. For the purposes of reporting the project roadmap, goals will be assigned to release cycle milestones. At the end of the year we will deliver a public facing retrospective, describing the goals ...

## id: 1105-api-evolution
Document type: Rust language/tooling RFC
Title: Rust RFC 1105: not applicable
Abstract: This RFC proposes a comprehensive set of guidelines for which changes to *stable* APIs are considered breaking from a semver perspective, and which are not. These guidelines are intended for both the standard library and for the crates.io ecosystem. This does *not* mean that the standard library should be completely free to make non-semver-breaking changes; there are sometimes still risks of ecosystem pain that need to be taken into account. Rather, this RFC makes explicit an initial set of changes that absolutely *cannot* be made without a semver bump. Along the way, it also discusses some interactions with potential language features that can help mitigate pain for non-breaking changes. The RFC covers only API issues; other issues related to language features, lints, type inference, command line arguments, Cargo, and so ...

## id: 3173-float-next-up-down
Document type: Rust language/tooling RFC
Title: Rust RFC 3173: float_next_up_down
Abstract: This RFC adds two argumentless methods to `f32`/`f64`, `next_up` and `next_down`. These functions are specified in the IEEE 754 standard, and provide the capability to enumerate floating point values in order.

## id: pep-0437
Document type: Python Enhancement Proposal (PEP)
Title: PEP 437: A DSL for specifying signatures, annotations and argument converters
Abstract: The Python C-API currently has no mechanism for specifying and auto-generating function signatures, annotations or custom argument converters. There are several possible approaches to the problem. Cython uses *cdef* definitions in *.pyx* files to generate the required information. However, CPython's C-API functions often require additional initialization and cleanup snippets that would be hard to specify in a *cdef*. :pep:`436` proposes a domain specific language (DSL) enclosed in C comments that largely resembles a per-parameter configuration file. A preprocessor reads the comment and emits an argument parsing function, docstrings and a header for the function that utilizes the results of the parsing step. The latter function is subsequently referred to as the *implementation function*.

## id: 1183-swap-out-jemalloc
Document type: Rust language/tooling RFC
Title: Rust RFC 1183: allocator
Abstract: Add support to the compiler to override the default allocator, allowing a different allocator to be used by default in Rust programs. Additionally, also switch the default allocator for dynamic libraries and static libraries to using the system malloc instead of jemalloc. *Note:* this RFC has been superseded by [RFC 1974][].

## id: 2834-cargo-report-future-incompat
Document type: Rust language/tooling RFC
Title: Rust RFC 2834: N/A
Abstract: Cargo should alert developers to upstream dependencies that trigger future-incompatibility warnings. Cargo should list such dependencies even when these warnings have been suppressed (e.g. via cap-lints or `#[allow(..)]` attributes.) Cargo could additionally provide feedback for tactics a maintainer of the downstream crate could use to address the problem (the details of such tactics is not specified nor mandated by this RFC).

## id: pep-0445
Document type: Python Enhancement Proposal (PEP)
Title: PEP 445: Add new APIs to customize Python memory allocators
Abstract: This PEP proposes new Application Programming Interfaces (API) to customize Python memory allocators. The only implementation required to conform to this PEP is CPython, but other implementations may choose to be compatible, or to re-use a similar scheme.

## id: pep-0362
Document type: Python Enhancement Proposal (PEP)
Title: PEP 362: Function Signature Object
Abstract: Python has always supported powerful introspection capabilities, including introspecting functions and methods (for the rest of this PEP, "function" refers to both functions and methods). By examining a function object you can fully reconstruct the function's signature. Unfortunately this information is stored in an inconvenient manner, and is spread across a half-dozen deeply nested attributes. This PEP proposes a new representation for function signatures. The new representation contains all necessary information about a function and its parameters, and makes introspection easy and straightforward. However, this object does not replace the existing function metadata, which is used by Python itself to execute those functions. The new metadata object is intended solely to make function introspection easier for Python programmers.

## id: pep-0352
Document type: Python Enhancement Proposal (PEP)
Title: PEP 352: Required Superclass for Exceptions
Abstract: In Python 2.4 and before, any (classic) class can be raised as an exception. The plan for 2.5 was to allow new-style classes, but this makes the problem worse -- it would mean *any* class (or instance) can be raised! This is a problem as it prevents any guarantees from being made about the interface of exceptions. This PEP proposes introducing a new superclass that all raised objects must inherit from. Imposing the restriction will allow a standard interface for exceptions to exist that can be relied upon. It also leads to a known hierarchy for all exceptions to adhere to. One might counter that requiring a specific base class for a particular interface is unPythonic. However, in the specific case of exceptions there's a good reason (which has generally ...

## id: 1789-as-cell
Document type: Rust language/tooling RFC
Title: Rust RFC 1789: as_cell
Abstract: - Change `Cell<T>` to allow `T: ?Sized`. - Guarantee that `T` and `Cell<T>` have the same memory layout. - Enable the following conversions through the std lib: - `&mut T -> &Cell<T> where T: ?Sized` - `&Cell<[T]> -> &[Cell<T>]` > Note: https://github.com/rust-lang/rfcs/pull/1651 has been accepted recently, > so no `T: Copy` bound is needed anymore.

