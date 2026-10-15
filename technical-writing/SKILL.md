---
name: technical-writing
description: Drafts, revises and reviews technical documents such as design docs, RFCs, architecture decision records, research papers, technical reports, mathematical exposition and technical blog posts. Keeps every claim grounded in the author's material, orders the argument so each claim follows its context, records design trade-offs as decisions, and reviews in a separate pass from substance down to sentences. Use when asked to write, outline, edit, tighten, critique or review any of these documents or a part of one, such as an abstract, a related-work section, a proof or an alternatives section, even if the request does not name the document type.
license: Unlicense
---

# Technical writing

## How to use this skill

Identify the task, then follow its path:

- **Drafting** a document or section: plan, draft one section at a time, then review (see "Process").
- **Revising** an author's draft: review it first, then make the smallest edit that fixes each finding.
- **Reviewing** a document: go straight to the review pass in "Process", and report findings rather than rewriting.

The author's instructions take precedence over this skill: a venue template, a required section or a house style wins. The rules under "Rules that are never broken" still hold. When you set a rule aside because the author asked, say which one in your note to the author.

Apply sections by content, not by document type. A design doc with a derivation uses "Mathematical exposition", and a paper that justifies a system design uses "Design docs, RFCs and decision records".

For anything longer than a few paragraphs, track this checklist in your working notes. It is for you, not for the document:

```
- [ ] Write the planning notes and get the author's corrections
- [ ] Draft one section at a time
- [ ] Review in a separate pass: substance, argument, design, math, sentences
- [ ] Report each finding with its location and a minimal fix
```

## What goes wrong, in order of importance

Technical prose fails at three levels:

1. **Substance.** The text has the form of a study or a design without the content: no sharp claim, no concrete instance, invented support. Polished prose makes the gap harder to see.
2. **Argument and structure.** Claims are declared before the context that would make them plausible. Steps and choices follow one another without motivation, so each piece checks out but nothing says what leads to what. Objects are defined and never used. Citations are listed rather than positioned.
3. **Sentences.** Nominalizations, jargon, padding, stock phrases.

Work top-down. Polishing sentences while the first two levels are broken produces fluent emptiness. Removing stock phrases without fixing the underlying problem only hides it.

Design docs are where missing motivation does the most damage, because the reasons are the content (see "Design docs, RFCs and decision records").

## Rules that are never broken

The author answers for the document, and a reader cannot tell invented support from real support. So:

- Work only from the author's material: results, logs, notes, drafts, data, benchmarks, incident reports, and the references they supply. Never invent numbers, experiments, examples, citations, or the story of how an idea or design was arrived at.
- In particular, never invent decision history: which alternatives were considered, why they lost, or what constraint drove a choice. Readers later rely on a design doc as the record of why the system is the way it is. Ask the author.
- If support is missing, ask, mark `[TODO: ...]`, or narrow the claim to what the evidence shows.
- A gap in what the author gave you goes to the author, not to the reader. Mark it with `[TODO: ...]` or raise it in the report to the author. Don't explain it in the prose ("the abstract does not say why", "the material does not record which alternatives were weighed"). A question that is open in the design itself is different: the document lists it (see "Open questions are listed" under "Design docs, RFCs and decision records"). A question about what the author meant or decided goes to the author.
- Add no references the author did not supply. If the author asks you to find sources, give them to the author as candidates to check, each with the claim it would support. Cite them in the document only after the author confirms them. Do not change reported numbers.
- When revising, make the smallest edit that fixes the problem. Never paraphrase just to disguise a pattern, and never add text whose only job is to satisfy a checklist item. List improvements beyond what the author asked for after the text, not in it.

## Plan before drafting

Prose drafted before the argument is settled fills its gaps with filler. For anything longer than a few paragraphs, write these notes and get the author's corrections before drafting any prose:

