# Rust RFC 2141: cargo_alternative_registries

- Feature Name: `cargo_alternative_registries`
- Start Date: 2016-08-24
- RFC PR: (to be assigned)
- Rust Issue: (to be assigned)

## Summary

This RFC adds support to Cargo for alternative package registries that run alongside the public crates.io index. A user should be able to publish crates to a registry that their organization operates, consume crates from that registry, and continue to consume crates from crates.io in the same project without any special bookkeeping. The design keeps the existing crates.io experience as the default and adds a small, explicit configuration surface for everything else.

## Motivation

Many teams write Rust code that cannot, or should not, be published to the public index. Some crates contain proprietary logic. Others depend on internal tooling that outside users cannot reach. Still others are useful only to a single company and would clutter the public namespace. Today these teams have two poor options. They can vendor every dependency into their repository, which makes updates painful and breaks normal dependency resolution, or they can run a mirror and hand-edit configuration on every machine.

Neither option scales. Vendoring duplicates code and loses the version semantics that Cargo provides. Hand-edited mirrors drift, and they force every developer and every continuous integration job to share the same ad hoc setup. What is missing is a first-class notion of a registry other than crates.io, one that Cargo understands, names, and can authenticate against.

The goal of this RFC is modest. It does not try to rebuild the crates.io protocol or to define a universal package format. It asks Cargo to accept a second, third, or Nth index, to resolve dependencies against it when told to, and to publish to it on request. A private registry that implements the same index and download conventions as crates.io should work with no changes to a user's workflow beyond a line in a configuration file.

## Guide-level explanation

A project that uses a private registry declares it in a `.cargo/config.toml` file, either in the project or in the user's home directory. The declaration gives the registry a short name and points at its index:

```toml
[registries.corp]
index = "https://crates.corp.example/git/index"
```

A dependency then selects the registry explicitly:

```toml
[dependencies]
billing-core = { version = "1.4", registry = "corp" }
serde = "1.0"
```

Dependencies without a `registry` key continue to resolve against crates.io, so existing manifests are unaffected. A crate may depend on crates from several registries at once. Cargo keeps the index caches separate, so a lookup in one registry never shadows a crate of the same name in another.

Publishing works the same way. The command `cargo publish --registry corp` uploads the package to the named registry. Because the registry is named in the configuration, the token needed to authenticate can also be stored there, and it does not need to appear in the project. Users who do not have credentials for a registry will see a clear error when Cargo tries to fetch from it, rather than a confusing failure during resolution.

A registry may also be declared as the default for publishing. In that case, a bare `cargo publish` targets it. Crates.io remains the default for consumption, so the common case of pulling public dependencies is unchanged.

## Reference-level explanation

### Configuration

Registries are declared in a `[registries]` table. Each entry has a name, which must be a valid identifier, and an index URL. The index may use either the git protocol or the sparse HTTP protocol. The configuration may also contain a `token` key, which is used for publishing and for fetching from private indices. Tokens found in project-level files are rejected unless the user passes an explicit flag, to prevent credentials from being committed by accident.

Cargo resolves the set of known registries by merging the user configuration with the project configuration. Project entries may add registries but may not silently redefine the index URL of an existing name, because doing so would let a checked-out repository redirect a trusted name to a different server.

### Resolution

When resolving a dependency, Cargo consults the index of the registry named in the manifest. The version requirement is evaluated against that index only. Cargo does not fall back to another registry when a version is missing, since such fallback would make builds depend on which indices happen to be reachable. If a named registry cannot be reached, the build fails and reports which registry was involved.

The lock file records the registry alongside the source of each package. A lock file produced by one configuration can therefore be read by another, provided the named registries are defined. Lock file entries for crates.io are written in the same form as before, so existing lock files need no migration.

### Publishing

`cargo publish` gains a `--registry` flag. The package manifest must not list crates.io as a dependency's registry if the package itself is destined for a private registry, and Cargo rejects a manifest that would publish a crate depending on a registry the target cannot serve. This check is intentionally conservative. It prevents the common mistake of publishing a crate whose dependencies exist only on a private server.

Packages are uploaded through the same web API that crates.io exposes. A registry that implements this API is compatible with Cargo's publish command. Registries that do not implement the full API may support consumption without publishing, and Cargo treats that case as an ordinary read-only registry.

### Crates.io as a special case

Crates.io keeps its built-in name and remains the default for every operation that does not name a registry. Its index URL is not stored in user configuration, so that changing the configuration cannot accidentally point the default at a different server.

## Drawbacks

Adding multiple registries adds configuration surface and a new class of errors. A user who names the wrong registry will get a failure that looks like a missing crate. The team must also operate the registry, including its authentication, storage, and availability. Cargo can make the failures clearer, but it cannot remove the operational work.

There is a security cost as well. Each additional registry is a source of code that Cargo will compile and run during builds. Users must trust the operators of every registry they name, and the lock file helps only after a version has been resolved once. This RFC does not attempt to solve signature verification or supply-chain attestation, which are better addressed in separate work.

## Rationale and alternatives

One alternative is to make every registry a git repository and let users point dependencies at a URL. This is already possible through the `git` source, but it does not support the version resolution, yanking, and publishing semantics that the index provides. A git dependency pins a commit rather than a version range, so it cannot participate in a normal dependency graph.

A second alternative is a global mirror setting that transparently redirects crates.io to a local server. Mirrors are useful, but they change the meaning of every dependency at once and cannot express a crate that exists only in the private registry. This RFC is complementary: a mirror remains a valid deployment choice for a registry that wishes to cache the public index.

A third alternative is to require each private registry to be a complete copy of crates.io. That would be expensive and would prevent teams from mixing public and private crates cleanly. The design here instead keeps the registries independent and lets a project choose which one serves each dependency.

## Prior art

Several language ecosystems already support multiple package sources, typically through a per-dependency or per-package source declaration. Teams using those ecosystems often report that the explicit form is easier to audit than a global redirect, because the manifest itself records where each package came from. The proposal here follows that pattern.

## Unresolved questions

The exact shape of the publish API for private registries is not yet settled. This RFC assumes a compatible subset of the crates.io web interface, but it does not specify how authentication tokens are scoped, how yanking propagates between registries, or whether a registry may serve a crate under a name that collides with a crate on crates.io. These questions are deferred to the stabilization report.

## Future possibilities

Once named registries exist, Cargo can offer richer policy controls. A project might allow only certain registries for certain dependencies, or require that every dependency come from an approved source. Tooling could also audit the lock file to report which registries a build depends on. These features are outside the scope of this RFC but become natural extensions once the basic mechanism is in place.
