# writing-skills

This repository collects skills for writing. Each skill lives in its own directory with a `SKILL.md` file in the [Agent Skills](https://agentskills.io) format, so any agent that supports the format can use it. The collection currently holds one skill, `technical-writing`.

| Skill | Use it to |
| --- | --- |
| [`technical-writing`](technical-writing/SKILL.md) | Draft, revise or review design docs, RFCs, architecture decision records, research papers, technical reports, mathematical exposition and technical blog posts. |

Part 1 of [`technical-writing/SKILL.md`](technical-writing/SKILL.md#part-1-writing-guide) also works as a writing guide for people, with no agent involved. Part 2 holds the rules for an agent writing on an author's behalf.

## Installation

To install a skill, copy its directory into the skills directory your agent reads. Check your agent's documentation for the path. For example, to install `technical-writing` for Claude Code in all your projects, run:

```sh
git clone https://github.com/WillyPillow/writing-skills.git
mkdir -p ~/.claude/skills
cp -r writing-skills/technical-writing ~/.claude/skills/
```

To install a skill in Claude Code for one project only, copy its directory into that project's `.claude/skills/` instead. If you commit it, anyone who clones the project gets the skill.

## Usage

The agent loads a skill when a request matches the description in its `SKILL.md`. For `technical-writing`, a request such as "review this design doc" or "draft the method section from these results" is enough. Some agents also let you invoke a skill by name. In Claude Code, for example, type `/technical-writing`.

To change a skill's rules, edit its `SKILL.md`.

## technical-writing

The `technical-writing` skill sorts the ways technical prose fails into three levels. In order of importance, they are substance, argument and structure, and sentences. Substance fails through a missing sharp claim, a missing concrete instance or invented support. Argument fails through claims stated before their context or steps without motivation. Sentences fail through nominalizations, jargon and padding. Polished sentences hide missing substance or a missing argument, so the agent fixes the levels from the top down.

The skill opens with rules that are never broken. The first is that the agent works only from your material. It does not invent numbers, examples or citations. It also does not invent the history of a design, such as which alternatives were considered and why they lost. When support is missing, the agent asks you, narrows the claim, or leaves a `[TODO: ...]` marker.

For anything longer than a few paragraphs, the agent first writes planning notes and waits for your corrections. The notes include the reader, the main point, the objections a skeptic will raise, one claim per planned paragraph, and questions for you.

In a design doc, the agent treats each significant choice as a decision record. The record states the force behind the decision (the requirement, constraint or failure that makes it necessary), the options considered, the deciding reason, the cost accepted, and how hard the decision is to reverse. A force states numbers where they exist. The skill's example contrasts "must be scalable", which is not a force, with "must sustain 40k writes/s with p99 under 50 ms", which is.

Two rules address habits of drafting with an agent. First, the text must make sense to a reader who never saw the conversation. If you reject the agent's suggestion A and ask for B, the document does not say "B rather than A" unless a reader would think of A and the document gives the reason it loses. Second, a comparison compares. A list of A's strengths beside a list of B's is not enough. The text compares A and B on the same criteria, with evidence, and says which criterion decides.

When you mark a passage as bad, the agent names the specific fault and offers to add it to the skill as a new rule.

### Contents

`technical-writing/SKILL.md` is a single file, so the skill can be copied or shared as one document. It has two parts.

Part 1 is a writing guide for anyone, and you can read it on its own without using an agent. It holds the rules that do not depend on who writes:

- What goes wrong, in order of importance: the three levels.
- Plan before drafting.
- Argument.
- Design docs, RFCs and decision records.
- Mathematical exposition.
- Form, with section outlines for papers and design docs.
- Sentences, including a loose adaptation of Simplified Technical English (ASD-STE100) and a list of stock phrases and moves to scan for.
- Process, including a review pass separate from drafting.

Part 2 is for an agent that writes on an author's behalf. It holds how to route a drafting, revising or reviewing task, the rules that are never broken, how to plan with the author, the drafting rules that come from working with someone else's material, the Part 1 rules that agent drafts break most often with the evidence for each, and the changes to the process for an agent.

The agent applies the sections by content rather than by document type, so a design doc that contains a derivation also gets the rules for mathematical exposition.

The skill names no particular model or agent. Where a step depends on what the agent can do, it gives a fallback. With no author available to answer the planning questions, the agent drafts anyway, marks the gaps with `[TODO: ...]`, and keeps its notes for the author out of the document. Without a way to start a fresh agent for the review, it reviews as a separate step after drafting.

The rules draw on Knuth's *Mathematical Writing*, Williams's *Style*, Gopen and Swan's "The Science of Scientific Writing", Ubl's "Design Docs at Google", Nygard's architecture decision records and other sources. The full list is in a comment at the end of `SKILL.md`.

## Research

The `research/` directory holds the evidence behind individual rules. It is not part of any skill, and installing a skill does not need it. [`research/rfc-slop-forensics`](research/rfc-slop-forensics/README.md) compares PEPs and Rust RFCs written by Claude models with human-written ones on the same topics. It is the source of three `technical-writing` rules: universal, compatibility and cost claims need support; gaps in the author's material go to the author, not into the prose; and the decision-record terms are not vocabulary for the document.

## License

The skills are released into the public domain under the Unlicense. See [LICENSE](LICENSE).
