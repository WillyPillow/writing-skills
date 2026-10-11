# RFC 1969: Cargo Prepublish

- Feature Name: `prepublish`
- Start Date: 2017-04-28
- RFC PR: rust-lang/rfcs#1969
- Rust Issue: N/A

## Summary

This RFC proposes the concept of *patching sources* for Cargo. Sources can have their existing versions of crates replaced with different copies, and sources can also have "prepublished" crates by adding versions of a crate which do not currently exist in the source. Dependency resolution will work *as if* these additional or replacement crates actually existed in the original source.

One primary feature enabled by this is the ability to "prepublish" a crate to crates.io. Prepublication makes it possible to perform integration testing within a large crate graph before publishing anything to crates.io, and without requiring dependencies to be switched from the crates.io index to git branches. It can, to a degree, simulate an "atomic" change across a large number of crates and repositories, which can then actually be landed in a piecemeal, non-atomic fashion.

## Motivation

Large Rust projects are rarely a single crate. A typical project is a graph of dozens of crates, some in one repository and some in several, each published separately to crates.io. A change that spans several of these crates has an awkward workflow.

Suppose crate `A` depends on `B`, which depends on `C`, and a developer wants to add a feature to `C` that `B` and then `A` will use. To test the whole chain, they must:

1. change `C` and publish it, or point `B` at a git branch of `C`;
2. change `B` to use `C`, again publishing or pointing at a git branch;
3. change `A`, and finally run its tests.

Publishing early is hard to undo. Crates.io is immutable, so a crate version that turns out to be wrong can only be yanked and superseded, and in the meantime others may have picked it up. Using git branches avoids that, but requires editing the dependency declarations of every crate in the chain, and then editing them again when the real versions are published. The result is a stream of churn commits and a high likelihood of forgetting to revert one.

Cargo's existing `[replace]` section addresses part of this problem. It lets a dependency graph substitute one crate for another, matching on an exact name and version. The substitute must have the same version number as the one it replaces and must exist in the original source. That is precisely the constraint that makes it unsuitable here: to test a new API, one needs a *new* version, and no such version exists yet in the registry.

The aim of this RFC is to let developers describe, in a single place, a set of local versions that should stand in for or supplement a registry, and have the resolver treat them as authoritative.

## Detailed design

### The `[patch]` section

A new top-level section is added to `Cargo.toml`:

```toml
[patch.crates-io]
foo = { path = "../foo" }
bar = { git = "https://github.com/example/bar", branch = "fix" }
```

The table key after `patch` names a source. The name `crates-io` refers to the default registry; any other source is named by its URL, in quotes:

```toml
[patch."https://github.com/example/index"]
baz = { path = "../baz" }
```

Each entry under a source has the same form as a normal dependency declaration with a path, a git URL, or a registry specification, and names a crate that will be available from that source in addition to, or in place of, what the source actually contains.

### Semantics

For the purposes of resolution, each patch entry is added to the patched source as if the source itself had published it. The effect depends on the version of the patch:

- **Prepublishing.** If the patch's version does not exist in the source, it is added as a new candidate. Any dependency on the source whose version requirement matches it may select it. A patch at `0.3.0` makes `foo = "0.3"` resolvable even if the registry has only `0.2.9`.
- **Replacement.** If the patch has the same version as an existing crate, it shadows the original; the resolver chooses the patched copy.

Crucially, the patch participates in ordinary version selection. It is not forced into the graph: if nothing depends on a matching version, it goes unused, and Cargo emits a warning to that effect. The rule is that the resolver must act *as if* the crates existed in the source from the beginning.

This is different from `[replace]` in three ways. The version need not already exist. The patch is matched by the normal requirement rules rather than an exact version string. And a patch applies to every dependent in the graph consistently, so there is no risk of two copies of the same crate with unified APIs being compiled into the same program.

### Where patches apply

Patches are honored only from the root of the workspace. A `[patch]` section in a dependency's manifest is ignored, since otherwise any crate on crates.io could redirect the resolution of its dependents. Only the top-level project, which is the one being built, decides how its sources are modified.

The lock file records the effect of patches. A package that was resolved from a patched copy is listed with its true source (the path or the git URL), and a `[[patch.unused]]` table notes patches that did not match anything, so that subsequent builds are reproducible and the unused-patch warnings are stable.

### Example workflow

Consider the earlier scenario. The developer clones `C` and `B` next to `A`, and writes in `A`'s manifest:

```toml
[patch.crates-io]
b = { path = "../b" }
c = { path = "../c" }
```

Now `C` is edited and bumped to `0.5.0`. In `B`'s manifest the dependency is changed to `c = "0.5"`; since `B` is itself patched, its own `[dependencies]` are read normally. `A` builds against the local copies, the whole test suite runs, and nothing was published. When all is well, `C` is published, then `B`, then `A`, each in turn. After each publication, the corresponding `[patch]` entry is deleted (or left, harmlessly, as an unused patch).

At no point were the dependency declarations in `B` or `A` changed to point to git. The only temporary edit is the patch table at the top-level project.

### Crates.io interaction

When publishing a crate to crates.io, a `[patch]` section in the manifest is not included in the uploaded package, and is not considered by the verification build. Verification proceeds against what crates.io really contains. Cargo publishes only what would be correct for end users.

This is why the feature is called "prepublish": the patches simulate the future state of the registry while leaving the real registry untouched.

### Cargo.lock considerations

A lock file produced with patches differs from one produced without them. If a project is intended to be built by others, patches are typically removed before committing the lock file. For projects that use patches long-term, such as an application vendoring a fork, the lock file and the `[patch]` table are committed together, and it is the user's responsibility to keep them consistent.

## Drawbacks

The new section adds to Cargo's configuration surface and, along with `[replace]`, provides two overlapping mechanisms. Documentation must explain when to use which. The longer-term plan is to deprecate `[replace]` in favor of `[patch]`, which covers its use cases and more.

There is a risk of misuse: a developer might leave patches in place for a published binary and build artifacts that do not correspond to any release. The unused-patch warning and the omission of patches from published packages mitigate, but do not eliminate, the issue.

The semantics also introduce the possibility of confusing resolutions. If the registry has `1.2.0` and the patch has `1.1.9`, the resolver will pick `1.2.0` for a requirement of `1.1`, ignoring the patch. This is faithful to the "as if published" model but may surprise users who expected the patch to win.

## Alternatives

**Extend `[replace]`** to allow differing versions. This would blur its simple meaning, and the exact-match semantics are relied upon by existing users.

**Use `path` overrides** in `.cargo/config`. These are the existing mechanism for local crates, but they are limited to crates whose version matches, are not recorded in the lock file, and are invisible in the project manifest.

**A workspace-wide virtual registry.** More powerful, but requires a substantial new subsystem and a specification of the registry format for local use.

## Unresolved questions

Whether patches should be allowed to name a crate that is absent from the source entirely, as opposed to a new version of an existing one. Whether `cargo publish` should warn when a patch is present. And what exactly the diagnostics for an unused patch should say, since the cause is often a version mismatch that the user must discover by inspection.
