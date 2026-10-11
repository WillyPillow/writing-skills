# Rust RFC 2136: Cargo and Build System Integration

- Feature Name: `build_systems`
- Start Date: 2017-08-21
- RFC PR: rust-lang/rfcs#2136
- Rust Issue: N/A

## Summary
[summary]: #summary

This **experimental RFC** lays out a high-level plan for improving Cargo's ability to integrate with other build systems and environments. As an experimental RFC, it opens the door to landing [unstable features] in Cargo to try out ideas, but *not* to stabilizing those features, which will require follow-up RFCs. It proposes a variety of features which, in total, permit a wide spectrum of integration cases, from customizing a single aspect of Cargo to letting an external build system run almost the entire show.

[unstable features]: https://github.com/rust-lang/cargo/blob/master/src/doc/unstable.md

## Motivation
[motivation]: #motivation

Cargo is the standard way to build Rust code. For the large majority of projects, it is all that is needed, and its conventions provide a smooth experience. But Rust is increasingly used in contexts where Cargo is not the top-level build tool. Examples include:

- Large companies with monorepos, where a single build system such as Bazel, Buck, or Make builds code in many languages, and where hermetic, cacheable builds are essential.
- Operating system distributions, which package software through their own build infrastructure and want precise control over where sources come from, how they are compiled, and where outputs go.
- Embedded and cross-compilation setups, in which the toolchain or sysroot is produced by another system.
- Projects that mix Rust with C, C++ or other languages, where some other tool is the natural driver for the whole build.

In each of these cases, users today face a choice between two unpleasant options. They can use Cargo as a black box, accepting that it will fetch dependencies, choose compiler flags, and decide on output locations without their input. Or they can bypass Cargo entirely and invoke `rustc` directly, reimplementing the parts of Cargo they need: dependency resolution, feature unification, build script handling, and so on. The second path means those users lose access to the ecosystem's conventions, and often end up duplicating a large amount of subtle logic.

The goal of this RFC is to carve out a middle ground. Cargo should expose the pieces it is good at as separable, well-defined steps, so that an external system can take over the pieces it wants while Cargo handles the rest.

## Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

The proposal is organized around the observation that integration needs fall along a spectrum. We describe the features starting at the lightest touch and moving to the heaviest.

### Customizing a single aspect: `rustc` wrappers and build plans

At the lightest end, a user wants Cargo to build things as usual but to run something different or additional at some step. Cargo already supports a `RUSTC` environment variable. This RFC proposes a more general `RUSTC_WRAPPER`, which causes Cargo to invoke the given program with the real compiler invocation as arguments. A wrapper can add flags, cache results, distribute compilation, or log invocations.

For somewhat more control, Cargo gains an unstable `--build-plan` flag. Passing it to `cargo build` causes Cargo to emit a JSON description of what it would do, a graph of compiler and build script invocations with their inputs, outputs and dependencies, without running anything. An external tool can consume the plan and execute it itself, taking care of scheduling and caching.

### Replacing dependency resolution: vendoring and lockfile-driven builds

In the middle of the spectrum, a user wants to keep Cargo's dependency resolver and manifest conventions but control where code comes from. Cargo already offers `cargo vendor`-like functionality through source replacement. This RFC proposes making the pieces more composable: an unstable `cargo metadata` extension that includes the full resolved graph with source locations and enabled features, so that an external tool can reproduce what Cargo would have built.

### Taking over: a library interface to Cargo

At the heavier end, some systems want to call Cargo's logic programmatically rather than as a subprocess. The `cargo` crate already exists, but its API is not stable and is not designed for consumers. The RFC proposes to identify a small number of entry points (resolving a workspace, generating a build plan, and running a single compilation unit) and experiment with stabilizing them as a separate crate or crates.

### Build scripts

Build scripts (`build.rs`) are a major obstacle to integration, because they are arbitrary programs that run at build time and communicate with Cargo through `cargo:` directives printed on stdout. An external build system needs to know what a build script will do in order to schedule it and model its outputs.

The RFC proposes exploring a way to separate "running the build script" from "interpreting its output." With such a split, an external system could run build scripts in its own sandbox, capture their directives, and feed the result back into the rest of the build.

## Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

None of the features below are to be stabilized by this RFC. Each is to be developed behind `-Z` flags, in the unstable features list, and documented as subject to change.

### `RUSTC_WRAPPER`

When `RUSTC_WRAPPER` is set, Cargo invokes `$RUSTC_WRAPPER $RUSTC <args>` in place of `$RUSTC <args>`. If the wrapper is empty, the variable is ignored. This is similar to how `ccache` is used with C compilers.

### `--build-plan`

`cargo build -Z unstable-options --build-plan` prints a JSON document to stdout and exits. The document has the following shape:

```json
{
  "invocations": [
    {
      "package_name": "foo",
      "package_version": "0.1.0",
      "target_kind": ["lib"],
      "deps": [0, 1],
      "outputs": ["target/debug/libfoo.rlib"],
      "links": {},
      "program": "rustc",
      "args": ["--crate-name", "foo", "..."],
      "env": {},
      "cwd": "/path/to/foo"
    }
  ],
  "inputs": ["/path/to/foo/Cargo.toml"]
}
```

The `deps` field refers to indices of other invocations. Build script invocations appear as ordinary entries, with their `links` recording the outputs the script is expected to produce. Because a build script's real output is known only after it runs, the plan may be incomplete; a consumer is expected to run the build script and then ask Cargo for the remainder of the plan.

### Metadata extensions

`cargo metadata` gains fields describing the resolved dependency graph in more detail: the feature set enabled for each package, the path of its manifest, and the identity of its source. Some of this is already available; the work consists of making it consistent and documenting its stability.

### Library interface

A new crate, provisionally named `cargo-lib`, will be created as a thin facade over a portion of Cargo's internals. The contents are not specified here. Experimentation will determine what is feasible.

## Drawbacks
[drawbacks]: #drawbacks

- Every new integration point is a new compatibility promise once stabilized, and it increases the maintenance burden on the Cargo team.
- There is a risk of fragmentation. If many projects bypass Cargo's default workflow, the community's shared conventions might weaken, and tooling written for Cargo might not work for those projects.
- The scope is large. An experimental RFC with a wide remit can drift without a clear endpoint.

## Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**Do nothing.** Users with integration needs continue to reimplement Cargo, or live with it as a black box. This is the status quo and the source of complaints.

**Provide one big hook.** A single mechanism, for example, "let an external program decide everything," would be simpler to specify but too coarse. Most users want to change one thing.

**Stabilize immediately.** Without experience, the Cargo team would risk locking in designs that do not fit real use. Marking everything experimental, and requiring follow-up RFCs for stabilization, allows learning first.

## Unresolved questions
[unresolved-questions]: #unresolved-questions

- What is the right granularity for the build plan? Per-crate, per-target, or per-compiler invocation?
- How should incremental compilation state be represented to an external system?
- How should build script outputs, especially those that depend on the environment, be modeled so that external systems can cache them?
- Which, if any, of these features should be accessible without a nightly compiler?
- How do we measure success? The proposal is to work with several concrete integrators (a monorepo build system and a distribution packager) and to ask them to report on their experience.
