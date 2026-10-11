- Feature Name: `editions`
- Start Date: 2017-08-15
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary
[summary]: #summary

Rust's ecosystem, tooling, documentation, and compiler are constantly improving. To make it easier to follow development, and to provide a clear, coherent "rallying point" for this work, this RFC proposes that we declare an *edition* every two or three years. Editions are designated by the year in which they occur, and represent a release in which several elements come together:

- A significant, coherent set of new features and APIs have been stabilized since the previous edition.
- Error messages and other important aspects of the user experience around these features are fully polished.
- Tooling (IDEs, rustfmt, Clippy, etc.) has been updated to work properly with these new features.
- There is a guide to the new features, explaining why they are important and how they should influence the way you write Rust code.
- The standard library and other core ecosystem crates have been adjusted to follow the idioms of the new edition.

Editions are opt-in at the crate level. A crate declares which edition it targets in its manifest, and the compiler accepts different syntax and applies different rules accordingly. Crates written for different editions can be freely linked together, so the ecosystem never splits.

# Motivation
[motivation]: #motivation

Since Rust 1.0, the language has evolved on a six-week train. Each release contains a handful of stabilizations, bug fixes and improvements. This cadence has served us well: it removed the pressure to rush a feature into a rare big release, and it gave users a steady supply of improvements.

It has a cost, however. When improvements arrive one at a time, it is hard for anyone, whether a user, a writer of blog posts, or a team deciding whether to adopt Rust, to see the overall picture. The sum of six months of progress does not have a name, a landing page, or a moment of celebration. Learning materials go stale in small increments, and there is no point at which we can say "the book now describes Rust as it is today."

Meanwhile, there is a second pressure running in the opposite direction. Some improvements to the language require breaking changes. A new keyword can only be introduced if no existing code uses that word as an identifier. A cleaner module system might change what an existing path means. Our stability promise forbids changing the meaning of code that compiles today, and so these improvements either wait forever or are shaped into something less good than they could be.

Editions address both problems at once. They provide a regular, human-scale unit of progress to communicate and to polish toward, and they provide a controlled mechanism for changes that cannot be made in a strictly backwards-compatible fashion.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

## What an edition is

An edition is a named snapshot of the language and its surrounding experience. The first edition is "Rust 2015," which is simply what Rust 1.0 and its descendants have been. The next might be "Rust 2018."

When you create a new project, Cargo records the edition in `Cargo.toml`:

```toml
[package]
name = "my-crate"
version = "0.1.0"
edition = "2018"
```

If the field is absent, the crate is assumed to be written for 2015, so that every existing crate continues to build without modification.

## What changes between editions

Almost nothing changes. The vast majority of the language, its semantics, its standard library, and its compiler behavior is identical across editions. Editions may only alter the way source code is *parsed and interpreted at the surface*. Examples include reserving new keywords, adjusting how paths resolve, or making a lint into a hard error.

What editions cannot do is change the meaning of the compiled program in a way that affects other crates. They do not change the ABI, the trait system's coherence rules, the layout of types, or the standard library as linked. All editions share the same compiler backend and the same MIR, so a function compiled under one edition is indistinguishable at link time from one compiled under another.

## Using multiple editions together

Suppose your crate is on 2018 and depends on a crate that is still on 2015. You can use it exactly as before. Types, traits and functions flow freely between the two. If the 2015 crate defines a function named `async`, you can call it from your 2018 code with the raw-identifier syntax; macros defined in a 2015 crate expand using the 2015 rules, regardless of where they are invoked.

This is the essential promise: **you never have to upgrade your dependencies for your own sake, and your dependents never have to upgrade for yours.**

## Migrating

Moving a crate to a new edition is an explicit step. The tool `cargo fix` is extended with an edition-migration mode that rewrites your code to compile under the new edition with unchanged behavior. In the best case, nothing visible happens: the tool rewrites a few identifiers, and the crate compiles. Each edition is accompanied by a migration guide describing the changes.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## Declaring the edition

The edition is a per-crate setting passed to `rustc` as `--edition=<year>`. Cargo passes this flag based on the `edition` key in the manifest. The default, when the flag is omitted, is `2015`.

## Rules on what an edition may change

To keep the system tractable, we adopt the following rules.

1. The set of valid editions is closed and enumerated by the compiler. Unknown editions are an error.
2. Edition differences are confined to the frontend: lexing, parsing, name resolution, and lints that can be made hard errors. After lowering, no edition information survives.
3. Editions may not introduce differences in the standard library's API. New APIs are available in all editions. The prelude is a special case and may differ, as it is a name-resolution concern.
4. Any change introduced by an edition must be mechanically migratable by tooling, with the old code behaving identically under the new edition after migration. A change for which this cannot be done will not be accepted into an edition.
5. The compiler continues to support all editions indefinitely.

## Spans and macros

Because macros may be defined in one crate and expanded in another, each token carries the edition of the crate in which it was written, as part of its span. The parser consults the edition of the token it is looking at, not that of the crate being compiled, when deciding if a word is a keyword. This is what lets a 2018 macro expand correctly inside a 2015 crate, and the reverse.

## Lints and warnings

Many edition changes begin as warn-by-default lints in the preceding edition, giving users a gradual path. The lint group `rust_2018_compatibility` allows a crate to detect, ahead of time, the code that will break on migration.

## The cadence

Editions are planned every two to three years, not as a fixed schedule. An edition is released when its criteria in the Summary are met, not when a date arrives. The six-week release train is unaffected; an edition is simply a particular stable release that the project declares to be the start of a new edition.

# Drawbacks
[drawbacks]: #drawbacks

- **Complexity in the compiler.** Supporting multiple frontends behavior adds code and testing burden. Every edition we ship remains supported forever.
- **Cognitive load for users.** Readers of Rust code will need to know which edition they are reading. We believe this is manageable if the differences are small and well-signposted.
- **Risk of fragmentation.** If editions are too ambitious, they could effectively become two languages. The rules above limit this.
- **Marketing.** There is a risk that editions are perceived as a "Rust 2.0," with the baggage that term carries from other communities. Messaging must emphasize that interoperation is seamless.

# Rationale and alternatives
[alternatives]: #rationale-and-alternatives

## Never break anything

We could continue to hold the line with no breaking changes of any kind. This keeps the language simple to describe, but at a growing price in awkward design, since every future feature must work around past decisions.

## A Rust 2.0

A traditional major version would let us fix mistakes in bulk, but history in other languages shows that major-version transitions split ecosystems for years. Editions are designed to be the opposite: any crate can mix with any other.

## Purely feature-gated improvements

We could use feature flags per crate to opt in to each change individually. This was rejected because it multiplies the number of language variants that exist in the wild, which complicates the learning story and makes tooling harder.

## Unstable-feature style "preview" channels

Previews let users try future syntax, but do not address the communication problem or the need for breaking changes.

# Unresolved questions
[unresolved]: #unresolved-questions

- What is the exact set of lints that should be promoted at the first edition boundary?
- How should the standard library documentation present edition-specific differences in the prelude?
- Should `cargo new` always default to the latest edition, and how long should the older ones remain advertised in the documentation?
- What should the process be for deciding what goes into an edition, and how can the community contribute to the polish criteria?
