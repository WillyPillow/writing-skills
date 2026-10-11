- Feature Name: `intra_rustdoc_links`
- Start Date: 2017-03-07
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary
[summary]: #summary

Add a notation for creating relative links in documentation comments, based on Rust item paths, and extend rustdoc to turn these into working links automatically.

# Motivation
[motivation]: #motivation

Documentation is far more useful when it links to the things it mentions. A doc comment for `Vec::push` that says "see also `Vec::extend`" should let the reader click through to `Vec::extend`.

Today, the only way to do this is to write the link target by hand, as a relative URL into the generated HTML:

```rust
/// Appends an element to the back of the collection.
///
/// See also [`extend`](struct.Vec.html#method.extend).
pub fn push(&mut self, value: T) { ... }
```

This has a number of problems:

- **Authors have to know rustdoc's output layout.** The file naming scheme (`struct.Vec.html`, `trait.Iterator.html`, `fn.from_fn.html`), the anchor format for methods and fields, and the directory structure for modules are implementation details that writers should not need to learn.
- **Links break silently.** If an item is renamed, moved to another module, or changed from a struct to an enum, the link target changes and the documentation keeps pointing at a page that no longer exists. Nothing warns the author.
- **Links are relative to the page, not to the code.** A doc comment on an item in `foo::bar` must link with `../baz/struct.Qux.html` to reach `foo::baz::Qux`. The same comment re-exported or inlined elsewhere may end up with a broken relative path.
- **Cross-crate links are especially painful.** Linking to an item in a dependency means hard-coding a URL to docs.rs or another host, with a specific version.

As a result, many crates link sparingly or not at all, and those that do accumulate broken links over time. Rust already has a precise way to refer to items, namely paths, and rustdoc already resolves paths when it generates documentation. Letting authors use paths as link targets makes the obvious thing easy.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

In a doc comment, you can link to any item that is in scope by writing its path as the link target, using ordinary Markdown link syntax:

```rust
/// Appends an element to the back of the collection.
///
/// See also [`Vec::extend`] and [the iterator trait](Iterator).
pub fn push(&mut self, value: T) { ... }
```

Rustdoc resolves `Vec::extend` and `Iterator` as Rust paths, from the scope of the item being documented, and produces links to the right pages.

Three forms of Markdown link are supported:

1. **Inline:** `[text](path)`, as in `[the iterator trait](Iterator)`.
2. **Reference:** `[text][label]` together with a definition line `[label]: path`.
3. **Shortcut:** `[path]` or `` [`path`] ``, where the link text is itself the path. Backticks around the text are allowed and are rendered as code.

Paths are resolved the same way as they would be in code at that location. If `HashMap` is imported with `use std::collections::HashMap;` in the module, `[HashMap]` works. Paths can begin with `crate::`, `self::`, `super::`, or the name of a dependency crate, and can refer to modules, types, traits, functions, macros, constants, statics, and associated items such as methods, fields, and enum variants.

If a name refers to more than one kind of item, for example a function and a module both named `foo`, you can say which one you mean with a prefix:

- `struct@Foo`, `enum@Foo`, `trait@Foo`, `union@Foo`, `type@Foo`
- `fn@foo`, `mod@foo`, `const@FOO`, `static@FOO`
- `macro@foo` or `foo!`
- `foo()` as a shorthand for a function

The prefix is removed from the displayed link text when the shortcut form is used.

If rustdoc cannot resolve a path, it emits a warning pointing at the doc comment, and renders the text without a link. This means broken intra-doc links are caught when documentation is built, not when a reader clicks on them.

Links that look like URLs (anything containing `://`, starting with `/` or `#`, or ending in `.html`) are left alone, so existing hand-written links keep working.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## Detecting candidate links

Rustdoc already parses doc comments as Markdown using pulldown-cmark. During rendering, for each link encountered, rustdoc examines the link destination. A destination is treated as an intra-doc link candidate if:

- it does not contain `://`,
- it does not start with `/`, `#`, `.` or `?`,
- it consists only of path-like characters: identifiers, `::`, an optional disambiguator prefix ending in `@`, an optional trailing `!` or `()`, and optional surrounding backticks.

For shortcut links with no explicit destination, pulldown-cmark normally treats `[foo]` as plain text if no reference definition exists. Rustdoc hooks the broken-link callback so that such text is offered as a candidate too.

## Resolution scope

Each doc comment is resolved in the scope of the item it documents. For items with an inner scope (modules, and also functions for `//!` comments inside them), inner doc comments are resolved in the inner scope. For re-exported items whose documentation is inlined, links are resolved in the scope of the original definition, so that the meaning of a link does not depend on where it is re-exported.

Resolution reuses the compiler's name resolution infrastructure. Rustdoc first tries to resolve the full path in the type namespace, value namespace and macro namespace. If the path does not resolve directly and has at least two segments, the last segment is tried as an associated item, field or variant of the type named by the prefix. Inherent impls and trait impls for the type are both searched.

If the path resolves in more than one namespace and no disambiguator was given, rustdoc emits a warning describing the ambiguity and suggesting the disambiguators, and links to one of them in a fixed preference order (type namespace first).

## Generating the URL

Once an item is resolved, rustdoc computes its URL using the same function it uses for all other cross-references, such as types in function signatures. For local items this is a relative path from the current page. For items in other crates, rustdoc uses the external crate's documentation location, determined in the usual way: from `--extern-html-root-url`, from `#![doc(html_root_url = "...")]` in the dependency, or from a local build of its documentation.

Associated items produce a URL with an appropriate anchor, such as `#method.extend` or `#variant.Some`.

## Lints

A new lint, `broken_intra_doc_links`, is warn-by-default and fires when a candidate link cannot be resolved or is ambiguous. Crate authors can raise it to `deny` in CI to guarantee their documentation has no broken links.

# Drawbacks
[drawbacks]: #drawbacks

- Rustdoc becomes more tightly coupled to the compiler's name resolution, which increases maintenance burden.
- The syntax overlaps with legitimate Markdown that was never meant as a link. For example, `[0]` or `[T]` in prose might be taken as a link candidate. Rustdoc only links candidates that actually resolve, and only warns for shortcut links in a conservative set of cases, but some false warnings are possible.
- Documentation rendered by tools other than rustdoc, such as a crate's README rendered on a hosting site, will show these links as broken, since those tools do not understand Rust paths.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**A new syntax instead of Markdown links.** Something like `{@link Vec::extend}` in the style of Javadoc was considered. Reusing Markdown links keeps doc comments readable as plain Markdown and requires no new syntax for authors to learn.

**Resolving paths from the crate root only.** This would be simpler to implement, but forces authors to write full paths for everything and does not match how paths are written in code.

**Doing nothing.** Authors can continue writing manual links, but the problems described in the motivation will persist, and documentation quality across the ecosystem will continue to suffer.

# Prior art
[prior-art]: #prior-art

Javadoc's `{@link}` tag, Python's Sphinx cross-referencing roles such as `:func:`, and Haddock's single-quoted identifiers all give authors a way to link to code by name rather than by URL. All have proven popular, and all show that resolving names at documentation build time catches broken links early.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

- Should links to primitive types such as `[u32]` or `[slice]` be supported, given that primitives have no path?
- How should links behave in documentation for items generated by macros, whose scope may be hygienic?
- Should the warning for unresolved shortcut links be on by default, or only for inline and reference links?
