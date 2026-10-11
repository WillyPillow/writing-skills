# RFC 2834: Cargo report of future-incompatibility warnings

- Feature Name: `cargo_report_future_incompat`
- Start Date: [TODO: date]
- RFC PR: [TODO: link]
- Rust Issue: [TODO: link]

## Summary

When a build compiles a dependency whose code triggers a future-incompatibility warning, Cargo tells the developer which dependency it is. Cargo does this even when the warning was suppressed, whether by `--cap-lints` or by an `#[allow(..)]` attribute in the dependency's source. Cargo may also suggest what the maintainer of the downstream crate can do about it. This RFC does not specify or require any particular suggestion.

## Motivation

The compiler marks some lints as future-incompatibility lints. Such a lint fires on code that compiles today but that a later Rust release plans to reject, usually because the code relies on a compiler bug or on an unsound rule. The warning period exists so that affected code can be fixed before the change lands. [TODO: author to give one or two concrete future-incompatibility lints and the release in which each became, or is planned to become, an error.]

For code in the developer's own crate, the warning period works: the warning appears in their build output. For code in a dependency, the warning period does not work, for two reasons.

1. Cargo passes `--cap-lints` when it compiles dependencies from a registry or a git repository, so warnings in those crates do not appear in the build output. [TODO: confirm the exact cap level Cargo uses and for which kinds of dependency.]
2. The dependency's own source can contain `#[allow(..)]` for the lint, which suppresses it in every build, including the dependency maintainer's own.

The result is that the first sign of the problem a downstream developer sees is a hard error, in a crate they did not write, after a toolchain upgrade. At that point the fix is in someone else's hands. The developer must wait for the upstream maintainer to release a fixed version, fork the crate, or hold back the toolchain. [TODO: author to cite an instance where this happened, with a link.]

The downstream developer is often the right person to notice the warning, even though they cannot fix the code. They can upgrade to a fixed version of the dependency if one exists. They can open an issue upstream, or replace the dependency. They can do none of this if they never see the warning.

## Goals and non-goals

Goals:

- A developer whose build compiles a dependency that triggers a future-incompatibility lint learns, from the output of that build, that this is the case and which dependency it is.
- This holds whether the lint was capped by Cargo or allowed in the dependency's source.
- The full warning text for each affected dependency can be retrieved after the build without rebuilding.

Non-goals:

- Changing which lints are future-incompatibility lints, or changing the schedule on which they become errors.
- Showing other warnings from dependencies. Ordinary lints in dependencies stay capped, as they are today.
- Fixing the dependency. Cargo reports; it does not patch upstream code.

## Guide-level explanation

Suppose a project depends on `foo 1.2.0`, and `foo` contains code that triggers a future-incompatibility lint. Today the build succeeds and prints nothing about `foo`. Under this RFC, the build still succeeds, and the end of the output contains a short note:

```text
warning: the following packages contain code that will be rejected by a future version of Rust: foo v1.2.0
note: to see what the problems were, use the option `--future-incompat-report`, or run `cargo report future-incompatibilities --id 1`
```

The command in the note prints the full compiler warnings for each listed package, as they would have appeared if the lint had not been suppressed. The `--id` names one stored report, so the developer can retrieve the warnings of a particular build.

The exact wording of the note is not part of this RFC. [TODO: author to decide whether the command name and flag are part of the proposal or illustrative.]

## Reference-level explanation

The mechanism has three parts.

1. When rustc compiles a crate and a future-incompatibility lint fires, rustc records the diagnostic. It records it whether or not the lint level, after `--cap-lints` and `#[allow]`, would have shown it. When Cargo asks for it through a flag, rustc emits the recorded diagnostics as a machine-readable message, separate from the normal diagnostic output. [TODO: author to specify the flag and the message format, or state that both are left to the implementation.]
2. Cargo collects these messages for each package it compiles, including packages whose build output comes from a cached build. The report must survive a rebuild that compiles nothing, or a developer who runs the build twice sees the note only the first time. [TODO: author to specify where Cargo stores the per-package diagnostics so that a no-op rebuild can still report them.]
3. At the end of the build, if any package produced such a message, Cargo prints the summary note and stores the full report, so that the report command can display it later.

Lints that the developer's own workspace members trigger are already shown in the normal output. [TODO: decide whether workspace members also appear in the summary note or only dependencies.]

Cargo may add to the full report suggestions for the downstream maintainer. An example is a note that a newer semver-compatible version of the dependency exists, so `cargo update -p foo` could pick it up. Such suggestions are optional, and this RFC does not specify which ones Cargo gives or how it decides.

## The central tension: visibility against noise

Showing a developer warnings about code they cannot edit has a cost. Every build that compiles the affected dependency prints the note, and the note stays until upstream releases a fix and the developer updates. If the note is too loud, developers learn to ignore it, which defeats the purpose. If it is too quiet, the hard error still arrives as a surprise.

The design above takes a position between the two. The note is one warning line that names packages, plus one line saying how to see more. The full diagnostics, which can run to many lines per package, are shown only on request. The cost accepted is that a developer who never reads the end of the build output still misses the note.

[TODO: author to supply the reasoning for this choice. The following options are suggestions for the author to evaluate, not alternatives this RFC records as considered:
- Print the full diagnostics inline on every build. This is maximally visible, but long reports would bury the developer's own warnings.
- Print the note only when a newer version of the affected dependency exists. This is quieter, but it hides the problem in exactly the case where the developer has to act upstream.
- Let the developer silence the note for a given package, through configuration. This reduces noise for known cases, but it brings back a way to never see the warning.]

A second question concerns timing. A lint that becomes an error in the next release is more urgent than one with no schedule. If rustc knows when a lint is planned to become an error, the note could say so. [TODO: author to decide whether the note distinguishes lints by urgency.]

## Drawbacks

Builds of projects with affected dependencies print a warning the developer cannot fix directly. The suppression that this RFC works around exists to keep such output out of the way. [TODO: author to state how much additional output this produces in practice, for example by running the prototype on a sample of crates.]

rustc must keep computing and recording diagnostics for lints that are allowed. [TODO: author to measure whether this has a measurable compile-time cost; do not claim it is free without a measurement.]

Cargo gains a stored report and a new command, which are more surface to maintain.

## Rationale and alternatives

The status quo leaves the warning period ineffective for dependencies, as the motivation describes.

Another place for the information is the registry rather than the build. For example, crates.io could flag published versions that trigger future-incompatibility lints. This is a suggestion for the author to evaluate, not a recorded alternative. Such a flag would reach crate maintainers and could reach developers browsing the registry, but not developers who only run builds. It also depends on the compiler version the registry checks with. [TODO: author to say whether this was considered.]

## Unresolved questions

- The flag name and the message format between rustc and Cargo.
- Where Cargo stores reports, and how many past reports it keeps.
- Whether developers can turn the note off, per package or globally, and whether doing so should itself be discouraged.
- Whether the summary includes workspace members.
- Which suggestions, if any, Cargo gives for the downstream maintainer.

## Future possibilities

Once rustc emits a machine-readable record of future-incompatibility lints, other tools, such as continuous integration services or the registry, could consume the same record. [TODO: author to decide whether to keep this section.]
