# writing-skills

This repository collects skills for writing. Each skill lives in its own directory with a `SKILL.md` file in the [Agent Skills](https://agentskills.io) format, so any agent that supports the format can use it. The agent loads a skill when a request matches the description in that file. The collection currently holds one skill, `technical-writing`.

| Skill | Use it to |
| --- | --- |
| [`technical-writing`](technical-writing/SKILL.md) | Draft, revise or review design docs, RFCs, architecture decision records, research papers, technical reports, mathematical exposition and technical blog posts. |

## Installation

To install a skill, copy its directory into the skills directory your agent reads. Check your agent's documentation for the path. For example, to install `technical-writing` for Claude Code in all your projects, run:

```sh
git clone https://github.com/WillyPillow/writing-skills.git
mkdir -p ~/.claude/skills
cp -r writing-skills/technical-writing ~/.claude/skills/
```

To install a skill in Claude Code for one project only, copy its directory into that project's `.claude/skills/` instead. If you commit it, anyone who clones the project gets the skill.

## Usage

The agent loads a skill when a request matches its description. For `technical-writing`, a request such as "review this design doc" or "draft the method section from these results" is enough. Some agents also let you invoke a skill by name. In Claude Code, for example, type `/technical-writing`.

To change a skill's rules, edit its `SKILL.md`.

## technical-writing

The `technical-writing` skill guides an agent when it drafts, revises or reviews technical documents. It sorts the ways technical prose fails into three levels. In order of importance, they are substance, argument and structure, and sentences. Substance fails through no sharp claim, no concrete instance or invented support. Argument fails through claims stated before their context or steps without motivation. Sentences fail through nominalizations, jargon and padding. Polished sentences hide missing substance or a missing argument, so the agent fixes the levels from the top down.

Section 0 of the skill lists rules that are never broken. The first is that the agent works only from your material. It does not invent numbers, examples or citations. It also does not invent the history of a design, such as which alternatives were considered and why they lost. When support is missing, the agent asks you, narrows the claim, or leaves a `[TODO: ...]` marker. For anything longer than a few paragraphs, the agent first writes planning notes and waits for your corrections. The notes include the reader, the main point, the objections a skeptic will raise, one claim per planned paragraph, and questions for you.

In a design doc, the agent treats each significant choice as a decision record. The record states the force behind the decision (the requirement or constraint that makes it necessary), the options considered, the deciding reason, the cost accepted, and how hard the decision is to reverse. A force states numbers where they exist. The skill's example contrasts "must be scalable", which is not a force, with "must sustain 40k writes/s with p99 under 50 ms", which is.

When you mark a passage as bad, the agent names the specific fault and offers to add it to `SKILL.md` as a new rule (section 7).

### Contents

`technical-writing/SKILL.md` opens with the three levels, followed by eight numbered sections. The agent applies them by content rather than by document type, so a design doc that contains a derivation also gets the rules for mathematical exposition.

0. Rules that are never broken.
1. Planning before drafting.
2. Argument.
3. Design docs, RFCs and decision records.
4. Mathematical exposition.
5. Sentences, including a loose adaptation of Simplified Technical English (ASD-STE100) and a list of leftover LLM habits to scan for.
6. Form, with section outlines for papers and design docs.
7. Process, including a review pass separate from drafting.

The rules draw on Knuth's *Mathematical Writing*, Williams's *Style*, Gopen and Swan's "The Science of Scientific Writing", Ubl's "Design Docs at Google", Nygard's architecture decision records and other sources. The full list is in a comment at the end of `SKILL.md`.

## License

The skills are released into the public domain under the Unlicense. See [LICENSE](LICENSE).
