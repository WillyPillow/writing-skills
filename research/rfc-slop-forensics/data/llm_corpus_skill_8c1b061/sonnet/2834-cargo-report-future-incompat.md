# Rust RFC 2834: Cargo report on future-incompatibility

## Summary

Cargo should tell developers which of their upstream dependencies trigger future-incompatibility warnings. It should list those dependencies even when the warnings are hidden in the build output, whether by `--cap-lints` or by an `#[allow(..)]` attribute. Cargo may also give the maintainer of the downstream crate hints on how to resolve the problem. This RFC does not specify or require the form of those hints.

## Motivation

A future-incompatibility warning (a "future-incompat" lint) tells the author of some code that the code will stop compiling in a later release of the compiler. The compiler team can only make such a change without breaking users if the people affected hear about the warning first. Where the warning appears determines whether they do.

Consider a crate `app` that depends on a library `old-lib`, which `app`'s author does not maintain. Suppose `old-lib` contains code that triggers a future-incompat lint. When Cargo builds `old-lib` as a dependency, it passes `--cap-lints` to `rustc` so that lints in dependency code do not flood the build output of the crate being developed. The effect is that the lint is capped at the "allow" level, and `rustc` prints nothing. `old-lib`'s own author may not see the warning either, if they do not build with a toolchain that reports it or have placed an `#[allow(..)]` attribute over the code.

When the compiler later turns the lint into a hard error, `app` stops building. The author of `app` has had no warning. They also cannot fix the code themselves without forking `old-lib`, publishing a fix upstream, or pinning an older version.

The problem is that the people best placed to act early, the maintainers of the downstream crate, are the people who currently receive no signal. The maintainers of the upstream crate may or may not be able to act, and the compiler team has no direct channel to either.

[TODO: the material for this RFC gives no past instance of a future-incompat change breaking a dependency tree. Add one, with the lint name and the crates affected, if available.]

## Guide-level explanation

After a build, Cargo prints a short note when at least one dependency in the build triggered a future-incompat warning that was not shown. The note names the package and version and says that a future release of Rust may reject it. The note does not fail the build and does not change the exit code.

Cargo then offers a way to see the details. [TODO: the author's material does not specify the command or flag. Decide whether this is a flag on `cargo build`, a subcommand, or both, and describe it here.] The report lists, for each affected package:

- the package name and version,
- the lint or lints that fired,
- where in the package the lints fired, if the compiler provides it.

For a developer, the sequence is as follows.

1. Run `cargo build` as usual.
2. Read the note at the end of the build that lists affected dependencies.
3. Look at the detailed report to find out which lint fired and in which package.
4. Decide on a response: upgrade the dependency, report the problem upstream, or replace the dependency.

Cargo may add advice to the report. For example, if a newer version of the dependency exists in the registry, the report might say so. The RFC does not require that advice, and it does not fix what the advice says. [TODO: confirm that Cargo is allowed to omit advice completely in the first implementation.]

## Reference-level explanation

The design has three parts: collecting the warnings from `rustc`, deciding which to report, and presenting them.

### Collecting warnings

The compiler needs to report future-incompat lints in a form that does not depend on lint levels. A lint capped at "allow" is normally not emitted at all. The compiler must therefore have a mode in which it still records that the lint would have fired, and emits this record as structured output (for instance, as a message in `--error-format=json` output). [TODO: the material does not describe the compiler-side mechanism or which interface Cargo reads. The author should specify it.]

The record needs to say which lint fired, in which crate, and, when possible, at which location. Cargo attaches the package identity it already knows from the build graph.

### Deciding what to report

Cargo reports a record when all of the following are true.

1. The lint is marked future-incompatible in the compiler.
2. The package that triggered it is a dependency of the workspace, not a workspace member. For workspace members, the compiler already shows the warning, unless the author has silenced it by choice. [TODO: decide whether a silenced warning in a workspace member should also appear in the report, since the RFC's goal is to list warnings regardless of suppression.]
3. The warning was hidden by `--cap-lints`, by an `allow` attribute, or by both.

Cargo should include dependencies that were already built and cached. A cached dependency does not run `rustc`, so Cargo needs to store the records alongside the build artifacts to repeat them on later builds. [TODO: ask the author what mechanism is intended, since a report that appears only on the first build would defeat the goal.]

### Presentation

The note after the build is a single block, not one line per warning, so that a large dependency tree does not produce pages of output. The format of the detailed report is left to the implementation. The RFC fixes only the content: package, version, lint name.

Machine-readable output is also useful, because continuous integration systems can use it to fail a job or open a ticket. [TODO: the author should say whether JSON output is part of this RFC.]

## Drawbacks

The note adds output to builds that previously printed nothing. Developers who cannot act on the report, for example because the dependency is unmaintained, will see it on every build. Whether a way to silence the note is needed is an open question.

The feature increases what Cargo has to store and what the compiler has to emit. The size of that cost is not measured in the material for this RFC. [TODO: add a measurement of the extra output size and build time for a large dependency tree, if the author has one.]

## Rationale and alternatives

The central design choice is where the warning appears. The status quo shows it to nobody when `--cap-lints` is active. Showing the full compiler warning inside dependency builds would show it to the right people, but would make the output of every build with an old dependency noisy, which is why `--cap-lints` is used in the first place. The compromise in this RFC is one summary per build, with the details on request.

Alternatives a reviewer may ask about:

- A separate Cargo subcommand that rebuilds with the lints enabled. [TODO: ask the author whether this was considered and why it lost.]
- A check in the crates.io registry that flags crates triggering the lints, so that maintainers hear about it at publish time. [TODO: ask the author whether this was considered.]
- Reporting only to the upstream maintainer, not to downstream users. [TODO: ask the author.]

Reversibility: the note and report are output formats for humans, so they are cheap to change. A structured format that CI systems parse would be harder to change once people depend on it, so if it is added, it should be treated as stable only after some experience with it. [TODO: confirm with the author.]

## Prior art

[TODO: the author's material cites no prior art. Name any comparable feature in other package managers, such as deprecation warnings for dependencies, and describe how it relates to this proposal.]

## Unresolved questions

- The command or flag by which the detailed report is requested.
- The compiler interface that carries the records.
- Whether the report should include lints silenced in workspace members.
- How cached dependencies preserve their records.
- What advice, if any, the first implementation gives.
- Whether the note can be silenced and how.

## Future possibilities

Cargo could suggest a specific newer version of an affected dependency when the registry has one that no longer triggers the lint. This depends on knowing which versions trigger the lint, which Cargo does not know today. The RFC leaves it out.
