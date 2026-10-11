## id: 2397-do-not-recommend
Document type: Rust language/tooling RFC
Title: Rust RFC 2397: do_not_recommend
Abstract: A new attribute can be placed on trait implementations: `#[do_not_recommend]`. This attribute will cause the compiler to never recommend this impl transitively as a way to implement another trait. For example, this would be placed on `impl<T: Iterator> IntoIterator for T`. The result of this is that when `T: IntoIterator` fails, the error message will only mention `IntoIterator`. It will not say "perhaps `Iterator` should be implemented?".

## id: 1937-ques-in-main
Document type: Rust language/tooling RFC
Title: Rust RFC 1937: ques_in_main
Abstract: Allow the `?` operator to be used in `main`, and in `#[test]` functions and doctests. To make this possible, the return type of these functions are generalized from `()` to a new trait, provisionally called `Termination`. libstd implements this trait for a set of types partially TBD (see list below); applications can provide impls themselves if they want. There is no magic added to function signatures in rustc. If you want to use `?` in either `main` or a `#[test]` function you have to write `-> Result<(), ErrorT>` (or whatever) yourself. Initially, it will also be necessary to write a hidden function head for any doctest that wants to use `?`, but eventually (see the deployment plan below) the default doctest template will be adjusted to make this unnecessary most ...

## id: 3016-const-ub
Document type: Rust language/tooling RFC
Title: Rust RFC 3016: const_ub
Abstract: Define UB during const evaluation to lead to an unspecified result or hard error for the affected CTFE query, but not otherwise infect the compilation process.

## id: 2089-implied-bounds
Document type: Rust language/tooling RFC
Title: Rust RFC 2089: implied_bounds
Abstract: Eliminate the need for “redundant” bounds on functions and impls where those bounds can be inferred from the input types and other trait bounds. For example, in this simple program, the impl would no longer require a bound, because it can be inferred from the `Foo<T>` type: Hence, simply writing `impl<T> Foo<T> { ... }` would suffice. We currently support implied bounds for lifetime bounds, super traits and projections. We propose to extend this to all where clauses on traits and types, as was already discussed [here][niko].

## id: pep-0442
Document type: Python Enhancement Proposal (PEP)
Title: PEP 442: Safe object finalization
Abstract: This PEP proposes to deal with the current limitations of object finalization. The goal is to be able to define and run finalizers for any object, regardless of their position in the object graph. This PEP doesn't call for any change in Python code. Objects with existing finalizers will benefit automatically.

## id: pep-0611
Document type: Python Enhancement Proposal (PEP)
Title: PEP 611: The one million limit
Abstract: This PR proposes a soft limit of one million (1 000 000), and a larger hard limit for various aspects of Python code and its implementation. The Python language does not specify limits for many of its features. Not having any limit to these values seems to enhance programmer freedom, at least superficially, but in practice the CPython VM and other Python virtual machines have implicit limits or are forced to assume that the limits are astronomical, which is expensive. This PR lists a number of features which are to have a limit of one million. For CPython the hard limit will be eight million (8 000 000).

## id: pep-0403
Document type: Python Enhancement Proposal (PEP)
Title: PEP 403: General purpose decorator clause (aka "@in" clause)
Abstract: This PEP proposes the addition of a new ``@in`` decorator clause that makes it possible to override the name binding step of a function or class definition. The new clause accepts a single simple statement that can make a forward reference to decorated function or class definition. This new clause is designed to be used whenever a "one-shot" function or class is needed, and placing the function or class definition before the statement that uses it actually makes the code harder to read. It also avoids any name shadowing concerns by making sure the new name is visible only to the statement in the ``@in`` clause. This PEP is based heavily on many of the ideas in :pep:`3150` (Statement Local Namespaces) so some elements of the rationale will be familiar ...

## id: pep-0207
Document type: Python Enhancement Proposal (PEP)
Title: PEP 207: Rich Comparisons
Abstract: This PEP proposes several new features for comparisons: - Allow separately overloading of <, >, <=, >=, ==, !=, both in classes and in C extensions. - Allow any of those overloaded operators to return something else besides a Boolean result.

## id: 1681-macros-1.1
Document type: Rust language/tooling RFC
Title: Rust RFC 1681: rustc_macros
Abstract: Extract a very small sliver of today's procedural macro system in the compiler, just enough to get basic features like custom derive working, to have an eventually stable API. Ensure that these features will not pose a maintenance burden on the compiler but also don't try to provide enough features for the "perfect macro system" at the same time. Overall, this should be considered an incremental step towards an official "macros 2.0".

## id: pep-0268
Document type: Python Enhancement Proposal (PEP)
Title: PEP 268: Extended HTTP functionality and WebDAV
Abstract: This PEP discusses new modules and extended functionality for Python's HTTP support. Notably, the addition of authenticated requests, proxy support, authenticated proxy usage, and WebDAV_ capabilities.

