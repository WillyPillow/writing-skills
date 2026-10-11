# RFC 1574: More API Documentation Conventions

- Feature Name: N/A
- Start Date: 2016-03-10
- Status: Proposed

## Summary

This RFC extends the conventions established in RFC 505 for documenting the public API of Rust crates. RFC 505 described how to write the summary line, how to structure a module's documentation, and how to document the common sections that appear in function and type documentation. This RFC keeps those conventions and adds guidance on several topics that the earlier document left open: how to document errors, how to document panics and safety requirements, how to structure examples, and how to cross-reference related items. The full text of the earlier conventions, with these modifications applied, is reproduced in an appendix so that a reader need not consult two documents.

## Motivation

Documentation is the main way that a library's users learn what it does. A well-documented crate can be used without reading its source, and a poorly documented one forces users to guess. RFC 505 set a baseline, but experience since then has revealed gaps. Authors have documented errors inconsistently, so that some functions list the conditions under which they return an error and others do not mention errors at all. Panics are often described in prose buried inside the function body, where readers cannot find them. Examples are written in a variety of styles, and some are never compiled, so they drift out of date.

The standard library is the reference point for most Rust authors, and its documentation shapes the expectations of its readers. Making the conventions explicit helps both standard library contributors and the authors of crates that follow the standard library's style. Consistency across the ecosystem makes it easier for users to move between libraries.

## Guide-level explanation

Every public function, method, and type should be documented with a short summary line followed by a longer description when one is needed. The summary is a single sentence in the third person, ending with a period. It describes what the item does, not how it does it. A function that converts a value might say "Converts the value into a string." A type might say "A buffered reader over a byte stream."

When a function can fail, the documentation should include an `# Errors` section. The section lists the conditions under which the function returns an error, and it names the error variants where a function returns an enumeration of errors. A reader who sees this section should be able to decide, without reading the implementation, whether the function's error handling meets their needs.

When a function can panic, the documentation should include a `# Panics` section. The section states the conditions under which the function panics, using the same level of detail as the errors section. Panics that occur only because of a programming error by the caller should still be documented, since the reader needs to know that the call is invalid.

When a function is marked `unsafe`, the documentation should include a `# Safety` section. This section states the conditions that the caller must uphold for the call to be sound. The conditions should be stated in terms that a reader can check, and they should not rely on phrases such as "the caller must be careful."

Examples should be included wherever they help the reader use the item. An example is a short code block that compiles and runs as part of the test suite. Authors should prefer examples that show a complete, realistic use over examples that only demonstrate a single method call in isolation.

## Reference-level explanation

The summary line should be no longer than one line in the rendered documentation. It should use the form of a complete sentence in the third person, such as "Returns the number of elements" rather than "Return the number of elements" or "This returns the number of elements."

Sections are introduced by level-one headings with the names given above. The sections appear in a fixed order: the description, followed by `# Examples`, `# Errors`, `# Panics`, and `# Safety`, in that order, with any section not applicable omitted. Authors should not invent additional section names for common concepts, since readers expect the standard names.

Code blocks in examples are compiled and run during testing unless they are explicitly marked otherwise. A block that is marked as not to be run should explain the reason in a comment. Examples should use the public interface of the crate, and they should not depend on private items, since the examples are compiled as an external user would compile them.

Cross-references to other items should use the intra-doc link syntax, which names the item in brackets. This allows the documentation tooling to check that the link is valid and to render it as a link to the correct page.

Module documentation should begin with a summary of the module's purpose, followed by a description of the types and functions that a reader is most likely to need. It should avoid restating the documentation of individual items.

## Drawbacks

The additional conventions add to the work of documenting a crate. Authors who are already stretched may find the requirement to write errors, panics, and safety sections burdensome, and some will write weaker documentation as a result. The RFC recognizes this, but it argues that the cost is small compared to the time users spend reconstructing the same information.

Compiling every example slows the test suite. Authors who have large examples may be tempted to mark them as not to be run, which defeats the purpose of the rule. The guidance asks authors to use the attribute only for examples that genuinely cannot run, such as those requiring network access.

## Rationale and alternatives

One alternative is to rely on the tooling to enforce these conventions with lints. Lints can check for the presence of sections, but they cannot judge whether the content is accurate or useful. The RFC treats the conventions as guidance for authors and leaves enforcement to review.

A second alternative is to define a richer markup language for documentation. This would give authors more control, but it would increase the learning burden and would complicate the tooling. The Markdown-based format already in use is sufficient for these purposes.

A third alternative is to leave the conventions as they are and rely on the examples in the standard library. This does not solve the problem, because most crate authors do not read the standard library's documentation source, and the examples do not cover the cases of errors, panics, and safety.

The chosen approach keeps the set of conventions small, uses names that readers already recognize, and ties the documentation to the test suite so that examples stay accurate.

## Appendix: Combined conventions

The combined conventions consist of the baseline from RFC 505, as modified by this RFC. The summary line, module documentation, and cross-reference rules from the earlier document remain in force. The additions in this RFC are the sections for errors, panics, and safety, the rule that examples compile by default, and the requirement that cross-references use intra-doc links. Where the two documents differ, this RFC governs.

## Unresolved questions

- Whether the `# Errors` section should be required for functions that return a boolean or an option, or only for functions that return a result, remains open.
- The guidance on examples for asynchronous code needs to be expanded once the relevant language features are stable.
- The conventions for documenting macros are not yet settled and may require a separate RFC.

## Future possibilities

The conventions can be checked more thoroughly by tooling that reads the documentation and reports missing sections. Such tooling would make the conventions easier to follow, and it would give crate authors a clear signal when their documentation falls short.