1. **Reader.** For a paper, default to a researcher in an adjacent area, who knows the field's basics but not this work's specifics. For a design doc, write for three readers: the reviewers who must approve it, the engineers who will build it, and a future maintainer asking why the system is the way it is. Knuth: if you write for the novice you reach the experts too.
2. **The point.** For a paper or post, the one claim the piece exists to make, in one sentence, stated so that it could turn out to be wrong (Peyton Jones: one clear, sharp idea, with contributions that can be refuted). For a design doc, the problem and the decisions that solve it.
3. **Instances.** The concrete examples, cases, failures, benchmarks or incidents available in the material.
4. **The skeptic.** The first three objections an expert or reviewer will raise, and where the text answers each. In a design doc the first objection is almost always "why not the simpler or obvious option?"
5. **Argument skeleton.** One sentence per paragraph stating its claim, each with its evidence source. A paragraph whose claim cannot be stated in one sentence is not ready to draft: split it, or settle its claim with the author first.
6. **Dependency map.** For a paper: every definition, assumption, lemma, equation, figure and table, with what it is used for and where. For a design doc: every requirement and constraint, with the decisions it drives. Anything nothing depends on is cut or moved to an appendix. A decision that no constraint drives, or a constraint that drives no decision, is a sign something is missing.
7. **Questions for the author.** Above all, why each nonobvious design choice or proof step is the way it is, and what else was considered. Motivation the author has not supplied must be asked for, not made up.

Write the notes in your reply, not only in your reasoning, so the author can correct them. Ask all your questions for the author at once, then end your turn. Once the author has answered, draft the whole document without stopping to ask again, and mark anything still open with `[TODO: ...]`.

If the author cannot answer before you draft, for example because no one is in the loop, draft anyway and mark each unanswered gap with `[TODO: ...]` rather than filling it. Give the planning notes and open questions to the author in a separate note outside the document, or leave them out if the output is only the document. Never write them into the document text.

## Argument

