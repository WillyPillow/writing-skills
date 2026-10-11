- Feature Name: `prior_art`
- Start Date: 2018-02-12
- RFC PR: rust-lang/rfcs#2333
- Rust Issue: N/A (process change)

# Summary

This RFC adds a *Prior art* section to the RFC template. In it, authors can describe how other programming languages and their communities have handled the problem the RFC addresses. The section can also cite theoretical work such as academic papers.

# Motivation

Few problems that come up in an RFC are new to Rust. Error handling, generics, async I/O, module systems, macros, and package management have all been designed several times over in other languages. Those languages made choices, shipped them, and found out over years which choices held up and which didn't. Some of them wrote it all down.

The current template has no slot for this. Authors who know the relevant history sometimes bring it up in *Motivation* or *Alternatives*. When it does appear it is scattered, and often it is left out altogether. Then reviewers raise it in the comments: "Swift did this and regretted it", "Haskell has had this since 1998", "there is a paper on exactly this soundness hole". The discussion grows by dozens of comments that cover ground the author could have covered up front.

A dedicated section would help in three ways.

**It helps authors.** A heading in the template prompts the author to go and look. Someone writing an RFC about pattern-matching ergonomics who stops to check OCaml, Scala, and F# will write a better RFC whatever they end up proposing.

**It helps reviewers.** A reviewer can evaluate a design faster if they can see how it compares to designs they already know. "This is like C#'s `using` but scoped to the block" says more than several paragraphs written from scratch.

**It improves the archive.** Accepted RFCs are the design record of the language. People read them years later to learn why Rust works the way it does. If the record shows what was borrowed, what was changed, and what was deliberately rejected, future contributors can reason from it instead of rediscovering it.

Theoretical work belongs in the section too. Several Rust features, including the borrow checker, the trait system, and variance, rest on ideas from programming-language research. When an RFC touches the type system, pointing to the relevant papers lets reviewers check soundness arguments against established results.

# Guide-level explanation

The RFC template gets a new section, placed between *Rationale and alternatives* and *Unresolved questions*:

```markdown
# Prior art
[prior-art]: #prior-art

Discuss prior art, both the good and the bad, in relation to this proposal.
A few examples of what this can include are:

- For language, library, cargo, tools, and compiler proposals: Does this
  feature exist in other programming languages and what experience have
  their community had?
- For community proposals: Is this done by some other community and what
  were their experiences with it?
- For other teams: What lessons can we learn from what other communities
  have done here?
- Papers: Are there any published papers or great posts that discuss this?
  If you have some relevant papers to refer to, this can serve as a more
  detailed theoretical background.

This section is intended to encourage you as an author to think about the
lessons from other languages, provide readers of your RFC with a fuller
picture. If there is no prior art, that is fine - your ideas are
interesting to us whether they are brand new or if it is an adaptation
from other languages.

Note that while precedent set by other languages is some motivation, it
does not on its own motivate an RFC. Please also take into consideration
that Rust sometimes intentionally diverges from common language features.
```

An author who has nothing to report can say so in a sentence. The section is a prompt, not a gate.

## What good prior art looks like

The most useful entries go beyond "language X has this". They say:

- what the feature looks like there, briefly, with a short code sample if it helps;
- how it has worked out in practice, including complaints and pitfalls the community has run into;
- how the proposal here is similar and how it differs, and why.

Here is a short example for a hypothetical RFC adding default arguments:

> Python, C++, Kotlin, and C# all support default arguments. In Python,
> defaults are evaluated once at definition time, which is a well-known source
> of bugs with mutable defaults. C++ allows defaults only in trailing
> positions and resolves them at the call site, which interacts poorly with
> virtual functions. This proposal evaluates defaults at each call, like
> Kotlin, and disallows them in trait method signatures to avoid the C++
> issue.

Entries about negative experiences are as useful as positive ones, and often more so.

## Community and process RFCs

Not every RFC is about the language. RFCs about governance, moderation, release processes, or the RFC process itself can look at other open-source projects, standards bodies, and foundations. For this RFC, that means the Python PEP template, which has no general prior-art heading but whose *Rationale* section often fills that role, and the IETF RFC tradition of citing related documents.

# Reference-level explanation

The change is a single edit to `0000-template.md` in the `rust-lang/rfcs` repository: the section text above is inserted after *Rationale and alternatives*.

RFCs already open when this lands don't need to add the section. Their authors may if they like.

`README.md` in the RFC repository will get a short paragraph saying the section exists and that a sentence like "no relevant prior art was found" is an acceptable entry.

# Drawbacks

- **Longer RFCs.** Writing an RFC already takes a lot of work, and a new section adds to it. Some authors may feel they have to survey a dozen languages before submitting, which could discourage first-time contributors. The template text tries to counter this by saying an empty section is fine.
- **Appeal to precedent.** Listing what other languages do can turn into "everyone else does it, so we should too". Rust has often and deliberately broken from common practice, for example by having no null, no exceptions, and no inheritance. The template says outright that precedent alone doesn't justify a proposal.
- **Inaccuracy.** An author may describe another language's feature wrongly or out of date. Reviewers who know that language will need to correct it, which adds a little review burden. Still, mistakes made in the open are better than assumptions nobody states.

# Rationale and alternatives

## Fold it into *Alternatives*

Prior art could stay a subsection of *Rationale and alternatives*. That section, though, is about other designs for Rust. Prior art is about what happened elsewhere. The two overlap, but keeping them apart makes each easier to read, and a separate heading is easier to notice.

## Make it mandatory with a minimum bar

The RFC process could require, say, at least two cited languages. That would be easy to game, would add little, and would push away newcomers. An optional prompt gets most of the benefit at less cost.

## Do nothing

Reviewers already bring up prior art in the comments, and that will go on. The value of this change is that the material ends up in the document and not in a long comment thread, and that authors are nudged to do the research before reviewers have to.

# Prior art

As this RFC adds the section, it should fill one in.

- **Python PEPs.** PEP 1 describes the expected PEP sections, including *Rationale*, which is supposed to explain why particular design decisions were made and to describe related work. Many PEPs survey other languages there, for example PEP 572 on assignment expressions and PEP 634 on pattern matching.
- **Swift Evolution.** The Swift proposal template has *Alternatives considered*, and proposals often discuss Rust, Kotlin, and C# in it, though there is no separate heading for it.
- **IETF RFCs.** The IETF expects informative and normative references, and many documents have a *Related Work* section.
- **Academic papers.** A *Related Work* section is standard in computer-science papers. Reviewers check that authors know the field and have placed their contribution in it. The section proposed here is a lighter version of the same convention.

All of these suggest that a dedicated place for related work is a well-tested convention that helps both authors and readers.

# Unresolved questions

- Should the section come before or after *Rationale and alternatives*? This RFC puts it after, so readers meet Rust-specific options first, but the order can be changed at little cost.
- Should the RFC book or README collect a list of language references (specifications, design documents, notable blog posts) to make research easier for authors? That could be done separately.
