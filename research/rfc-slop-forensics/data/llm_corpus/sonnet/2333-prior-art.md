# RFC 2333: prior_art

- Feature Name: `prior_art`
- Start Date: 2018-02-12
- RFC PR: rust-lang/rfcs#2333
- Rust Issue: N/A

## Summary

This RFC adds a *Prior art* section to the RFC template. In it, RFC authors may discuss the experience of other programming languages and their communities with respect to what is being proposed. The section may also discuss theoretical work, such as academic papers.

## Motivation

Rust did not appear from nowhere. Its ownership model draws on region-based memory management and linear and affine type systems. Its traits descend from Haskell's type classes. Its pattern matching comes from the ML family, and its `async` and iterator designs have counterparts in C#, JavaScript, Python and many other languages. When the community proposes a new feature, there is almost always somebody, somewhere, who has tried something similar.

Learning from that experience is valuable, for several reasons.

**It prevents repeating mistakes.** If another language tried an approach and later regretted it, we want to know why before we adopt it. A short note such as "Java added checked exceptions and most of the ecosystem now works around them" can save the team months of debate.

**It confirms good ideas.** If a feature has worked well for a decade in a language with a similar audience, that is real evidence. It does not settle the question, but it shifts the burden of proof.

**It sharpens the proposal.** Writing about how others solved the same problem forces the author to state which aspects of the design are essential and which are accidents. It also exposes whether the proposed design is novel or a variation on an existing one.

**It helps reviewers.** Members of the teams reading the RFC come with different backgrounds. One may know Haskell well and another may have written C++ for twenty years. A prior art section lets each check whether the author has understood the relevant precedent and lets them contribute what they know.

**It is already happening informally.** Many accepted RFCs already include discussions of other languages, often under headings like "Related work" or tucked into the rationale. Giving it a standard place makes it easier to find and easier to remember to write.

The community's discussions also often have a recurring pattern: someone asks "what do other languages do here?", an author answers in a comment thread, and the answer is then lost when the thread scrolls out of view. Putting the answer into the document preserves it for future readers, including people who later want to understand why a decision was made.

## Guide-level explanation

The RFC template gains a new section placed between *Rationale and alternatives* and *Unresolved questions*:

```markdown
# Prior art
[prior-art]: #prior-art

Discuss prior art, both the good and the bad, in relation to this proposal.
A few examples of what this can include are:

- For language, library, cargo, tools, and compiler proposals: Does this feature exist in other programming languages and what experience have their community had?
- For community proposals: Is this done by some other community and what were their experiences with it?
- For other teams: What lessons can we learn from what other communities have done here?
- Papers: Are there any published papers or great posts that discuss this? If you have some relevant papers to refer to, this can serve as a more detailed theoretical background.

This section is intended to encourage you as an author to think about the lessons from other languages, provide readers of your RFC with a fuller picture. If there is no prior art, that is fine - your ideas are interesting to us whether they are brand new or if it is an adaptation from other languages.

Note that while precedent set by other languages is some motivation, it does not on its own motivate an RFC.
Please also take into consideration that rust sometimes intentionally diverges from common language features.
```

### How an author should use it

Suppose an author is proposing a new form of pattern matching on slices. In the prior art section they might write:

> Haskell and OCaml both support list patterns of the form `x : xs`, which are idiomatic because their lists are linked. Python 3 added extended unpacking (`first, *rest = items`) in PEP 3132 and the community found it intuitive for sequences. Swift's pattern matching on arrays is more limited, and users frequently ask for the Python behaviour. These precedents suggest that the feature is widely wanted, but Rust's slices are borrowed views rather than owned lists, so the binding of the rest must be a subslice, not a new allocation.

The paragraph does three things: it names the precedents, it says what experience tells us, and it explains where Rust differs.

### What the section is not

The section is not a requirement to survey every language. An author may reasonably write "I am not aware of precedent for this" and move on. A proposal does not become better because it lists many languages, and it does not become worse because it lists none. The section is also not an argument from authority. The fact that another language does something is not on its own a reason for Rust to do the same, and the template says so explicitly.

Nor is the section confined to language features. Proposals for Cargo might discuss npm, Bundler or Go modules. Proposals for the community or process might discuss how Python's PEP process, the TC39 stages or the Apache Software Foundation handle the same question.

## Reference-level explanation

The change consists of editing `0000-template.md` in the `rust-lang/rfcs` repository to add the section shown above, immediately before *Unresolved questions*. No other mechanics change.

Existing RFCs are not modified. RFCs in flight are not required to add the section, though reviewers may ask authors to do so if prior art appears relevant.

The section is not mandatory in the sense that an RFC without it will not be rejected on those grounds alone. Because it is part of the template, authors will see the prompt and will have to make a conscious choice to leave it empty or write "none".

The README for the RFC repository should be updated to mention the section when it describes the contents of an RFC.

## Drawbacks

**More work for authors.** Writing about other languages takes time, and some authors will not be familiar with the relevant precedent. This may discourage some contributors. The mitigation is that the section is explicitly allowed to be short, and that other community members can help fill it in during review.

**Risk of superficial surveys.** Authors may add a list of languages with a sentence each without having used them or understood the trade-offs. A shallow comparison could mislead readers. Reviewers should push back on claims they believe are inaccurate, and the template text asks for lessons learned, not a feature matrix.

**Argument by analogy.** Prior art can be used as a rhetorical weapon: "language X has it, so we should too". The template guards against this, but the risk remains in practice.

**Bikeshedding about other languages.** Discussion threads may drift into debates about the merits of languages other than Rust. Moderators and team members should keep conversations focused on the proposal.

## Rationale and alternatives

### Why a separate section

One alternative is to leave the discussion in the *Motivation* or *Rationale* sections, as many RFCs do now. The problem is that it is easy to skip, and it mixes two different things: why the feature is needed, and what we can learn from others who have built it. A named section signals that the second is a normal expectation.

### Why not make it mandatory

A hard requirement would force authors to invent comparisons for features that are truly new or that have no direct counterpart. The prompt achieves most of the benefit with none of that cost.

### Alternative: name it "Related work"

"Related work" is the traditional name in academic writing. "Prior art" is borrowed from patent law and has become common in software discussions, and it is also used by the Python and other communities' proposals. Either name would do; "prior art" is the more familiar in this community and covers non-academic sources such as blog posts and mailing list threads.

### Alternative: do nothing

The community can continue to discuss prior art in comments. The cost is that valuable discussion remains scattered and the RFC itself does not record the reasoning that influenced it.

## Prior art

This RFC is a little self-referential, but prior art for it exists.

- **Python PEPs** have a "Rejected Ideas" section and often a "Rationale" that cites other languages. PEP 3132, for instance, discusses how other languages handle extended unpacking.
- **The Haskell proposals process** asks authors to describe related work and how the proposal compares to existing extensions and implementations in other compilers.
- **Swift Evolution** proposals contain "Alternatives considered" and, since the process was formalized, a standing expectation to cite how other languages approach the problem.
- **The IETF** requires that RFCs for protocols discuss related protocols and the lessons learned from them.
- **Academic papers** have a related work section as a standard component, whose purpose is to situate the contribution relative to existing results.

In each case the experience has been that the section improves discussion and provides a record. It has also sometimes been abused as a list of citations without analysis, which is why the guidance emphasises lessons learned.

## Unresolved questions

- Should the section be placed earlier in the template, for example after *Motivation*, so that it informs the reading of the design rather than following it?
- Should a similar section be recommended for the pull request template used by the compiler and standard library?
- Would the team want a short list of resources, such as a curated bibliography of foundational papers, linked from the template?
