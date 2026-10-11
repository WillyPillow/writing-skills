- Feature Name: `cargo_alternative_registry_auth`
- Start Date: 2021-03-31
- RFC PR: [rust-lang/rfcs#3139](https://github.com/rust-lang/rfcs/pull/3139)
- Tracking Issue: [rust-lang/cargo#10474](https://github.com/rust-lang/cargo/issues/10474)

# Summary
[summary]: #summary

Enables Cargo to include the authorization token for all API requests, crate downloads and index updates (when using HTTP) by adding a configuration option to `config.json` in the registry index.

# Motivation
[motivation]: #motivation

Organizations that want to keep their code private often run their own crate registry rather than publishing to crates.io. In many cases these registries require authentication for every request, not only for publishing. A company with proprietary libraries has no wish to let anyone on the internet download them, and no wish to let anyone enumerate the names and versions of its crates either.

Cargo's alternative registry support, stabilized in 1.34, only attaches the authentication token to a subset of requests. The token is sent for operations that are defined in terms of the web API: publish, yank, unyank, owner changes and search. It is not sent when Cargo:

- downloads the `.crate` file for a dependency,
- fetches the index, which for a git-based registry is performed by git using its own credentials, and for the sparse HTTP protocol is performed by Cargo itself.

For the git index, authentication is handled out of band by the git credential system. This works but requires a registry to run a git server in addition to its web API and downloads server, which is a significant operational cost. A registry that wants to use the new sparse HTTP index protocol cannot require authorization at all, because the index requests would arrive without a token.

The workarounds in use today are unsatisfactory. Some organizations put the registry behind a VPN, which restricts developers working from home or on CI services outside the network. Others use custom `.netrc` or `http.extraheader` configuration applied through the HTTP proxy settings of Cargo, which is not discoverable, is not scoped to the registry, and leaks credentials to other hosts if misconfigured. Others use a git `insteadOf` rewrite to embed credentials in the URL, which are then visible in logs and in `Cargo.lock`.

By letting a registry declare that it requires authentication on all requests, and by letting Cargo send the token it already holds, the full range of private-registry deployments is supported without out-of-band configuration.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

If you are an organization running a private registry, you can require users to authenticate for every request by setting `auth-required` in the registry's `config.json`:

```json
{
    "dl": "https://crates.example.com/api/v1/crates/{crate}/{version}/download",
    "api": "https://crates.example.com",
    "auth-required": true
}
```

When Cargo reads this file, it learns that the registry wants a token on every request, and it will send one when it:

- fetches index files over the sparse HTTP protocol,
- downloads a crate,
- calls any web API endpoint, including search and the endpoints used for publishing.

The token is the one you have configured already. You can obtain it with `cargo login --registry my-registry`, which stores it in `$CARGO_HOME/credentials.toml`, or provide it via the `CARGO_REGISTRIES_MY_REGISTRY_TOKEN` environment variable or through a credential provider.

Using such a registry as a developer requires nothing more than what you do today:

```toml
# .cargo/config.toml
[registries.my-registry]
index = "sparse+https://crates.example.com/index/"
```

```toml
# Cargo.toml
[dependencies]
internal-lib = { version = "1.2", registry = "my-registry" }
```

If you have not logged in, Cargo reports a clear error:

```
error: failed to download from `https://crates.example.com/index/in/te/internal-lib`

Caused by:
  authentication required: registry `my-registry` requires a token for all requests.
  Run `cargo login --registry my-registry` to configure one.
```

Registries that do not set `auth-required` behave exactly as before, and in particular crates.io is unaffected.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## `config.json`

A new optional boolean field, `auth-required`, is added to the registry's `config.json`. Its default is `false`. When `true`, Cargo attaches an `Authorization` header with the registry token to:

1. index requests made over the sparse HTTP protocol, including the request for `config.json` itself;
2. crate download requests, both to the URL in `dl` and to any redirect target that has the same origin as the registry;
3. web API requests, including those that already carry the token.

The `config.json` file is the one place where the field cannot be discovered by Cargo before making a request. To resolve the circularity, Cargo behaves as follows when fetching the index for the first time:

1. It sends a request for `config.json` without a token.
2. If the server responds with `401 Unauthorized` or `403 Forbidden`, Cargo retries the request with the token if one is available, and otherwise reports the missing-token error above. The registry's index server is therefore expected to answer an unauthenticated request for `config.json` with a `401` and a `WWW-Authenticate: Cargo login_url="https://crates.example.com/me"` header, where `login_url` is an optional URL at which the user can obtain a token. Cargo shows it to the user in the error message.
3. If the server responds successfully, Cargo reads `auth-required` from the file and caches it, in the registry's index cache directory, with the index data. For subsequent requests the value read is used without the first unauthenticated attempt.

A registry that sets `auth-required` but serves `config.json` openly is allowed; Cargo will still attach the token to later requests. This is useful to registries that want users' tools to be able to discover the setting without credentials.

## Credential scope

The token is sent only to the host and scheme of the registry's index URL, `dl` URL, and `api` URL. If a download redirects to another host, for example to a CDN or object store with pre-signed URLs, the token is not forwarded. This rule is the same as that applied by common HTTP clients to the `Authorization` header and prevents tokens leaking to third parties.

If the `dl` URL is on a different host from the index, the token is still sent there, since the registry declared it. Registry operators must understand that the `dl` host receives the token and should apply the same trust to it as to the registry itself.

Cargo refuses to send tokens over plain `http://` URLs unless the host is a loopback address, in which case development registries on localhost are supported. This check already exists for `cargo publish`; it is generalized to the new cases.

## Git-based indexes

For registries using a git index, the field is not meaningful for index updates, since git performs the fetch. If `auth-required` is set, Cargo still sends the token for downloads and API calls. Authentication of git operations continues to be through git's credential helpers, as today.

## Interaction with `Cargo.lock` and offline mode

No change is made to `Cargo.lock`. The checksum of each package continues to be recorded, so no token or credential-bearing URL is included in the lockfile. In `--offline` mode, no requests are made and no token is needed, as long as the index data and `.crate` files are cached.

## Interaction with `cargo vendor` and `cargo fetch`

`cargo fetch` and `cargo vendor` perform downloads through the normal paths and therefore send the token. No special handling is needed.

# Drawbacks
[drawbacks]: #drawbacks

- The design relies on a field that Cargo cannot know before its first request. The fallback via a `401` response mitigates that, but registry operators must implement the challenge correctly.
- Sending tokens on more requests slightly expands the set of places a token can leak. The scope rules above restrict this.
- Operators serving the index from a static file host (for example an object store) must now add authentication on the host side, which may be nontrivial. The sparse index is cache-friendly, but authenticated responses are harder to cache in shared proxies.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**Always send the token.** Cargo could attach the token to every request to an alternative registry. This avoids a new field but would send credentials to registries that do not want or expect them, and some servers reject unrecognized Authorization headers or behave differently. An explicit opt-in is safer.

**A per-user configuration option.** Users could set `auth-required = true` in their own `config.toml`. This puts the burden on every developer and breaks when the registry's policy changes. The registry is the right owner of this decision.

**HTTP-level negotiation only.** Cargo could rely solely on `401` responses, retrying with a token. This requires a wasted round trip for every request and does not work with servers that return `404` to hide existence of private resources. Declaring `auth-required` lets Cargo send the token proactively.

**Out-of-band credential helpers.** Cargo could rely on the git credential system or a new credential provider protocol for everything. This is complementary and is being designed separately; it does not remove the need for Cargo to know when to attach credentials.

# Prior art
[prior-art]: #prior-art

npm supports `always-auth` in `.npmrc`, which makes the client send the token on every request to a registry, including tarball downloads. Maven repositories use per-repository credentials in `settings.xml`, applied to all operations on that repository. Pip supports credentials in index URLs and via keyring integration. Cargo's approach, with the registry declaring the policy, is closest to npm's but moves the decision to the server.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

- Should the name of the field be `auth-required` or something more general, to allow future values such as a scheme specifier?
- Should Cargo support a distinct, lower-privilege token for read-only requests?
- What should happen if a registry changes `auth-required` from `false` to `true` while clients hold a cached `config.json`? The expected behaviour is that clients receive a `401` and refresh the cached value.

# Future possibilities
[future-possibilities]: #future-possibilities

The `WWW-Authenticate` challenge could carry additional parameters, such as the authentication scheme or the token endpoint, to enable credential providers that exchange short-lived tokens. A later RFC could also add support for signed requests rather than bearer tokens.
