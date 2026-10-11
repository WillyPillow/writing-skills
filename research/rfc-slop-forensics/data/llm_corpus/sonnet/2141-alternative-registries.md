# Rust RFC 2141: cargo_alternative_registries

- Feature Name: `cargo_alternative_registries`
- Start Date: 2017-09-01
- RFC PR: rust-lang/rfcs#2141
- Rust Issue: rust-lang/rust#44931

## Summary
[summary]: #summary

This RFC proposes support for alternative crates.io-style servers ("registries") that can be used alongside the public crates.io server. Users will be able to publish crates to their own private registry while continuing to depend on crates from the public one. Cargo will gain a way to name registries in configuration, a way to refer to them from dependency declarations, and a way to publish to them.

## Motivation
[motivation]: #motivation

Many organizations write Rust code that cannot or should not be published to the public crates.io. The code may be proprietary, may depend on internal infrastructure, or may simply not be useful outside the company. These organizations still want the benefits that the crate ecosystem gives open source developers: semantic versioning, a central place to find libraries, reproducible builds from a lockfile, and a simple `cargo publish` workflow.

Today the options are poor. A team can use `path` dependencies, but these require every consumer to check out the sources in a matching layout. A team can use `git` dependencies, but these have no notion of version resolution, so Cargo cannot pick a compatible release from a range. A team can use a local "directory source" or a source replacement, but source replacement is designed to mirror an existing registry, not to host additional crates with their own namespace.

What these teams want is a second registry, with the same index format and the same web API as crates.io, that they host themselves. The index format and the API are already documented, and the `crates.io` server software is open source, so the missing piece is purely in Cargo: it has no way to talk to more than one registry, and it has no way to record in a manifest which registry a given dependency comes from.

A secondary motivation is mirroring and vendoring. Organizations behind restrictive networks sometimes need to point Cargo at a locally hosted copy of crates.io. That case is already covered by source replacement and is out of scope here, but the design below is intended to compose with it.

## Detailed design
[detailed-design]: #detailed-design

### Registry definitions

Registries are defined in Cargo's configuration files (`.cargo/config`) in a new `[registries]` table. Each entry has a name and a URL pointing at the registry's index:

```toml
[registries]
my-registry = { index = "https://my-intranet:8080/index" }
other = { index = "https://example.com/other-index" }
```

The name is local to the machine or project that defines it. It is not part of the registry itself, and two developers may use different names for the same registry. Because of this, names are never recorded in published package metadata (see below).

The existing `crates.io` registry remains the default and needs no definition. The name `crates-io` is reserved for it and cannot be redefined.

Configuration files are merged in the usual hierarchical way, so an organization can distribute a shared `.cargo/config` checked into a repository root, and individual developers can override it.

### Credentials

Publishing requires an API token. `cargo login` currently stores a single token for crates.io. This RFC extends it with a `--registry` flag:

```
cargo login --registry my-registry
```

Tokens are stored in the credentials file, keyed by registry name:

```toml
[registries.my-registry]
token = "..."
```

The `CARGO_REGISTRY_TOKEN`-style environment variables are likewise extended with a per-registry form. The exact environment variable naming is left as an implementation detail.

### Dependencies

A dependency may now carry a `registry` key naming a configured registry:

```toml
[dependencies]
serde = "1.0"
internal-lib = { version = "0.3", registry = "my-registry" }
```

If `registry` is omitted, the dependency is resolved from crates.io, exactly as today. A dependency that names a registry must also specify a `version`, as it would for crates.io.

Resolution treats each registry as a distinct source. A crate `foo` in `my-registry` and a crate `foo` in crates.io are different packages, even if they share a name and version. The resolver already identifies packages by name, version, and source, so no new concept is required here, but the lockfile must record the source URL of every package. It already does so for registry packages; this RFC only requires that it distinguishes between registries by their index URL.

### Publishing

`cargo publish` gains a `--registry` flag:

```
cargo publish --registry my-registry
```

Additionally, a package can restrict where it may be published by setting the `publish` key in its manifest:

```toml
[package]
name = "internal-lib"
version = "0.3.0"
publish = ["my-registry"]
```

The existing `publish = false` form continues to mean "never publish." When `publish` is a list, `cargo publish` will refuse to upload to any registry not in the list. When the key is absent, publishing is allowed to any registry, subject to the rules below. This gives teams a guard against accidentally uploading proprietary code to the public crates.io.

### Metadata sent to the registry

When Cargo uploads a package, it sends the registry a JSON document describing the package and its dependencies. Because registry names are local, Cargo cannot send the name `my-registry` for a dependency. Instead, the upload metadata gains a `registry` field per dependency containing the index URL of the dependency's registry, or null for crates.io. Registries that do not understand the field may ignore it.

For the same reason, the dependency entries recorded in the index also gain a `registry` field holding the index URL. A consumer reading the index of `my-registry` will therefore see exactly which registry each dependency came from, and Cargo can resolve it without consulting the consumer's local names.

### Restrictions on crates.io

The public crates.io must continue to be a self-contained, reproducible ecosystem. A crate published to crates.io may only depend on other crates in crates.io. If a package that depends on an alternative registry is uploaded to crates.io, the server rejects it. Cargo performs a matching client-side check to give a clearer error before the upload.

Alternative registries have no such restriction. A package in a private registry may depend on packages from crates.io, from itself, and from other registries.

### Unstable rollout

The feature will be implemented behind an unstable flag, `-Z unstable-options` together with the `alternative-registries` feature in the manifest, until it has been exercised in practice. Stabilization will proceed through the normal process.

## How We Teach This
[how-we-teach-this]: #how-we-teach-this

The Cargo book gains a chapter on alternative registries covering the configuration table, `cargo login --registry`, the `registry` dependency key, and `cargo publish --registry`. The key idea is that a registry is just "another crates.io" with a name local to your configuration.

The error message when publishing a crate that depends on an alternative registry to crates.io should explain why: crates.io packages must be resolvable by anyone without extra configuration.

## Drawbacks
[drawbacks]: #drawbacks

- Local names mean a manifest is not self-describing. A dependency saying `registry = "my-registry"` cannot be resolved without the matching configuration. This is the price of keeping URLs out of manifests, and it is a deliberate trade.
- Index and API implementors must handle one new field. Because it is optional, this should be backward compatible.
- Teams can fragment their dependency graphs across several registries, increasing the number of places a security advisory must be checked.

## Rationale and Alternatives
[alternatives]: #alternatives

**Put the index URL directly in the manifest.** This avoids the need for configuration but embeds infrastructure details into every `Cargo.toml`. Moving a registry to a new host would then require editing every manifest in the organization. Named registries allow the URL to change in one place.

**Use source replacement.** Source replacement substitutes one source for another wholesale. It cannot express "use crates.io for most things, and this other server for these particular crates," which is the core requirement.

**Use `git` dependencies with tags.** This lacks version resolution and does not integrate with `cargo publish`.

**Make names global.** A central naming authority for registries would make manifests self-describing but would introduce governance cost and a single point of failure, which is contrary to the purpose of private registries.

## Unresolved Questions
[unresolved]: #unresolved-questions

- Should credentials support external helper programs, similar to Git credential helpers, rather than plain text in the credentials file?
- Should there be a way to set a default registry for `cargo publish` for a given project, so that `--registry` need not be passed every time?
- How should `cargo search` and `cargo install` select a registry? This RFC specifies flags for the former but leaves `cargo install` for follow-up work.
