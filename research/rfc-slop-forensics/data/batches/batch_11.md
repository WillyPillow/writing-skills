## id: pep-0439
Document type: Python Enhancement Proposal (PEP)
Title: PEP 439: Inclusion of implicit pip bootstrap in Python installation
Abstract: This PEP proposes the inclusion of a pip bootstrap executable in the Python installation to simplify the use of 3rd-party modules by Python users. This PEP does not propose to include the pip implementation in the Python standard library. Nor does it propose to implement any package management or installation mechanisms beyond those provided by PEP 427 ("The Wheel Binary Package Format 1.0") and TODO distlib PEP.

## id: pep-3134
Document type: Python Enhancement Proposal (PEP)
Title: PEP 3134: Exception Chaining and Embedded Tracebacks
Abstract: This PEP proposes three standard attributes on exception instances: the ``__context__`` attribute for implicitly chained exceptions, the ``__cause__`` attribute for explicitly chained exceptions, and the ``__traceback__`` attribute for the traceback. A new ``raise ... from`` statement sets the ``__cause__`` attribute.

## id: 2052-epochs
Document type: Rust language/tooling RFC
Title: Rust RFC 2052: N/A
Abstract: Rust's ecosystem, tooling, documentation, and compiler are constantly improving. To make it easier to follow development, and to provide a clear, coherent "rallying point" for this work, this RFC proposes that we declare a *edition* every two or three years. Editions are designated by the year in which they occur, and represent a release in which several elements come together: - A significant, coherent set of new features and APIs have been stabilized since the previous edition. - Error messages and other important aspects of the user experience around these features are fully polished. - Tooling (IDEs, rustfmt, Clippy, etc) has been updated to work properly with these new features. - There is a guide to the new features, explaining why they're important and how they should influence the way ...

## id: pep-0425
Document type: Python Enhancement Proposal (PEP)
Title: PEP 425: Compatibility Tags for Built Distributions
Abstract: This PEP specifies a tagging system to indicate with which versions of Python a built or binary distribution is compatible. A set of three tags indicate which Python implementation and language version, ABI, and platform a built distribution requires. The tags are terse because they will be included in filenames.

## id: 1857-stabilize-drop-order
Document type: Rust language/tooling RFC
Title: Rust RFC 1857: stable_drop_order
Abstract: I propose we specify and stabilize drop order in Rust, instead of treating it as an implementation detail. The stable drop order should be based on the current implementation. This results in avoiding breakage and still allows alternative, opt-in, drop orders to be introduced in the future.

## id: 1398-kinds-of-allocators
Document type: Rust language/tooling RFC
Title: Rust RFC 1398: allocator_api
Abstract: Add a standard allocator interface and support for user-defined allocators, with the following goals: 1. Allow libraries (in libstd and elsewhere) to be generic with respect to the particular allocator, to support distinct, stateful, per-container allocators. 2. Require clients to supply metadata (such as block size and alignment) at the allocation and deallocation sites, to ensure hot-paths are as efficient as possible. 3. Provide high-level abstraction over the layout of an object in memory. Regarding GC: We plan to allow future allocators to integrate themselves with a standardized reflective GC interface, but leave specification of such integration for a later RFC. (The design describes a way to add such a feature in the future while ensuring that clients do not accidentally opt-in and risk unsound behavior.)

## id: pep-0570
Document type: Python Enhancement Proposal (PEP)
Title: PEP 570: Python Positional-Only Parameters
Abstract: This PEP proposes to introduce a new syntax, ``/``, for specifying positional-only parameters in Python function definitions. Positional-only parameters have no externally-usable name. When a function accepting positional-only parameters is called, positional arguments are mapped to these parameters based solely on their order. When designing APIs (application programming interfaces), library authors try to ensure correct and intended usage of an API. Without the ability to specify which parameters are positional-only, library authors must be careful when choosing appropriate parameter names. This care must be taken even for required parameters or when the parameters have no external semantic meaning for callers of the API. In this PEP, we discuss: * Python's history and current semantics for positional-only parameters * the problems encountered by not having them * how these problems are ...

## id: 2904-compiler-major-change-process
Document type: Rust language/tooling RFC
Title: Rust RFC 2904: N/A
Abstract: Introduce the **major change process** for the compiler team. This process has the following goals: * to advertise major changes and give the team a chance to weigh in; * to help scale the amount of work being done to reviewing bandwidth by choosing a reviewer in advance; * to avoid a lot of process overhead. The intent here is that if you have a plan to make some "major change" to the compiler, you will start with this process. It may either simply be approved, but if the change proves more controversial or complex, we may escalate towards design meetings, longer write-ups, or full RFCs before reaching a final decision. This process does not apply to adding new language features, but it can be used for minor features such ...

## id: pep-0414
Document type: Python Enhancement Proposal (PEP)
Title: PEP 414: Explicit Unicode Literal for Python 3.3
Abstract: This document proposes the reintegration of an explicit unicode literal from Python 2.x to the Python 3.x language specification, in order to reduce the volume of changes needed when porting Unicode-aware Python 2 applications to Python 3.

## id: pep-0597
Document type: Python Enhancement Proposal (PEP)
Title: PEP 597: Add optional EncodingWarning
Abstract: Add a new warning category ``EncodingWarning``. It is emitted when the ``encoding`` argument to ``open()`` is omitted and the default locale-specific encoding is used. The warning is disabled by default. A new ``-X warn_default_encoding`` command-line option and a new ``PYTHONWARNDEFAULTENCODING`` environment variable can be used to enable it. A ``"locale"`` argument value for ``encoding`` is added too. It explicitly specifies that the locale encoding should be used, silencing the warning.

