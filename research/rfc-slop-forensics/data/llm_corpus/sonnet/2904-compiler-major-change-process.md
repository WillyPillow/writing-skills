- Feature Name: N/A
- Start Date: 2020-09-15
- RFC PR: (leave this empty)
- Rust Issue: N/A

# Summary
[summary]: #summary

Introduce the **major change process** for the compiler team. This process has the following goals:

* to advertise major changes and give the team a chance to weigh in;
* to help scale the amount of work being done to reviewing bandwidth by choosing a reviewer in advance;
* to avoid a lot of process overhead.

The intent here is that if you have a plan to make some "major change" to the compiler, you will start with this process. It may either simply be approved, but if the change proves more controversial or complex, we may escalate towards design meetings, longer write-ups, or full RFCs before reaching a final decision.

This process does not apply to adding new language features, but it can be used for minor features such as adding new `-C` flags to the compiler, which are not subject to the RFC process.

# Motivation
[motivation]: #motivation

The compiler is a large codebase maintained by a team that is spread across many time zones and employers, and many of its contributors work on it part-time. Over the years, a handful of recurring problems have emerged.

**Surprise.** A large pull request lands, or is proposed, and other members of the team learn about it only when they see the diff. By then the author has invested weeks of work. Reviewers who see problems with the approach are in the unpleasant position of asking for a redesign after the fact, and the author is in the unpleasant position of receiving that request.

**Review bandwidth.** Reviewing is the scarcest resource. A large change that no one has agreed to review can sit in the queue for months, going stale and accumulating merge conflicts. Authors reasonably become frustrated; reviewers feel pressure they did not choose.

**Over-formality.** The existing way to get a design decision is the RFC process. It is heavy: the writing, the discussion period, the final comment period and the sign-off. For a change that is internal to the compiler and does not alter the language or its user-visible stability guarantees, a full RFC is disproportionate. The result is that authors skip the process altogether and simply open a pull request, which brings us back to surprise.

What we want is a lightweight, early, low-ceremony step that makes plans visible, assigns a reviewer, and leaves a record. If the change turns out to be uncontroversial, the step should take a few days and end with approval. If it turns out to be controversial, the step should lead naturally into the heavier process.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

## What is a major change?

A *major change* is a change that is large enough, or invasive enough, that the team would want to hear about it before the work is done. There is no bright line. Some indicators:

* The change touches many parts of the compiler, or restructures a significant component (for example, a new intermediate representation, a new query, or a rewrite of an analysis pass).
* The change will take more than a few days to implement, or more than a few hundred lines to review.
* The change affects other people's work in a way they would care about, such as altering an interface used by many contributors.
* The change introduces a new dependency, or changes the build in an important way.
* You are not sure whether the change is acceptable and want an early opinion.

When in doubt, ask. A major change proposal costs little, and the team would prefer a proposal that turns out to be unnecessary over a surprise.

Bug fixes, small refactorings, and performance tweaks that are self-contained are *not* major changes and do not need to go through this process.

## How to propose one

1. Open an issue on the compiler team's repository (`rust-lang/compiler-team`), using the "Major Change Proposal" template. The template asks for a short summary of the change, the motivation, and a sketch of the plan. It should read in a few minutes; it is not a design document.
2. A member of the team will look at it within a few days. If it is clear and uncontroversial, a team member may **second** the proposal. A second says: "I think this is a good idea, and I commit to reviewing the work (or to finding a reviewer)." The second is the person who will usually review the resulting pull requests.
3. After the proposal has been seconded, a ten-day **final comment period** begins, announced in the weekly meeting notes and through the usual channels. During this time, any member of the team may raise a concern.
4. If no concerns are raised, the proposal is **accepted**, and the author may proceed. If concerns are raised, they must be resolved before the proposal is accepted. A concern is an explicit objection from a team member that the proposal as stated should not go forward until it is addressed.

Proposals that are not seconded within a reasonable time (about three weeks) are closed, with the option of reopening. This is a signal that no one on the team currently has the bandwidth to take it on; it is not a judgement on the quality of the idea.

## Escalation

Some proposals will be more contentious than expected. The team has several options:

* Hold a **design meeting** on the topic, scheduled into the regular meeting slot, with a document prepared by the author in advance.
* Ask for a **longer write-up**, as an issue comment or a document in the repository, covering alternatives and tradeoffs.
* Require a **full RFC** if the change has implications beyond the compiler, such as a change to documented behavior or a stability commitment.

Escalation is not a rejection. It is a way to give the proposal the attention it requires.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

## Roles

* **Author**: the person proposing the change. Need not be a team member.
* **Second**: a team member (or a contributor with review rights) who agrees to see the change through. A proposal may be seconded by anyone except the author.
* **Team**: the compiler team, which includes members and, for purposes of raising concerns, contributors invited to participate.

## Labels and tracking

The repository uses labels to track state: `major-change`, `final-comment-period`, `accepted`, `closed`. A bot comments on each state transition. The meeting agenda is generated from the list of open proposals.

## Records

Accepted proposals remain in the issue tracker as the record of the decision. When the implementation is completed, the author links the tracking issue and closes the proposal.

## Concerns and the meaning of acceptance

Acceptance is not a guarantee that the resulting pull request will be merged. Review may reveal problems that were not apparent from the proposal. It is, however, a statement that the team has seen the plan and has no objection in principle, and a statement from the second that they will review. If the implementation departs significantly from the plan, the author should update the proposal.

## Relationship to the RFC process

This process does not replace RFCs. Anything that the RFC process requires remains subject to it, including new language features, changes to stable library APIs, and changes to the semantics of stable code. It is expected that a few major change proposals will point to an RFC as a follow-up, and some RFCs might be preceded by one.

# Drawbacks
[drawbacks]: #drawbacks

* **More process.** Even a light process is some process. Some contributors will find it a hurdle, and the risk is that it discourages people from making contributions.
* **Ambiguity.** There is no firm definition of "major." Reasonable people will disagree, and some changes that should have gone through the process will not.
* **Dependence on seconds.** If team members are busy, proposals will languish.
* **Visibility.** Proposals in an issue tracker may be missed by those who do not follow it.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

**Do nothing.** The current approach has the problems already described. It works well for experienced contributors who know whom to ask, and poorly for everyone else.

**Require an RFC for everything large.** This is too heavy for internal matters and has been tried informally, with the result that authors avoid it.

**Use a mailing list or chat only.** Chat discussions are ephemeral and hard to find later. An issue provides a durable record and a stable URL.

**Assign reviewers through a bot at pull request time.** This helps with load balancing but comes too late to prevent surprise.

# Prior art
[prior-art]: #prior-art

Other teams in the project have adopted similar lightweight processes. Several other open source projects use proposals with a sponsor, a pattern in which a maintainer champions a proposal and shepherds it to a decision.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

* What is the right length for the final comment period: ten days, or shorter for small changes?
* Should the second be required to be a team member, or should trusted contributors be allowed?
* How should we handle proposals that are made retroactively, after the work was done?

# Future possibilities
[future-possibilities]: #future-possibilities

The process could be extended with a lightweight "minor change" path, and with tooling that links proposals to the pull requests that implement them. It might also be adopted by other teams.
