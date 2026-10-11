## id: 2141-alternative-registries
Document type: Rust language/tooling RFC
Title: Rust RFC 2141: cargo_alternative_registries
Abstract: This RFC proposes the addition of the support for alternative crates.io servers to be used alongside the public crates.io server. This would allow users to publish crates to their own private instance of crates.io, while still able to use the public instance of crates.io.

## id: pep-0447
Document type: Python Enhancement Proposal (PEP)
Title: PEP 447: Add __getdescriptor__ method to metaclass
Abstract: Currently ``object.__getattribute__`` and ``super.__getattribute__`` peek in the ``__dict__`` of classes on the MRO for a class when looking for an attribute. This PEP adds an optional ``__getdescriptor__`` method to a metaclass that replaces this behavior and gives more control over attribute lookup, especially when using a `super`_ object. That is, the MRO walking loop in ``_PyType_Lookup`` and ``super.__getattribute__`` gets changed from:: def lookup(mro_list, name): for cls in mro_list: if name in cls.__dict__: return cls.__dict__ return NotFound to:: def lookup(mro_list, name): for cls in mro_list: try: return cls.__getdescriptor__(name) except AttributeError: pass return NotFound The default implementation of ``__getdescriptor__`` looks in the class dictionary:: class type: def __getdescriptor__(cls, name): try: return cls.__dict__[name] except KeyError: raise AttributeError(name) from None

## id: pep-0296
Document type: Python Enhancement Proposal (PEP)
Title: PEP 296: Adding a bytes Object Type
Abstract: This PEP proposes the creation of a new standard type and builtin constructor called 'bytes'. The bytes object is an efficiently stored array of bytes with some additional characteristics that set it apart from several implementations that are similar.

## id: pep-0405
Document type: Python Enhancement Proposal (PEP)
Title: PEP 405: Python Virtual Environments
Abstract: This PEP proposes to add to Python a mechanism for lightweight "virtual environments" with their own site directories, optionally isolated from system site directories. Each virtual environment has its own Python binary (allowing creation of environments with various Python versions) and can have its own independent set of installed Python packages in its site directories, but shares the standard library with the base installed Python.

## id: 2136-build-systems
Document type: Rust language/tooling RFC
Title: Rust RFC 2136: N/A
Abstract: This **experimental RFC** lays out a high-level plan for improving Cargo's ability to integrate with other build systems and environments. As an experimental RFC, it opens the door to landing [unstable features] in Cargo to try out ideas, but *not* to stabilizing those features, which will require follow-up RFCs. It proposes a variety of features which, in total, permit a wide spectrum of integration cases -- from customizing a single aspect of Cargo to letting an external build system run almost the entire show.

## id: pep-3141
Document type: Python Enhancement Proposal (PEP)
Title: PEP 3141: A Type Hierarchy for Numbers
Abstract: This proposal defines a hierarchy of Abstract Base Classes (ABCs) (PEP 3119) to represent number-like classes. It proposes a hierarchy of ``Number :> Complex :> Real :> Rational :> Integral`` where ``A :> B`` means "A is a supertype of B". The hierarchy is inspired by Scheme's numeric tower [#schemetower]_.

## id: pep-0616
Document type: Python Enhancement Proposal (PEP)
Title: PEP 616: String methods to remove prefixes and suffixes
Abstract: This is a proposal to add two new methods, ``removeprefix()`` and ``removesuffix()``, to the APIs of Python's various string objects. These methods would remove a prefix or suffix (respectively) from a string, if present, and would be added to Unicode ``str`` objects, binary ``bytes`` and ``bytearray`` objects, and ``collections.UserString``.

## id: 2113-dyn-trait-syntax
Document type: Rust language/tooling RFC
Title: Rust RFC 2113: dyn-trait-syntax
Abstract: Introduce a new `dyn Trait` syntax for trait objects using a contextual `dyn` keyword, and deprecate "bare trait" syntax for trait objects. In a future edition, `dyn` will become a proper keyword and a lint against bare trait syntax will become deny-by-default.

## id: 2115-argument-lifetimes
Document type: Rust language/tooling RFC
Title: Rust RFC 2115: argument_lifetimes
Abstract: Eliminate the need for separately binding lifetime parameters in `fn` definitions and `impl` headers, so that instead of writing: you can write: Lint against leaving off lifetime parameters in structs (like `Ref` or `Iter`), instead nudging people to use explicit lifetimes in this case (but leveraging the other improvements to make it ergonomic to do so). The changes, in summary, are: - A signature is taken to bind any lifetimes it mentions that are not already bound. - A style lint checks that lifetimes bound in `impl` headers are multiple characters long, to reduce potential confusion with lifetimes bound within functions. (There are some additional, less important lints proposed as well.) - You can write `'_` to explicitly elide a lifetime, and it is deprecated to entirely leave off lifetime ...

## id: 1598-generic_associated_types
Document type: Rust language/tooling RFC
Title: Rust RFC 1598: generic_associated_types
Abstract: Allow type constructors to be associated with traits. This is an incremental step toward a more general feature commonly called "higher-kinded types," which is often ranked highly as a requested feature by Rust users. This specific feature (associated type constructors) resolves one of the most common use cases for higher-kindedness, is a relatively simple extension to the type system compared to other forms of higher-kinded polymorphism, and is forward compatible with more complex forms of higher-kinded polymorphism that may be introduced in the future.

