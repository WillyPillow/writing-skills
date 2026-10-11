# Rust RFC 2333: `prior_art`

- Feature Name: `prior_art`
- Start Date: 2018-03-02
- RFC PR: rust-lang/rfcs#2333
- Rust Issue: not applicable

## Summary

This RFC adds a *Prior art* section to the standard RFC template. RFC authors use the section to describe the experience of other programming languages and their communities with the feature or design under discussion. The section may also cite theoretical work, such as academic papers, that bears on the proposal.

The change is to the template and to the guidance that accompanies it. It does not change the process by which RFCs are accepted, and it does not make the section mandatory for every proposal.

## Motivation

A design proposal is stronger when its author can show what has been tried elsewhere. Other languages have built similar features, sometimes successfully and sometimes with lessons that the Rust project would benefit from. When these experiences are not written down in the RFC, reviewers must reconstruct them from memory, and the discussion often repeats questions that other communities answered years ago.

The current template invites authors to discuss alternatives and drawbacks, but it does not clearly ask for the broader context. Authors who know of relevant prior work sometimes fold it into the alternatives section, where it is easy to miss. Others omit it entirely because the template gives them no obvious place to put it.

A dedicated section makes the question explicit. It also signals that comparison with other systems is a normal and expected part of the review, not an afterthought.

## Guide-level explanation

The RFC template gains a new heading, placed after *Alternatives* and before *Unresolved questions*. Authors use the section to answer a simple question: how have other languages, libraries, or research communities handled this problem?

A good entry describes what those systems do, where the information came from, and what the experience showed. It should be specific. For example, a sentence that says a feature is "used in some languages" is not useful, while a sentence that names a language, describes its approach, and mentions a known difficulty gives reviewers something concrete to evaluate.

Authors should also note when the prior art is inconclusive. A feature may have been tried and abandoned, or it may have been adopted without a formal evaluation. Both facts matter to a reviewer deciding whether the proposal repeats an old mistake.

The section is optional in the sense that a proposal with no relevant prior art may leave it out. Reviewers may ask for it when they suspect that comparable work exists.

## Reference-level explanation

The template change is small. The new heading is titled *Prior art*. It appears after the *Alternatives* heading in the template file. The template comment beneath the heading explains that authors should discuss the experience of other languages and communities, and may cite theoretical work such as papers.

The section has no required format. Authors may use prose, a list of entries, or a short table. The Rust project does not prescribe citation style, though authors are encouraged to include enough detail for a reader to locate the source.

Existing RFCs are not required to be revised. The section applies to proposals opened after the template is updated.

## Drawbacks

Adding a section increases the length of the template, and some authors may feel pressure to fill it with material that is not really relevant. Reviewers should be willing to ask an author to remove weak entries rather than treat every heading as mandatory.

There is also a risk that authors will describe other systems in a way that favors their own proposal. The section does not solve this problem by itself. Reviewers remain responsible for checking the claims and asking for sources where needed.

## Rationale and alternatives

The main alternative is to leave the template unchanged and rely on reviewers to ask about prior art when it matters. This keeps the template short, but it places the burden of recall on the reviewers, and it does not help authors who are not sure what kind of information is expected.

A second alternative is to add the information to the *Motivation* section. This would avoid a new heading, but motivation is about the problem, not the existing solutions. Mixing the two would make both sections harder to read.

A third alternative is to create a separate document for each proposal's background research. This would be more thorough, but it would add a step that most authors would skip, and it would separate the research from the proposal it supports.

## Prior art

This section is itself a modest proposal, and its precedent is the practice of academic papers and many standards bodies, which commonly include a discussion of related work. The Rust project already includes comparisons with other languages in many of its accepted RFCs, so the change makes an existing practice visible in the template.

## Unresolved questions

The project has not yet decided whether the section should be required for language-level changes while remaining optional for library or tooling changes. This RFC leaves that decision to the teams that review proposals in each area.

It is also unclear how long a prior art discussion should be. The RFC does not set a length limit, and reviewers are expected to use their judgment.

## Future possibilities

If the section proves useful, the project could maintain a shared bibliography of common references, so that authors can cite sources consistently. The template could also include a short checklist that asks authors whether they have consulted the relevant language documentation and any published evaluations of similar features.
