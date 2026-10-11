# Rust RFC 2052: Epochs

**Type:** Language / Tooling
**Status:** Proposed
**Area:** Language, Tooling, Ecosystem

## Summary

This RFC proposes that the Rust project publish a named *edition* every two or three years. An edition is identified by the year in which it is released, for example "2030". Each edition gathers a set of stabilized features, a polished user experience around them, updated tooling, and a guide that explains the changes. The project would not break existing code to make an edition. Instead, the edition gives users and the community a shared point to aim for when they upgrade, document their work, and teach the language.

## Motivation

Rust moves quickly. The compiler gains features, the standard library grows, the formatter and the linter learn new rules, and the documentation is revised. This is a sign of a healthy project, but it makes the language hard to follow for people who are not working on it every day. A developer who last looked at Rust a year ago may find that the advice they remember is partly out of date, and may not know which of the new features are ready to use.

The project already has a stable release train, which ships a new compiler every six weeks. That train is valuable for delivering fixes and for keeping users close to the current state of the tools. It does not, however, provide a coherent story about what has changed in a given period. Release notes list many items with equal weight. Important changes can be buried in a long list of small ones, and related features that arrive in different releases are hard to see as a group.

An edition offers a way to tell that story. It bundles changes that belong together, presents them with explanation, and makes the set of changes something people can name. Naming matters for teaching, for reference material, for reporting a bug against a known baseline, and for deciding when a project should move forward.

## Guide-level explanation

Each edition is a point in time. A program is compiled as part of one edition, and the edition is recorded in the package manifest. Programs written for an older edition continue to compile under a newer compiler, so an edition does not force anyone to change their code on a fixed schedule.

When a new edition is released, the project publishes a guide. The guide describes each new feature, says why it was added, and shows how to adopt it. It also lists the changes that matter for code written in the previous edition, and it explains the migration tools that help with the most common transitions. The guide is written so that a reader who has used the language for a few years can follow it without reading the compiler source.

Tooling is part of every edition. The formatter, the linter, the language server and the build system are expected to support the new features when the edition ships. A feature that is stable in the compiler but unsupported by these tools is not considered complete for the purposes of an edition.

## Reference-level explanation

An edition is defined by a set of features whose stabilization falls between the previous edition and the new one. The release process proceeds as follows.

First, a candidate list is assembled from features that have been stabilized since the previous edition. The list is reviewed by the language team to confirm that the features are coherent and that none is blocked on an open design question.

Second, the user experience of each feature is reviewed. This includes the wording of error messages, the quality of diagnostics for common mistakes, and the presence of documentation in the standard library and the reference. A feature that does not meet this bar is held back until it does, or is removed from the candidate list.

Third, the tools are brought up to date. The project requires that the formatter, the linter and the language server handle every feature in the candidate list before the edition is announced.

Fourth, the guide is written and reviewed. The guide is treated as part of the edition and is subject to the same review as code.

Editions are released on a fixed schedule of two or three years. The schedule is a commitment to regularity rather than a deadline for any particular feature. If the candidate list is not ready when the time comes, the edition is delayed rather than shipped with incomplete features.

## Compatibility

Editions do not change the meaning of programs that already compile. A crate that declares an older edition keeps the behavior of that edition, and the compiler continues to support every edition that it has released. Crates may depend on crates written for other editions, and the compiler handles the interaction between them.

There are a small number of changes that cannot be made without an edition, because they would alter the meaning of existing code. Keywords are the clearest example. A new keyword would make some identifiers invalid, so it can only be introduced in an edition where the change is opt-in. Edition-gated changes allow the project to make such adjustments while keeping older code working.

Migration is supported by automated tools where possible. The tools rewrite source files to the new form and flag the places where a human decision is required. The goal is that most crates can be moved to a new edition with a small amount of manual work, and that the work can be done gradually, one crate at a time.

## Drawbacks

Editions add a layer of concept that users must learn. Someone who is new to the language may be confused by the distinction between the compiler version and the edition, and by the fact that a crate can be on an older edition than the toolchain that compiles it.

The project must maintain support for every edition it has released. This adds some cost to the compiler and to the tools, because changes that affect syntax or semantics need to be checked against each supported edition. The cost is bounded by the number of editions, which is small, but it is not zero.

There is a risk that the edition becomes a deadline that drives decisions about features. The project should avoid this by keeping the edition schedule loose and by allowing features to be stabilized independently of it.

## Rationale and alternatives

The main alternative is to continue with release notes only. This keeps the process simple but leaves the difficulties described in the motivation unresolved. Release notes describe what changed, but they do not offer a coherent unit that users can adopt or refer to.

A second alternative is to issue major versions of the language with breaking changes. This was rejected because it would impose the cost of migration on every user at once, and because Rust's stability promises make such breaks unattractive. Editions allow change without the breakage that a major version would require.

A third alternative is to publish an edition every year. This would keep the rhythm short, but the work needed to produce a coherent edition, including the guide and the tooling, takes time. A shorter cycle would either produce thin editions or shift the cost onto the people who maintain the tools.

## Unresolved questions

The exact length of the cycle is open. Two years and three years are both defensible, and the right choice may depend on how much the language changes between editions.

The naming of editions by year is a convention. It has the advantage of being easy to remember, but it implies a particular release calendar. The project may need to clarify that an edition's name does not mean that it was released in that year.

The relationship between editions and the stability guarantees of the standard library is not fully specified. The project will need to decide how library additions interact with edition boundaries.

## Future possibilities

Once editions are established, the project may choose to use them as the basis for deprecating old idioms, for gradually moving default behaviors, and for introducing lints that prepare users for future changes. Each of these would be considered as a separate proposal, with the edition mechanism providing the framework for the schedule.

## Conclusion

An edition is a modest proposal. It adds a name and a schedule to work that the project is already doing, and it gives users a clearer picture of where the language has been and where it is going. The cost is a small amount of process and a commitment to keep older editions working. The benefit is a language that is easier to follow, teach and adopt without giving up the stability that users depend on.
