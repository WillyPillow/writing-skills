## id: pep-0521
Document type: Python Enhancement Proposal (PEP)
Title: PEP 521: Managing global context via 'with' blocks in generators and coroutines
Abstract: While we generally try to avoid global state when possible, there nonetheless exist a number of situations where it is agreed to be the best approach. In Python, a standard pattern for handling such cases is to store the global state in global or thread-local storage, and then use ``with`` blocks to limit modifications of this global state to a single dynamic scope. Examples where this pattern is used include the standard library's ``warnings.catch_warnings`` and ``decimal.localcontext``, NumPy's ``numpy.errstate`` (which exposes the error-handling settings provided by the IEEE 754 floating point standard), and the handling of logging context or HTTP request context in many server application frameworks. However, there is currently no ergonomic way to manage such local changes to global state when writing a generator or coroutine. For example, this ...

## id: pep-0610
Document type: Python Enhancement Proposal (PEP)
Title: PEP 610: Recording the Direct URL Origin of installed distributions
Abstract: Following :pep:`440`, a distribution can be identified by a name and either a version, or a direct URL reference (see :pep:`PEP440 Direct References <440#direct-references>`). After installation, the name and version are captured in the project metadata, but currently there is no way to obtain details of the URL used when the distribution was identified by a direct URL reference. This proposal defines additional metadata, to be added to the installed distribution by the installation front end, which records the Direct URL Origin for use by consumers which introspect the database of installed packages (see :pep:`376`).

## id: pep-0532
Document type: Python Enhancement Proposal (PEP)
Title: PEP 532: A circuit breaking protocol and binary operators
Abstract: Inspired by :pep:`335`, :pep:`505`, :pep:`531`, and the related discussions, this PEP proposes the definition of a new circuit breaking protocol (using the method names ``__then__`` and ``__else__``) that provides a common underlying semantic foundation for: * conditional expressions: ``LHS if COND else RHS`` * logical conjunction: ``LHS and RHS`` * logical disjunction: ``LHS or RHS`` * the None-aware operators proposed in :pep:`505` * the rich comparison chaining model proposed in :pep:`535` Taking advantage of the new protocol, it further proposes that the definition of conditional expressions be revised to also permit the use of ``if`` and ``else`` respectively as right-associative and left-associative general purpose short-circuiting operators: * Right-associative short-circuiting: ``LHS if RHS`` * Left-associative short-circuiting: ``LHS else RHS`` In order to make logical inversion (``not EXPR``) consistent with the above ...

## id: pep-0309
Document type: Python Enhancement Proposal (PEP)
Title: PEP 309: Partial Function Application
Abstract: This proposal is for a function or callable class that allows a new callable to be constructed from a callable and a partial argument list (including positional and keyword arguments). I propose a standard library module called "functional", to hold useful higher-order functions, including the implementation of partial(). An implementation has been submitted to SourceForge [2]_.

## id: pep-0450
Document type: Python Enhancement Proposal (PEP)
Title: PEP 450: Adding A Statistics Module To The Standard Library
Abstract: This PEP proposes the addition of a module for common statistics functions such as mean, median, variance and standard deviation to the Python standard library. See also http://bugs.python.org/issue18606

## id: pep-0504
Document type: Python Enhancement Proposal (PEP)
Title: PEP 504: Using the System RNG by default
Abstract: Python currently defaults to using the deterministic Mersenne Twister random number generator for the module level APIs in the ``random`` module, requiring users to know that when they're performing "security sensitive" work, they should instead switch to using the cryptographically secure ``os.urandom`` or ``random.SystemRandom`` interfaces or a third party library like ``cryptography``. Unfortunately, this approach has resulted in a situation where developers that aren't aware that they're doing security sensitive work use the default module level APIs, and thus expose their users to unnecessary risks. This isn't an acute problem, but it is a chronic one, and the often long delays between the introduction of security flaws and their exploitation means that it is difficult for developers to naturally learn from experience. In order to provide an eventually pervasive solution ...

## id: pep-0511
Document type: Python Enhancement Proposal (PEP)
Title: PEP 511: API for code transformers
Abstract: Propose an API to register bytecode and AST transformers. Add also ``-o OPTIM_TAG`` command line option to change ``.pyc`` filenames, ``-o noopt`` disables the peephole optimizer. Raise an ``ImportError`` exception on import if the ``.pyc`` file is missing and the code transformers required to transform the code are missing. code transformers are not needed code transformed ahead of time (loaded from ``.pyc`` files).

## id: pep-0499
Document type: Python Enhancement Proposal (PEP)
Title: PEP 499: ``python -m foo`` should also bind ``'foo'`` in ``sys.modules``
Abstract: When a module is used as a main program on the Python command line, such as by: python -m module.name ... it is easy to accidentally end up with two independent instances of the module if that module is again imported within the program. This PEP proposes a way to fix this problem. When a module is invoked via Python's -m option the module is bound to ``sys.modules['__main__']`` and its ``.__name__`` attribute is set to ``'__main__'``. This enables the standard "main program" boilerplate code at the bottom of many modules, such as:: if __name__ == '__main__': sys.exit(main(sys.argv)) However, when the above command line invocation is used it is a natural inference to presume that the module is actually imported under its official name ``module.name``, and therefore that if the program ...

## id: pep-0367
Document type: Python Enhancement Proposal (PEP)
Title: PEP 367: New Super
Abstract: This PEP proposes syntactic sugar for use of the ``super`` type to automatically construct instances of the super type binding to the class that a method was defined in, and the instance (or class object for classmethods) that the method is currently acting upon. The premise of the new super usage suggested is as follows:: super.foo(1, 2) to replace the old:: super(Foo, self).foo(1, 2) and the current ``__builtin__.super`` be aliased to ``__builtin__.__super__`` (with ``__builtin__.super`` to be removed in Python 3.0). It is further proposed that assignment to ``super`` become a ``SyntaxError``, similar to the behaviour of ``None``.

## id: 1946-intra-rustdoc-links
Document type: Rust language/tooling RFC
Title: Rust RFC 1946: intra_rustdoc_links
Abstract: Add a notation how to create relative links in documentation comments (based on Rust item paths) and extend Rustdoc to automatically turn this into working links.

