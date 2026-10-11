# RFC 1946: intra-doc links for rustdoc

- **Start Date:** 2018
- **Status:** Proposed

## Summary

This RFC adds a notation for linking from one documentation comment to another item in the same crate or in a dependency, using paths that follow Rust's own name resolution rules. Rustdoc, the documentation generator, is extended to read these links and to replace them with working hyperlinks in the generated HTML. A link such as `[HashMap]` or `[Vec::push](Vec::push)` resolves against the scope in which the comment appears, so authors no longer need to know where the target page lives on disk.

The change is limited to the syntax of documentation comments and to the way rustdoc resolves names. It does not change the language, the compiler, or the meaning of any item.

## Motivation

Documentation in Rust is written in Markdown inside doc comments. Authors who want to refer to another item currently have two options. They can write a link to a fixed URL, which is fragile because the generated page location depends on the crate version and on how the documentation is hosted. Or they can write plain text and leave the reader to search. Both options are weak, and the first breaks silently when items are moved.

The standard library documentation contains many references between types and functions. Each one is a candidate for a link that would be checked and kept up to date. Third-party crates have the same need, and many of them maintain long lists of hand-written URLs that go stale over time.

A link that names an item by its path is more durable. If the item moves within the crate, the path in the link still refers to it as long as the name resolves. If the path does not resolve, rustdoc can report a warning, which gives authors an early signal that a reference is broken.

## Guide-level explanation

An author who wants to link to another item writes its path inside square brackets. The path is interpreted in the scope of the item whose documentation contains the link. A type in the same module can be named directly. An item from another module can be named with its path relative to the current module or with an absolute path from the crate root.

```rust
/// Returns the number of entries in the [`Config`] file.
///
/// For a faster check, see [`Config::is_empty`].
pub fn count_entries(path: &Path) -> usize { ... }
```

When the author writes only the path in brackets, rustdoc uses the path as the text of the link. When a different text is wanted, the author writes the text in brackets and the target in parentheses, in the usual Markdown style, so that `[the cache](Cache)` displays as "the cache" and links to `Cache`.

Items with the same name in different namespaces need a disambiguator. A function and a module can share a name, so the author writes `fn@name` or `mod@name` to choose the one wanted. Macros are referred to with a trailing exclamation mark, as in `vec!`.

Links to items in dependencies work when the dependency is in the crate's dependency graph. The author writes the path as it would appear in code that uses the dependency.

## Reference-level explanation

Rustdoc parses each documentation comment and finds bracketed text that is followed by neither a URL nor a reference definition. Such text is treated as a candidate link. Rustdoc then attempts to resolve the candidate using the same rules that the compiler applies to paths in source code, starting from the module that contains the documented item.

Resolution proceeds in the following order. The first step checks names in the local scope, including items defined in the same module and names imported by `use` declarations. The second step checks the prelude. The third step checks the crate root and the names of direct dependencies.

If a candidate resolves to exactly one item in the expected namespace, rustdoc generates a link to that item's page. If it resolves to several items, rustdoc reports an ambiguity and asks the author to add a disambiguator. If it does not resolve, rustdoc emits a warning and leaves the text unlinked.

Items that are private and not documented are not linked. Rustdoc does not generate pages for them, so a link to such an item would be broken, and the warning makes this visible. Items that are re-exported are linked at the location of their public re-export, which is the page a reader would visit.

## Drawbacks

The main drawback is that link resolution now depends on the state of the code being documented. A documentation comment that resolved correctly yesterday may produce a warning after a refactoring that changes an import. Authors may find this surprising, and some will see the warnings as noise.

Resolution also adds work to documentation generation. Each candidate must be checked, and the checks depend on the scope of the item, so the cost grows with the size of the crate. Early estimates suggest the cost is modest, but it has not been measured on the largest crates.

The notation borrows the syntax of Markdown reference links. A bracketed phrase that was never meant as a link, such as a list of options, will now be checked and may produce a warning. Authors can escape it with a backslash, but the escape must be learned.

## Rationale and alternatives

The chosen design keeps the existing Markdown syntax and adds only the rule for resolution. A new syntax would be more explicit, but it would require every existing documentation tool to change, and it would make comments harder to read in source form.

An alternative is to require full URLs. This is the status quo, and it is the reason for the proposal. It remains the only option for links to external sites, which the RFC does not change.

Another alternative is to resolve paths only against the item's module and never against the crate root. This is simpler, but it would make many natural references fail, and the proposal judged that the simplicity did not justify the lost convenience.

A third alternative is to resolve links at compile time rather than in rustdoc. This would give stronger guarantees, but it would require changing the compiler's handling of comments, which is outside the scope of this RFC.

## Prior art

Several documentation systems in other languages resolve references between items by name. Some of them report unresolved references as errors rather than warnings. The design here draws on those systems but follows the scoping rules of Rust, so that a path means the same thing in a comment as it does in code.

## Unresolved questions

The first open question is whether unresolved links should be errors under a flag, so that projects can make documentation a hard requirement. The RFC proposes warnings by default and leaves the flag for a later decision.

The second question is how to handle links to items that are hidden with the `doc(hidden)` attribute. The proposal suggests that these links be treated as unresolved, but some authors want to refer to hidden items from public documentation.

The third question concerns the interaction with the existing rules for disambiguation. The proposal reuses the prefixes for namespaces, but the precise set of prefixes has not been finalised.

## Future possibilities

If this RFC is accepted, rustdoc can later check links against the state of the whole workspace, and can provide editor support so that authors see unresolved links while they type. The same resolution rules could also be used by other tools that read documentation, such as search indexes that group items by name.

## Summary

This RFC extends rustdoc so that bracketed paths in documentation comments are resolved against Rust's own name resolution rules and turned into working links. It keeps the Markdown syntax, adds a small set of disambiguators, and reports unresolved links as warnings. The change makes documentation more durable and reduces the number of hand-written URLs that go stale.
