# Rust RFC 2834: Cargo report future-incompat

## Summary

Cargo should alert developers to upstream dependencies that trigger future-incompatibility warnings. It should list such dependencies even when the warnings have been suppressed, for example through `cap-lints` or an `#[allow(..)]` attribute. Cargo could also give the maintainer of the downstream crate feedback on tactics to address the problem. This RFC does not specify or mandate those tactics.

## Motivation

A future-incompatibility warning tells a developer that code compiles today and is expected to stop compiling in a later compiler release. The warning exists so that the developer can fix the code before the break. The warning works only if the developer sees it.

The developer who sees it is often the wrong one. Consider a crate `app` that depends on a crate `util` from a registry, and `util` contains a construct that triggers a future-incompatibility lint. The author of `app` did not write that construct and cannot change it. Cargo normally limits the lint level for dependencies from a registry, so `rustc` does not print the warning when `app` builds. [TODO: confirm the exact mechanism and which dependency kinds Cargo caps, such as registry, git and path dependencies.] The author of `util` sees the warning only if they build `util` with their own settings and read the output.

The suppression has two sources, both named in the abstract.

1. A `cap-lints` setting passed to the compiler, which limits every lint in a crate to a maximum level, in practice to "allow" or "warn".
2. An `#[allow(..)]` attribute in the source, which the crate author may have added for any reason, including to silence this warning.

In both cases the compiler may not produce the warning, so Cargo has nothing to relay. A report that depends on the visible warning would miss the cases where the problem is hardest to find. This is why the abstract asks for the listing "even when" the warnings are suppressed.

The consequence is a delayed failure. The first sign is a compile error after a compiler upgrade, in a crate the developer has not touched, at a time the developer did not choose. [TODO: the author should supply a real instance from the Rust project, such as a lint that was turned into a hard error and the number of crates affected. No such data was available for this draft.]

## Guide-level explanation

After a build, Cargo prints a note when at least one dependency in the build graph triggered a future-incompatibility lint. The note lists each affected dependency by name and version, and says which lint fired.

Here is a sketch of the note. It is an illustration of the information the RFC requires, not a format the RFC specifies. [TODO: the author should decide whether a format is specified here or left to implementation.]

```text
note: the following packages contain code that will be rejected by a future
      version of Rust: util v0.3.1
```

A developer who sees this note can do one of three things: update the dependency, report the problem to its maintainer, or replace it. The RFC is only about telling the developer that the choice exists.

For a maintainer who is releasing a crate, the same information is more actionable. The maintainer can see that their own crate triggers the lint for downstream users and fix it before users get stuck. [TODO: the author should say whether the report also covers the root package of a build, since the abstract speaks of "upstream dependencies".]

The abstract adds that Cargo could suggest ways to address the problem. Possible content includes naming the lint, linking to the explanation of the lint, or suggesting a newer version of the dependency that no longer triggers it. The RFC does not say which of these Cargo provides and does not require any of them. The suggestions are mentioned in the abstract as optional ("could"), and this document keeps them optional.

## Reference-level explanation

The RFC needs two pieces of behaviour. The compiler must report that a future-incompatibility lint would fire, independent of the configured lint level. Cargo must collect these reports from every crate in the build and show them to the user.

[TODO: the author should describe the interface between `rustc` and Cargo. The abstract gives no detail on whether the compiler emits a structured message, a separate file or a flag. This is the central technical question of the RFC, and the draft cannot answer it from the material.]

[TODO: the author should say what happens to the report for cached crates. If Cargo skips compiling a dependency because the build artifact is fresh, no compiler run produces a report, and the note would disappear on the second build.]

The listing must satisfy these rules, which follow from the abstract:

1. A dependency appears in the listing whenever a future-incompatibility lint applies to its code, regardless of `cap-lints` or `#[allow(..)]`.
2. The listing does not depend on the level at which the lint is otherwise reported.
3. The listing names the dependency so that the developer can find it in the dependency graph.

## Drawbacks

A report that ignores `#[allow(..)]` overrides a choice of the crate author. An author who allowed the lint on purpose, for example because a workaround is planned, now sees the lint reported to all downstream users. Downstream users in turn see a note they cannot act on. [TODO: the author should say whether any opt-out exists, and whether the author considers the override acceptable.]

The note adds output to every build that includes an affected dependency. Developers who see it every time and cannot fix it may learn to ignore it. [TODO: the author should state what the RFC does to keep the note from becoming noise, such as showing it once per dependency version.]

The RFC adds a communication path between the compiler and Cargo. The cost of that path in compile time, if any, is not measured. [TODO: measurement or an explicit statement that it is unknown.]

## Rationale and alternatives

The reason for the RFC is that the lint's audience, the people who can change the code, is not the audience that sees the message. Moving the message to Cargo puts it where the dependency is known by name.

Alternatives below are suggestions for the author to evaluate. They are not alternatives the author has recorded as considered.

- Stop capping lints for dependencies, so that `rustc` prints the warning in the normal way. This needs no new reporting path, but it prints every lint of every dependency, not only the future-incompatibility ones, and it does not cover `#[allow(..)]`.
- Run a separate command, outside the build, that re-checks dependencies at a higher lint level. This puts the cost on the developer who has to remember to run it, and the abstract's goal is that the alert reaches developers without that step.
- Leave the problem to the ecosystem, so that the compiler team finds affected crates by building a large set of them before changing a lint. [TODO: the author should say whether this process exists and what it covers.]

## Prior art

[TODO: the author should list comparable features in other build tools or package managers, such as deprecation notices in package registries, with citations. None were supplied.]

## Unresolved questions

- How does the report behave for cached builds? [TODO]
- Which dependency kinds are covered: registry, git, path, build dependencies and proc macros? [TODO]
- Should the report be available in machine-readable form for tools that run on top of Cargo? [TODO]
- Does the RFC require any tactic text at all? The abstract says the tactics are neither specified nor mandated, so the implementation team decides.

## Future possibilities

Cargo could later link the report to a published advisory for each lint. This is outside the abstract and is listed only to mark the direction. The RFC does not depend on it.
