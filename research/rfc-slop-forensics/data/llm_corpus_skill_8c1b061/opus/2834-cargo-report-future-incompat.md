# RFC 2834: Cargo reports future-incompatible dependencies

- Feature name: `future_incompat_report`
- Start date: [TODO: date]
- RFC PR: [TODO: link]
- Tracking issue: [TODO: link]

## Summary

When a build compiles a dependency that triggers a future-incompatibility warning, Cargo tells the developer, even if the warning was suppressed by `--cap-lints` or by an `#[allow(..)]` attribute in the dependency. Cargo lists the affected dependencies at the end of the build. It may also suggest what the maintainer of the downstream crate can do about each one, but this RFC does not specify or require those suggestions.

## Motivation

The Rust compiler uses future-incompatibility lints when it needs to turn code that compiles today into an error. The lint warns first, and a later release makes the code a hard error. The warning period exists so that crate authors can fix their code before the error lands.

That process works for code in the crate being built. It does not work for code in its dependencies. Cargo passes `--cap-lints allow` when it compiles a dependency from a registry or a git source, so no warning from a dependency reaches the developer. A dependency can also suppress the lint itself with `#[allow(..)]`. In both cases, the first sign of the problem the downstream developer sees is a hard error after a compiler upgrade, in code they did not write and may not be able to change quickly.

[TODO: cite the cases that motivated this RFC, for example a lint that was turned into an error and broke crates through their dependencies, with the number of affected crates if Crater data exists.]

The person who can fix the problem is the maintainer of the dependency. The person who sees the error is the downstream developer. Reporting the warning to the downstream developer during the warning period gives them time to upgrade the dependency, report the problem upstream, or pin a compiler version, before the break.

## Goals

- When a build compiles a dependency that triggers any future-incompatibility lint, the build output says so and names the dependency, its version, and the lint.
- The report appears whether the lint was capped by Cargo or allowed in the dependency's source.
- The report does not change the build result. A build that succeeded still succeeds.

## Non-goals

- Fixing the dependency. Cargo reports the problem; it does not patch code or upgrade versions on its own.
- Reporting ordinary warnings from dependencies. Capping those is intended. Only lints marked as future-incompatible are reported.
- Specifying which fix Cargo suggests. Suggestions such as "a newer version of this crate does not trigger the lint" are allowed but left to the Cargo team.

## Guide-level explanation

Suppose a project depends on `foo 1.2.0`, and `foo` contains code that a future-incompatibility lint flags. Today the build prints nothing about `foo`. With this RFC, a build ends with a short note:

```text
warning: the following packages contain code that will be rejected by a future version of Rust: foo v1.2.0
note: to see what the problems were, use the option `--future-incompat-report`, or run `cargo report future-incompatibilities --id 1`
```

The note is one entry per affected package. It does not print the lint messages themselves, because those point at code in a dependency that the developer usually cannot edit, and a long list of them would bury the warnings for the developer's own crate.

The developer can view the full report, with each lint message and its source location in the dependency, by passing a flag on the next build or by running a separate command that reads the report stored from the last build. [TODO: confirm the flag and command names. The names above are placeholders for the design, not settled names.]

## Reference-level explanation

The design has three parts: rustc tells Cargo which lints are future-incompatible, Cargo collects them for each package, and Cargo stores and prints the result.

### Signaling from rustc

Cargo cannot recognize a future-incompatibility lint by name, because the set changes with each compiler release. Rustc must mark them. When rustc runs with JSON diagnostics, it adds a field to each diagnostic produced by a lint that is registered as future-incompatible. [TODO: decide the JSON shape. The field must be ignored by tools that do not know it.]

The important change is in how rustc treats capped and allowed lints. Today, a lint at level `allow` produces no diagnostic. Under this RFC, when Cargo asks for it with a flag, rustc still runs future-incompatibility lints that are capped or allowed, and emits them in a separate section of its JSON output. The diagnostic is not shown to the user by rustc. Cargo decides what to show.

The flag keeps the cost off builds that do not use it. Running a lint that would otherwise be skipped costs some compile time. [TODO: measure the cost of running allowed future-incompatibility lints on a large dependency graph.]

### Collection in Cargo

For each compilation unit, Cargo reads the future-incompatibility diagnostics from rustc's output and records them with the package ID. Diagnostics from the crate being built are already shown by rustc as normal warnings, so Cargo includes only packages that are not workspace members in the summary. [TODO: decide whether path dependencies outside the workspace count as dependencies here. Cargo does not cap lints for path dependencies today, so their warnings are already visible.]

A cached build does not rerun rustc. Cargo must therefore store each unit's future-incompatibility diagnostics alongside its other build output, so that a no-op build reports the same packages as the build that compiled them. Without this, the report would appear once and then disappear, and a developer would think the problem was gone.

### Storage and display

At the end of the build, Cargo writes the collected diagnostics to a report file in the target directory and prints the one-line summary described above. The report file keeps a small number of recent reports, each with an ID, so the separate command can show one after later builds have run. [TODO: decide how many reports to keep.]

The summary is printed once per build, after all other output, and only when at least one dependency is affected.

### Suggestions

Cargo may add a note to each entry. One useful note says whether a newer version of the package that is compatible with the current requirement exists, since the fix may then be `cargo update -p foo`. Whether that newer version is free of the lint is unknown without building it, so the note must not claim it is. This RFC does not require any suggestion.

### Configuration

A developer who has already acted on a report, for example by filing an upstream issue, may want the summary to stop. Cargo provides a configuration value to turn the summary off. [TODO: decide whether this setting can be scoped to one package or one lint, and whether turning it off for all packages is allowed at all, given that the point of the feature is to keep the warning visible.]

## Drawbacks

The summary adds output to builds that the developer cannot act on directly. A developer whose dependency is unmaintained has few options beyond replacing it. Some will see the note on every build for a long time.

The feature adds a contract between rustc and Cargo. Rustc must keep marking future-incompatibility diagnostics in its JSON output, and Cargo must keep reading them. Other build systems that call rustc directly get none of this unless they implement the same collection.

Running capped lints makes dependency builds slower by an amount not yet measured.

## Rationale and alternatives

The central choice is to report from Cargo, after the build, rather than to stop capping these lints. If Cargo passed future-incompatibility lints through uncapped, the developer would see each lint message for code in a dependency, in the middle of the build output, with source locations in files they did not write. A summary gives the developer the one fact they can act on: which package has the problem.

[TODO: Was uncapping only future-incompatibility lints considered? If so, record why the summary was preferred.]

[TODO: Was relying on Crater runs and upstream issues by the compiler team, with no change to Cargo, considered? That approach reaches crates on crates.io but not private dependencies. If it was considered, record why it was judged insufficient.]

## Unresolved questions

- The names of the flag, the command, and the configuration value.
- The JSON field rustc uses to mark future-incompatibility diagnostics.
- Whether the report can be turned off per package or per lint.
- How long a lint must have been reported this way before it can become a hard error. [TODO: decide whether this RFC sets a policy for that or leaves it to the compiler team.]
