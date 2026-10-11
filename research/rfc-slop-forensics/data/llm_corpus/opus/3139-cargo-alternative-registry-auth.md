- Feature Name: `cargo_alternative_registry_auth`
- Start Date: 2021-03-31
- RFC PR: [rust-lang/rfcs#3139](https://github.com/rust-lang/rfcs/pull/3139)
- Tracking Issue: [rust-lang/cargo#10474](https://github.com/rust-lang/cargo/issues/10474)

# Summary

Let Cargo send the registry authorization token with every request to a registry, including API calls, crate downloads, and index fetches over HTTP. A registry opts in by adding a field to the `config.json` at the root of its index.

# Motivation

Cargo supports alternative registries: package registries other than crates.io, configured in `.cargo/config.toml`. Many organizations run them to host internal crates that cannot be published publicly.

Today Cargo sends the registry token only for operations that modify the registry: `publish`, `yank`, `owner`, and similar API calls. Reading from the registry, which means fetching the index and downloading `.crate` files, is always anonymous.

This works for crates.io, where all content is public. It does not work for a private registry, whose whole point is that not everyone can read it. Registry operators currently have three unsatisfying options:

1. **Network-level access control.** Put the registry behind a VPN or firewall. This is coarse, does not distinguish between users, and is awkward for CI systems and remote developers.
2. **Credentials in the URL.** Embed a token in the download URL template in `config.json` or in the index URL. Every user of the index then shares one credential, which cannot be revoked per user, and the credential ends up in lock files, logs and shell history.
3. **Git credentials for the index plus unauthenticated downloads.** The index can be protected with git's own credential mechanisms, but the download endpoint is still open to anyone who can guess a crate name and version.

None of these give per-user, revocable read access, which is what registry operators and their security teams expect from every other package ecosystem.

The introduction of the sparse HTTP index protocol makes this more pressing: an HTTP index has no equivalent of git credential helpers, so without Cargo-level authentication there is no way to protect it at all.

# Guide-level explanation

A registry that requires authentication for all requests adds `"auth-required": true` to its `config.json`:

```json
{
    "dl": "https://registry.example.com/api/v1/crates",
    "api": "https://registry.example.com",
    "auth-required": true
}
```

Users configure the registry and log in as they already do:

```toml
# .cargo/config.toml
[registries.example]
index = "sparse+https://registry.example.com/index/"
```

```console
$ cargo login --registry example
please paste the token found on https://registry.example.com/me below
```

From then on, Cargo includes the token in the `Authorization` header of every request it makes to that registry: index files, crate downloads and API calls.

If a user has not logged in, Cargo reports an error that names the registry and tells them to run `cargo login --registry example`, instead of failing with a bare HTTP 401.

# Reference-level explanation

## Index configuration

The registry's `config.json` gains an optional boolean field `auth-required`. When absent or `false`, behaviour is unchanged. When `true`:

- Every HTTP request Cargo makes to the index URL, the download URL (`dl`), or the API URL (`api`) includes `Authorization: <token>`.
- Cargo never sends the request without a token. If no token is available, Cargo stops with an error before sending anything.

## Bootstrapping: fetching `config.json` itself

For a sparse HTTP index, `config.json` is itself a file served by the protected endpoint. Cargo cannot know whether to send a token before reading it.

Cargo first requests `config.json` without credentials. If the server responds `401 Unauthorized`, Cargo retries with the token if one is configured. If the retry succeeds and the returned config has `auth-required: true`, Cargo uses the token for all subsequent requests. If the server responds `401` and no token is configured, Cargo reports that the registry requires authentication.

The server may include a `WWW-Authenticate: Cargo login_url="..."` header on the 401 response. Cargo shows the URL in its error message so the user knows where to obtain a token.

For git indexes, authentication of the clone or fetch continues to use git's mechanisms. The `auth-required` field controls only the download and API requests.

## Download URL templates

The token is sent as a header. It is never interpolated into the URL. This avoids leaking it into `Cargo.lock`, proxy logs or error messages.

## Redirects

Download endpoints commonly redirect to a CDN or object store with a pre-signed URL. Cargo does not forward the `Authorization` header across a redirect to a different origin. Registries that redirect must therefore produce redirect targets that do not require the token, such as short-lived signed URLs.

## Credential sources

The token comes from the same places it does today: `CARGO_REGISTRIES_<NAME>_TOKEN`, `credentials.toml`, or a credential provider. This RFC does not change how tokens are stored.

## Cache and offline behaviour

Downloaded crates and cached index entries are stored locally as before. `--offline` mode uses the cache and never needs a token.

## `cargo publish` to a different registry

When a crate depends on a crate from an auth-required registry, `cargo publish` to that same registry works as usual. Publishing to crates.io with a dependency from a private registry is already disallowed.

# Drawbacks

- Sending the token on every request expands its exposure. A compromised index server or misconfigured proxy now sees the token more often. Registries should issue read-scoped tokens, and the asymmetric token work in a later RFC reduces this risk further.
- The 401-then-retry bootstrap adds a round trip for the first request to a protected registry.
- Registries must implement header-based authentication on their download endpoints, which some static file hosts cannot do without a proxy in front.

# Rationale and alternatives

**A flag in the user's Cargo config instead of `config.json`.** Every user would have to set it, and a user who forgot would send unauthenticated requests and get confusing failures. The registry knows whether it requires authentication, so it should say so.

**Always send the token if one is configured.** Simpler, but it would send crates.io tokens (which grant publish rights) on every crates.io download, needlessly increasing exposure. Opt-in per registry limits the token to registries that need it.

**Credentials in URLs.** Rejected for the leakage reasons above.

# Prior art

- **npm** sends a bearer token configured per registry on every request when the registry is private.
- **pip** supports per-index credentials via URLs or keyring and sends them on every request to that index.
- **Maven** and **NuGet** configure credentials per repository and send them on every request.

All of these treat reading from a private repository as an authenticated operation, as this RFC does.

# Unresolved questions

- Should Cargo support different tokens for read and write operations on the same registry?
- Should `auth-required` be honoured for git indexes' download URLs before the sparse protocol is stable?

# Future possibilities

- Asymmetric tokens, where Cargo signs each request with a private key rather than sending a bearer secret, would remove the exposure concern.
- Credential provider plugins for platform keychains and corporate SSO.
