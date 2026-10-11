## id: pep-0234
Document type: Python Enhancement Proposal (PEP)
Title: PEP 234: Iterators
Abstract: This document proposes an iteration interface that objects can provide to control the behaviour of ``for`` loops. Looping is customized by providing a method that produces an iterator object. The iterator provides a *get next value* operation that produces the next item in the sequence each time it is called, raising an exception when no more items are available. In addition, specific iterators over the keys of a dictionary and over the lines of a file are proposed, and a proposal is made to allow spelling ``dict.has_key(key)`` as ``key in dict``. Note: this is an almost complete rewrite of this PEP by the second author, describing the actual implementation checked into the trunk of the Python 2.2 CVS tree. It is still open for discussion. Some of the more esoteric ...

## id: 2528-type-changing-struct-update-syntax
Document type: Rust language/tooling RFC
Title: Rust RFC 2528: type_changing_struct_update_syntax
Abstract: Extend struct update syntax (a.k.a. functional record update (FRU)) to support instances of the *same* struct that have different types due to generic type or lifetime parameters. Fields of different types must be explicitly listed in the struct constructor, but fields of the same name and same type can be moved with struct update syntax. This will make the following possible. In this example, `base` and `updated` are both instances of `Foo` but have different types because the generic parameter `T` is different. Struct update syntax is supported for `field2` because it has the same type `i32` in both `base` and `updated`:

## id: 0320-nonzeroing-dynamic-drop
Document type: Rust language/tooling RFC
Title: Rust RFC 320: (none for the bulk of RFC); unsafe_no_drop_flag
Abstract: Remove drop flags from values implementing `Drop`, and remove automatic memory zeroing associated with dropping values. Keep dynamic drop semantics, by having each function maintain a (potentially empty) set of auto-injected boolean flags for the drop obligations for the function that need to be tracked dynamically (which we will call "dynamic drop obligations").

## id: pep-0327
Document type: Python Enhancement Proposal (PEP)
Title: PEP 327: Decimal Data Type
Abstract: The idea is to have a Decimal data type, for every use where decimals are needed but binary floating point is too inexact. The Decimal data type will support the Python standard functions and operations, and must comply with the decimal arithmetic ANSI standard X3.274-1996 [1]_. Decimal will be floating point (as opposed to fixed point) and will have bounded precision (the precision is the upper limit on the number of significant digits in a result). However, precision is user-settable, and a notion of significant trailing zeroes is supported so that fixed-point usage is also possible. This work is based on code and test functions written by Eric Price, Aahz and Tim Peters. Just before Python 2.4a1, the decimal.py `reference implementation`_ was moved into the standard library; along with the ...

## id: 1560-name-resolution
Document type: Rust language/tooling RFC
Title: Rust RFC 1560: item_like_imports
Abstract: Some internal and language-level changes to name resolution. Internally, name resolution will be split into two parts - import resolution and name lookup. Import resolution is moved forward in time to happen in the same phase as parsing and macro expansion. Name lookup remains where name resolution currently takes place (that may change in the future, but is outside the scope of this RFC). However, name lookup can be done earlier if required (importantly it can be done during macro expansion to allow using the module system for macros, also outside the scope of this RFC). Import resolution will use a new algorithm. The observable effects of this RFC (i.e., language changes) are some increased flexibility in the name resolution rules, especially around globs and shadowing. There is an implementation ...

## id: 3139-cargo-alternative-registry-auth
Document type: Rust language/tooling RFC
Title: Rust RFC 3139: cargo_alternative_registry_auth
Abstract: Enables Cargo to include the authorization token for all API requests, crate downloads and index updates (when using HTTP) by adding a configuration option to `config.json` in the registry index.

## id: pep-0650
Document type: Python Enhancement Proposal (PEP)
Title: PEP 650: Specifying Installer Requirements for Python Projects
Abstract: Python package installers are not completely interoperable with each other. While pip is the most widely used installer and a de facto standard, other installers such as Poetry_ or Pipenv_ are popular as well due to offering unique features which are optimal for certain workflows and not directly in line with how pip operates. While the abundance of installer options is good for end-users with specific needs, the lack of interoperability between them makes it hard to support all potential installers. Specifically, the lack of a standard requirements file for declaring dependencies means that each tool must be explicitly used in order to install dependencies specified with their respective format. Otherwise tools must emit a requirements file which leads to potential information loss for the installer as well as an ...

## id: pep-0485
Document type: Python Enhancement Proposal (PEP)
Title: PEP 485: A Function for testing approximate equality
Abstract: This PEP proposes the addition of an isclose() function to the standard library math module that determines whether one value is approximately equal or "close" to another value.

## id: pep-0516
Document type: Python Enhancement Proposal (PEP)
Title: PEP 516: Build system abstraction for pip/conda etc
Abstract: This PEP specifies a programmatic interface for pip [#pip]_ and other distribution or installation tools to use when working with Python source trees (both the developer tree - e.g. the git tree - and source distributions). The programmatic interface allows decoupling of pip from its current hard dependency on setuptools [#setuptools]_ able for two key reasons: 1. It enables new build systems that may be much easier to use without requiring them to even appear to be setuptools. 2. It facilitates setuptools itself changing its user interface without breaking pip, giving looser coupling. The interface needed to permit pip to install build systems also enables pip to install build time requirements for packages which is an important step in getting pip to full feature parity with the installation components of ...

## id: 1774-roadmap-2017
Document type: Rust language/tooling RFC
Title: Rust RFC 1774: N/A
Abstract: This RFC proposes the *2017 Rust Roadmap*, in accordance with RFC 1728. The goal of the roadmap is to lay out a vision for where the Rust project should be in a year's time. **This year's focus is improving Rust's *productivity*, while retaining its emphasis on fast, reliable code**. At a high level, by the end of 2017: * Rust should have a lower learning curve * Rust should have a pleasant edit-compile-debug cycle * Rust should provide a solid, but basic IDE experience * Rust should provide easy access to high quality crates * Rust should be well-equipped for writing robust, high-scale servers * Rust should have 1.0-level crates for essential tasks * Rust should integrate easily into large build systems * Rust's community should provide mentoring at all ...

