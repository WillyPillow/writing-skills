- Feature Name: N/A
- Start Date: 2019-12-05
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Cargo should tell developers when their upstream dependencies trigger future-incompatibility warnings. It should list those dependencies even when the warnings have been suppressed, whether through `--cap-lints` or through `#[allow(..)]` attributes. Cargo may also suggest ways a downstream maintainer could deal with the problem, but this RFC neither specifies nor requires any particular suggestions.

# Motivation

Rust's stability promise allows one important kind of change: when the compiler accepts code it should not, because of a soundness hole or a bug in the type checker, the fix may break that code. To soften the blow, the compiler first issues a *future-incompatibility warning* for a while, usually through a lint such as `safe_packed_borrows` or `order_dependent_trait_objects`. Once enough time has passed and the ecosystem has caught up, the warning becomes a hard error.

This works well for code the developer owns. It works badly for dependencies.

When Cargo builds a crate from crates.io or a git repository, it passes `--cap-lints=allow` to `rustc`. The developer sees no warnings from that crate at all. That is usually what people want, since nobody wants a screen full of style lints from code they cannot change. But it also hides future-incompatibility warnings, which are exactly the warnings that predict the build will break.

The result is a familiar sequence:

1. The compiler team adds a future-incompatibility lint.
2. A widely used crate, several levels deep in the dependency graph, triggers it.
3. No one downstream sees the warning, because lints are capped.
4. The maintainer of that crate may never see it either, if they are not running the newest compiler or their CI ignores warnings.
5. The lint becomes a hard error, and suddenly thousands of builds fail.

The compiler team works around this with crater runs and by opening pull requests against affected crates by hand. That is a lot of work, it does not scale, and it still misses crates that are not on crates.io.

Even when a crate author has fixed the problem upstream, downstream users may be pinned to an old version through `Cargo.lock`. They will not know they need to run `cargo update` until the build breaks.

If developers learned early that a dependency they use is on track to stop compiling, they could upgrade, report the problem upstream, or switch to an alternative long before the warning becomes an error.

# Guide-level explanation

When you build a project and one of its dependencies triggers a future-incompatibility warning, Cargo prints a short notice at the end of the build:

```
warning: the following packages contain code that will be rejected by a future version of Rust: old-parser v0.3.1, legacy-macros v1.0.4
note: to see what the problems were, use the option `--future-incompat-report`, or run `cargo report future-incompatibilities --id 3`
```

The notice appears even though Cargo normally hides warnings from dependencies. It appears only once per build, at the end, so it does not get lost in the build output or flood the terminal.

To see details, run the suggested command:

```
$ cargo report future-incompatibilities --id 3
The following warnings were discovered during the build. These warnings are an
indication that the packages contain code that will become an error in a
future release of Rust. These warnings typically cover changes to close
soundness problems, unintended or undocumented behavior, or critical problems
that cannot be fixed in a backwards-compatible fashion, and are not expected
to be in wide use.

Each warning should contain a link for more information on what the warning
means and how to resolve it.

The package `old-parser v0.3.1` currently triggers the following future
incompatibility lints:
> warning: borrow of packed field is unsafe and requires unsafe function or block (error E0133)
>   --> src/lib.rs:42:13
>    |
> 42 |     let r = &self.header.len;
>    |             ^^^^^^^^^^^^^^^^
>    = note: for more information, see issue #46043
```

The report reproduces the diagnostics that were suppressed, including source locations in the dependency, so you can judge how serious the problem is and pass the details on to the maintainer.

If a newer, compatible version of the affected package exists, Cargo may add a hint such as:

```
note: old-parser v0.3.2 is available and may fix this. Run `cargo update -p old-parser`.
```

Developers who do not want these notices can turn them off in `.cargo/config.toml`:

```toml
[future-incompat-report]
frequency = "never"
```

# Reference-level explanation

## Compiler side

`rustc` gains a way to emit future-incompatibility diagnostics in its JSON output *even when lints are capped or allowed*. Each future-incompatibility lint is already marked in the compiler's lint registry with a `FutureIncompatibleInfo` entry. When such a lint fires:

- if it would normally be emitted, nothing changes;
- if it is suppressed by `--cap-lints` or by `#[allow]`, the compiler still records the diagnostic and emits it as a separate JSON message with a distinct `$message_type` (for example `"future_incompat"`), which tools may consume or ignore.

When JSON output is not requested, the compiler does not print these suppressed diagnostics. Plain `rustc` usage is unchanged.

The compiler also includes, in each record, the lint name and the tracking issue number, so tools can group and link them.

## Cargo side

Cargo already invokes `rustc` with `--error-format=json` and parses its output. It will:

1. Collect every `future_incompat` message, keyed by package ID.
2. After the build finishes, if any were collected for packages other than the workspace members, print the short summary shown above.
3. Store the full set of diagnostics on disk under the target directory, keyed by a report ID. Only a limited number of recent reports are kept.
4. Add a `cargo report future-incompatibilities` subcommand that displays a stored report. With no `--id`, it shows the most recent one.
5. Add a `--future-incompat-report` flag to `cargo build` and similar commands that prints the full report right after the build.

Warnings from workspace members are not included in the summary, because they are already shown through the normal path unless the developer has silenced them on purpose.

Cached builds also need handling. If a dependency is not rebuilt because it is already fresh, Cargo must still know about its future-incompatibility warnings. Cargo already caches compiler output for replaying warnings, and the `future_incompat` records will be stored in the same cache.

## Configuration

A new config table `[future-incompat-report]` supports one key, `frequency`, with values `"always"` (default) and `"never"`.

# Drawbacks

- **Noise.** A developer who cannot do anything about a deep dependency may find a recurring notice annoying. The `frequency` setting, and keeping the notice to a single line, are meant to limit this.
- **Requires both compiler and Cargo changes.** The two must be designed together, and older compilers will not produce the new messages.
- **Disk usage.** Stored reports take space in the target directory, although each is small.

# Rationale and alternatives

**Show all dependency warnings.** Removing `--cap-lints` would be far too noisy.

**Rely on crater and manual outreach.** That is the status quo. It is expensive, and it misses private and git dependencies.

**Have crates.io flag affected versions.** This would help but would not cover git or path dependencies, and it would depend on server-side builds.

# Prior art

- npm prints deprecation notices for dependencies at install time.
- `pip` warns when installed packages declare incompatible requirements.

# Unresolved questions

- How long should reports be kept?
- Should the notice also appear for `cargo check`, or only for full builds?

# Future possibilities

- Automatically suggesting the minimal `cargo update` command that removes all warnings.
- Opening an issue on the upstream repository with the report contents, at the user's request.
