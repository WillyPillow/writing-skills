# RFC 2834: Reporting upstream future-incompatibility warnings in Cargo

- Status: [TODO: status and tracking issue link]
- Number and title: [TODO: confirm the RFC number and final title; the draft is listed without them]

## Summary

Cargo should tell developers when an upstream dependency triggers a future-incompatibility warning. It should list such dependencies even when the warning has been suppressed, for example by `cap-lints` or by an `#[allow(..)]` attribute. Cargo may also give the downstream crate's maintainer feedback on how to address the problem. The specific steps for that feedback are not defined by this RFC.

## Motivation

A future-incompatibility warning tells the author of a crate that its code will stop compiling, or will change meaning, in a later compiler release. The author of the crate that uses it is usually not the person who can fix the problem. The upstream maintainer can fix it, but only if the downstream developer learns about it and passes the report on.

The obstacle is suppression. When an upstream crate suppresses its own warning, or the build caps the lint level, the warning never reaches the developer who would see it in their build output. The developer then has no signal that a dependency will break. [TODO: give a concrete case from the material, such as a crate that was broken by a later release after its warnings had been suppressed, or the number of crates affected.]

## Design

Cargo gathers the future-incompatibility reports of the dependency graph and lists the dependencies that emit them. The list includes dependencies whose warnings were suppressed, so the developer sees them even when the upstream crate chose to hide them.

The reason for including suppressed warnings is that suppression changes what the developer can see, not whether the code will break. A suppressed warning still predicts a future failure. Listing only unsuppressed warnings would leave the developer with the same blind spot the suppression created. [TODO: confirm this reasoning matches the authors' intent, and state whether any other reason applies.]

The RFC deliberately leaves the feedback for downstream maintainers unspecified. The tactics a downstream maintainer can use, such as pinning a version, opening an issue upstream, or applying a patch, depend on the crate and the situation. The RFC does not prescribe them. This is a non-goal: the message content is not part of this proposal. [TODO: state whether the authors plan a follow-up RFC for the content of that feedback.]

## Alternatives considered

[TODO: list the alternatives the authors considered. The material does not record them. Candidates to check with the authors include a separate report command, a flag that opt-in users set, and listing only unsuppressed warnings. Do not treat any of these as considered until the authors confirm it and give the reason it lost.]

## Cost accepted

Cargo will print more information during builds, and the information is about dependencies the developer may not control. [TODO: state how the extra output is presented, whether it appears during every build or only in a separate report, and whether the authors have measured its volume.]

## Reversibility

The output format of Cargo is not a language or ABI commitment, so the report can change later at lower cost than a stable public interface. [TODO: confirm whether any machine-readable form of the report is planned, because tools that parse it would make changes costly.]

## Rollout

[TODO: describe how the report is enabled, whether by default or behind a flag, and how it is turned off.]

## Open questions

- [TODO: decide how the feedback to downstream maintainers is worded and where it appears.]
- [TODO: decide whether suppressed warnings should be marked differently from unsuppressed ones in the list.]
