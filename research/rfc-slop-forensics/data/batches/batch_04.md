## id: pep-0620
Document type: Python Enhancement Proposal (PEP)
Title: PEP 620: Hide implementation details from the C API
Abstract: Introduce C API incompatible changes to hide implementation details. Once most implementation details will be hidden, evolution of CPython internals would be less limited by C API backward compatibility issues. It will be way easier to add new features. It becomes possible to experiment with more advanced optimizations in CPython than just micro-optimizations, like tagged pointers. Define a process to reduce the number of broken C extensions. The implementation of this PEP is expected to be done carefully over multiple Python versions. It already started in Python 3.7 and most changes are already completed. The `Process to reduce the number of broken C extensions`_ dictates the rhythm.

## id: 2316-safe-unsafe-trait-methods
Document type: Rust language/tooling RFC
Title: Rust RFC 2316: safe_unsafe_trait_methods
Abstract: This RFC allows safe implementations of `unsafe` trait methods. An `impl` may implement a trait with methods marked as `unsafe` without marking the methods in the `impl` as `unsafe`. This is referred to as *overconstraining* the method in the `impl`. When the trait's `unsafe` method is called on a specific type where the method is known to be safe, that call does not require an `unsafe` block.

## id: 2480-liballoc
Document type: Rust language/tooling RFC
Title: Rust RFC 2480: liballoc
Abstract: Stabilize the `alloc` crate. This crate provides the subset of the standard library’s functionality that requires a global allocator (unlike the `core` crate) and an allocation error handler, but not other operating system capabilities (unlike the `std` crate).

## id: pep-3153
Document type: Python Enhancement Proposal (PEP)
Title: PEP 3153: Asynchronous IO support
Abstract: This PEP describes an abstraction of asynchronous IO for the Python standard library. The goal is to reach an abstraction that can be implemented by many different asynchronous IO backends and provides a target for library developers to write code portable between those different backends.

## id: pep-0383
Document type: Python Enhancement Proposal (PEP)
Title: PEP 383: Non-decodable Bytes in System Character Interfaces
Abstract: File names, environment variables, and command line arguments are defined as being character data in POSIX; the C APIs however allow passing arbitrary bytes - whether these conform to a certain encoding or not. This PEP proposes a means of dealing with such irregularities by embedding the bytes in character strings in such a way that allows recreation of the original byte string.

## id: pep-0618
Document type: Python Enhancement Proposal (PEP)
Title: PEP 618: Add Optional Length-Checking To zip
Abstract: This PEP proposes adding an optional ``strict`` boolean keyword parameter to the built-in ``zip``. When enabled, a ``ValueError`` is raised if one of the arguments is exhausted before the others.

## id: pep-0316
Document type: Python Enhancement Proposal (PEP)
Title: PEP 316: Programming by Contract for Python
Abstract: This submission describes programming by contract for Python. Eiffel's Design By Contract(tm) is perhaps the most popular use of programming contracts [#dbc]_. Programming contracts extends the language to include invariant expressions for classes and modules, and pre- and post-condition expressions for functions and methods. These expressions (contracts) are similar to assertions: they must be true or the program is stopped, and run-time checking of the contracts is typically only enabled while debugging. Contracts are higher-level than straight assertions and are typically included in documentation.

## id: pep-0346
Document type: Python Enhancement Proposal (PEP)
Title: PEP 346: User Defined ("``with``") Statements
Abstract: This PEP is a combination of :pep:`310`'s "Reliable Acquisition/Release Pairs" with the "Anonymous Block Statements" of Guido's :pep:`340`. This PEP aims to take the good parts of :pep:`340`, blend them with parts of :pep:`310` and rearrange the lot into an elegant whole. It borrows from various other PEPs in order to paint a complete picture, and is intended to stand on its own.

## id: 1444-union
Document type: Rust language/tooling RFC
Title: Rust RFC 1444: union
Abstract: Provide native support for C-compatible unions, defined via a new "contextual keyword" `union`, without breaking any existing code that uses `union` as an identifier. **Note:** This RFC has been partially superseded by `unions-and-drop`.

## id: pep-0242
Document type: Python Enhancement Proposal (PEP)
Title: PEP 242: Numeric Kinds
Abstract: This proposal gives the user optional control over the precision and range of numeric computations so that a computation can be written once and run anywhere with at least the desired precision and range. It is backward compatible with existing code. The meaning of decimal literals is clarified.

