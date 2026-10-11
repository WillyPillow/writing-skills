- Feature Name: N/A (experimental RFC)
- Start Date: 2017-08-25
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

This is an **experimental RFC**. It sets out a plan for making Cargo work better inside other build systems and environments: Bazel, Buck, Meson, CMake, distribution packaging tools like Debian's and Nix, and the in-house build systems of large companies. Accepting it permits landing unstable Cargo features to try out the ideas below. It does not permit stabilizing any of them. Each feature will need its own RFC before it can be stabilized, informed by what we learn.

The features fall along a spectrum. At one end, a user keeps Cargo in charge but overrides one decision, such as where a dependency comes from or how a native library is found. At the other end, an external build system does almost everything and uses Cargo only to read manifests and resolve dependencies.

# Motivation

Cargo was designed for a world where Cargo is the build system. For most Rust projects that is true and it works well. But Rust is increasingly used in places where something else is already in charge:

- **Large monorepos.** Companies with Bazel or Buck want Rust to be one more language in a single build graph, with the same caching, remote execution, and hermeticity guarantees as their C++ and Java code. They cannot let Cargo download from the network or decide on its own where outputs go.
- **Linux distributions.** Debian, Fedora, and others package each crate separately, build offline from source packages they have vetted, and need control over which version of each dependency is used. They also want to link against system libraries rather than vendored copies.
- **Mixed-language projects.** Firefox, for example, builds C++ and Rust together. Its build system needs to call into Cargo for the Rust parts while controlling compiler flags, targets, and output locations.
- **Embedded and unusual targets.** Projects that need to build `core` or `std` themselves, or use custom linkers and toolchains, often work around Cargo rather than through it.

Each of these communities has built workarounds: scripts that generate `Cargo.toml` files, tools that parse `cargo build -v` output to extract `rustc` command lines, vendoring tools, and so on. These workarounds are fragile because they depend on details Cargo never promised to keep stable.

We do not yet know the right design for all of these needs. That is why this is an experimental RFC: we want to ship prototypes behind unstable flags, let these communities try them, and come back with stabilization RFCs once the designs have settled.

# Guide-level explanation

The plan is organized around the things an external build system might want to control. For each, we describe the rough shape of the feature we expect to prototype.

## 1. Where dependencies come from

Cargo already supports source replacement and vendoring. We want to extend this so a build system can say "every crate comes from this local directory, never touch the network," and have Cargo fail clearly if something is missing. We also want to support multiple versions of a crate side by side in a local source, which distributions need.

## 2. How native dependencies are found

Today `-sys` crates use build scripts that probe for system libraries with `pkg-config` or by searching paths. An external build system often already knows exactly where each library is and how to link it. We want a declarative way to override a build script's output:

```toml
[target.x86_64-unknown-linux-gnu.openssl]
rustc-link-lib = ["ssl", "crypto"]
rustc-link-search = ["/opt/openssl/lib"]
```

Cargo already has a version of this. The plan is to make it more complete and to let a crate declare, in its manifest, which native library it provides, so that overrides can be applied by library name rather than by crate.

## 3. What the build plan is

A build system that wants to drive `rustc` itself needs to know what Cargo would have done. We propose an unstable `--build-plan` flag that, instead of building, prints a JSON description of every compiler invocation Cargo would make: the inputs, the outputs, the arguments, the environment variables, and the dependencies between steps. An external tool can then translate the plan into its own rules.

Build scripts complicate this, because their output can change later steps. The build plan will mark build script outputs as dynamic, and the external tool will be responsible for running them and applying their results. Figuring out how well this works in practice is one of the main goals of the experiment.

## 4. Where outputs go

Cargo decides the layout of `target/`. Build systems that need hermetic, content-addressed outputs want to choose those paths. We will prototype an `--out-dir` flag for final artifacts and investigate a more general mechanism for intermediate files.

## 5. Which compiler and flags are used

Cargo already reads `RUSTC`, `RUSTC_WRAPPER`, and `RUSTFLAGS`. These are blunt: `RUSTFLAGS` applies to every crate. We will prototype per-crate and per-profile flag control, and a supported way to declare that a custom `rustc` wrapper is responsible for caching.

## 6. Building the standard library

Some targets have no prebuilt `std`. We will prototype letting Cargo build `core`, `alloc`, and `std` from source as ordinary dependencies, with the same overrides available as for any other crate.

## 7. Cargo as a library or metadata service

`cargo metadata` already prints the resolved dependency graph. We will extend it with the information external tools most often have to scrape from elsewhere: features enabled per crate, target-specific dependencies after resolution, and build script presence.

# Reference-level explanation

Because this is an experimental RFC, it deliberately does not specify formats or flag names in detail. Each feature will be developed under a `-Z` flag or a `cargo-features` manifest key and will carry a tracking issue that links back here.

The Cargo team will apply a few constraints to every prototype:

- **No change to default behavior.** A user who does not opt in should see no difference.
- **Prefer data over hooks.** Where possible, Cargo should describe what it would do (build plans, metadata) or accept a description of what to do (overrides), rather than calling out to arbitrary user code at many points. Data formats are easier to stabilize and to support across versions.
- **Keep Cargo's own model intact.** Features should let external systems integrate with Cargo's notions of packages, features, profiles, and targets, not replace them. A crate should build the same way whether it is built by Cargo or by an external tool driven by Cargo's output.
- **Gather feedback from real users.** Each prototype should have at least one external project trying it before a stabilization RFC is written.

# Drawbacks

Unstable features cost maintenance even if they are never stabilized. Several of these features touch core parts of Cargo (the resolver, the compilation pipeline, the layout of `target/`), and prototypes there can slow down other work.

There is also a risk that external tools come to depend on unstable features and pressure the Cargo team to stabilize designs that are not ready. We will be explicit in documentation that these features may change or be removed.

# Rationale and alternatives

**Write a full design RFC now.** We considered specifying each feature in detail up front. We do not think we know enough. The needs of Bazel users, distribution packagers, and Firefox overlap but are not the same, and a design that looks right on paper could easily miss a constraint that only shows up in use.

**Leave integration to third parties.** Tools like `cargo-vendor` and `cargo-raze` show that a lot can be done outside Cargo. But each of them reverse-engineers behavior Cargo does not guarantee, and they break when Cargo changes. Some things, such as a build plan, can only be produced reliably by Cargo itself.

**Tell these users to use `rustc` directly.** Some do. They lose the crate ecosystem's conventions (features, build scripts, profiles) and have to reimplement dependency resolution. This splits the ecosystem.

# Unresolved questions

Essentially everything about the concrete designs is unresolved, by intent. Some questions we especially want the experiments to answer:

- Can a static build plan handle real-world build scripts, or do we need a richer protocol between Cargo and the external system?
- How should features be resolved when an external system builds only part of a dependency graph?
- What is the right granularity for overriding native dependencies: per crate, per library name, or per target?
- Which of these features should eventually be stable, and which should stay as escape hatches with weaker guarantees?
