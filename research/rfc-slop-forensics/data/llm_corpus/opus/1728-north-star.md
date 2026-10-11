- Feature Name: `north_star`
- Start Date: 2016-08-30
- RFC PR: (leave this empty)
- Rust Issue: N/A

# Summary

This RFC refines how the Rust project plans its work and reports on it. It has three aims: give contributors a shared vision of where the project is going, make the path toward that vision visible, and take time to recognize what we have accomplished.

The roadmap will run in year-long cycles. At the start of each cycle the project as a whole identifies the most critical problems facing the language and its ecosystem, and writes down the story we want to be able to tell the world about Rust at the end of the year. Individual teams then decide on the short-term goals that address those problems and re-triage them regularly. For reporting, each goal is attached to a release-cycle milestone. When the year ends, the project publishes a retrospective covering what we set out to do, what we did, and what we learned.

# Motivation

Rust has grown quickly. Several teams now work in parallel: language, libraries, compiler, tools, documentation, community, and infrastructure. Each has its own RFCs, its own issue tracker labels, and its own idea of what matters most. That independence is mostly healthy, but it has costs that become harder to ignore as the project grows.

**There is no single place to learn what Rust is working on.** Someone who wants to know whether incremental compilation will land this year, or whether the IDE story is a priority, has to piece the answer together from team meeting minutes, internals threads, and a long trail of RFC discussions. Contributors inside the project find this hard. Outside observers such as companies evaluating Rust, educators, and potential contributors find it close to impossible.

**Teams do not always pull in the same direction.** When each team picks its priorities alone, related work can fall between teams. Improving the experience of a new user, for example, touches the compiler's error messages, the documentation, Cargo, and the community team's outreach. If nobody says that this is a project-wide priority for the year, each team may reasonably decide it belongs to somebody else.

**We do not stop to look back.** The six-week release train is good at shipping, but it does not create natural moments for reflection. Large efforts like MIR finish quietly, and it is easy to forget how much the project has done. Without a regular retrospective we also miss the chance to ask which approaches worked and which did not.

**The RFC process is bottom-up by design.** That is a strength, but it means the project has no lightweight way to say "these are the problems we most want solved." Contributors who want to help have no clear signal about where their effort would count most.

The goal of this RFC is to add a small amount of top-down coordination without disturbing the decentralized, team-driven way Rust already works.

# Detailed design

The process has four parts: problem statements, the north-star narrative, team goals, and reporting.

## The yearly cycle

Each roadmap covers one calendar year. Planning for the next year starts in the autumn of the current one, so the roadmap can be accepted before January.

1. **Call for input (September to October).** The core team asks for public input. Anyone can write a blog post, an internals thread, or a survey response describing what they think are Rust's most important problems. The annual community survey feeds directly into this step.
2. **Roadmap RFC (November).** The core team, working with team leads, synthesizes the input into a roadmap RFC. Like any other RFC, it goes through public discussion and a final comment period.
3. **Acceptance (December).** Once accepted, the roadmap RFC becomes the official plan for the coming year.
4. **Execution (January to December).** Teams set and adjust goals throughout the year.
5. **Retrospective (December).** The project publishes a public retrospective on the year that is ending, and this feeds into the next cycle.

## Problem statements

The roadmap RFC centers on a short list of problem statements, usually between four and eight. Each one describes a concrete obstacle Rust faces, phrased from the point of view of the people it affects. Examples of the kind of problem we mean:

- "Rust has a steep learning curve, and new users often give up before they become productive."
- "Rust lacks first-class IDE support, which makes it a hard sell for teams used to such tooling."
- "Compile times are long enough to disrupt the edit-compile-test loop."

Problem statements say nothing about solutions. They describe what is wrong and why it matters. This keeps the roadmap RFC from turning into a design discussion and leaves teams free to choose their own approach.

## The north-star narrative

Alongside the problem statements, the roadmap RFC includes a short narrative, a few paragraphs long, describing the story we want to tell about Rust at the end of the year if things go well. For example: "In 2017, Rust became a language that teams could adopt with confidence for production network services."

The narrative ties the problem statements into a coherent message. It also gives us a yardstick for the retrospective: at the end of the year, can we honestly tell that story?

## Team goals

Each team owns the goals that address the problems relevant to it. A goal is a concrete, achievable piece of work, such as "stabilize incremental compilation" or "ship the second edition of the book."

Goals are:

- **Decided by teams.** The core team does not assign goals. Teams know their own domains best.
- **Tied to problems.** Every goal should name the problem statement or statements it addresses. Work that addresses none of them can still happen, since teams are not limited to roadmap work, but it is not tracked as part of the roadmap.
- **Re-triaged regularly.** Each team reviews its goals at least once per release cycle. Goals can be added, dropped, or rescoped. A dropped goal is not a failure; it is information.

## Milestones and reporting

For reporting purposes, each goal is assigned to the release whose six-week cycle it is expected to finish in. This lets us show a rolling view of the roadmap in terms everyone already understands: "this is expected in 1.15, this in 1.17."

The project will keep a single tracking page, ideally generated from GitHub issues and labels, listing:

- each problem statement;
- the goals attached to it and the team that owns each goal;
- each goal's target release and current status.

Each release announcement will include a short section on roadmap progress.

## The retrospective

At the end of each year the core team, with input from every team, publishes a retrospective blog post. It covers:

- what we set out to do, with the problem statements and the narrative;
- what we actually did, goal by goal;
- what we did not do, and why;
- what we learned about the process itself.

The retrospective is meant to celebrate. Rust contributors do a lot of work that goes unrecognized, and the end of the year is a good time to say thank you. It is also meant to be honest, and it is the main input for planning the following year.

# Drawbacks

**Overhead.** Every process takes time. Writing a roadmap RFC, keeping a tracking page current, and writing a retrospective all cost effort that could have gone into code. We have tried to keep the process light, but the cost is real.

**Rigidity.** A yearly plan can make the project slower to react when circumstances change mid-year. We address this by keeping goals flexible and team-owned, but a project-wide problem statement fixed in December may look less urgent by July.

**Exclusion.** Work that does not fit a problem statement may feel second-class. We want to be clear that roadmap work is not the only valued work. The roadmap tells contributors where focus would help most; it does not tell them what they are allowed to do.

**Over-promising.** Publishing target releases invites people outside the project to treat them as commitments. Release targets in the tracker should be clearly labeled as estimates.

# Alternatives

**Keep the status quo.** Teams continue to plan alone, and the project communicates through blog posts as things happen. This costs nothing but leaves the problems in the Motivation section unsolved.

**A shorter cycle.** Planning every six weeks, in step with releases, would be more responsive, but it is too short to make progress on the kind of problems this RFC is about, and planning that often would be tiring.

**A longer cycle.** A multi-year vision would offer more stability but would be harder to get agreement on, and it would rarely produce a satisfying retrospective.

**Top-down goals.** The core team could assign goals to teams directly. That would make coordination easier, but it goes against the way Rust governance works and would waste the domain knowledge each team has.

# Unresolved questions

- What tooling should generate the tracking page? A small bot that reads GitHub labels is the likely answer, but nobody owns it yet.
- How should we measure progress on problems that do not reduce to finished goals, such as "the learning curve is too steep"? The community survey may help, but it is a blunt instrument.
- Should the subteams of each team set their own goals, or roll them up into the parent team's list?
