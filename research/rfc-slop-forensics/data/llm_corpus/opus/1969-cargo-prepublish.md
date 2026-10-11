- Feature Name: `prepublish`
- Start Date: 2017-03-27
- RFC PR: rust-lang/rfcs#1969
- Rust Issue: rust-lang/rust#41532

# Summary

This RFC introduces *patching sources* in Cargo. A project can replace the existing versions of a crate in a source with a different copy, and can add versions of a crate that the source does not yet contain. Dependency resolution then proceeds *as if* those replacement or additional crates existed in the original source.

The main use is to "prepublish" a crate to crates.io. Prepublication allows integration testing across a large crate graph before anything is published, without switching dependencies from crates.io to git branches. To a degree it simulates an atomic change across many crates and repositories, which can then be published for real, one crate at a time, once it is known to work.

# Motivation

Consider a common situation. A maintainer of the `xml-rs` crate fixes a bug and wants to know whether the fix resolves a problem reported by users of a higher-level crate, say `servo`, that depends on `xml-rs` through two or three intermediate crates. To test the fix in context, the maintainer has a few options today.

**Publish and hope.** Publish a new version of `xml-rs` and run `cargo update` in the downstream project. If the fix is wrong, the broken version is now public and permanent.

**Rewrite dependencies to git.** Change each intermediate crate's `Cargo.toml` to depend on `xml-rs` through a git URL, then change the top-level project to depend on each intermediate crate through git too. This is a lot of edits across repositories, all of which must be undone later. It also changes the source of every crate in the chain, so the dependency graph no longer looks like the one users will get from crates.io.

**Use `[replace]`.** Cargo's existing `[replace]` section lets the top-level project substitute one specific version of a crate with another copy. This avoids touching intermediate crates, but it is limited: the replacement must have exactly the same version as the crate it replaces. That works for testing a patch to version `0.10.3`, but not for testing a new `0.11.0` that has not been published yet, which is what happens whenever a fix requires a minor or major version bump. `[replace]` also requires naming the exact version being replaced, which is awkward when the graph contains several.

**Use `paths` overrides.** The older `.cargo/config` `paths` mechanism is similar to `[replace]` in its limitations and is not checked into the project.

None of these support the case of a coordinated change, for example a breaking change in a core crate together with matching updates in five dependents, each in its own repository, all to be tested together before any is released.

# Guide-level explanation

A new section is added to `Cargo.toml`:

```toml
[patch.crates-io]
xml-rs = { path = "../xml-rs" }
```

This says: when resolving dependencies against crates.io, pretend that the crate at `../xml-rs` is also available on crates.io. If its version is `0.10.4`, which is not yet published, any dependency on `xml-rs = "0.10"` anywhere in the graph can now resolve to it. Because `0.10.4` is newer than any published `0.10.x`, it will be chosen, as long as the lock file allows an update.

If the local crate has version `0.11.0`, then dependencies on `xml-rs = "0.10"` are unaffected, and dependencies on `xml-rs = "0.11"`, which might be introduced by a local patch to an intermediate crate, resolve to the local copy. This is how a coordinated breaking change is tested:

```toml
[patch.crates-io]
xml-rs = { path = "../xml-rs" }           # now 0.11.0
xml5ever = { path = "../xml5ever" }       # updated to depend on xml-rs 0.11
```

The key after `patch` names the source being patched. `crates-io` refers to the default registry. A git URL can also be patched:

```toml
[patch."https://github.com/example/repo"]
foo = { path = "../foo" }
```

Patches can point to a path or a git repository. They are honored only in the top-level workspace, just as `[replace]` is. A library's `[patch]` section is ignored when it is used as a dependency, so publishing a crate with a `[patch]` section does not affect its users.

Once testing is done, the maintainer publishes `xml-rs`, then each dependent in order. As each crate is published, its `[patch]` entry can be removed. Since the patched graph had the same shape as the graph that crates.io will produce, the final result is the one that was tested.

# Reference-level explanation

## Resolution

During resolution, Cargo queries a source for the candidate versions of each crate name. With `[patch]`, Cargo wraps the source so that the query returns:

1. All versions from the original source, except any version for which a patch supplies a crate with exactly the same name and version, in which case the patched copy takes its place.
2. Every patched crate whose version does not exist in the original source.

The resolver is otherwise unchanged. A patched crate is selected only if it satisfies some dependency's version requirement and the usual preference for newer versions picks it. If a patch is never selected, Cargo emits a warning, since an unused patch usually means a version mismatch the user did not intend.

## Lock file

Patched crates are recorded in `Cargo.lock` with their patch source, so a subsequent build without changes uses the same crates. Removing a `[patch]` entry causes the corresponding locked crate to become unavailable, and Cargo re-resolves just that part of the graph as it does today when a path dependency disappears.

## Relationship to `[replace]`

`[patch]` is strictly more capable than `[replace]` for the cases this RFC addresses. `[replace]` remains supported. Its documentation will recommend `[patch]` for new uses. A future RFC may deprecate it.

## Errors

- Patching a crate with a different name than the key is an error.
- Patching a source that the workspace does not use is a warning.
- Two patches for the same name and version in the same source is an error.

# Drawbacks

This adds a third override mechanism alongside `paths` and `[replace]`. Users will have to learn which to use. The documentation must be clear that `[patch]` is the recommended one.

Patches make it easy to build a project with crates that do not exist anywhere public. A team that forgets to remove its `[patch]` section may ship a binary built from unpublished code. This risk already exists with path dependencies, and the unused-patch warning helps a little, but it does not go away.

# Rationale and alternatives

**Extend `[replace]`** to allow version mismatches. The semantics of "replace" make it hard to explain why the replacement can have a different version than the thing it replaces. "Patching a source" is a clearer model: the source looks the same as before, with some extra or different entries.

**A staging registry.** crates.io could offer a staging area where unreleased crates are uploaded but not visible to the public. This would be useful but is a much larger service-side change, and would not help with sources other than crates.io.

# Unresolved questions

- Should `[patch]` be permitted in `.cargo/config` for local, uncommitted overrides, replacing `paths`?
- Should Cargo offer a command that publishes a chain of patched crates in dependency order?