- **Explicit epistemic status.** Distinguish what is known, what this work shows, and what is conjecture. In a design doc, distinguish what is decided, what is proposed, and what is open. Hedge once, where the uncertainty is, and only as much as the evidence warrants. Use no superlatives about your own work (Knuth).
- **Claim only qualities you evaluated.** Adjectives and adverbs such as "seamless", "elegant" and "dramatically" assign the work qualities nobody measured, and each one invites a reviewer to ask for the evidence (Buschek 2026). Delete them, or replace them with the measured result. A result that is better on one measure and worse on another is a fine finding when the text says why.
- **At least one displayed instance.** Aggregate results need a shown example, case or failure from the material, or readers will assume individual cases were inspected. If none exists, say so plainly and limit claims about how individual cases behave to what the aggregates support.
- **Universal, compatibility and cost claims need support.** Three kinds of claim read as plain facts, so a missing source is easy to overlook. A universal claim says something holds in every case ("every tool already parses them", "this cannot fail"). A compatibility claim says existing code or users are unaffected. A cost claim says what a change costs ("the overhead is a single branch"). Keep each one only if the author's material supports it. Otherwise narrow it to what the material shows, or mark `[TODO: ...]`. In a comparison made for this skill, three Claude models each wrote 120 PEPs and Rust RFCs from the titles and abstracts of human-written ones from before 2022. The models had no benchmarks or compatibility data. Even so, compatibility claims appeared 5.6 to 7.6 times as often as in about 1,100 human-written PEPs and RFCs.
- **Restated findings keep their scope.** When you summarize a result, whether this work's or a cited work's, keep its conditions: the population or dataset, the setting, the sample size, and the tense. "Improved accuracy on two benchmarks" does not become "improves accuracy". Peters and Chin-Yee (2025) found LLM summaries of scientific papers nearly five times as likely as human summaries to generalize beyond the source, even when prompted for accuracy. A summary also adds no concept the results lack. If no reported quote or question concerns unobtrusiveness, the summary does not call the feature an "unobtrusive guardrail" (Buschek 2026). Mark any metaphor as the authors' interpretation, not as something participants said.
- **Attributions name their sources.** "Studies show", "experts argue" and "prior work has found" need the specific citations, as many as the plural claims. Each cited work must say what the sentence attributes to it. If the author has not supplied the citation, mark `[TODO: citation]`.
- **Cited work is described from its text.** Describe what a cited work shows only from its text or the author's notes on it, never from memory or a generated summary. Otherwise ask the author to confirm the description, or mark `[TODO: check]`. Buschek's (2026) example: a submission credited a study with showing that doing X causes effect E, but X was part of the task in every condition, so the study never compared it. Restate what a cited work found in your own words, and put any wording you take from it in quotation marks.
- **Cite the most fitting work.** A citation supports its claim directly and comes from a context close to this work's. Flag a citation that makes the point only in passing, or that comes from a distant domain, such as a smart-home finding cited for touchscreen keyboards (Buschek 2026). Reviewers in the field spot such citations as filler. Ask the author whether closer work exists; don't search for it yourself unless the author asks.
- **Context before claim.** Set out the limitation, observation or constraint first, then state the claim or decision it supports. The reader can only judge a claim once they have its context, so a document that announces its conclusion first has declared the claim, not argued it. An abstract or a contributions list may still give the result first, because the argument follows it.
- **Concrete motivation.** Motivation is a goal ("we need to bound X by Y", "writes must stay under 50 ms at p99") or an obstacle ("bounding each term separately loses a factor of n, because ...", "a single leader saturates at 12k writes/s"). A sentence that only announces the next step ("Naturally, one asks ...", "We now turn to ...") is not motivation.
- **Example before generalization** (Peyton Jones). A specific instance gives the reader something to test the general statement against.
- **Mark an example as an example.** A plain statement about one case reads as a rule that always holds. "The client retries three times" reads as fixed behavior, even if three is only the default or the value in one walkthrough. Introduce a case with "for example", "suppose" or "in this run", or state the rule beside it: "The retry count is configurable, and the default is three." Values chosen only to illustrate are labeled as such, so the reader does not take them for the system's real limits. When an example stands for a general rule, state the rule too, and say which parts of the example the rule covers.
- **Why before significance.** Readers want to know why a result holds before being told it matters (Knuth).
- **Comparisons say which wins, on what, and why.** A list of A's strengths beside a list of B's ("A is simple and fast; B is flexible and widely used") is not a comparison. It never says how A and B differ on any one criterion, or which criterion matters here. Compare them on the same criteria: what A does, what B does, and how large the difference is. Then name the criterion that decides, tie it to a stated goal or force, and say which option wins and what the winner costs. Each difference needs evidence from the material, such as a measurement, a documented limit, an incident or a prototype result. If the material has none, mark `[TODO: ...]` instead of asserting a difference. "SQLite is simpler; Postgres scales better" compares nothing. "We expect 200 concurrent writers. SQLite allows one writer at a time, and our prototype's throughput stopped growing at 30 writers, while Postgres sustained 200. So Postgres, at the cost of running a database server" does.
- **Results, not history** (Widom). In a paper, tell the story of the results, not of how you arrived at them. Keep the story linear, and move significant interruptions to an appendix. This does not apply to design docs, where the alternatives considered are part of the content (see "Design docs, RFCs and decision records").
- **The text stands without the conversation.** The reader sees only the finished document, not the conversation or the drafts that produced it. The usual leak: you suggest A, the author rejects it and asks for B, and the text then says "B rather than A" or "we do not use A" with no reason. To a first-time reader, A comes from nowhere and its rejection looks arbitrary. Other leaks are corrections of claims the reader never saw ("unlike a cache, ..."), words that point at an earlier version ("now", "instead", "no longer", "the revised approach"), and extra emphasis on a point only because the author stressed it in the conversation. Mention a rejected option only if a reader would plausibly think of it, and then give the reason it loses (see "Design docs, RFCs and decision records"). If the author rejected it without a reason, ask for one or leave the option out. Test each contrast and emphasis by asking whether a reader who has only this document would know why it is there.
- **Every object is used.** Refer to each figure, table, diagram and important equation from a sentence that reads something off it or draws a conclusion from it. Put that sentence where the reader needs the object.
- **Positioned citations.** When you discuss a prior work, say how it relates to this work or to another cited work. The relation can be a shared limitation, a different assumption, or what this work takes from it or does differently. The failure is a run of sentences that each describe one prior work in isolation ("X proposed A. Y extended A to B. Z applied B to C."). That lists the literature but never shows where this work fits in it. Citing one work per sentence is fine when the sentence states such a relation. The same holds for prior systems in a design doc.
- **No recycled text.** A sentence that repeats an earlier section either adds what its own section needs (a detail, a consequence, a qualification) or is deleted.
- **Diagrams depict the mechanism.** Method figures and architecture diagrams show components and how they connect. Settings, datasets, results and narration go in the text.

The rules on used objects, recycled text, positioned citations, displayed instances and diagrams, along with context before claim, adapt the six scientific-slop patterns of Oh et al. (2026).

## Design docs, RFCs and decision records

Ubl ("Design Docs at Google") puts it directly: the design doc is the place to write down trade-offs. A doc that says "this is how we will build it" without trade-offs, alternatives and the reasoning behind decisions is an implementation manual. If there truly were no trade-offs, the doc probably should not exist.

