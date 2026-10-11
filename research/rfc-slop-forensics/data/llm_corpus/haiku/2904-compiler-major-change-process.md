# Rust RFC 2904: Compiler major change process

**Type:** Process
**Status:** Proposed
**Area:** Compiler team governance

## Summary

This RFC introduces a *major change process* for the compiler team. The process gives the team a structured way to announce significant changes, to invite comment, and to assign a reviewer in advance. It is intended to scale the team's review capacity to the amount of work being proposed, and to avoid heavyweight design procedures for changes that do not need them. A change that proves contested or complex can be escalated to a design meeting, a longer write-up, or a full RFC before a decision is made.

## Motivation

The compiler is a large and active project. Many contributors propose changes that alter its internals, its diagnostics, its performance characteristics or its handling of particular language features. Most of these changes are straightforward. A few have consequences that reach across the team, for example a change to how type information is represented or to the order in which analysis passes run. Those changes benefit from discussion before they land, because a reviewer who was not consulted may discover a problem only after the code is written.

At present the team has no standard way to surface such changes. A contributor who plans a large refactoring may post an issue, or may open a pull request and wait for feedback. Reviewers have limited time, and a pull request that arrives unannounced can take a long time to review, especially when no one has been asked to take responsibility for it. The result is uneven: some significant changes get careful attention, and others are merged with less scrutiny than they deserve, or wait indefinitely.

The process is meant to address these problems in a lightweight way. It asks contributors to state their plan early, to name the team members who should look at it, and to accept that the team may ask for more detail. It does not require a fixed set of documents or a long waiting period for ordinary work.

## Guide-level explanation

If you plan a major change to the compiler, you begin by opening a short proposal. The proposal describes the change, its motivation, the parts of the compiler it touches, and the risks you see. It also names a reviewer. The reviewer is a team member who agrees to look at the change and to make the final call on the reviewer side of the work, although the team as a whole retains the authority to decide.

The proposal is announced to the team. Members who are interested can comment on it. The reviewer decides whether the change can proceed as planned, whether it needs changes, or whether it should be escalated.

For most changes, the outcome is simple. The proposal is approved, the change is implemented, and the reviewer reviews the implementation in the usual way. The process adds a few days of visibility and a named point of contact, and it costs the contributor very little.

For changes that prove more controversial or complex, the process allows escalation. The team may schedule a design meeting to talk through the options. The contributor may be asked to write a longer document that explores alternatives. In the most significant cases, the change is brought forward as a full RFC, which goes through the complete design process.

The process does not apply to new language features. Those follow the RFC process directly. It can be used for minor features, for example a new diagnostic or a new optimization, if the author wishes to make the change visible before implementing it.

## Reference-level explanation

A major change proposal is a document with a fixed set of headings. It states the change in one or two paragraphs. It describes the motivation, the design at a level of detail sufficient for reviewers to judge its effect, and the implementation plan. It lists the risks and the parts of the compiler that will be affected. It names the proposed reviewer and, where relevant, any other team members who should be consulted.

The proposal is opened as an issue in the compiler repository and tagged so that it appears on the team's tracking board. The team's process for triage includes a regular review of open proposals, during which members can raise concerns.

A reviewer is chosen in advance. The reviewer's role is to read the proposal, to ask questions, to decide whether the change should proceed, and to review the implementation when it arrives. A reviewer may decline the role, in which case the proposal is reassigned. The reviewer is expected to act within a reasonable period, and the author may ask the team to find a reviewer if none responds.

A proposal is approved when the reviewer has indicated approval and no member has raised a blocking concern within the comment period. The comment period is short for most changes. A concern is blocking if it identifies a problem the reviewer has not addressed, and the reviewer must respond to it before approval.

If concerns cannot be resolved, the proposal may be escalated. Escalation takes one of three forms: a design meeting, a longer write-up, or a full RFC. The team decides which form is appropriate, based on the size of the change and the nature of the disagreement.

## Drawbacks

The process adds a step to changes that would otherwise have been made directly. Contributors who are used to opening pull requests may find the proposal stage tedious for small changes. The RFC asks the team to make clear that the process is optional for changes that are not major, and to avoid applying it to work that does not need it.

Assigning reviewers in advance places a load on the people who take the role. A reviewer who accepts many proposals may find the work unmanageable. The RFC expects the team to watch the distribution of reviews and to adjust assignments when necessary.

There is also a risk that the process becomes a gate that slows down useful work. The team should measure the time from proposal to approval and should respond if it grows.

## Rationale and alternatives

The main alternative is to do nothing and rely on the existing practice of informal discussion. This works when the team is small and the changes are few, but it does not scale as the project grows, and it leaves reviewers with no predictable way to plan their work.

A second alternative is to require a full RFC for every significant change. This would provide thorough design review but would impose a cost that is out of proportion for many changes. Contributors would be discouraged from proposing work, and the RFC process would be overloaded.

A third alternative is to require approval from the whole team for every change. This would give every member a voice but would make the process slow and would place an unreasonable burden on members who have no interest in most proposals.

The process described here sits between these extremes. It gives visibility and a named reviewer for most work, and it reserves the heavier procedures for the cases that need them.

## Unresolved questions

The exact comment period and the threshold for a major change are open. The RFC suggests a starting point, but the team should revise these based on experience. The definition of a major change should also be refined over time, since it depends on how the compiler is organized.

The relationship between this process and the existing triage procedures needs to be documented, so that contributors know which steps apply to their work.

## Future possibilities

Once the process has run for a while, the team may choose to publish summaries of approved proposals, which would help contributors understand the decisions that have been made. The team may also build tools that track proposals and their status, so that reviewers and authors can see the state of the work without searching through issues.

## Conclusion

A lightweight process for major changes gives the compiler team a shared way to talk about significant work before it is done. It makes reviewer responsibility explicit, it keeps the cost low for ordinary changes, and it leaves room for deeper design when the change warrants it. The RFC asks the team to try the process and to refine it as the project learns from it.
