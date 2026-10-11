---
name: technical-writing
description: Use when drafting, revising, or reviewing design docs, RFCs, architecture decision records, research papers, technical reports, mathematical exposition, or technical blog posts. Covers grounding, argument, design rationale, motivation, notation, and sentences, plus a separate review pass.
---

# Technical writing

Apply sections by content, not by document type. A design doc with a derivation uses section 4, and a paper that justifies a system design uses section 3.

## What goes wrong, in order of importance

Technical prose fails at three levels, listed here from most to least important:

1. **Substance.** The text has the form of a study or a design without the content: no sharp claim, no concrete instance, invented support. Polished prose makes this worse because it hides the gap.
2. **Argument and structure.** Claims are declared before the context that would make them plausible. Steps and choices follow one another without motivation, so each piece checks out but nothing says what leads to what. Objects are defined and never used. Citations are listed rather than positioned.
3. **Sentences.** Nominalizations, jargon, padding, stock phrases.

Work top-down. Polishing sentences while the first two levels are broken produces fluent emptiness. Removing surface tells without fixing the underlying problem only hides it.

Design docs are where missing motivation does the most damage, because the reasons are the content (section 3).

## 0. Rules that are never broken

- Work only from the author's material: results, logs, notes, drafts, data, benchmarks, incident reports, and the references they supply. Never invent numbers, experiments, examples, citations, or the story of how an idea or design was arrived at.
- In particular, never invent decision history: which alternatives were considered, why they lost, or what constraint drove a choice. Readers later rely on a design doc as the record of why the system is the way it is. Ask the author.
- If support is missing, ask, mark `[TODO: ...]`, or narrow the claim to what the evidence shows.
- Do not add references the author did not supply. Do not change reported numbers.
- When revising, make the smallest edit that fixes the problem. Never paraphrase just to disguise a pattern, and never add text whose only job is to satisfy a checklist item.

## 1. Plan before drafting

Prose drafted before the argument is settled fills its gaps with filler. For anything longer than a few paragraphs, write these notes and get the author's corrections before drafting any prose:

1. **Reader.** For a paper, default to a researcher in an adjacent area, who knows the field's basics but not this work's specifics. For a design doc, write for three readers: the reviewers who must approve it, the engineers who will build it, and a future maintainer asking why the system is the way it is. Knuth: if you write for the novice you reach the experts too.
2. **The point.** For a paper or post, the one claim the piece exists to make, in one sentence, stated so that it could turn out to be wrong (Peyton Jones: one clear, sharp idea, with contributions that can be refuted). For a design doc, the problem and the decisions that solve it.
3. **The skeptic.** The first three objections an expert or reviewer will raise, and where the text answers each. In a design doc the first objection is almost always "why not the simpler or obvious option?"
4. **Argument skeleton.** One sentence per paragraph stating its claim, each with its evidence source. A paragraph whose claim cannot be stated in one sentence is not written.
5. **Dependency map.** For a paper: every definition, assumption, lemma, equation, figure and table, with what it is used for and where. For a design doc: every requirement and constraint, with the decisions it drives. Anything nothing depends on is cut or moved to an appendix. A decision that no constraint drives, or a constraint that drives no decision, is a sign something is missing.
6. **Instances.** The concrete examples, cases, failures, benchmarks or incidents available in the material.
7. **Questions for the author.** Above all, why each nonobvious design choice or proof step is the way it is, and what else was considered. Motivation the author has not supplied must be asked for, not made up.

## 2. Argument

