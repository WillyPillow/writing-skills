- Feature Name: `cargo_alternative_registries`
- Start Date: 2017-08-24
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Cargo can currently fetch dependencies from exactly one registry: crates.io. This RFC adds support for additional registries that run the same protocol as crates.io. A user can name a registry in Cargo configuration, depend on crates from it, and publish crates to it, while continuing to use crates.io for everything else. The main use case is a company or organization that runs a private registry for internal code but still depends on the open source ecosystem.

# Motivation

Many organizations write Rust code that they cannot or do not want to publish publicly. Today they have three options, and none of them is good:

1. **Git dependencies.** A crate can depend on `{ git = "https://internal/foo.git" }`. This works, but it loses semver resolution. Every consumer pins a branch, tag, or revision by hand, and Cargo cannot pick a compatible version when two crates in the graph both depend on `foo`.
2. **Path dependencies and monorepos.** This works when all code lives in one repository. It does not scale across teams that release independently.
3. **Source replacement.** Cargo's `[source]` configuration can replace crates.io with a mirror. A mirror can contain extra private crates, but the result is an all-or-nothing substitute: there is still only one logical registry, the organization has to mirror all of crates.io to add one private crate, and publishing to the mirror is not supported.

What users want is closer to how package managers in other ecosystems work: a private index for private packages, with the public index still available. Cargo's registry design already supports most of this. The index format is a git repository with a `config.json` that points to a download URL and an API URL. Nothing in that design assumes the registry is crates.io. What is missing is a way to name more than one registry and to say which registry a dependency comes from.

# Guide-level explanation

## Defining a registry

A registry is defined in `.cargo/config` (or any config file Cargo reads) under the `[registries]` table:

```toml
[registries]
my-company = { index = "https://git.example.com/rust/index.git" }
```

The key, `my-company`, is the name used elsewhere to refer to this registry. Registry names follow the same rules as crate names.

## Depending on a crate from a registry

A dependency gets a `registry` key to say where it comes from:

```toml
[dependencies]
serde = "1.0"
internal-auth = { version = "0.4", registry = "my-company" }
```

`serde` comes from crates.io, as before. `internal-auth` comes from `my-company`. Version resolution works the same way for both: Cargo reads the index for each registry and picks the newest version that satisfies the requirement.

The lock file records the source of each package, so `Cargo.lock` will contain entries like:

```toml
[[package]]
name = "internal-auth"
version = "0.4.2"
source = "registry+https://git.example.com/rust/index.git"
```

## Publishing

`cargo publish` and the other commands that talk to a registry API (`cargo yank`, `cargo owner`, `cargo login`, `cargo search`) take a `--registry` flag:

```
cargo login --registry my-company
cargo publish --registry my-company
```

Credentials are stored per registry in Cargo's credentials file:

```toml
[registries.my-company]
token = "..."
```

## Preventing accidental publication

A crate that contains private code should never be published to crates.io by mistake. The `publish` key in `Cargo.toml`, which today accepts only `true` or `false`, is extended to accept a list of registry names:

```toml
[package]
name = "internal-auth"
publish = ["my-company"]
```

`cargo publish` refuses to publish to any registry not on the list. An empty list is equivalent to `publish = false`.

# Reference-level explanation

## Index format

The index format is unchanged except for one addition. Each line in an index file describes one version of one crate, including its dependencies. Today a dependency entry has no source information because every dependency is assumed to come from the same registry as the crate itself. This RFC adds an optional `registry` field to each dependency entry, containing the index URL of the registry the dependency comes from. If the field is absent, the dependency comes from the same registry as the crate that declares it.

Using the index URL rather than the registry name in the published metadata matters. Registry names are local configuration; two users might call the same registry by different names. The URL is the stable identity.

When a crate is published, Cargo translates each `registry = "name"` in the manifest into the corresponding index URL before uploading.

## Cross-registry dependencies

A crate on a private registry may depend on crates from crates.io; that is the whole point. The reverse is restricted: crates.io will reject any crate whose dependencies come from another registry. A public crate that depends on a private one is unbuildable for everyone outside the organization, which would harm the public ecosystem. Other registries may set their own policies; the protocol allows any registry to reference any other.

## `config.json`

A registry's index already contains a `config.json` with `dl` and `api` keys. No new required keys are added. A registry that does not support publishing may omit `api`, and Cargo will report a clear error if a user tries to publish to it.

## Interaction with source replacement

Source replacement continues to work and applies to any registry, not only crates.io. A user can write:

```toml
[source.my-company]
registry = "https://git.example.com/rust/index.git"
replace-with = "my-company-mirror"
```

This lets organizations mirror private registries as well as public ones.

## Authentication for downloads

This RFC does not add authentication for fetching the index or downloading `.crate` files. The index is a git repository, so whatever authentication Cargo's git support already offers (SSH keys, credential helpers) applies. Downloads go to the `dl` URL over plain HTTP(S). Organizations that need authenticated downloads can put the registry behind a network boundary for now. Authenticated downloads are a natural follow-up but are not needed for a first version, and designing them well depends on experience with this feature.

## Registry name in the lock file

The lock file stores the index URL, not the registry name, for the same reason the index does. Changing the name of a registry in local config does not change the lock file.

# Drawbacks

- **More configuration surface.** Users have a new config table, a new dependency key, and a new form of the `publish` key to learn. Most users will never touch any of it, and the defaults are unchanged.
- **Name squatting across registries.** A crate called `foo` on a private registry and a different `foo` on crates.io are unrelated. A user who forgets the `registry` key gets the public one. The `publish` list helps on the publishing side but does nothing on the consuming side. In practice the version requirement and the lock file catch most mistakes, but not all of them.
- **No download authentication.** Some organizations will find the feature incomplete without it.

# Rationale and alternatives

**Extend source replacement instead.** We could allow a replacement source to fall back to crates.io for crates it lacks. This keeps the configuration smaller but makes resolution depend on which crates happen to exist where, which makes builds harder to reason about and opens the door to dependency confusion attacks. Naming the registry explicitly on each dependency avoids that.

**Put registry definitions in `Cargo.toml`.** That would make a project self-contained, but it would also put organization-specific URLs into every manifest. Keeping definitions in `.cargo/config` lets an organization configure them once, at the user or workspace level. A future RFC could allow manifest-level definitions if there is demand.

**Use the index URL directly in the dependency.** `registry-index = "https://..."` would avoid the need for a name. We support names because URLs are long and change when infrastructure moves. Supporting a URL form alongside names is left as a possible extension.

**Do nothing.** Organizations would keep using git dependencies, and the lack of real private package support would remain a common complaint from companies evaluating Rust.

# Unresolved questions

- Should Cargo ship a minimal reference registry server, or leave that to third parties? This RFC specifies only the client side.
- What is the exact error behavior when a lock file references a registry that is not configured locally?
- Should `cargo search` default to all configured registries, or only crates.io?
- How should authenticated downloads work, and should they block stabilization?
