# RFC 2834: Cargo report future-incompat

- Feature Name: `cargo_report_future_incompat`
- Start Date: 2019-12-05
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

Cargo should alert developers to upstream dependencies that trigger future-incompatibility warnings. Cargo should list such dependencies even when these warnings have been suppressed (for example via `cap-lints` or `#[allow(..)]` attributes).

Cargo could additionally provide feedback for tactics a maintainer of the downstream crate could use to address the problem. The details of such tactics are neither specified nor mandated by this RFC.

## Motivation

Rust evolves under a strong stability guarantee, yet occasionally the compiler needs to tighten a rule that was found to be unsound or ill-specified. When this happens, the compiler first introduces a lint that fires on the affected code. These are the *future-incompatibility lints*, and they warn that the construct will become a hard error in a later release.

The mechanism is only useful if the warning reaches someone who can act on it. For code in the current workspace this works: the author sees the warning when they build, and can fix it. For code in dependencies it does not.

Cargo passes `--cap-lints allow` when compiling dependencies from a registry, to prevent the build output of a user's project from being swamped by warnings in code they do not control. This is a sensible default for ordinary lints. For future-incompatibility lints it has an unfortunate effect: the warnings are suppressed precisely for the code that the user is least able to fix and where the problem is most likely to cause breakage later. When the lint finally becomes an error, a build that worked yesterday fails today because of a crate five levels deep in the dependency tree, whose maintainer may be unresponsive.

There have been several such episodes. Each followed the same pattern: the compiler team announced a change; a warning had existed for many releases; nobody noticed it because it was hidden; crater runs found the breakage but needed manual follow-up with maintainers; and some changes had to be postponed because too much of the ecosystem would be hurt.

The goal of this RFC is to close the loop between the compiler's warnings and the people who can resolve them, without returning to a world where every build prints every warning from every dependency.

## Guide-level explanation

After building a project, Cargo may print a short note:

```
warning: the following packages contain code that will be rejected by a future version of Rust: old-parser v0.3.1, fancy-macros v1.2.0
note: to see what the problems were, use the option `--future-incompat-report`, or run `cargo report future-incompatibilities --id 1`
```

This is not a hard error and does not change the exit code. It is printed at most once per build, and it is compact: a single line naming the packages and a single line explaining how to learn more.

Running the suggested command shows the underlying detail:

```
$ cargo report future-incompatibilities --id 1

The following warnings were discovered during the build. These warnings are
an indication that the packages contain code that will become an error in a
future release of Rust. These warnings typically cover changes to close
soundness problems, unintended or undocumented behavior, or critical
problems that cannot be fixed in a backwards-compatible fashion, and are not
expected to be in wide use.

Each warning should contain a link for more information on what the warning
means and how to resolve it.

To solve this problem, you can try the following approaches:

- Some affected dependencies have newer versions available.
  You may want to consider updating them to a newer version to see if the
  issue has been fixed.

  old-parser v0.3.1 has the following newer versions available: 0.3.2, 0.4.0

- If the issue is not solved by updating the dependencies, a fix has to be
  implemented by those dependencies. You can help with that by notifying the
  maintainers of this problem (e.g. by creating a bug report) or by proposing a
  fix to the maintainers (e.g. by creating a pull request).

  - fancy-macros v1.2.0
    - Repository: https://github.com/example/fancy-macros
    - Detailed warning command: `cargo report future-incompatibilities --id 1 --package fancy-macros@1.2.0`
```

A developer who does not care can ignore the note. A developer who wants to act now has what they need: the identity of the problematic packages, newer versions to try, and a link to the repository.

## Reference-level explanation

### Compiler support

The compiler already knows which lints are future-incompatible: they are marked with a `future_incompatible` flag and have an associated reference. This RFC asks that, for lints with this flag, the compiler additionally emit a machine-readable summary even when the lint level is `allow` or capped.

Concretely, `rustc` gains the option `--json=future-incompat`. When it is given, the compiler, at the end of the compilation of a crate, emits a JSON message listing every future-incompatibility diagnostic that would have been reported had the lint level not been lowered. Each entry contains the lint name, the span, the rendered diagnostic, and the link to the tracking issue or explanatory page.

Reporting is a separate channel from the usual warnings. The existing level and cap logic continues to operate as before. Whether a lint appears on the user-visible stream is unchanged.

### Cargo behavior

Cargo passes the new flag when compiling every package in the build, including dependencies whose lints are capped. It collects the resulting messages and stores them in a report file under `target/`, tagged with an incrementing identifier so that repeated builds do not overwrite each other without notice. Cargo retains a small number of recent reports.

At the end of the build, if any report entries were collected, Cargo prints the short summary shown above. If a package in the workspace itself generated the warnings, they are already shown in the usual way and the summary mentions only dependencies.

The new subcommand `cargo report future-incompatibilities` prints the stored report. It takes `--id <n>` to select a report and `--package <spec>` to restrict output to one package. The default is the most recent report.

Cargo may, when forming the report, consult the registry index to determine whether a newer version of a flagged package exists, and list it. This is best-effort and must not require network access if the index is not already available.

A configuration option, `future-incompat-report.frequency` in the Cargo configuration, controls how often the note is printed: `always` (the default for the first release), or `never`. A future revision may add `daily` or `weekly`, which would avoid repeated notes in an edit-compile loop.

### Relationship to `cargo install`

`cargo install` builds a crate and its dependencies from scratch, and the user has little ability to patch them. In this case Cargo prints the note and also suggests contacting the maintainers of the installed package itself, since it is the one with the dependency graph in a state to fix.

### Stability

The JSON message format is considered unstable initially, controlled by `-Z unstable-options`, and is stabilized once Cargo and rustc have exercised it. The `cargo report` subcommand is similarly unstable at first.

## Drawbacks

- This adds user-visible output to builds that previously were silent, which some users will find noisy or alarming. The design counters with brevity and a configuration switch.
- It adds persistent data in `target/` and a new subcommand to maintain.
- Printing this note may lead users to open issues against dependency maintainers when the issue is already known and fixed in an unreleased version. Maintainers could find this tiresome.
- The compiler must produce additional diagnostics in the capped case, which has a small cost to compile time.

## Rationale and alternatives

**Stop capping lints for future-incompatible diagnostics.** The simplest approach is to let these warnings through on dependencies. The downside is the possibility of large amounts of output for a user who cannot act on any of it. The aggregated summary is gentler.

**Rely on crater.** The compiler team already uses crater runs to assess the effect of a change. This is valuable but only samples public crates at a point in time, and it does not help private code or code that depends on a pinned old version.

**A separate lint tool.** A `cargo` subcommand could run a dedicated analysis over the lock file. This avoids touching normal builds but requires the user to remember to run it, which defeats the purpose.

**Put the note on `cargo build` only if requested.** An opt-in flag would be unobtrusive but would reach only the users who already care.

## Prior art

Several ecosystems provide dependency advisories. `npm audit` reports known vulnerabilities in a dependency tree at install time, and `cargo audit` does likewise for security advisories in the RustSec database. Python's `-W error::DeprecationWarning` and its default hiding of deprecation warnings outside `__main__` is a cautionary tale: a warning that nobody sees is not a warning.

## Unresolved questions

- What is the right default frequency for the note?
- Should the report include a suggestion of specific tactics, such as `[patch]` entries or a version bump?
- How should Cargo present reports for packages that appear multiple times at different versions?
- Which of the compiler's lints should be classed as future-incompatible for this purpose, and who decides?