The default failure is a confident tour of the chosen design. It lists components, presents every property as a benefit, and appends an alternatives section of strawmen afterward. Prevent it by treating each significant choice as a decision record (Nygard's architecture decision records: context, decision, consequences). For each decision, state:

1. **The force.** The requirement, constraint or failure that makes a decision necessary, with numbers where they exist: load, latency budget, data size, cost, team size, deadline, compatibility. "Must be scalable" is not a force; "must sustain 40k writes/s with p99 under 50 ms" is.
2. **The options actually considered,** each in its strongest form, including keeping the status quo if the author considered it. Each rejected option gets the reason it lost, tied to a specific goal or constraint, and compared with the chosen option on that criterion (see "Comparisons say which wins" under "Argument").
3. **The deciding reason.** Usually one or two factors decide. Say which, and why they outweigh the others. Naming a goal is not a reason: "this matches the self-hosted goal" says which goal the choice serves, not why it serves that goal better than the alternatives.
4. **The cost accepted.** What the chosen design gives up or makes harder. Rust's RFC template has a "Drawbacks" section. A decision with no stated cost either had no real alternative (state it in one sentence and move on) or hides its trade-off.
5. **Reversibility.** Say which decisions are expensive to undo: data formats, public APIs, storage engines, anything clients depend on. These get the most justification; cheap, reversible choices get the least.

Mark each alternative you think of yourself with a `[TODO: ...]` marker asking the author whether it was considered. Never present it as an option that was considered and rejected. An option you suggested while drafting and the author turned down is not, for that reason alone, part of the decision record. Include it only if the author agrees it belongs there and gives the reason it lost.

Further rules:

- **Evidence where it exists.** Use benchmarks, prototypes and incidents from the material. Ubl: "I tried it out and it works" is one of the best arguments for a design. Back-of-envelope estimates show their inputs, and no estimate is more precise than its inputs. A timeline in exact hours with no measured basis is false precision.
- **The hardest problem gets the most space.** Name the design's central tension and spend the most words on it. In Lynch's blind comparison of a hand-written design doc with two AI-drafted ones, the human doc centered on security against usability for a self-hosted photo app. Both AI docs missed that tension and offered generic lists of web-app best practices instead.
- **The context section is facts.** It gives objective background briefly and links to details (Ubl). Arguments for the design belong elsewhere.
- **Goals are checkable, and non-goals are real.** A goal says how you would know it was met. A non-goal is something a reader could reasonably expect the system to do that is deliberately excluded, such as Ubl's example of ACID compliance for a database. A negated goal like "the system should not crash" is not a non-goal.
- **Present the design through its decisions.** Start with an overview, then go into the parts where decisions live. Sketch only the parts of APIs and schemas that bear on a trade-off, and don't paste full definitions, which bury the trade-offs and go stale (Ubl). A system-context diagram shows where the system sits among things the reader already knows.
- **Failure behavior is concrete.** For each dependency that can fail, say what happens, what users see, how it is detected and how it recovers. "We will add monitoring" is not an answer.
- **Rollout and rollback.** Give the migration steps, how to turn the feature off, and what becomes irreversible once shipped.
- **Open questions are listed.** Say where the design is unresolved and what input is needed, rather than smoothing it over.
- **No template filling.** Omit a section that has nothing real to say, or state in one line why it does not apply. A cross-cutting section, such as security, privacy or observability, explains how this design affects that concern, not general best practice.

**The disagreement test.** A reviewer who disagrees should be able to point to the specific decision, the reason given for it, and the number or assumption they dispute. If they cannot, the doc has hidden its reasoning.

The five parts of a decision record are a checklist for the writer, not vocabulary for the document. Write each one in the terms of the domain: "Writes must stay under 50 ms at p99, so a second round trip is ruled out", not "The force behind this decision is the latency budget". The same holds for "deciding reason", "cost accepted" and "expensive to reverse".

## Mathematical exposition

For each derivation or proof:

1. State the goal first, exactly: the statement to be proved or the quantity to be bounded.
2. Say why the obvious approach fails, concretely. If you don't know why, ask the author.
3. Keep the reader synchronized with the strategy, with short clauses saying what the current subgoal is and how the proof will reach it. Knuth's model proof does this. Signposts about the proof's goals are good; signposts about the document's own layout are not.
4. Mark the crux and give the intuition for why it works. Compress routine steps or move them to an appendix.
5. Prefer a direct proof to an unnecessary proof by contradiction. It shows why the result holds, and in Knuth's example it also needed fewer assumptions.
6. After the result, say what it buys and where it is used next.

For each definition, say what problem it solves and why the simpler alternative is inadequate. Give one example and, where useful, a non-example. State it twice, formally and informally (Knuth). For each assumption, name the step that uses it and what breaks without it.

**The blah test** (Knuth). Many readers skip formulas on a first reading, so the text must still read smoothly with every nontrivial formula replaced by "blah." A stronger version: the prose between displayed equations must tell the whole story on its own (the goal, the obstacle, the idea, the payoff). If it reads as "We have ... Then ... Thus ... Hence ...", rewrite it.

Knuth's rules for formulas (*Mathematical Writing*, 1989):

- Define every variable when it is introduced. Never use one notation for two things, or two notations for one thing.
- Minimize subscripts, and don't name elements you never need to name. Halmos: the best notation is no notation.
- Tie formulas together with running commentary rather than listing them homework-style.
- The sentence before a theorem is complete and, ideally, motivating. The theorem statement is self-contained, because readers jump straight to theorems.
- Display important formulas, and number only the ones you refer to. Punctuate displayed equations as parts of sentences. Never display a false equation, because skimming readers take displays as true.
- Separate adjacent formulas with words: "Consider S_q, where q < p", not "Consider S_q, q < p". Otherwise they read as one formula.
- Start each sentence with a word, not a symbol. Otherwise the reader cannot see where the sentence begins, and the symbol cannot be capitalized.
- In running text, write words instead of ∴, ⇒, ∀ and ∃.

## Form

Keep the author's source format: LaTeX, Markdown, reStructuredText, or the team's wiki or template. Return a draft as the document text only, and keep any note to the author separate.

Papers:

- **Abstract:** problem, gap, approach, main quantitative result, implication.
- **Introduction:** Widom's five questions, roughly a paragraph each: what the concrete problem is, why it matters, why it is hard (why naive approaches fail), why existing approaches fall short, and what the key idea and results are, with their limitations. End with the contributions, stated so they can be refuted, as a list that names the section supporting each. The list doubles as the outline, so no separate "the rest of this paper is organized as follows" paragraph is needed.
- **Related work:** organized by idea and contrasted with this work.
- **Preliminaries:** the notation, terminology and background the paper needs but did not originate, kept short. This marks off what is new from what came before. Define global terms here and other terms just before their first use.
- **Running example:** where possible, one example introduced early and reused throughout.
- **Method:** enough detail to reimplement it, with the reason for each design choice. A clear new contribution should appear by about a quarter of the way through the paper (Widom). Describe it top-down, so the reader can see where it is going and can skip ahead.
- **Experiments:** a reproducible setup, with each table's and figure's takeaway stated in the text. Compare against a naive baseline, against prior work, and among this work's own variants where there are several. Measure sensitivity to the important parameters and scaling, not only a headline number. Choose experiments and settings that show where the work is weak as well as where it is strong.
- **Limitations:** specific enough that a reviewer would recognize them.
- **Conclusions:** a short paragraph that does not repeat the abstract or introduction. Where possible, it makes the introduction's claims concrete with the measured numbers.
- **Appendices:** detailed proofs and algorithms that most readers will skip. Nothing needed to understand the contributions goes there.

Design docs (adapt to the team's template; drop sections with nothing to say):

- **Context and scope:** the background facts, briefly, and what is being built.
- **Goals and non-goals.**
- **Design:** an overview, then each significant decision with its force, options, deciding reason and cost (see "Design docs, RFCs and decision records").
- **Alternatives considered:** whole-design alternatives, if any, in their strongest form. This section is not a restatement of the non-goals.
- **Cross-cutting concerns:** only those the design actually affects.
- **Rollout, migration and rollback.**
- **Open questions.**

An architecture decision record is a single decision: status, context, decision, consequences (including the bad ones).

Blog posts can use the first person and more voice. Open with the concrete problem, result or surprising observation. All the argument and precision rules still apply.

Write prose paragraphs. Use lists only for genuinely parallel items, such as a contributions list, hyperparameters, goals and non-goals, or procedure steps. Use headers only at the depth the venue uses. A table is good for comparing alternatives against the same criteria, but the prose must still say which criterion decided and why. A table with a separate column of pros for each option is two lists, not a comparison (see "Argument").

## Sentences

- **Specific over general.** Give numbers with conditions and baselines, not "significantly improves" or "highly scalable".
- **Spare the reader arithmetic.** Numbers the reader will compare use the same unit, scale and baseline. Write "p99 fell from 120 ms to 45 ms", not "from 0.12 s to 45 ms". Don't set a relative change beside an absolute one ("misses fell 30% and hits rose by 2,000/s"), or two percentages of different baselines beside each other. If the reader needs a difference, ratio or total, state it rather than leave it to them, and say what a percentage is a percentage of. Distinguish percent from percentage points. For a derived number, such as an estimate, a ratio or a value in a worked example, show the inputs and the operation: "3 replicas × 2 TB = 6 TB of disk", so the reader can check it and redo it with their own inputs. Derive only from numbers in the material, and keep the reported number when you convert it.
- **Name the reasons and the items** (Widom). Give the reasons instead of writing "for various reasons". Use "etc." only when the remaining items are obvious ("phases 1, 3, 5, 7, etc."), never to stand for items you have not named ("volatility, scalability, etc.").
- **The curse of knowledge** (Pinker). Define what the reader doesn't know, and never define what they do.
- **The opening sentence is the best sentence.** Don't open with a sentence of the form "An X is Y" (Knuth).
- **Reader expectations** (Gopen and Swan, "The Science of Scientific Writing"). Readers take the end of a sentence as its emphasis. Put familiar information that links backward at the start, and new or important information at the end. Keep the subject close to its verb. Give context before asking the reader to take in something new.
- **Characters as subjects, actions as verbs** (Joseph Williams, *Style*). Turn nominalizations back into verbs: "we performed an optimization of" becomes "we optimized". Journal editors who measured AI-assisted submissions found them harder to read, with more nominalizations, longer words and more jargon (Organization Science AI Task Force 2026). A corpus study of NLP papers found the same shift toward longer words and formal substitutes such as "utilize" and "enhance" (Miletić and Falk 2026). Expert readers in its small pilot, however, rated LLM-edited paragraphs slightly clearer. Apply the rule because a nominalization hides the actor and the action, not because it signals machine writing.
- **Orwell's six rules** ("Politics and the English Language", paraphrased):
  1. Don't use figures of speech you are used to seeing in print. Readers no longer see them, and they stand in for a precise statement. The same holds for fresh figures that perform rather than inform: "most of the latency is spent waiting in the scheduler queue", not "the scheduler is where latency goes to hide" (Anthropic's prompting guide for Claude Fable 5.1 calls this mannered prose).
  2. Prefer the short word.
  3. Cut any word that can go. Strunk and White say the same ("omit needless words"), but keep the words that help parsing. Knuth: write "Assume that A is a group", not "Assume A is a group".
  4. Prefer the active voice.
  5. Prefer everyday English to jargon and foreign phrases.
  6. Break any of these rules rather than write something barbarous.

  In technical writing, rule 5 needs a qualification: a precise technical term beats a vague everyday one, but don't use jargon where a plain word is equally precise.
- **Every "this" has a referent** (Widom, after Ullman). When "this", "that", "these" or "it" could point to more than one thing, add the noun: "this gap", not "this".
- **Mark examples in parentheses as examples.** A list or case in parentheses right after a noun reads as its definition or its complete list. "The stateful services (Postgres and Redis)" says there are exactly two, and "a failed request (a timeout)" says that failure means timeout. If the parentheses hold examples or one special case, say so: "stateful services such as Postgres and Redis", "a failed request, for example a timeout". Keep bare parentheses for a definition or a complete list.
- **Say who "we" is.** In papers and mathematical exposition, "we" means the author and the reader together. In a design doc it usually means the team; say so if it could be ambiguous.
- **Start each sentence with a word, not a code identifier.** This is Knuth's rule for formulas (see "Mathematical exposition") applied to code. An identifier at the start hides where the sentence begins, and it cannot be capitalized, because code is case-sensitive. Write "The `parse_header` function returns `None` on EOF", not "`parse_header` returns `None` on EOF".

### Simplified Technical English (ASD-STE100), applied loosely

ASD-STE100 is the controlled-language standard used in aerospace maintenance documentation. Its idea is that a reader should not be able to misread a sentence. Use its rules as defaults and as review triggers, not literally: its approved dictionary and ban on most "-ing" forms are too restrictive for papers and design docs.

- **One word, one meaning; one meaning, one word.** In the standard, each approved word has a single meaning and part of speech. Here, use one term per concept throughout, and keep each term for that concept alone, even where a synonym would read better, because in technical writing a new word signals a new thing. Don't use the same word as both a noun and a verb with different meanings. In a design doc, a component keeps the same name everywhere, including in diagrams.
- **Don't coin labels to keep terms consistent.** One term per concept does not mean a short name for every concept. A label you make up, such as "the drift window" or "the fan-out tax", reads as an established term the reader should already know, so they search for it or guess at its meaning. Use the established term if one exists. Otherwise repeat a plain description, shortened only as far as it stays self-explanatory. If a concept recurs often enough to need a name, introduce the name at its first use as one this document gives it, with its definition: "We call the time between a write and its arrival at every replica the drift window." Never introduce a coined label first in a heading, table or diagram. A label coined in the drafting conversation is one more leak of the kind described in "The text stands without the conversation".
- **Topic first.** The first sentence of a paragraph says what the paragraph is about, which is not necessarily its claim (see "Context before claim"). Keep paragraphs short.
- **Procedures are imperative, one instruction per sentence.** Use a numbered list for three or more steps or conditions instead of chaining them in one sentence. This applies to reproduction steps, algorithms written in prose, rollout and rollback plans, and setup sections of blog posts.
- **One new fact per sentence.** Give information gradually, because readers take in one new thing at a time. A sentence that introduces two new things should usually become two sentences.
- **Sentence length as a review trigger.** STE caps descriptive sentences at 25 words and procedural ones at 20. Treat a sentence over about 25 words as a candidate for splitting, not a violation. Theorem statements and carefully qualified claims may need more.
- **Shorten by splitting sentences, not by dropping grammar or facts.** Keep articles, subjects and verbs explicit, and keep every fact, number, condition and scope qualifier when meeting a length target.
- **Simple tenses, and name the actor** when it matters: which service, which team, which user. This is where Orwell's active-voice rule matters most: procedures, method descriptions and the description of a design.
- **Noun clusters of at most three words.** Break longer chains with prepositions: "inlet valve of the high-pressure fuel pump", not "high-pressure fuel pump inlet valve". Knuth's example of a long chain is "packet switched data communication network protocol problem".

Scan last for leftover LLM habits. This list is for scanning, not a target. Many items come from Wikipedia's "Signs of AI writing" guide. No item proves a text was machine-written, and people use all of them; each is listed because it weakens the sentence it appears in. When an item turns up, rewrite the sentence rather than swapping in a synonym, since a synonym keeps the empty sentence.

- **Chat residue:** "I hope this helps", "let me know if", "as discussed", placeholders such as `[Describe ...]` or `2025-XX-XX`, citation markup left by a chat tool, and contrasts with options or drafts the reader never saw (see "The text stands without the conversation").
- **Typography:** bold or italics for emphasis (italics are for definitions and quotes; Widom), headers on everything, title-case headings, bullets where prose belongs (often each opening with a bold label and a colon), frequent em dashes.
- **Stock moves:**
  - Closing sentences that restate the paragraph, and formulaic closing sections ("Despite these challenges, ...", "Future outlook").
  - Several bullets that restate one idea with different nouns.
  - Lists of three used for rhythm.
  - Rhetorical questions used as transitions, and colon reveals.
  - "It's not X, it's Y" and "not just X, but Y".
  - Trailing clauses that assert vague importance.
  - "It is worth noting", "importantly", "notably", "interestingly".
- **Vague relations:** "associated with", "in connection with", "linked to", where the text should say which relation holds, such as causes, correlates with, is part of, or depends on.
- **Stock significance:** pivotal, crucial, plays a key role, underscores, landscape, realm, testament.
- **Stock vocabulary:** delve, leverage, utilize, enhance, subsequently, robust, seamless, harness, unlock, showcase, nuanced, intricate. In design docs also: scalable, flexible, extensible, maintainable, future-proof, best practices, when used without a number or a concrete scenario.
- **Avoided "is" and "has":** "serves as", "stands as", "boasts", "features", where the plain verb would do.

## Process

1. Write the plan (see "Plan before drafting") and get the author's corrections.
2. Draft one section at a time, because a whole document drafted in one pass comes out uniform and thin. Revise earlier sections when later ones change them (Halmos: write in spirals).
3. Review in a separate pass, so the draft is not judged by the context that wrote it. If you can hand the review to a fresh agent or session that did not see the drafting, do so. Otherwise, review as a separate step after drafting, rereading the document from the start as a reader who has only the document. Work top-down:
   - **Substance.** Check every number against the material. Confirm nothing is invented, including decision history, and locate each claim's evidence. Check that no gap in the author's material is explained in the prose instead of marked with `[TODO: ...]`. Check that every quality claimed for the work was evaluated and that aggregate results come with a displayed instance. Check that each universal, compatibility and cost claim has support in the material. Check that each restated finding keeps its source's scope and adds no concept the results lack. Check that each cited work exists, says what it is cited for, and is the most fitting support available in the material. Check that every bibliography entry is complete and consistent with the others.
   - **Argument.** For each sentence, ask what it claims, whether it is true, and whether it follows from what came before. Check that each statement about one case is marked as an example or matched with the rule it illustrates. Check that the skeptic's objections are answered. Check that each comparison says how the options differ on a shared criterion, with evidence, and which criterion decides. Read as a first-time reader: flag each rejection, contrast or emphasis that only makes sense to someone who saw the drafting conversation or an earlier draft. Compare the dependency map against the text, looking for claims before their context, undefined terms, unused objects and isolated citations.
   - **Design.** For each significant decision, check that the force, the options, the deciding reason and the cost are all present, and that the most expensive-to-reverse decisions are the best justified. Check that the hardest problem gets the most space. Check that non-goals are real and that failure behavior is concrete. Apply the disagreement test. Check that no section is template filler and that the decision-record terms, such as force, deciding reason and cost accepted, do not appear as prose.
   - **Math.** Check that each derivation states its goal first, that the crux is marked, and that each assumption is linked to its use. Apply the blah test.
   - **Sentences.** Flag every sentence whose removal loses nothing. Apply "Sentences", including the STE triggers: terms used in two senses or two terms for one concept, two new facts in one sentence, sentences over about 25 words, and noun clusters over three words. Flag coined labels that the text never introduces as its own, numbers the reader must convert or combine to compare, derived numbers without their inputs, and examples in parentheses that read as definitions.

   Report each finding with its location and a proposed minimal fix, rather than silently rewriting. A finding names a specific passage and judges what the document does against its own goals and method, not what a different document could have done (Buschek 2025). This holds for the author's draft and for someone else's paper alike. For example:

   ```
   Substance, section 3.2, "the cache adds negligible overhead": a cost claim
   with no measurement in the material. Fix: give the measured overhead, or
   write "[TODO: measure cache overhead]".
   ```

   Concerns that fit any document are findings only when tied to this one. Examples are scalability, generalization, sample size, study duration, "more objective metrics" and "the analysis could go deeper". Name the stated goal the concern threatens or the claim it undercuts. In a design doc, an alternative is a finding when a stated force favors it (see "Design docs, RFCs and decision records"), not merely because the design could have been different. Drop untied concerns rather than listing them. A long list of generic concerns is not a review, and an author who acts on it can make the document worse. If a level has no findings, say so in one line. A short review of a sound document is a correct result.
4. When the author marks a passage as bad, name the specific fault and offer to add it to this skill as a rule.

<!--
Sources

- Knuth, Larrabee and Roberts, *Mathematical Writing* (Stanford CS 209 notes, 1989)
- Halmos, "How to Write Mathematics" (1970)
- Orwell, "Politics and the English Language" (1946)
- Strunk and White, *The Elements of Style*
- Williams, *Style: Lessons in Clarity and Grace*
- Gopen and Swan, "The Science of Scientific Writing", *American Scientist* (1990)
- Pinker, *The Sense of Style* (2014)
- Widom, "Tips for Writing Technical Papers" (Stanford InfoLab, 2006)
- Peyton Jones, "How to Write a Great Research Paper" (talk)
- Ubl, "Design Docs at Google" (industrialempathy.com, 2020)
- Nygard, "Documenting Architecture Decisions" (2011)
- Rust RFC template (rust-lang/rfcs, 0000-template.md)
- ASD-STE100, Simplified Technical English (ASD, Issue 9, 2025)
- Oh et al., "Science or Slop?", arXiv 2610.00531 (2026)
- Organization Science AI Task Force, "More versus Better" (2026), on readability of AI-assisted submissions
- Miletić and Falk, "What Are LLMs Doing to Scientific Communication?", arXiv 2605.19936 (2026)
- Peters and Chin-Yee, "Generalization Bias in Large Language Model Summarization of Scientific Research", *Royal Society Open Science* 12(4) (2025)
- Buschek, "When LLMs Write Our Papers" (Medium, 2026), on LLM writing smells seen while reviewing for CHI
- Buschek, "Don't Review with an LLM (Laundry List Method)" (Medium, 2025), on generic generated review concerns
- Lynch, "Which Design Doc Did a Human Write?" (refactoringenglish.com, 2026)
- Comparison of Claude-written and human-written PEPs and Rust RFCs (research/rfc-slop-forensics in github.com/WillyPillow/writing-skills, 2026), for the rules on universal, compatibility and cost claims, on gaps in the author's material, and on decision-record terms in prose
- Anthropic, "Prompting Claude Fable 5.1" (platform.claude.com, 2026), for the term mannered prose
- WikiProject AI Cleanup, "Wikipedia:Signs of AI writing" (accessed October 2026)
-->
