# RFC: More API Documentation Conventions

- Feature Name: (fill me in with a unique ident, my_awesome_feature)
- Start Date: 2016-03-31
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

[RFC 505] introduced certain conventions around documenting Rust projects. This RFC augments that one, and a full text of the older one combined with these modifications is provided below.

[RFC 505]: https://github.com/rust-lang/rfcs/blob/master/text/0505-api-comment-conventions.md

## Motivation

Documentation is one of the most visible parts of any library. A user's first contact with a crate is often its rendered docs, and their ongoing experience depends on how quickly they can answer "what does this do, how do I call it, and what can go wrong?" The standard library sets the tone for the whole ecosystem, so consistency in its docs matters beyond the standard library itself.

RFC 505 established a good baseline, but experience since has revealed gaps. In particular:

- Documentation for functions that can fail often does not say how, or lists the failure modes inconsistently.
- Unsafe functions frequently omit the contract that callers must uphold.
- Examples sometimes use `unwrap()` or `try!` in ways that are noisy or hard to copy into real programs.
- Reviewers repeatedly leave the same comments on pull requests. These comments should be written down once.

Writing the conventions in a single place gives contributors a reference to work from and reviewers something to point to.

## Detailed design

The conventions below are the combined text of RFC 505 and the amendments. Items that are new or substantially changed are marked as such.

### Summary sentence

Every public item must have a doc comment that begins with a single-sentence summary. This sentence should be short, in the third person, and end with a period. It describes what the item does, not how.

```rust
/// Returns the number of elements in the vector.
pub fn len(&self) -> usize { ... }
```

Avoid beginning the sentence with the name of the item or with "This function". Prefer the present tense: "Returns", not "Will return". *(Amended: the summary of a type should be a noun phrase describing what it is, e.g. "A growable array.")*

The summary is used by `rustdoc` in module indexes, so it should make sense without any surrounding context.

### Longer description

After the summary, leave a blank line and add any further explanation. Keep paragraphs short. Use full sentences. Link to other items with intra-doc style links where practical, and prefer reference-style links for long URLs, collected at the bottom of the comment.

### Section headings

Use level-one markdown headings (`#`) for sections within a doc comment. The following section names are standard, and should appear in this order when present:

1. `# Examples`
2. `# Panics`
3. `# Errors`
4. `# Safety`
5. `# Aborts`
6. `# Undefined Behavior`

*(New: `# Errors` and `# Safety` as standard sections. `# Aborts` and `# Undefined Behavior` are added for completeness.)*

#### Examples

Every public item should have at least one example. Examples must compile and run as doctests. A good example demonstrates the most typical use first, followed by less common uses. An example should be as short as it can be while still being illustrative.

Hide boilerplate lines with a leading `# `. Do not hide lines that a reader must understand to use the API.

*(New)* Prefer `?` in examples rather than `unwrap()` when the example is about a function returning `Result`, showing how the error would be handled in real code. For doctests that use `?`, add a hidden `fn main() -> Result<(), Box<dyn Error>>` wrapper, as in:

```rust
/// # Examples
///
/// ```
/// # use std::error::Error;
/// # fn main() -> Result<(), Box<dyn Error>> {
/// let n: i32 = "42".parse()?;
/// assert_eq!(n, 42);
/// # Ok(())
/// # }
/// ```
```

*(New)* Examples should not print to standard output unless output is the point. Use `assert_eq!` to show results; it documents the expected value and checks it.

#### Panics

*(Amended)* If a function can panic, there must be a `# Panics` section describing every condition under which it does so. State conditions precisely: "Panics if `index` is greater than or equal to `len`." A panic that is purely a consequence of an internal bug is not documented.

#### Errors

*(New)* If a function returns `Result`, there must be an `# Errors` section describing the conditions under which each error variant is returned. When the error type has a single variant, one sentence suffices. When it has several, a bulleted list is clearer.

```rust
/// # Errors
///
/// Returns an error if the file does not exist, or if the process
/// lacks permission to read it.
```

#### Safety

*(New)* Every `unsafe fn` and every `unsafe trait` must have a `# Safety` section stating the invariants that the caller or implementor must uphold. Safe functions that contain `unsafe` blocks do not need this section, but may describe their invariants in code comments. The section should be precise enough that a reader can determine, for a given call, whether the contract is satisfied.

```rust
/// # Safety
///
/// `ptr` must be non-null, properly aligned and point to a valid `T`
/// for the duration of the call.
```

### Type, trait and module docs

Type-level documentation should explain the purpose of the type, how it relates to other types, and any invariants it maintains. Trait documentation should explain what implementors must guarantee, and give at least one example implementation when the trait is not obvious. Module documentation should explain what the module is for, and give an overview of the main types.

*(New)* Documentation for a trait method that has a default implementation should say what the default does.

### Formatting

- Wrap lines at 80 columns for prose.
- Use backticks for code identifiers, including type names and keywords: `Vec<T>`, `None`.
- Use emphasis sparingly. Avoid bold in the middle of a sentence unless it highlights a warning.
- Write `e.g.` and `i.e.` with periods and followed by a comma.
- Use "Returns" and not "Return" in the imperative-versus-descriptive question: the descriptive form is chosen for consistency.

### Cross references

*(New)* Prefer links to the canonical item rather than restating its behavior. If two methods are related, such as `iter` and `iter_mut`, each should mention the other.

### Deprecation

When deprecating an item, explain what to use instead and why. Keep the old documentation in place beneath the deprecation note so that existing users are able to understand what they are looking at.

### Stability and version notes

Where an item behaves differently across editions or releases, mention it in a `# Compatibility` section *(new, optional)*.

## Drawbacks

The conventions add a certain amount of work to every contribution, and the larger set of sections means more words in the source. The check that contributors follow them depends on reviewers, as there is no automated linting for most of the rules. Some APIs have trivial failure modes where the `# Errors` section feels like boilerplate.

## Alternatives

We could leave RFC 505 as is, and rely on review comments. This keeps the process lightweight but results in inconsistency. We could instead build lints, such as a `missing_docs_sections` lint in Clippy, but conventions need to be decided first. Alternatively, we could stop short of requiring `# Errors` and `# Safety` and treat them as recommendations; however, `# Safety` in particular is important enough to be required.

## Unresolved questions

- Should the conventions be enforced by a Clippy lint, and which ones?
- Should the ordering of sections be enforced by `rustdoc`?
- How should conventions apply to private items, if at all?
