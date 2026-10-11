## id: pep-0532
Document type: Python Enhancement Proposal (PEP)
Title: PEP 532: A circuit breaking protocol and binary operators
Abstract: Inspired by :pep:`335`, :pep:`505`, :pep:`531`, and the related discussions, this PEP proposes the definition of a new circuit breaking protocol (using the method names ``__then__`` and ``__else__``) that provides a common underlying semantic foundation for: * conditional expressions: ``LHS if COND else RHS`` * logical conjunction: ``LHS and RHS`` * logical disjunction: ``LHS or RHS`` * the None-aware operators proposed in :pep:`505` * the rich comparison chaining model proposed in :pep:`535` Taking advantage of the new protocol, it further proposes that the definition of conditional expressions be revised to also permit the use of ``if`` and ``else`` respectively as right-associative and left-associative general purpose short-circuiting operators: * Right-associative short-circuiting: ``LHS if RHS`` * Left-associative short-circuiting: ``LHS else RHS`` In order to make logical inversion (``not EXPR``) consistent with the above ...

## id: pep-0504
Document type: Python Enhancement Proposal (PEP)
Title: PEP 504: Using the System RNG by default
Abstract: Python currently defaults to using the deterministic Mersenne Twister random number generator for the module level APIs in the ``random`` module, requiring users to know that when they're performing "security sensitive" work, they should instead switch to using the cryptographically secure ``os.urandom`` or ``random.SystemRandom`` interfaces or a third party library like ``cryptography``. Unfortunately, this approach has resulted in a situation where developers that aren't aware that they're doing security sensitive work use the default module level APIs, and thus expose their users to unnecessary risks. This isn't an acute problem, but it is a chronic one, and the often long delays between the introduction of security flaws and their exploitation means that it is difficult for developers to naturally learn from experience. In order to provide an eventually pervasive solution ...

## id: pep-0367
Document type: Python Enhancement Proposal (PEP)
Title: PEP 367: New Super
Abstract: This PEP proposes syntactic sugar for use of the ``super`` type to automatically construct instances of the super type binding to the class that a method was defined in, and the instance (or class object for classmethods) that the method is currently acting upon. The premise of the new super usage suggested is as follows:: super.foo(1, 2) to replace the old:: super(Foo, self).foo(1, 2) and the current ``__builtin__.super`` be aliased to ``__builtin__.__super__`` (with ``__builtin__.super`` to be removed in Python 3.0). It is further proposed that assignment to ``super`` become a ``SyntaxError``, similar to the behaviour of ``None``.

## id: 2316-safe-unsafe-trait-methods
Document type: Rust language/tooling RFC
Title: Rust RFC 2316: safe_unsafe_trait_methods
Abstract: This RFC allows safe implementations of `unsafe` trait methods. An `impl` may implement a trait with methods marked as `unsafe` without marking the methods in the `impl` as `unsafe`. This is referred to as *overconstraining* the method in the `impl`. When the trait's `unsafe` method is called on a specific type where the method is known to be safe, that call does not require an `unsafe` block.

## id: pep-0383
Document type: Python Enhancement Proposal (PEP)
Title: PEP 383: Non-decodable Bytes in System Character Interfaces
Abstract: File names, environment variables, and command line arguments are defined as being character data in POSIX; the C APIs however allow passing arbitrary bytes - whether these conform to a certain encoding or not. This PEP proposes a means of dealing with such irregularities by embedding the bytes in character strings in such a way that allows recreation of the original byte string.

## id: pep-0346
Document type: Python Enhancement Proposal (PEP)
Title: PEP 346: User Defined ("``with``") Statements
Abstract: This PEP is a combination of :pep:`310`'s "Reliable Acquisition/Release Pairs" with the "Anonymous Block Statements" of Guido's :pep:`340`. This PEP aims to take the good parts of :pep:`340`, blend them with parts of :pep:`310` and rearrange the lot into an elegant whole. It borrows from various other PEPs in order to paint a complete picture, and is intended to stand on its own.

## id: pep-0234
Document type: Python Enhancement Proposal (PEP)
Title: PEP 234: Iterators
Abstract: This document proposes an iteration interface that objects can provide to control the behaviour of ``for`` loops. Looping is customized by providing a method that produces an iterator object. The iterator provides a *get next value* operation that produces the next item in the sequence each time it is called, raising an exception when no more items are available. In addition, specific iterators over the keys of a dictionary and over the lines of a file are proposed, and a proposal is made to allow spelling ``dict.has_key(key)`` as ``key in dict``. Note: this is an almost complete rewrite of this PEP by the second author, describing the actual implementation checked into the trunk of the Python 2.2 CVS tree. It is still open for discussion. Some of the more esoteric ...

## id: pep-0327
Document type: Python Enhancement Proposal (PEP)
Title: PEP 327: Decimal Data Type
Abstract: The idea is to have a Decimal data type, for every use where decimals are needed but binary floating point is too inexact. The Decimal data type will support the Python standard functions and operations, and must comply with the decimal arithmetic ANSI standard X3.274-1996 [1]_. Decimal will be floating point (as opposed to fixed point) and will have bounded precision (the precision is the upper limit on the number of significant digits in a result). However, precision is user-settable, and a notion of significant trailing zeroes is supported so that fixed-point usage is also possible. This work is based on code and test functions written by Eric Price, Aahz and Tim Peters. Just before Python 2.4a1, the decimal.py `reference implementation`_ was moved into the standard library; along with the ...

## id: pep-0650
Document type: Python Enhancement Proposal (PEP)
Title: PEP 650: Specifying Installer Requirements for Python Projects
Abstract: Python package installers are not completely interoperable with each other. While pip is the most widely used installer and a de facto standard, other installers such as Poetry_ or Pipenv_ are popular as well due to offering unique features which are optimal for certain workflows and not directly in line with how pip operates. While the abundance of installer options is good for end-users with specific needs, the lack of interoperability between them makes it hard to support all potential installers. Specifically, the lack of a standard requirements file for declaring dependencies means that each tool must be explicitly used in order to install dependencies specified with their respective format. Otherwise tools must emit a requirements file which leads to potential information loss for the installer as well as an ...

## id: 1774-roadmap-2017
Document type: Rust language/tooling RFC
Title: Rust RFC 1774: N/A
Abstract: This RFC proposes the *2017 Rust Roadmap*, in accordance with RFC 1728. The goal of the roadmap is to lay out a vision for where the Rust project should be in a year's time. **This year's focus is improving Rust's *productivity*, while retaining its emphasis on fast, reliable code**. At a high level, by the end of 2017: * Rust should have a lower learning curve * Rust should have a pleasant edit-compile-debug cycle * Rust should provide a solid, but basic IDE experience * Rust should provide easy access to high quality crates * Rust should be well-equipped for writing robust, high-scale servers * Rust should have 1.0-level crates for essential tasks * Rust should integrate easily into large build systems * Rust's community should provide mentoring at all ...

