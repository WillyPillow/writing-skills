- Feature Name: N/A
- Start Date: 2017-07-03
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Rust's ecosystem, tooling, documentation, and compiler are constantly improving. To make it easier to follow development, and to provide a clear, coherent "rallying point" for this work, this RFC proposes that we declare an *edition* every two or three years. Editions are designated by the year in which they occur, and represent a release in which several elements come together:

- A significant, coherent set of new features and APIs have been stabilized since the previous edition.
- Error messages and other important aspects of the user experience around these features are fully polished.
- Tooling (IDEs, rustfmt, Clippy, etc.) has been updated to work properly with these new features.
- There is a guide to the new features, explaining why they're important and how they should influence the way you write Rust.
- The book has been updated to cover the new features.

Editions also give us a mechanism for making a limited class of changes that would otherwise be breaking, such as introducing new keywords, by letting each crate opt in to a particular edition. Crates on different editions interoperate seamlessly.

# Motivation

Rust ships a new stable release every six weeks. This train model has served us well: features land when they are ready, there is little pressure to rush, and users can upgrade with confidence because stable releases do not break their code.

But the rapid cadence has a cost that becomes clearer as the language matures. From the outside, Rust does not appear to change much in any single release. A user who returns to the language after a year finds that many things are different, yet there was no single moment at which those differences were announced, documented and explained together. Blog posts about individual releases list a handful of stabilized APIs; they rarely tell the story of how idiomatic Rust has shifted. Features often land in a state that is technically complete but not yet well supported by tooling, documentation or diagnostics, and the final polish arrives piecemeal over subsequent releases.

This leads to several concrete problems:

- **Communication.** It is hard to tell people outside the community what has changed. "Rust 1.23 stabilized three methods on slices" is not news. "Rust 2018 makes the module system easier to learn, adds non-lexical lifetimes, and has first-class support in your editor" is.
- **Coordination.** The compiler, Cargo, rustfmt, Clippy, the RLS and the documentation are developed by different teams. Without a shared target, it is easy for a feature to stabilize in the compiler long before the other tools understand it.
- **Evolution.** Some desirable changes cannot be made without breaking existing code. The most prominent example is new keywords: `async`, `await`, `try` and `dyn` are all plausible additions, but each is currently a valid identifier and may be used as one in published crates. Under our stability guarantee we cannot simply reserve them.

Editions address all three.

# Guide-level explanation

## What an edition is

An edition is a named point in Rust's evolution, identified by a year: Rust 2015, Rust 2018, and so on. Rust 2015 is the name we give, retroactively, to the language as it has existed since 1.0.

Each crate declares which edition it is written in, in `Cargo.toml`:

```toml
[package]
name = "my-crate"
version = "0.1.0"
edition = "2018"
```

If no edition is specified, the crate is treated as Rust 2015. `cargo new` will set the field to the latest edition for new projects.

## What changes between editions

Most of the work that makes up an edition is not specific to any edition at all. New features stabilized during the edition's development cycle are available to crates on every edition, wherever that is possible. The edition is primarily a marketing and coordination milestone: a release in which we stop, polish, and tell a coherent story.

A small number of changes are only possible with an opt-in, because they would break existing code. These changes are tied to the edition. Examples of the kind of change we expect:

- Reserving new keywords.
- Turning a lint that was previously warn-by-default into an error, after a deprecation period.
- Changing the meaning of syntax in a way that is backward-incompatible but mechanically migratable.

## Interoperation

A crate on one edition can depend on crates on any other edition. The ecosystem is never split. A Rust 2018 crate can call functions defined in a Rust 2015 crate, implement its traits, and use its macros, and vice versa. If a 2015 crate exports a function named `async`, a 2018 crate can still call it using raw identifier syntax (`r#async`), which this RFC also proposes.

This works because edition differences are confined to the front end of the compiler: parsing, name resolution and lints. After that, all editions are lowered to the same internal representation. There is one compiler, not several.

## Migration

Moving a crate to a new edition is meant to be routine. The previous edition will receive warnings for code that would break on the new edition, and `rustfix` (invoked through `cargo fix --edition`) will apply the suggested changes automatically. The expected workflow is:

1. Update to the latest toolchain.
2. Run `cargo fix --edition` and commit the result.
3. Change `edition` in `Cargo.toml`.
4. Optionally adopt new idioms, with help from edition-idiom lints.

Crates are never required to migrate. A crate written for Rust 2015 will continue to compile on all future compilers.

# Reference-level explanation

## Constraints on edition changes

To keep editions cheap for users and maintainers, we impose the following rules on what an edition can change:

- **No silent changes in meaning.** If code compiles on two editions, it must mean the same thing on both, or the compiler must warn about the difference on the earlier edition before migration.
- **Migration must be automatable** for the overwhelming majority of code. Any breaking change tied to an edition must come with a lint on the previous edition and a machine-applicable fix.
- **Warnings come first.** A change can become an error in a new edition only if it has been a warning on the previous edition for at least one release cycle before the edition ships.
- **Interop is preserved.** Edition-specific changes must not affect the public interface that a crate presents to its dependents in a way that prevents cross-edition use.
- **The standard library is shared.** There is one `std`, compiled once, usable by all editions. Edition differences cannot require divergent library APIs.

## Compiler support

The compiler accepts an `--edition` flag, which Cargo sets from the manifest. Internally, edition-dependent behaviour is keyed off the edition of the span being processed, so that macros defined in a crate on one edition and expanded in a crate on another behave according to the edition of the code that wrote the tokens.

Before an edition is released, its features are available on nightly behind the edition flag, so that the migration path can be tested on real crates.

## Release process

An edition is declared well in advance, with a target release. Teams identify the work they intend to complete for it, and that work is tracked publicly. A "preview" period on nightly and beta lets crate authors try the migration. At release time, the stable compiler accepts the new edition, `cargo new` defaults to it, and the documentation, book and edition guide are published together.

# Drawbacks

- Editions add a concept that users must learn, and there is a risk that people perceive them as "Rust 2.0" and fear a split.
- The compiler must carry support for every edition indefinitely, which adds some ongoing maintenance cost to the front end.
- Tying marketing to a date creates pressure to ship features to meet it, which is in tension with the train model's philosophy that things ship when they are ready.

# Rationale and alternatives

We could continue with the train model alone and accept that keyword reservation and similar changes are impossible. This would leave the language increasingly constrained by decisions made before 1.0.

We could make breaking changes through a major version bump of the language, as some languages have done. Experience elsewhere shows that this risks fracturing the ecosystem for years.

We could allow fine-grained feature opt-ins per crate, rather than bundling them into editions. This would produce a combinatorial explosion of language dialects, making code harder to read and tooling harder to write. Editions keep the number of dialects small and linear.

# Unresolved questions

- The exact cadence. We propose "every two or three years" but will learn from the first edition.
- Which specific changes the first new edition should contain; that is left to separate RFCs.
