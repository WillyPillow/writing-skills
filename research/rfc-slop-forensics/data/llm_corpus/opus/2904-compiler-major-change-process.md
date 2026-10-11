- Feature Name: N/A
- Start Date: 2020-04-02
- RFC PR: (leave this empty)
- Rust Issue: N/A

# Summary

Introduce the **major change process** for the compiler team. This process has the following goals:

- to advertise major changes and give the team a chance to weigh in;
- to help scale the amount of work being done to reviewing bandwidth by choosing a reviewer in advance;
- to avoid a lot of process overhead.

The intent here is that if you have a plan to make some "major change" to the compiler, you will start with this process. It may simply be approved, but if the change proves more controversial or complex, we may escalate towards design meetings, longer write-ups, or full RFCs before reaching a final decision.

This process does not apply to adding new language features, but it can be used for minor features such as adding new `-C` flags to the compiler.

# Motivation

As the compiler team has grown, so has the volume and ambition of the work landing in rustc. That is good news, but it has exposed some gaps in how we coordinate.

Today, large changes to the compiler usually arrive as pull requests. The author does the work, opens the PR, and a reviewer is assigned by the bot. Sometimes this goes well. Often it does not:

- **Surprise.** Team members learn about a significant refactoring of, say, the query system or the trait solver only when a 5,000-line PR appears. People with relevant context, or with competing plans for the same code, had no opportunity to raise concerns before the work was done.
- **Reviewer mismatch.** The randomly assigned reviewer may not be familiar with the area, may not have time for a large review, or may disagree with the approach. The PR then sits idle, or is passed from reviewer to reviewer, while the author's branch rots.
- **Wasted effort.** Occasionally a PR is rejected outright because the team would have preferred a different design. The contributor has spent weeks on work that will not land, and is understandably discouraged.
- **Undiscussed user-facing changes.** New command-line flags and other small user-visible features are sometimes added without anyone outside the PR noticing, leading to inconsistent naming and options that are hard to remove later.

At the other end of the spectrum, the full RFC process is too heavy for most of these changes. An internal refactoring does not need weeks of community discussion, and asking for an RFC for a new codegen flag would discourage useful contributions.

What we want is a lightweight step between "just open a PR" and "write an RFC": a way to say "I plan to do this" early, get a quick yes or no, and line up a reviewer before the work starts.

# Guide-level explanation

## What counts as a major change?

A change is "major" if any of the following apply:

- It substantially changes the design of some part of the compiler, such as restructuring a central data structure, changing how a query is computed, or introducing a new intermediate representation.
- It is large enough that reviewing it will take significant time.
- It adds, removes or changes a stable or unstable compiler flag, or otherwise affects the user-visible behaviour of the compiler outside of the language itself.
- It changes the supported platforms or the minimum version of an external dependency such as LLVM.
- You are not sure whether it is major.

Bug fixes, small refactorings, performance tweaks within a single module and diagnostic improvements generally do not count, and can be submitted directly as PRs.

## Filing a Major Change Proposal

To propose a major change, open an issue on the compiler team's repository using the "Major Change Proposal" template. The template asks for:

- A short summary of what you want to do.
- The motivation: what problem does this solve?
- A sketch of the approach, at whatever level of detail you have.
- Links to any prior discussion.
- The name of a team member you would like to review the work, if you have one in mind.

Opening the issue automatically creates a discussion topic on the team's chat, where people can ask questions and raise concerns. The proposal is also announced in the team's weekly meeting agenda.

Writing an MCP should take minutes, not hours. It is not a design document. If you find yourself writing pages, consider whether the change needs a design meeting instead.

## Getting a second

An MCP is accepted once a member of the compiler team (or a contributor with review privileges) "seconds" it, and no objections are raised during a waiting period.

To second a proposal, a team member comments on the issue to say so. By seconding, they are saying: "I think this is a reasonable idea, and I am aware of no serious objections." Seconding does not commit the person to reviewing the implementation, though in practice the seconder often does.

Once seconded, a ten-day final comment period begins. If nobody raises a concern during that time, the MCP is accepted, the issue is labelled as such, and the author may proceed with implementation. If a concern is raised, the MCP is blocked until the concern is resolved, either through discussion, through changes to the proposal, or by escalation.

## Reviewers

Part of the purpose of the MCP is to find a reviewer before the implementation exists. When the MCP is accepted, the issue should name the reviewer who has agreed to look at the eventual PR. That person has had a chance to shape the plan and has committed some of their time to the review.

## Escalation

Some proposals turn out to be bigger or more contentious than they first seemed. When that happens, the team may decide that the MCP is not the right venue and ask for one of:

- **A design meeting**, in which the author presents the proposal and the team discusses it in depth. The compiler team already holds regular design meetings; MCPs are a natural source of topics.
- **A longer write-up**, such as a document in the rustc-dev-guide or a HackMD document reviewed asynchronously.
- **A full RFC**, if the change has implications beyond the compiler team, for example because it affects the language, Cargo or the stability guarantees.

Escalation is not a rejection. It means the team wants to understand the proposal better before deciding.

# Reference-level explanation

## Scope

The MCP process applies to the compiler team's areas of responsibility: rustc itself, its internal libraries, and its command-line interface. It does not apply to:

- New language features, which go through the lang team and the RFC process.
- Changes to the standard library API, which go through the libs team.
- Changes to Cargo, rustdoc or other tools, which have their own teams.

New unstable `-Z` flags are within scope. Stabilizing a `-C` flag is within scope, but because stabilization is a permanent commitment, it requires a full team FCP rather than a single second.

## Labels and automation

The process is supported by the triage bot:

- A new MCP issue receives the `major-change` label and the bot opens a chat topic.
- A command such as `@rustbot second` records a second and starts the waiting period.
- After ten days with no concerns, the bot applies `major-change-accepted` and closes the issue.
- A command such as `@rustbot concern <reason>` blocks acceptance until resolved.

## Relationship to PRs

A PR implementing an accepted MCP should link to it. Reviewers may ask that a PR that should have had an MCP be paused until one is filed. This is expected to be rare and friendly; the goal is coordination, not gatekeeping.

# Drawbacks

- It adds a step for contributors, which might discourage drive-by contributions. We mitigate this by keeping the template short and the threshold for "major" high.
- A ten-day wait before work can begin may frustrate contributors who are eager to start. In practice nothing stops people from prototyping during the waiting period; only merging is deferred.
- Deciding what is "major" is subjective. We prefer to err on the side of filing.

# Rationale and alternatives

- **Status quo.** Leaves the problems described above unaddressed.
- **Require RFCs for all major compiler changes.** Too heavy; discourages contributions.
- **Rely on design meetings alone.** Meetings are limited in number and require synchronous attendance. An asynchronous first step lets most proposals be handled quickly and reserves meetings for those that need them.

# Unresolved questions

- The exact length of the waiting period may be tuned based on experience.
- Whether contributors outside the team should be able to second proposals.
