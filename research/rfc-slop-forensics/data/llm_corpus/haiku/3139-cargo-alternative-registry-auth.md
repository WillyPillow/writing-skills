- Feature Name: `cargo_alternative_registry_auth`
- Start Date: 2022-03-14
- RFC PR: [rust-lang/rfcs#3139](https://github.com/rust-lang/rfcs/pull/3139)
- Cargo Issue: [rust-lang/cargo#10519](https://github.com/rust-lang/cargo/issues/10519)

# Summary

Enable Cargo to send the authorization token for every request it makes to an alternative registry. The requests covered are API calls, crate downloads, and index updates when the index is accessed over HTTP. The behaviour is controlled by a new option in the `config.json` file that each registry publishes at the root of its index. When the option is set, Cargo attaches the registry's token to all of these requests, not only to publish calls.

# Motivation

Alternative registries allow organizations to host crates privately. A company that keeps its internal crates behind authentication needs Cargo to present credentials not only when a crate is published, but also when it is downloaded and when the index is read. Without this, the registry must either allow anonymous access to all of its contents or sit behind a network boundary that is set up outside Cargo.

The current behaviour is inconsistent. Cargo already sends the token for publishing and for a few other API calls. For downloads and index reads, it does not, and a private registry therefore cannot be used through the normal dependency workflow without extra configuration. Teams have worked around the problem with proxies, custom scripts, and vendoring, each of which adds maintenance cost and introduces its own risks.

A registry operator who wants to restrict access to a subset of users needs a way to say so in a form that Cargo understands. The registry's index is the natural place for this statement, because Cargo reads it first and because it describes the registry as a whole.

# Guide-level explanation

A registry that requires authentication for all of its contents publishes a field in the `config.json` file at the root of its index. The field tells Cargo that every request to the registry should carry the token. When a user has configured a token for that registry, Cargo includes it in the authorization header of each request.

From the point of view of a user, nothing changes in the commands they run. They add the registry to their configuration, provide the token in the usual way, and then use the crates from it as they would use crates from the public registry. The difference is that the token is now used for everything the registry serves, and Cargo does not need a separate step.

The option is off by default. Registries that do not set it continue to behave as they do today. This means that the change cannot break an existing public registry, and that operators can adopt the option when they are ready.

Users should understand that the token is sent to the registry on every request, including requests for crate files. They should therefore only configure tokens for registries they trust. Cargo will not send a token to a registry for which no token has been configured, and it will not send a token to a different host from the one named in the registry's configuration.

# Reference-level explanation

The index of an alternative registry contains a file named `config.json`. The file has a set of keys that describe where the registry's download URL and API URL are located. This RFC adds one optional boolean key to that file. The key is named `auth-required` in the current design, and when it is `true`, Cargo must send the token for every request to the registry.

When Cargo reads the configuration of a registry that has the key set to `true`, it marks the registry as requiring authentication. Before making a request to the index, to the download URL, or to the API URL, Cargo checks this mark. If the mark is set and a token is configured for the registry, Cargo attaches the token to the request in the same header that it uses for publishing. If no token is configured, Cargo reports an error that names the registry and explains how to add a token.

The index is read over HTTP in the sparse protocol, and over git in the older protocol. The RFC applies only to the HTTP case, because the git protocol has its own authentication mechanisms that are handled by the git client. For the git protocol, the behaviour is unchanged.

Cargo must not send a token to a URL that is not on the same host as the registry's configured index URL. This check is made after URL normalization and before the request is constructed. A registry that serves its download URL from a different host must set a separate option to allow the token to be sent there, and the design of that option is covered in the unresolved questions below.

The token is sent in the authorization header, using the same format that Cargo already uses for publishing. No new header format is introduced.

# Drawbacks

Sending a token on every request increases the exposure of the token. A token that is leaked from a log or from a proxy could be used to read the private crates as well as to publish them. Cargo must therefore avoid printing the token in verbose output, and it must redact the header when it logs requests.

The option adds one more key to a file whose format is already relied upon by many registries. Operators must learn a new key, and tools that generate `config.json` must be updated to write it when needed.

There is a risk that a registry operator sets the option incorrectly, so that a public registry requires a token it does not need. The error messages must make clear that the problem is in the registry configuration, not in the user's token.

# Rationale and alternatives

The main alternative is to continue to rely on external proxies and on network controls. This keeps Cargo simple but makes the private registry model depend on infrastructure that many teams cannot run. It also means that the security properties of the registry are not visible to Cargo, so users cannot see from their own configuration whether a registry is protected.

A second alternative is to send the token on every request whenever one is configured, without any option in the index. This is simpler, but it would send tokens to public registries that never asked for them, and it would change the behaviour of existing setups. The explicit option avoids both problems.

A third alternative is to add a separate configuration setting in the user's Cargo configuration rather than in the index. This would let each user decide, but it would place the responsibility for the security of the registry in the hands of each user, when the registry operator is the one who knows what is required.

# Prior art

Package managers in other ecosystems handle private registries in varied ways. Some send credentials with every request by default, and others require a separate authentication step for each kind of access. The approach taken here is closer to the second group, because it keeps the decision with the registry and lets users opt in through their configuration.

Cargo already has a mechanism for registries that need credentials for publishing. The present proposal extends that mechanism to the other request types, and it reuses the existing header format and the existing token storage.

# Unresolved questions

The name of the option has not been settled. The name used in this document is a proposal, and the final choice should follow the naming conventions of the existing keys in the registry configuration.

The handling of registries whose download URL is on a different host from the index needs a design of its own. The RFC proposes that such a registry must list the additional host explicitly, but the exact form of that list has not been decided.

It is also unclear how the option interacts with credential providers that refresh tokens during a session. The proposal assumes that the token is read once per invocation, and this assumption should be checked against the credential provider design.

# Future possibilities

Once the option is in place, Cargo could support more fine-grained permissions, so that a token can be limited to read access for downloads while allowing publishing only with a different token. This would make it safer to hand out read-only credentials to build systems.

The same mechanism could be extended to the git protocol, if the git authentication story becomes more uniform across platforms. For now the git protocol is outside the scope of this RFC.
