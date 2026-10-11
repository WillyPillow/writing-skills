# Rust RFC 1969: Cargo patching sources and prepublishing crates

- Start Date: (draft)
- RFC PR: (pending)
- Rust Issue: (pending)

## Summary

This RFC proposes the concept of *patching sources* for Cargo. Sources can have their existing versions of crates replaced with different copies, and sources can also have "prepublished" crates by adding versions of a crate which do not currently exist in the source. Dependency resolution will work *as if* these additional or replacement crates actually existed in the original source.

## Motivation

Large Rust projects are often split across many crates that depend on one another. A change to a low-level crate may need to be tested against the crates that consume it before anything is published. Today, the usual approach is to point each dependent at a git branch or a local path, which requires editing manifests in several repositories and remembering to revert those edits before publishing.

This approach has several problems. Manifest edits are easy to forget, and a forgotten edit can publish a crate that refers to a local path, which crates.io will reject. Switching a dependency from a registry version to a git branch changes the dependency graph, so the test no longer exercises the exact resolution that users will see. Multi-crate changes that must land together are difficult to test as a unit, because each crate must be published or patched in an order that respects the graph.

The goal of this RFC is to let a developer test a set of coordinated changes without modifying the manifests of the dependent crates. The developer should be able to declare, in a single place, that a crate version should be taken from a different location or should be treated as existing even though it has not been published. Cargo should then resolve the graph as if the registry contained that version, and build and test the result.

Prepublication is the most ambitious use of this mechanism. It would let a team publish a crate in a private state, test it inside a realistic graph of consumers, and then publish the real version to crates.io once the test passes. The RFC considers this valuable enough to justify the design work, and recognizes that the feature also serves simpler needs such as overriding a single dependency with a local fork.

## Guide-level explanation

A user who wishes to test an unpublished change to a crate can add a patch entry to the workspace configuration. The entry names the source being patched, which is usually the crates.io registry, and gives the crate name and the replacement location. Cargo then uses the replacement wherever the original crate would have been used, including in transitive dependencies.

For prepublication, the user adds an entry that names a version which does not yet exist in the registry, and points it at the local copy. Cargo treats the version as available during resolution, so a dependent crate that requires that version will resolve to the local copy without any change to its manifest. The lock file records the resolution in the usual way, but the entry is marked so that a later attempt to publish the lock file will not leak the local location.

The user is expected to remove the patch entries once the change has been published. Cargo warns if a patch entry refers to a version that already exists in the registry, since the entry is then redundant and may be hiding a real update.

## Reference-level explanation

Cargo's configuration gains a section that maps a source to a set of replacement packages. Each replacement names a package, a version, and a source, which may be a path on the local file system or a git location. During resolution, when the resolver would consult the registry for a package, it first checks the replacement set. If a replacement matches the requested version requirement, the replacement is used in place of the registry entry.

Prepublished packages are handled by inserting the replacement's manifest into the resolver's view of the source before resolution begins. The resolver then sees the version as a candidate, with its declared dependencies, and includes it in the graph like any other version. The dependencies of the prepublished crate are themselves resolved against the same sources, so a chain of unpublished crates can be tested together.

The lock file records each resolved package along with its source. For a replacement, the source is recorded as the replacement location with a marker indicating that the package is a patch. The marker prevents the package from being published with a source that other users cannot reach. Cargo refuses to publish a crate whose lock file contains an unresolved patch marker for a dependency of the published crate, with an error that names the offending dependency.

When the build runs, Cargo compiles the replacement package as if it were a path dependency. Features, build scripts, and target-specific dependencies behave as they would for an ordinary dependency of the same source. Test and benchmark targets of the replacement package are built only when the workspace requests them.

The configuration may be placed in the workspace or in a user-level file. Entries in the user-level file apply to all workspaces, which is useful for developers who maintain forks of several crates, but Cargo emits a warning when a user-level entry overrides a workspace entry for the same package.

## Drawbacks

The feature introduces a second resolution path that differs from the one users see on crates.io. A build that succeeds with patches may fail once the patches are removed, if the patched code relied on behavior that the published version does not have. The RFC addresses this by recommending that prepublished versions be tested again after publication, but cannot enforce it.

The lock file gains a new marker, which tools that read lock files must understand. Older versions of Cargo would not understand the marker and would resolve the package from its recorded source, which may not be reachable. The RFC proposes that the marker be written in a form that older tools ignore gracefully, with a warning rather than a failure.

Prepublication also creates a risk of confusion about which version is real. A developer may see a version number in a dependency tree and assume it has been published, when it exists only on the local machine. The authors suggest that Cargo display the source of each package in the tree output, which would make this visible.

## Rationale and alternatives

The existing workaround of editing manifests is widely used, and the authors do not dispute that it works for small cases. The argument for a patching mechanism is that it moves the change into a single place and makes the temporary nature of the change explicit. Manifest edits are scattered and easy to forget, while a patch entry is a deliberate, reviewable statement that a particular source is being overridden.

An alternative is to rely on a separate local registry that mirrors crates.io and contains the prepublished versions. This avoids changes to Cargo, but it requires running and maintaining a server, and it still requires the dependent crates to point at the local registry, which means editing manifests or configuration in each consumer. The authors judge this to be more complicated than the proposed approach.

A second alternative is to use a workspace that contains all the crates, so that path dependencies resolve automatically. This works well within a single repository, but it does not help when the crates live in separate repositories with separate owners, which is common in the ecosystem.

## Prior art

Other package managers have supported overrides of this kind for some time. Some allow a dependency to be replaced by a local directory, and others allow a dependency to be pinned to a particular commit in a repository. The design here combines these ideas and adds the prepublication case, which the authors are not aware of being provided in the same form elsewhere.

## Unresolved questions

The authors list several questions for the implementation phase. The first is how the patch marker should be encoded in the lock file so that it is both clearly visible to humans and ignored safely by older tools. The second is whether a prepublished version should be allowed to satisfy a requirement that the registry would otherwise fail to meet, or only to add candidates alongside existing versions.

The third question concerns the interaction with yanked versions. A patch that replaces a yanked version may hide the fact that the version was withdrawn, and the authors suggest a warning rather than a silent replacement.

## Future possibilities

If prepublication proves useful, the tooling could be extended to publish a set of crates in dependency order automatically, after checking that each one passes tests in its patched graph. The mechanism could also be used to test a proposed change against a snapshot of the registry without publishing anything, which would support continuous integration for large ecosystems. These extensions are outside the scope of this RFC.
