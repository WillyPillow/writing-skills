- Feature Name: `intra_rustdoc_links`
- Start Date: 2017-03-01
- RFC PR: rust-lang/rfcs#1946
- Rust Issue: rust-lang/rust#43466

# Summary
[summary]: #summary

Add a notation how to create relative links in documentation comments (based on Rust item paths) and extend Rustdoc to automatically turn this into working links.

# Motivation
[motivation]: #motivation

Good documentation links items together. A reader of the docs for `Vec::push` wants to jump to `Vec::pop`; a reader of `Iterator::map` wants to see `Option`, `Result`, or the trait it returns. Right now, writing such a link in a doc comment is an exercise in guessing and maintenance.

There are two options today, and both are poor.

**Hard-coded relative URLs.** The author writes a path to the generated HTML file:

```rust
/// See [`Vec`](../../std/vec/struct.Vec.html) for details.
```

This depends on how the output directory is laid out, which is an implementation detail of Rustdoc. The link is wrong when the item is documented from a different module than where it is defined, when re-exports move it, or when the crate is built in a different documentation tree. Struct, enum, trait and function pages each have different file name prefixes (`struct.`, `enum.`, `trait.`, `fn.`), and a link that is correct today breaks silently if the item changes kind. Nothing in the build checks it.

**Absolute URLs.** Standard library docs on the web have stable addresses, so authors link to those. This ties the documentation of a crate to a specific hosted version and makes it useless offline. It also cannot be used for items within the crate being documented, since their location depends on where they are published.

The consequence is that most doc comments contain fewer links than they should. Authors who want to link to `Foo::bar` write the name in backticks and leave readers to search for it. This is a common complaint about Rust documentation, and it makes docs for large crates harder to navigate.

The ideal is the thing the author already knows: the Rust path. In source code the author writes `std::collections::HashMap` or `crate::config::Settings` or just `Settings` when in scope. If the documentation tool could resolve that, the author could write the same path in a link.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

You can link to other items in documentation by using their Rust path as the link target. In a doc comment:

```rust
/// Returns a [`Vec`] containing the results of [`parse`].
///
/// See also [`Config::load`] and [`crate::errors::ParseError`].
```

Rustdoc replaces each of these with a link to the item's documentation page. The link text is whatever you write between the brackets. If you want different text, use the inline form:

```rust
/// Uses a [growable array](Vec) to store values.
```

or the reference-style form:

```rust
/// Uses a [growable array][vec].
///
/// [vec]: std::vec::Vec
```

## What paths mean

Paths are resolved as they would be in Rust code at the location of the documentation:

- A bare name such as `Vec` is looked up in scope of the item being documented, including `use` declarations in the surrounding module. The documentation of a function sees the imports of the module it is declared in.
- Paths starting with `crate::`, `self::` or `super::` are relative to the corresponding module.
- Paths of other crates start with the crate name, as in `serde::Serialize`.
- Associated items use the usual syntax: `Vec::push`, `Iterator::next`, `<Vec<u8> as Write>::write`. Generic arguments are ignored in links.

## Disambiguation

Sometimes a name can refer to several things, for example a struct and a function with the same name, or a type and a module. Such names are ambiguous. Rustdoc reports a warning and asks for a hint. A hint is a prefix naming the kind of item:

```rust
/// See [struct@Foo] or [fn@Foo].
```

The recognised prefixes are `struct@`, `enum@`, `trait@`, `union@`, `mod@`, `module@`, `const@`, `constant@`, `fn@`, `function@`, `field@`, `variant@`, `method@`, `type@`, `value@`, `macro@` and `prim@`. Function-like items can alternatively be suffixed with `()`, and macros with `!`: `[Foo()]`, `[vec!]`.

## What can't be resolved

If a name cannot be found, Rustdoc emits a warning pointing at the offending link, and leaves the text alone. This turns broken links into something CI can detect. Text in square brackets that does not look like a path, for example `[1, 2, 3]` or `[ ]`, is never treated as a link and does not produce warnings.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## Parsing

Rustdoc already parses doc comments as Markdown. Links appear in three forms in that grammar: inline links `[text](target)`, reference links `[text][label]` with a matching definition `[label]: target`, and shortcut links `[label]` or `[label][]`, which use the label as both text and key.

For each link whose target does not look like a URL (does not have a scheme such as `https:`, does not begin with `/` or `#`, and contains no `.` followed by an extension), Rustdoc attempts to interpret the target as a Rust path. For shortcut links, the label text is stripped of surrounding backticks before being considered as a path, and the backticks remain in the rendered text.

## Resolution

Resolution runs after the compiler's name resolution pass has produced the module tree and the imports for each module. For each documented item, the path is resolved within the scope of the item's parent module (or the item itself, for modules, so that a module's inner docs can refer to its children without a prefix).

The result is a definition identifier. Rustdoc then maps this to its output location in the same way it computes links for type names appearing in signatures. If the item belongs to the current crate, the link is relative; if it belongs to another crate, the link uses the same mechanism as for external types, which follows the `html_root_url` attribute or the `--extern-html-root-url` command line flag, and falls back to no link when neither is available.

Associated items are resolved by first resolving the type or trait, then searching inherent impls and trait impls for the name. If several impls provide the item, resolution reports an ambiguity.

Items that are not themselves documented, for example private items, are still resolvable, but the link refers to a page that does not exist. Rustdoc warns in this case, because the link would be broken in the output.

## Output

A resolved link is replaced with the relative or absolute URL of the item's page, with a fragment for associated items such as `#method.push`. The resulting Markdown is rendered normally.

# Drawbacks
[drawbacks]: #drawbacks

- It adds complexity to Rustdoc, which now depends on the resolution machinery of the compiler more deeply and must keep it consistent across editions.
- The notation changes the meaning of existing doc comments. A comment such as `[Foo](bar)` that previously produced a link to a relative file named `bar` now attempts to resolve `bar` as a path. Authors who relied on relative links to non-item files are affected, although the heuristic for URLs mitigates most cases.
- Disambiguators add surface area to learn, and the set of prefixes must be maintained.
- Resolution makes documentation builds slower, though the cost should be small relative to the rest of the compilation.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**Use a new syntax such as `[[Foo]]` or `{@link Foo}`.** A custom notation would avoid collisions with existing links, but would not be readable in rendered Markdown by other tools, such as editors and code hosting sites, and adds yet another syntax. Using the standard Markdown link forms keeps source readable everywhere, and degrades gracefully: a viewer unaware of the feature shows the path as text.

**Resolve names globally rather than in scope.** Looking up a name in a crate-wide table is simpler, but ambiguous for common names, and unlike how Rust names work elsewhere. Using the scope of the item matches programmer expectations.

**Leave it to external tools.** Third-party preprocessors could rewrite doc comments. This duplicates resolution logic and cannot see the compiler's view of imports.

**Do nothing.** The status quo remains, with brittle URLs and missing links.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

- How should links to items from other crates be handled when no documentation URL is known? The proposal omits the link and warns, but a different default may serve better.
- Should links to a primitive type such as `str` or `u32` be resolved by name, given that they can be shadowed in principle?
- Is the set of disambiguator prefixes the right one, or should it be reduced to a smaller core?
- How should links in `#[doc = "..."]` attributes generated by macros be handled, given that their scope may differ from the expansion site?
- Should there be a lint level for unresolved links, allowing projects to turn warnings into errors?
