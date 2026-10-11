## id: 1869-eprintln
Document type: Rust language/tooling RFC
Title: Rust RFC 1869: eprintln
Abstract: This RFC proposes the addition of two macros to the global prelude, `eprint!` and `eprintln!`. These are exactly the same as `print!` and `println!`, respectively, except that they write to standard error instead of standard output. An [implementation][] already exists.

## id: 2500-needle
Document type: Rust language/tooling RFC
Title: Rust RFC 2500: needle
Abstract: Generalize the needle (née pattern) API to support `&str`, `&mut str`, `&[T]`, `&mut [T]`, `Vec<T>` and `&OsStr`. <!-- TOC depthTo:2 --> - Summary - Motivation - Stabilize the Pattern API - Implement OMG-WTF-8 - Guide-level explanation - Reference-level explanation - API - Standard library changes - Performance - Drawbacks - Rationale and alternatives - Principles - Design rationales - Miscellaneous decisions - Alternatives - Prior art - Previous attempts - Haskell - Unresolved questions <!-- /TOC -->

## id: pep-0246
Document type: Python Enhancement Proposal (PEP)
Title: PEP 246: Object Adaptation
Abstract: This proposal puts forth an extensible cooperative mechanism for the adaptation of an incoming object to a context which expects an object supporting a specific protocol (say a specific type, class, or interface). This proposal provides a built-in "adapt" function that, for any object X and any protocol Y, can be used to ask the Python environment for a version of X compliant with Y. Behind the scenes, the mechanism asks object X: "Are you now, or do you know how to wrap yourself to provide, a supporter of protocol Y?". And, if this request fails, the function then asks protocol Y: "Does object X support you, or do you know how to wrap it to obtain such a supporter?" This duality is important, because protocols can be developed after ...

## id: pep-0227
Document type: Python Enhancement Proposal (PEP)
Title: PEP 227: Statically Nested Scopes
Abstract: This PEP describes the addition of statically nested scoping (lexical scoping) for Python 2.2, and as a source level option for python 2.1. In addition, Python 2.1 will issue warnings about constructs whose meaning may change when this feature is enabled. The old language definition (2.0 and before) defines exactly three namespaces that are used to resolve names -- the local, global, and built-in namespaces. The addition of nested scopes allows resolution of unbound local names in enclosing functions' namespaces. The most visible consequence of this change is that lambdas (and other nested functions) can reference variables defined in the surrounding namespace. Currently, lambdas must often use default arguments to explicitly creating bindings in the lambda's namespace.

## id: 2582-raw-reference-mir-operator
Document type: Rust language/tooling RFC
Title: Rust RFC 2582: raw_ref_op
Abstract: Introduce new variants of the `&` operator: `&raw mut <place>` to create a `*mut <T>`, and `&raw const <place>` to create a `*const <T>`. This creates a raw pointer directly, as opposed to the already existing `&mut <place> as *mut _`/`&<place> as *const _`, which create a temporary reference and then cast that to a raw pointer. As a consequence, the existing expressions `<term> as *mut <T>` and `<term> as *const <T>` where `<term>` has reference type are equivalent to `&raw mut *<term>` and `&raw const *<term>`, respectively. Moreover, emit a lint for existing code that could use the new operator.

## id: pep-0633
Document type: Python Enhancement Proposal (PEP)
Title: PEP 633: Dependency specification in pyproject.toml using an exploded TOML table
Abstract: This PEP specifies how to write a project's dependencies in a ``pyproject.toml`` file for packaging-related tools to consume using the fields defined in :pep:`621`, as an alternative to the :pep:`508`-based approach defined in :pep:`631`.

## id: 3037-roadmap-2021
Document type: Rust language/tooling RFC
Title: Rust RFC 3037: n/a
Abstract: The focus of this year is on project health, specifically as it relates to Rust's governance structure. * Establishing charters for teams in the Rust project * Provide for unified process and vocabulary across the project * Creating a single place for tracking a list of ongoing projects The core team will drive these efforts in coordination with all Rust teams and working groups. As the Rust teams have grown over the years, there is increasingly less cross-chatter that naturally happens due to shared membership of teams, and this RFC aims to improve our written documentation to provide for a smoother onboarding process for new team members, as well as improving the ability of current team members to evaluate who to consult on new ideas or projects.

## id: 2996-async-iterator
Document type: Rust language/tooling RFC
Title: Rust RFC 2996: async_iterator
Abstract: Introduce the `AsyncIterator` trait into the standard library, using the design from `futures`. Redirect the `Stream` trait definition in the `futures-core` crate (which is "pub-used" by the `futures` crate) to the `AsyncIterator` trait in the standard library.

## id: 2585-unsafe-block-in-unsafe-fn
Document type: Rust language/tooling RFC
Title: Rust RFC 2585: unsafe_block_in_unsafe_fn
Abstract: No longer treat the body of an `unsafe fn` as being an `unsafe` block. To avoid a breaking change, this is a warning now and may become an error in a future edition.

## id: pep-3127
Document type: Python Enhancement Proposal (PEP)
Title: PEP 3127: Integer Literal Support and Syntax
Abstract: This PEP proposes changes to the Python core to rationalize the treatment of string literal representations of integers in different radices (bases). These changes are targeted at Python 3.0, but the backward-compatible parts of the changes should be added to Python 2.6, so that all valid 3.0 integer literals will also be valid in 2.6. The proposal is that: a) octal literals must now be specified with a leading "0o" or "0O" instead of "0"; b) binary literals are now supported via a leading "0b" or "0B"; and c) provision will be made for binary numbers in string formatting.