- **Context before claim.** Set out the limitation, observation or constraint first, then state the claim or decision it supports. The reader can only judge a claim once they have its context, so a document that announces its conclusion first has declared the claim, not argued it.
- **Concrete motivation.** Motivation is a goal ("we need to bound X by Y", "writes must stay under 50 ms at p99") or an obstacle ("bounding each term separately loses a factor of n, because ...", "a single leader saturates at 12k writes/s"). A sentence that only announces the next step ("Naturally, one asks ...", "We now turn to ...") is not motivation.
- **Example before generalization** (Peyton Jones). A specific instance gives the reader something to test the general statement against.
- **Results, not history** (Widom). In a paper, tell the story of the results, not of how you arrived at them. Keep the story linear, and move significant interruptions to an appendix. This does not apply to design docs, where the alternatives considered are part of the content (section 3).
- **Why before significance.** Readers want to know why a result holds before being told it matters (Knuth).
- **Explicit epistemic status.** Distinguish what is known, what this work shows, and what is conjecture. In a design doc, distinguish what is decided, what is proposed, and what is open. Hedge once, where the uncertainty is, and only as much as the evidence warrants. Use no superlatives about your own work (Knuth).
- **Every object is used.** Refer to each figure, table, diagram and important equation from a sentence that reads something off it or draws a conclusion from it, placed where the reader needs it.
- **No recycled text.** A sentence that repeats an earlier section either adds what its own section needs (a detail, a consequence, a qualification) or is deleted.
- **Positioned citations.** When you discuss a prior work, say how it relates to this work or to another cited work. The relation can be a shared limitation, a different assumption, or what this work takes from it or does differently. The failure is a run of sentences that each describe one prior work in isolation ("X proposed A. Y extended A to B. Z applied B to C."). That lists the literature but never shows where this work fits in it. Citing one work per sentence is fine when the sentence states such a relation. The same holds for prior systems in a design doc.
- **At least one displayed instance.** Aggregate results need a shown example, case or failure from the material, or readers will assume individual cases were inspected. If none exists, say so plainly and limit claims about how individual cases behave to what the aggregates support.
- **Diagrams depict the mechanism.** Method figures and architecture diagrams show components and how they connect. Settings, datasets, results and narration go in the text.

The rules on used objects, recycled text, citations, displayed instances and diagrams, along with context before claim, adapt the six scientific-slop patterns of Oh et al. (2026).

## 3. Design docs, RFCs and decision records

Ubl ("Design Docs at Google") puts it directly: the design doc is the place to write down trade-offs. A doc that says "this is how we will build it" without trade-offs, alternatives and the reasoning behind decisions is an implementation manual. If there truly were no trade-offs, the doc probably should not exist.

