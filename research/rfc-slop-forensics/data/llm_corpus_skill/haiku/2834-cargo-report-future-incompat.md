# Rust RFC 2834: [TODO: title; the material gives "N/A"]

Document type: Rust language/tooling RFC
Status: [TODO: RFC status and tracking details]

## Context and scope

Cargo builds a package together with its dependencies. Some compiler warnings are future-incompatibility warnings, which report code that a later Rust release will reject. A crate's author can suppress such a warning with `cap-lints` or with `#[allow(..)]` attributes. The `cap-lints` setting limits the lint level applied to a dependency.

This RFC concerns what Cargo reports. Cargo should alert a developer to upstream dependencies that trigger future-incompatibility warnings, and should list those dependencies even when the warnings were suppressed.

## Motivation

[TODO: A concrete obstacle from the author. Give one case in which a developer could not see a future-incompatibility problem because the upstream crate suppressed the warning, and the consequence for that developer. The abstract states the goal but no case.]

## Goals

- Cargo reports upstream dependencies that trigger future-incompatibility warnings.
- Cargo reports these dependencies even when their warnings are suppressed through `cap-lints` or `#[allow(..)]`.
- [TODO: How a user would verify the second goal, such as a test project in which a warning is suppressed upstream.]

## Non-goals

- Specifying the tactics that a maintainer of a downstream crate could use to address the problem. The RFC does not specify these tactics and does not mandate them.

The RFC says that Cargo "could additionally provide feedback" on such tactics. That feedback is outside this RFC. [TODO: Whether the author plans it for a later RFC.]

## Design

Cargo lists each upstream dependency that triggers a future-incompatibility warning. The list includes dependencies whose warnings were suppressed.

[TODO: Where the list appears, its format, and whether it appears on every build or only on request.]

[TODO: How Cargo detects that a warning was suppressed, and whether suppressed and unsuppressed dependencies appear differently in the output.]

## Alternatives considered

[TODO: Alternatives the author weighed. A reviewer might ask whether reporting only unsuppressed warnings would meet the goal. The author should say whether that option was considered and why it was not chosen. Do not present it as considered until the author confirms.]

## Cost

[TODO: What reporting suppressed warnings costs. The author should state whether it adds output for every build, and whether it exposes dependencies whose authors chose to silence a warning.]

## Reversibility

[TODO: Whether the output format and the reporting behavior are expected to stay stable. If other tools parse this output, changing it later is expensive, and the author should say so.]

## Rollout

[TODO: How the change ships, and whether a user can turn the reporting off.]

## Open questions

- [TODO: Questions the author wants reviewers to address.]
