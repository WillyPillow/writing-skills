# RFC 1728: north_star

- Feature Name: `north_star`
- Start Date: 2016-10-04
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

This RFC refines the Rust planning and reporting process. Its aims are to establish a shared vision of the project among contributors, to make the roadmap toward that vision clear, and to celebrate what we achieve along the way.

Rust's roadmap will be set in year-long cycles. At the start of each cycle the project identifies, together, the most critical problems facing the language and its ecosystem, along with the story we want to be able to tell the world about Rust at the end of the year. Work toward solving those problems, the short-term goals, is decided by the individual teams as they see fit and is regularly re-triaged. For reporting purposes, goals are assigned to release-cycle milestones. At the end of the year we deliver a public retrospective describing which goals were met, which were not, and what we learned.

## Motivation

Rust has grown quickly in contributors, teams, and users. Most of the growth has been healthy, but the process by which we decide what to work on has not kept pace with it. Several symptoms are visible today.

**Priorities are implicit.** Each team has its own idea of what matters most, and those ideas are mostly sound, but nobody has written down how they fit together. A contributor who wants to help can find hundreds of open issues and dozens of accepted RFCs, with little guidance on which of them the project as a whole considers urgent.

**The yearly story is told after the fact.** Looking back, each year of Rust has had a clear theme. We rarely chose the theme in advance. It emerged from whatever shipped, and the narrative was assembled when the release notes and blog posts were written. That is better than having no narrative, but we lose the chance to rally around it while the work is still in progress.

**Roadmaps are split and brittle.** Today we have release milestones, team-specific tracking issues, and informal intentions on the internals forum. These sources are inconsistent and are rarely reconciled. When a goal slips, there is no obvious place where the slip is recorded, and so no occasion to ask whether the goal still deserves the effort.

**Achievements go unremarked.** Landing a large feature is the end of months of design, implementation, review, and polish. With no regular occasion for reflection, the people involved are thanked in passing at best, and the lessons of the effort are not collected.

None of this calls for heavy process. It calls for a light, regular rhythm that lets the project say what it is trying to do, check how that is going, and acknowledge the result.

## Detailed design

### The yearly cycle

The Rust roadmap operates on a cycle of about one calendar year. The cycle has three phases: setting the north star, executing, and the retrospective.

#### Setting the north star

In the final weeks of each cycle, the core team opens a discussion, held in public on the RFC repository, to decide what the next cycle's *north star* should be. The north star is a short document containing:

1. **Critical problems.** A small number (no more than five is a good guideline) of problems that most limit Rust's success in the coming year. These are stated in terms of users and their obstacles, not in terms of solutions. "New users cannot find a productive path from the book to a working network service" is a problem statement. "Stabilize async" is a solution and belongs further down.
2. **The story.** A paragraph or two describing what we would like to be able to say about Rust at the end of the year, if we succeed. It is written in the voice of the announcement we hope to publish.
3. **Principles for choosing.** Any constraints that should guide how teams trade off competing work, such as an emphasis on stability, or on polish over novelty.

The north star is itself adopted through the RFC process, so it receives the same level of public scrutiny as any other significant decision. Individual teams are expected to take part in drafting it, because they will be the ones working against it.

#### Executing: short-term goals

The north star does not prescribe tasks. Once it is accepted, each team is responsible for deciding which concrete goals will best address the critical problems, and for tracking them. A goal is a small, verifiable outcome: for example, "the new borrow checker is enabled by default" or "the package index supports a search by category."

Goals must name an owning team and, where possible, one or more individual contributors. Teams are free to add, drop, and reorder goals during the year. The only requirement is that the change is recorded in the same place as the original goal, together with a brief reason. This keeps the roadmap honest without turning it into a contract.

Teams re-triage their goals at least once per release cycle. Re-triage asks three questions. Is the goal still the best way to address the problem it was written for? Is it on track? Does it need help?

#### Milestones and reporting

For public reporting, each goal is assigned to a release-cycle milestone, the six-week train on which Rust ships. Assignment reflects the team's current best estimate of when the goal will be usable by ordinary users, not a promise. When a goal moves from one milestone to another, the change is visible in the roadmap, and the owning team is expected to explain it in their next status report.

A single roadmap page, maintained by the core team and generated from the tracking data wherever possible, displays the north star at the top and the goals grouped by milestone below. This page is the canonical answer to the question "what is Rust working on?"

#### The retrospective

At the end of the cycle, before the next north star is chosen, the project publishes a retrospective. The retrospective covers:

- Which critical problems were substantially addressed, and which remain.
- Which goals were completed, which were dropped, and why.
- A frank assessment of what the process did and did not do for us.
- Acknowledgment of the people and teams who did the work.

The retrospective is intended to be read by users as much as by contributors. It is the moment at which we celebrate, and it is also the moment at which we learn, since the findings feed directly into the next north star.

### Relationship to existing processes

This RFC does not change how individual RFCs are proposed, reviewed, or accepted. A feature does not need to appear in the roadmap to be proposed, and appearing in the roadmap does not exempt a feature from the RFC process. The north star merely provides context: when a team weighs an RFC against its capacity, the north star is one input.

Likewise, this RFC does not alter the release train. Releases continue every six weeks regardless of whether the goals assigned to them are ready; unready goals simply move.

### Roles

The core team is responsible for convening the north star discussion, for maintaining the roadmap page, and for writing or delegating the retrospective. Team leads are responsible for the accuracy of their teams' goals. Neither role grants the authority to override a team's technical decisions.

### First cycle

Because the process needs a first north star, the core team will draft one in the weeks following the acceptance of this RFC. The first cycle may be shorter or longer than a year so that future cycles align with a convenient calendar boundary.

## How we teach this

The roadmap page and the north star document are the primary teaching materials. Each team's introduction for new contributors should link to them. The yearly retrospective doubles as an explanation of the process: it records not just what happened but how the cycle worked.

The terminology is intentionally small: *north star*, *critical problem*, *goal*, *milestone*, *retrospective*. We should avoid introducing further vocabulary.

## Drawbacks

- **Overhead.** Writing a north star, tracking goals, and writing a retrospective take real effort, and volunteer time is scarce. The design tries to limit this by reusing existing tracking issues and by generating the roadmap page automatically, but some cost remains.
- **False precision.** Assigning goals to milestones may create expectations that the project cannot meet. Public dates that slip can look like failures even when the underlying decision was sensible.
- **Top-down drift.** A north star chosen by a small group could suppress worthwhile work that does not fit the story. The open RFC process and the explicit statement that teams own their goals are meant to guard against this.
- **Annual granularity.** A year is a long time in the life of a language, and the critical problems could change midway through.

## Alternatives

**Do nothing.** The project has done well without a formal yearly roadmap. The costs described in the motivation are real but diffuse, and some would say they are the price of a volunteer-driven project.

**Shorter cycles.** A six-month or per-release roadmap would adapt faster, but it would be dominated by incremental work and could not support a coherent yearly story.

**Team-only roadmaps.** Each team could publish its own plan with no shared vision. This is closest to the status quo and does not address the lack of project-level direction.

**A prescriptive plan.** The core team could set the specific tasks. This would be more predictable, but it would conflict with the way Rust teams make decisions and with the contributions of volunteers who work on what they care about.

## Unresolved questions

- How should goals that cross team boundaries be assigned an owner?
- What is the right threshold for amending the north star mid-cycle, if any?
- Should the retrospective be an RFC, a blog post, or both?
- What tooling is needed to generate the roadmap page from existing issue trackers?
