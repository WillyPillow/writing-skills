## id: 1040-duration-reform
Document type: Rust language/tooling RFC
Title: Rust RFC 1040: duration
Abstract: This RFC suggests stabilizing a reduced-scope `Duration` type that is appropriate for interoperating with various system calls that require timeouts. It does not stabilize a large number of conversion methods in `Duration` that have subtle caveats, with the intent of revisiting those conversions more holistically in the future.

## id: 2930-read-buf
Document type: Rust language/tooling RFC
Title: Rust RFC 2930: read_buf
Abstract: The current design of the `Read` trait is nonoptimal as it requires that the buffer passed to its various methods be pre-initialized even though the contents will be immediately overwritten. This RFC proposes an interface to allow implementors and consumers of `Read` types to robustly and soundly work with uninitialized buffers.

## id: pep-0400
Document type: Python Enhancement Proposal (PEP)
Title: PEP 400: Deprecate codecs.StreamReader and codecs.StreamWriter
Abstract: io.TextIOWrapper and codecs.StreamReaderWriter offer the same API [#f1]_. TextIOWrapper has more features and is faster than StreamReaderWriter. Duplicate code means that bugs should be fixed twice and that we may have subtle differences between the two implementations. The codecs module was introduced in Python 2.0 (see the :pep:`100`). The io module was introduced in Python 2.6 and 3.0 (see the :pep:`3116`), and reimplemented in C in Python 2.7 and 3.1.

## id: 1937-ques-in-main
Document type: Rust language/tooling RFC
Title: Rust RFC 1937: ques_in_main
Abstract: Allow the `?` operator to be used in `main`, and in `#[test]` functions and doctests. To make this possible, the return type of these functions are generalized from `()` to a new trait, provisionally called `Termination`. libstd implements this trait for a set of types partially TBD (see list below); applications can provide impls themselves if they want. There is no magic added to function signatures in rustc. If you want to use `?` in either `main` or a `#[test]` function you have to write `-> Result<(), ErrorT>` (or whatever) yourself. Initially, it will also be necessary to write a hidden function head for any doctest that wants to use `?`, but eventually (see the deployment plan below) the default doctest template will be adjusted to make this unnecessary most ...

## id: pep-0442
Document type: Python Enhancement Proposal (PEP)
Title: PEP 442: Safe object finalization
Abstract: This PEP proposes to deal with the current limitations of object finalization. The goal is to be able to define and run finalizers for any object, regardless of their position in the object graph. This PEP doesn't call for any change in Python code. Objects with existing finalizers will benefit automatically.

## id: pep-0207
Document type: Python Enhancement Proposal (PEP)
Title: PEP 207: Rich Comparisons
Abstract: This PEP proposes several new features for comparisons: - Allow separately overloading of <, >, <=, >=, ==, !=, both in classes and in C extensions. - Allow any of those overloaded operators to return something else besides a Boolean result.

## id: pep-0439
Document type: Python Enhancement Proposal (PEP)
Title: PEP 439: Inclusion of implicit pip bootstrap in Python installation
Abstract: This PEP proposes the inclusion of a pip bootstrap executable in the Python installation to simplify the use of 3rd-party modules by Python users. This PEP does not propose to include the pip implementation in the Python standard library. Nor does it propose to implement any package management or installation mechanisms beyond those provided by PEP 427 ("The Wheel Binary Package Format 1.0") and TODO distlib PEP.

## id: pep-0425
Document type: Python Enhancement Proposal (PEP)
Title: PEP 425: Compatibility Tags for Built Distributions
Abstract: This PEP specifies a tagging system to indicate with which versions of Python a built or binary distribution is compatible. A set of three tags indicate which Python implementation and language version, ABI, and platform a built distribution requires. The tags are terse because they will be included in filenames.

## id: pep-0570
Document type: Python Enhancement Proposal (PEP)
Title: PEP 570: Python Positional-Only Parameters
Abstract: This PEP proposes to introduce a new syntax, ``/``, for specifying positional-only parameters in Python function definitions. Positional-only parameters have no externally-usable name. When a function accepting positional-only parameters is called, positional arguments are mapped to these parameters based solely on their order. When designing APIs (application programming interfaces), library authors try to ensure correct and intended usage of an API. Without the ability to specify which parameters are positional-only, library authors must be careful when choosing appropriate parameter names. This care must be taken even for required parameters or when the parameters have no external semantic meaning for callers of the API. In this PEP, we discuss: * Python's history and current semantics for positional-only parameters * the problems encountered by not having them * how these problems are ...

## id: pep-0597
Document type: Python Enhancement Proposal (PEP)
Title: PEP 597: Add optional EncodingWarning
Abstract: Add a new warning category ``EncodingWarning``. It is emitted when the ``encoding`` argument to ``open()`` is omitted and the default locale-specific encoding is used. The warning is disabled by default. A new ``-X warn_default_encoding`` command-line option and a new ``PYTHONWARNDEFAULTENCODING`` environment variable can be used to enable it. A ``"locale"`` argument value for ``encoding`` is added too. It explicitly specifies that the locale encoding should be used, silencing the warning.