The default failure is a confident tour of the chosen design. It lists components, presents every property as a benefit, and appends an alternatives section of strawmen afterward. Prevent it by treating each significant choice as a decision record (Nygard's architecture decision records: context, decision, consequences). For each decision, state:

1. **The force.** The requirement, constraint or failure that makes a decision necessary, with numbers where they exist: load, latency budget, data size, cost, team size, deadline, compatibility. "Must be scalable" is not a force; "must sustain 40k writes/s with p99 under 50 ms" is.
2. **The options actually considered,** each in its strongest form, including keeping the status quo. Each rejected option gets the reason it lost, tied to a specific goal or constraint.
3. **The deciding reason.** Usually one or two factors decide. Say which, and why they outweigh the others.
4. **The cost accepted.** What the chosen design gives up or makes harder. Rust's RFC template has a "Drawbacks" section. A decision with no stated cost either had no real alternative (state it in one sentence and move on) or hides its trade-off.
5. **Reversibility.** Say which decisions are expensive to undo: data formats, public APIs, storage engines, anything clients depend on. These get the most justification; cheap, reversible choices get the least.

Label alternatives you think of yourself as suggestions for the author to evaluate. Never present them as options that were considered and rejected.

Further rules:

- **Context is facts.** The context section gives objective background briefly and links to details (Ubl). Arguments for the design belong elsewhere.
- **Goals are checkable, and non-goals are real.** A goal says how you would know it was met. A non-goal is something a reader could reasonably expect the system to do that is deliberately excluded, such as Ubl's example of ACID compliance for a database. A negated goal like "the system should not crash" is not a non-goal.
- **Present the design through its decisions.** Start with an overview, then go into the parts where decisions live. Sketch only the parts of APIs and schemas that bear on a trade-off, and don't paste full definitions, which bury the trade-offs and go stale (Ubl). A system-context diagram shows where the system sits among things the reader already knows.
- **Failure behavior is concrete.** For each dependency that can fail, say what happens, what users see, how it is detected and how it recovers. "We will add monitoring" is not an answer.
- **Rollout and rollback.** Give the migration steps, how to turn the feature off, and what becomes irreversible once shipped.
- **No template filling.** Omit a section that has nothing real to say, or state in one line why it does not apply. A cross-cutting section (security, privacy, observability) explains how this design affects that concern, not general best practice.
- **Open questions are listed.** Say where the design is unresolved and what input is needed, rather than smoothing it over.
- **Evidence where it exists.** Use benchmarks, prototypes and incidents from the material. Ubl: "I tried it out and it works" is one of the best arguments for a design. Back-of-envelope estimates show their inputs.

**The disagreement test.** A reviewer who disagrees should be able to point to the specific decision, the reason given for it, and the number or assumption they dispute. If they cannot, the doc has hidden its reasoning.

## 4. Mathematical exposition

For each derivation or proof:

1. State the goal first, exactly: the statement to be proved or the quantity to be bounded.
2. Say why the obvious approach fails, concretely. If you don't know why, ask the author.
3. Keep the reader synchronized with the strategy, with short clauses saying what the current subgoal is and how the proof will reach it. Knuth's model proof does this. Signposts about the proof's goals are good; signposts about the document's own layout are not.
4. Mark the crux and give the intuition for why it works. Compress routine steps or move them to an appendix.
5. Prefer a direct proof to an unnecessary proof by contradiction. It shows why the result holds, and in Knuth's example it also needed fewer assumptions.
6. After the result, say what it buys and where it is used next.

For each definition, say what problem it solves and why the simpler alternative is inadequate. Give one example and, where useful, a non-example. State it twice, formally and informally (Knuth). For each assumption, name the step that uses it and what breaks without it.

Knuth's rules for formulas (*Mathematical Writing*, 1989):

- Separate adjacent formulas with words: "Consider S_q, where q < p", not "Consider S_q, q < p". Otherwise they read as one formula.
- Do not start a sentence with a symbol. The reader cannot see where the sentence begins, and the symbol cannot be capitalized.
- In running text, write words instead of ∴, ⇒, ∀ and ∃.
- The sentence before a theorem is complete and, ideally, motivating. The theorem statement is self-contained, because readers jump straight to theorems.
- Do not list formulas homework-style. Tie them together with running commentary.
- Define every variable when it is introduced. Never use one notation for two things, or two notations for one thing.
- Minimize subscripts, and don't name elements you never need to name. Halmos: the best notation is no notation.
- Display important formulas, and number only the ones you refer to. Punctuate displayed equations as parts of sentences. Never display a false equation, because skimming readers take displays as true.
- In papers and mathematical exposition, "we" means the author and the reader together. In a design doc it usually means the team; say so if it could be ambiguous.

**The blah test** (Knuth). Many readers skip formulas on a first reading, so the text must still read smoothly with every nontrivial formula replaced by "blah." A stronger version: the prose between displayed equations must tell the whole story on its own (the goal, the obstacle, the idea, the payoff). If it reads as "We have ... Then ... Thus ... Hence ...", rewrite it.

## 5. Sentences

- **Characters as subjects, actions as verbs** (Joseph Williams, *Style*). Turn nominalizations back into verbs: "we performed an optimization of" becomes "we optimized". Journal editors who measured AI-assisted submissions found them harder to read, with more nominalizations, longer words and more jargon.
- **Reader expectations** (Gopen and Swan, "The Science of Scientific Writing"). Readers take the end of a sentence as its emphasis. Put familiar information that links backward at the start, and new or important information at the end. Keep the subject close to its verb. Give context before asking the reader to take in something new.
- **Orwell's six rules** ("Politics and the English Language", paraphrased):
  1. Don't use figures of speech you are used to seeing in print. Readers no longer see them, and they stand in for a precise statement.
  2. Prefer the short word.
  3. Cut any word that can go. Strunk and White say the same ("omit needless words"), but keep the words that help parsing. Knuth: write "Assume that A is a group", not "Assume A is a group".
  4. Prefer the active voice.
  5. Prefer everyday English to jargon and foreign phrases.
  6. Break any of these rules rather than write something barbarous.

  In technical writing, rule 5 needs a qualification: a precise technical term beats a vague everyday one, but don't use jargon where a plain word is equally precise. Avoid long stacks of nouns used as adjectives; Knuth's example is "packet switched data communication network protocol problem".
- **The curse of knowledge** (Pinker). Define what the reader doesn't know, and never define what they do.
- **Specific over general.** Give numbers with conditions and baselines, not "significantly improves" or "highly scalable".
- **Name the reasons and the items** (Widom). Never write "for various reasons"; give the reasons. Use "etc." only when the remaining items are obvious ("phases 1, 3, 5, 7, etc."), never to stand for items you have not named ("volatility, scalability, etc.").
- **Every "this" has a referent** (Widom, after Ullman). When "this", "that", "these" or "it" could point to more than one thing, add the noun: "this gap", not "this".
- **The opening sentence is the best sentence.** Don't open with a sentence of the form "An X is Y" (Knuth).

### Simplified Technical English (ASD-STE100), applied loosely

ASD-STE100 is the controlled-language standard used in aerospace maintenance documentation. Its idea is that a reader should not be able to misread a sentence. Do not follow it literally here: its approved dictionary and ban on most "-ing" forms are too restrictive for papers and design docs. Use its rules as defaults and as review triggers.

- **One word, one meaning; one meaning, one word.** In the standard, each approved word has a single meaning and part of speech. Here, pick one term per concept and never use it for anything else. Never vary terms for elegance, because in technical writing a new word signals a new thing. Don't use the same word as both a noun and a verb with different meanings. In a design doc, a component keeps the same name everywhere, including in diagrams.
- **One new fact per sentence.** Give information gradually, because readers take in one new thing at a time. A sentence that introduces two new things should usually become two sentences.
- **Sentence length as a review trigger.** STE caps descriptive sentences at 25 words and procedural ones at 20. Treat a sentence over about 25 words as a candidate for splitting, not a violation. Theorem statements and carefully qualified claims may need more.
- **Noun clusters of at most three words.** Break longer chains with prepositions: "inlet valve of the high-pressure fuel pump", not "high-pressure fuel pump inlet valve".
- **Simple tenses, and name the actor** when it matters: which service, which team, which user. This is where Orwell's active-voice rule matters most: procedures, method descriptions and the description of a design.
- **Topic first.** The first sentence of a paragraph says what the paragraph is about. Keep paragraphs short.
- **Procedures are imperative, one instruction per sentence.** Use a numbered list for three or more steps or conditions instead of chaining them in one sentence. This applies to reproduction steps, algorithms written in prose, rollout and rollback plans, and setup sections of blog posts.
- **Never shorten by deleting.** Keep articles, subjects and verbs explicit, and never drop a fact, number, condition or scope qualifier to meet a length target. Split the sentence instead.

Scan last for leftover LLM habits. This list is for scanning, not a target. When an item turns up, rewrite the sentence rather than swapping in a synonym, since a synonym keeps the empty sentence.

- **Stock significance:** pivotal, crucial, plays a key role, underscores, landscape, realm, testament.
- **Stock vocabulary:** delve, leverage, utilize, robust, seamless, harness, unlock, showcase, nuanced, intricate. In design docs also: scalable, flexible, extensible, maintainable, future-proof, best practices, when used without a number or a concrete scenario.
- **Stock moves:**
  - "It's not X, it's Y" and "not just X, but Y".
  - Rhetorical questions used as transitions, and colon reveals.
  - Lists of three used for rhythm.
  - "It is worth noting", "importantly", "notably", "interestingly".
  - Closing sentences that restate the paragraph.
  - Trailing clauses that assert vague importance.
- **Typography:** bold or italics for emphasis (italics are for definitions and quotes; Widom), headers on everything, bullets where prose belongs, frequent em dashes.

## 6. Form

Write prose paragraphs. Use lists only for genuinely parallel items, such as a contributions list, hyperparameters, goals and non-goals, or procedure steps. Use headers only at the depth the venue uses. A table is good for comparing alternatives against the same criteria, but the prose must still say which criterion decided and why.

Papers:

- **Abstract:** problem, gap, approach, main quantitative result, implication.
- **Introduction:** Widom's five questions, roughly a paragraph each: what the concrete problem is, why it matters, why it is hard (why naive approaches fail), why existing approaches fall short, and what the key idea and results are, with their limitations. End with the contributions, stated so they can be refuted, as a list that names the section supporting each. The list doubles as the outline, so no separate "the rest of this paper is organized as follows" paragraph is needed.
- **Related work:** organized by idea and contrasted with this work.
- **Preliminaries:** the notation, terminology and background the paper needs but did not originate, kept short. This marks off what is new from what came before. Define global terms here and other terms just before their first use.
- **Running example:** where possible, one example introduced early and reused throughout.
- **Method:** enough detail to reimplement it, with the reason for each design choice. A clear new contribution should appear by about a quarter of the way through the paper (Widom). Describe it top-down, so the reader can see where it is going and can skip ahead.
- **Experiments:** a reproducible setup, with each table's and figure's takeaway stated in the text. Compare against a naive baseline, against prior work, and among this work's own variants where there are several. Measure sensitivity to the important parameters and scaling, not only a headline number. Don't choose experiments or settings that show the work only at its best.
- **Limitations:** specific enough that a reviewer would recognize them.
- **Conclusions:** a short paragraph that does not repeat the abstract or introduction. Where possible, it makes the introduction's claims concrete with the measured numbers.
- **Appendices:** detailed proofs and algorithms that most readers will skip. Nothing needed to understand the contributions goes there.

Design docs (adapt to the team's template; drop sections with nothing to say):

- **Context and scope:** the background facts, briefly, and what is being built.
- **Goals and non-goals.**
- **Design:** an overview, then each significant decision with its force, options, deciding reason and cost (section 3).
- **Alternatives considered:** whole-design alternatives, if any, in their strongest form.
- **Cross-cutting concerns:** only those the design actually affects.
- **Rollout, migration and rollback.**
- **Open questions.**

An architecture decision record is a single decision: status, context, decision, consequences (including the bad ones).

Blog posts can use the first person and more voice. Open with the concrete problem, result or surprising observation. All the argument and precision rules still apply.

## 7. Process

1. Write the plan (section 1) and get the author's corrections.
2. Draft one section at a time, because a whole document drafted in one pass comes out uniform and thin. Revise earlier sections when later ones change them (Halmos: write in spirals).
3. Review in a separate pass, ideally by a fresh agent that did not see the drafting, so the draft is not judged by the context that wrote it. Work top-down:
   - **Substance.** Check every number against the material. Confirm nothing is invented, including decision history, and locate each claim's evidence. Check that every bibliography entry is complete and consistent with the others.
   - **Argument.** For each sentence, ask what it claims, whether it is true, and whether it follows from what came before. Check that the skeptic's objections are answered. Compare the dependency map against the text, looking for unused objects, undefined terms, claims before their context, isolated citations, and missing instances.
   - **Design.** For each significant decision, check that the force, the options, the deciding reason and the cost are all present, and that the most expensive-to-reverse decisions are the best justified. Check that non-goals are real, that failure behavior is concrete, and that no section is template filler. Apply the disagreement test.
   - **Math.** Apply the blah test. Check that each derivation states its goal first, that the crux is marked, and that each assumption is linked to its use.
   - **Sentences.** Apply section 5, including the STE triggers: sentences over about 25 words, noun clusters over three words, terms used in two senses, and two new facts in one sentence. Delete every sentence whose removal loses nothing.

   Report each finding with its location and a proposed minimal fix, rather than silently rewriting.
4. When the author marks a passage as bad, name the specific fault and offer to add it to this file as a rule.

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
-->
