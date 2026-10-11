# Rust RFC 1728: north_star

- Feature Name: `north_star`
- Start Date: 2018-07-12
- Status: Accepted (process proposal)

## Summary

This RFC refines how the Rust project plans its work and reports on it. It asks the project to agree, once a year, on a shared picture of where Rust should be, to write down the concrete problems that stand between us and that picture, and to record our progress in public. Year-long cycles replace an ad hoc collection of roadmap items. Within a cycle, individual teams decide on the short-term goals they will pursue, and those goals are re-triaged regularly. At the end of each year the project publishes a retrospective that describes what was accomplished, what was not, and what we learned.

## Motivation

Rust has grown from a language maintained by a handful of people into a project with dozens of working groups, hundreds of regular contributors, and a large ecosystem that depends on the compiler and standard library. Coordination at this scale is difficult. Teams make reasonable local decisions, but without a shared sense of direction those decisions can pull against one another. Contributors who want to help often cannot tell which work matters most. Users outside the project see a stream of releases and feature announcements but have little sense of the larger story.

Earlier planning efforts helped, but they tended to produce long lists of desirable features with no ordering and no way to tell when an item was finished. A list of this kind records what people wanted at one moment. It does not tell a newcomer what the project is trying to accomplish, and it does not give a team permission to say that something is no longer a priority.

This RFC addresses three needs. First, the project needs a vision that is short enough to remember and specific enough to guide choices. Second, it needs a small set of problems to focus on, chosen by the whole project rather than by whichever team is loudest. Third, it needs an honest record of outcomes, so that the next cycle starts from evidence rather than memory.

## Guide-level explanation

Each year the project goes through a planning cycle with four steps.

1. **Vision.** The project agrees on a short statement of the future it wants for Rust. The statement should be concrete enough that a reader can imagine a specific situation that would count as success.

2. **Problems.** Contributors propose the critical problems that stand between the project and the vision. The project as a whole selects a manageable number of them. A problem is something observable, such as "embedded developers cannot easily build for an unfamiliar target," rather than an implementation plan.

3. **Goals.** Teams propose goals that address the selected problems. A goal names a specific outcome, an owner, and a rough schedule. Goals are assigned to release-cycle milestones so that progress can be reported on a steady rhythm.

4. **Retrospective.** At the end of the year the project publishes a document that describes which goals were met, which were dropped and why, and what the project would do differently. The retrospective is written for people outside the project as well as for those inside it.

Within the year, teams are free to re-triage their goals. A goal that turns out to be impossible, or that has been overtaken by events, may be dropped. Such a decision should be recorded in the public tracking material with a short explanation. Dropping a goal is not a failure of the process. Keeping a goal that nobody is working on is.

## Reference-level explanation

The planning artifacts live in a dedicated repository. Each cycle has a directory containing the vision statement, the list of selected problems, and a table of goals. Each goal row records its owning team, its milestone, its current status, and a link to the tracking issue.

Status values are limited to a small set: proposed, active, completed, and dropped. A goal moves to completed only when its owner has written a short closing note describing the outcome. A goal moves to dropped only with a note explaining the decision. The planning working group is responsible for keeping the table consistent and for flagging goals whose milestone has passed without an update.

Milestones follow the existing release train. Because a release is produced every six weeks, a year contains roughly nine milestones. Teams report status at the end of each milestone, and the planning working group summarizes these reports in a short public update. The update is intentionally brief so that it can be read in a few minutes.

The vision statement is revised at most once per cycle. Changes to the vision require the same approval as an RFC because they affect the whole project. Problem selection is made by a poll of the contributors who are members of at least one team, with the planning working group counting the results and resolving ties by discussion.

## Drawbacks

A yearly cycle adds bookkeeping. Someone must maintain the tables, collect status updates, and write the retrospective. Teams that are already stretched may see this as overhead. The process also risks becoming a ritual in which goals are written down to satisfy the format and then ignored. Careful attention from the planning working group is needed to prevent that outcome.

There is also a risk that a shared vision narrows the project too much. Work that does not fit the chosen problems may be discouraged, even when it is valuable. The process mitigates this by allowing teams to add goals outside the selected problems with a lighter review, but the balance will need to be watched.

## Rationale and alternatives

The main alternative is to keep the existing practice of maintaining a single roadmap document that is updated whenever someone remembers. That approach has the advantage of costing almost nothing, but it has not produced the shared direction that the project needs. Another alternative is to plan in shorter cycles, such as quarters. Shorter cycles would generate more reports but would make it harder to tackle problems that take longer than a few months. A year is long enough to see real change and short enough that the plan does not drift far from reality.

A third alternative is to let each team plan independently and merely collect their plans in one place. This is simpler, but it would not produce the shared problem list, which is the main point of the exercise.

## Prior art

Many open source projects publish periodic roadmaps, and some have adopted explicit goal tracking. The most useful lessons come from projects that separated the vision from the task list and that published honest retrospectives. Those projects showed that readers value a clear account of what did not happen as much as a list of accomplishments. The process proposed here borrows that emphasis on candor.

## Unresolved questions

It is not yet decided how the project should handle goals that span several teams with conflicting priorities. The planning working group will propose a mechanism for resolving such conflicts during the first cycle.

It is also unclear how much of the retrospective should be written by individual teams and how much by the working group. A reasonable starting point is for teams to write their own sections and for the working group to edit for consistency.

## Future possibilities

If the process works well, the project could extend it to cover ecosystem goals, such as the health of key libraries, and to track the experience of new users more directly. Better tooling for the planning repository would reduce the bookkeeping burden. In later years the project might also experiment with longer horizons for problems that cannot be solved in a single cycle, while keeping the annual rhythm for accountability.
