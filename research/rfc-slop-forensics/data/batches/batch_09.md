## id: pep-0323
Document type: Python Enhancement Proposal (PEP)
Title: PEP 323: Copyable Iterators
Abstract: This PEP suggests that some iterator types should support shallow copies of their instances by exposing a ``__copy__`` method which meets some specific requirements, and indicates how code using an iterator might exploit such a ``__copy__`` method when present.

## id: pep-0525
Document type: Python Enhancement Proposal (PEP)
Title: PEP 525: Asynchronous Generators
Abstract: :pep:`492` introduced support for native coroutines and ``async``/``await`` syntax to Python 3.5. It is proposed here to extend Python's asynchronous capabilities by adding support for *asynchronous generators*.

## id: 1040-duration-reform
Document type: Rust language/tooling RFC
Title: Rust RFC 1040: duration
Abstract: This RFC suggests stabilizing a reduced-scope `Duration` type that is appropriate for interoperating with various system calls that require timeouts. It does not stabilize a large number of conversion methods in `Duration` that have subtle caveats, with the intent of revisiting those conversions more holistically in the future.

## id: 1985-tiered-browser-support
Document type: Rust language/tooling RFC
Title: Rust RFC 1985: tiered_browser_support
Abstract: Official web content produced by the Rust teams for consumption by Rust users should work in the majority of browsers that Rust users are visiting these sites in. The Rust compiler only supports [a finite number of targets][forge], with varying degrees of support, due to the limits on time, expertise, and testing resources. Similarly, we don't have enough time, expertise and testing resources to be sure that our web content works in every version of every browser. We should have a list of browsers and versions in various tiers of support.

## id: 1682-field-init-shorthand
Document type: Rust language/tooling RFC
Title: Rust RFC 1682: field-init-shorthand
Abstract: When initializing a data structure (struct, enum, union) with named fields, allow writing `fieldname` as a shorthand for `fieldname: fieldname`. This allows a compact syntax for initialization, with less duplication. Example usage: struct SomeStruct { field1: ComplexType, field2: AnotherType } impl SomeStruct { fn new() -> Self { let field1 = { // Various initialization code }; let field2 = { // More initialization code }; SomeStruct { field1, field2 } } }

## id: 2930-read-buf
Document type: Rust language/tooling RFC
Title: Rust RFC 2930: read_buf
Abstract: The current design of the `Read` trait is nonoptimal as it requires that the buffer passed to its various methods be pre-initialized even though the contents will be immediately overwritten. This RFC proposes an interface to allow implementors and consumers of `Read` types to robustly and soundly work with uninitialized buffers.

## id: 1969-cargo-prepublish
Document type: Rust language/tooling RFC
Title: Rust RFC 1969: prepublish
Abstract: This RFC proposes the concept of *patching sources* for Cargo. Sources can be have their existing versions of crates replaced with different copies, and sources can also have "prepublished" crates by adding versions of a crate which do not currently exist in the source. Dependency resolution will work *as if* these additional or replacement crates actually existed in the original source. One primary feature enabled by this is the ability to "prepublish" a crate to crates.io. Prepublication makes it possible to perform integration testing within a large crate graph before publishing anything to crates.io, and without requiring dependencies to be switched from the crates.io index to git branches. It can, to a degree, simulate an "atomic" change across a large number of crates and repositories, which can then actually be ...

## id: pep-0508
Document type: Python Enhancement Proposal (PEP)
Title: PEP 508: Dependency specification for Python Software Packages
Abstract: This PEP specifies the language used to describe dependencies for packages. It draws a border at the edge of describing a single dependency - the different sorts of dependencies and when they should be installed is a higher level problem. The intent is to provide a building block for higher layer specifications. The job of a dependency is to enable tools like pip [#pip]_ to find the right package to install. Sometimes this is very loose - just specifying a name, and sometimes very specific - referring to a specific file to install. Sometimes dependencies are only relevant in one platform, or only some versions are acceptable, so the language permits describing all these cases. The language defined is a compact line based format which is already in widespread use ...

## id: pep-0400
Document type: Python Enhancement Proposal (PEP)
Title: PEP 400: Deprecate codecs.StreamReader and codecs.StreamWriter
Abstract: io.TextIOWrapper and codecs.StreamReaderWriter offer the same API [#f1]_. TextIOWrapper has more features and is faster than StreamReaderWriter. Duplicate code means that bugs should be fixed twice and that we may have subtle differences between the two implementations. The codecs module was introduced in Python 2.0 (see the :pep:`100`). The io module was introduced in Python 2.6 and 3.0 (see the :pep:`3116`), and reimplemented in C in Python 2.7 and 3.1.

## id: 1513-less-unwinding
Document type: Rust language/tooling RFC
Title: Rust RFC 1513: panic_runtime
Abstract: Stabilize implementing panics as aborts. * Stabilize the `-Z no-landing-pads` flag under the name `-C panic=strategy` * Implement a number of unstable features akin to custom allocators to swap out implementations of panic just before a final product is generated. * Add a `[profile.dev]` option to Cargo to configure how panics are implemented.

