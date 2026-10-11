- Feature Name: N/A
- Start Date: 2016-03-31
- RFC PR: rust-lang/rfcs#1574
- Rust Issue: N/A

# Summary

[RFC 505] set out conventions for writing documentation comments in Rust. This RFC extends those conventions with guidance on Markdown style, standard section headings, examples, links, and module-level documentation. To make the result easy to read in one place, the full text of RFC 505 as amended by this RFC is given in the "Detailed design" section.

[RFC 505]: https://github.com/rust-lang/rfcs/blob/master/text/0505-api-comment-conventions.md

# Motivation

RFC 505 covered the basics: use `///` doc comments, write a one-line summary, use Markdown. In the time since, the standard library and the wider ecosystem have grown much larger, and a number of conventions have emerged informally. Some are followed consistently, others vary from crate to crate and even from module to module within `std`.

This inconsistency has costs:

- Readers have to relearn where to find information like panics, errors and safety requirements for each crate.
- Contributors to `std` get conflicting review feedback about headings, link style and example format.
- Tools that consume documentation, such as rustdoc's search and IDE hover text, cannot rely on structure.

Writing these conventions down gives reviewers something to point at, gives newcomers a template, and lets tooling assume more about the shape of documentation.

# Detailed design

The following is the combined set of conventions. Items new in this RFC are marked *(new)*.

## Use line comments

Use `///` for item documentation and `//!` for module and crate documentation. Avoid the block forms `/** */` and `/*! */`. Line comments are easier to edit, do not have nesting pitfalls, and are what the rest of the ecosystem uses.

## Summary sentence

The first line of every doc comment is a single sentence that summarises the item. It should be short enough to fit in the listing pages rustdoc generates, which show only this line. End it with a period.

Write the summary in the third person indicative: "Returns the length of the string," not "Return the length" or "This function returns the length."

## English

Use American English spelling in the standard library, matching the language's own keywords and identifiers. *(new)* Crates outside `std` may choose either, but should be consistent.

## Markdown style *(new)*

- Use ATX headings (`#`), not underline headings.
- Use `#` as the top-level heading inside a doc comment. Rustdoc places documentation under its own page heading, so a top-level `#` in the comment renders as a section heading.
- Use `*` for bullet lists and `_` or `*` consistently for emphasis within a crate.
- Wrap prose at 80 or 100 columns, matching the crate's code style. Do not wrap inside links or inline code if that hurts readability.
- Use fenced code blocks with three backticks. Do not use indented code blocks.

## Standard sections *(new)*

After the summary and any longer description, use these headings, in this order, where they apply:

- `# Examples` — one or more examples of using the item. See below.
- `# Panics` — the conditions under which the function panics. Required for any function that can panic on caller input, other than through a bug.
- `# Errors` — for functions returning `Result`, the conditions that produce each kind of error.
- `# Safety` — for `unsafe` functions and traits, the invariants the caller must uphold. Required.
- `# Aborts` — for functions that may abort the process.
- `# Undefined Behavior` — when it differs from what `# Safety` already states.

Always use the plural `# Examples`, even if there is only one example. This makes it easy to add more later without changing the heading, and makes search across documentation simpler.

## Examples *(new)*

Every public item should have at least one example, unless it is trivial (for instance, a field accessor whose summary already says everything). Examples should:

- Be complete enough to compile and run as doc tests. Use `#` to hide setup lines that would distract from the point, such as imports and `fn main`.
- Use `assert!` and `assert_eq!` to show results rather than `println!`, so the doc test actually checks the behaviour.
- Use `?` in examples where errors can occur, rather than `unwrap()`, by hiding a `fn main() -> Result<(), Box<dyn Error>>` wrapper. This shows readers the idiomatic way to handle errors.
- Show common use first and edge cases afterwards.

Mark code that should not be compiled with ` ```text`, and code that is expected to fail compilation with ` ```compile_fail`. Use ` ```no_run` for examples that compile but should not be executed, such as those that touch the network. Avoid ` ```ignore` except as a last resort, and explain why when you use it.

## Links *(new)*

- Link to other items whenever you mention them by name in prose, at least on the first mention in each doc comment.
- Use reference-style links, with the definitions collected at the end of the doc comment, so that the prose stays readable in source:

  ```rust
  /// Converts this value into a [`String`].
  ///
  /// [`String`]: ../string/struct.String.html
  ```

- Put item names in backticks inside the link text.
- Prefer relative links within a crate so that documentation works offline and in local builds.

## Module-level documentation *(new)*

Each public module should begin with a `//!` comment that:

1. Gives a one-line summary of the module's purpose.
2. Explains the main types and how they relate to each other.
3. Includes at least one example of typical use.

Crate root documentation follows the same pattern, and should additionally give an overview of features and pointers to the most important modules.

## Using `Self` and type names

In method documentation, refer to the type by name rather than "this type" or "self", so that the text makes sense when shown out of context, for example in search results. *(new)*

## Documenting trait implementations *(new)*

Trait implementations inherit documentation from the trait. Only write additional documentation on an implementation when its behaviour has something specific worth noting, such as complexity or allocation.

## Avoid "this function" phrasing

Start sentences with the verb. "Returns the first element" reads better than "This function returns the first element" and is shorter in listings.

# Drawbacks

- Some existing documentation in `std` and elsewhere will not conform. Bringing it in line is work, and the conventions cannot be enforced instantly.
- Prescribing structure can produce boilerplate: a heading with one sentence under it. We think the consistency is worth the small cost.
- Reference-style links are more verbose in source and can drift from the text they belong to.

# Alternatives

- Leave conventions informal, relying on reviewers. This is the status quo and has led to the inconsistency described above.
- Enforce conventions with a lint in rustdoc or Clippy rather than an RFC. Linting is complementary; it needs agreed rules to check against, which this RFC provides.
- Adopt a structured format like Javadoc tags instead of Markdown headings. This would be a much larger change and would not fit the existing body of documentation.

# Unresolved questions

- Should rustdoc gain native support for intra-doc links by item path, making the relative-URL convention unnecessary?
- Should missing `# Panics` or `# Safety` sections be linted?
