- Feature Name: `tiered_browser_support`
- Start Date: 2017-04-28
- RFC PR: rust-lang/rfcs#1985
- Rust Issue: N/A

# Summary

Official web content that the Rust teams produce for Rust users should work in the browsers those users actually use. We cannot test every version of every browser, any more than the compiler can support every target. This RFC establishes tiers of browser support, modelled on the compiler's platform tiers, and describes what each tier promises.

# Motivation

The Rust project publishes a growing amount of web content:

- the main website, rust-lang.org
- crates.io
- docs.rs
- the standard library and compiler-generated documentation produced by `rustdoc`
- the books and other mdBook-based documentation
- the playground at play.rust-lang.org
- the various team and working-group pages

Each of these was built by a different group of people at a different time, and each makes its own implicit assumptions about which browsers matter. Today, when someone reports that the search box on a rustdoc page does nothing in an older browser, there is no shared answer to the question "is this a bug?". Sometimes the report is fixed promptly. Sometimes it sits open because nobody is sure whether fixing it is worth the effort or whether the fix will make the page worse for everyone else. Contributors proposing a modern CSS or JavaScript feature have no way to know whether they are allowed to use it.

Undocumented expectations cause friction in both directions. Users of less common browsers have no idea what to expect. Contributors either over-engineer for browsers nobody uses, or break browsers that a meaningful number of people depend on without knowing it.

The compiler already solves the same kind of problem. Its target list is split into tiers. Tier 1 targets are tested on every merge. Tier 2 targets are guaranteed to build. Tier 3 targets are supported on a best-effort basis. Contributors and users both know what to expect, and the tiers can be revisited as the world changes. Web content needs the same kind of written policy.

# Guide-level explanation

Browsers are grouped into three tiers.

**Tier 1** browsers are expected to work fully. All features of every official site should function, and layout should look as intended. A defect that affects a Tier 1 browser is a bug and should be prioritized like any other bug that affects many users. Where automated testing exists for a site, it should run against Tier 1 browsers.

**Tier 2** browsers are expected to be usable. Content must be readable and navigation must work, but some enhancements may be missing and the presentation may differ. For example, rustdoc search might fall back to a simpler interface, or an animation might not play. A defect that makes content unreadable or a site unusable in a Tier 2 browser is a bug. A purely cosmetic difference is not.

**Tier 3** browsers have no guarantees. We will accept reasonable patches that improve support for them, provided those patches do not hurt Tier 1 or Tier 2 browsers and do not impose a significant maintenance burden. We will not block other work on them.

Any browser not listed is treated as Tier 3.

The initial lists are:

| Tier | Browsers |
|---|---|
| 1 | The current and previous stable releases of Firefox, Chrome, Safari, and Edge, on desktop. Firefox and Chrome on Android, and Safari on iOS, current release. |
| 2 | Firefox ESR. Releases of the Tier 1 browsers going back roughly two years. Text-mode browsers such as Lynx and w3m, for reading documentation only. |
| 3 | Everything else, including Internet Explorer. |

Text-mode browsers are in Tier 2 for a specific reason: they are a reasonable proxy for screen readers and other assistive technology, and a documentation page that cannot be read in Lynx is very likely to be inaccessible in other ways. This placement is not about the popularity of text-mode browsers.

# Reference-level explanation

## How the lists are chosen

The lists should be based on data rather than guesses. Where the infrastructure team can collect aggregate, privacy-respecting browser statistics from official sites, those statistics should inform the lists. As a rule of thumb, a browser family and version range that accounts for more than about 1% of visits to official sites should be at least Tier 2, and one that accounts for more than about 5% should be Tier 1. Statistics from a single site can mislead, since the audience for crates.io differs from the audience for the beginner-oriented book, so numbers should be pooled where possible.

Data is not the only input. Some users are underrepresented in visit statistics because the site does not work for them and they leave. Teams should consider requests from users who explain that they are stuck on an older browser for reasons outside their control, such as corporate policy or old hardware.

## Who owns the lists

The lists live in the rust-lang/rust-forge repository next to the platform support page. The infrastructure team owns them. Changes go through ordinary pull requests and should be reviewed by at least one member of each team that maintains an affected site. Moving a browser into Tier 1 or out of Tier 2 should be announced on internals.rust-lang.org with at least a few weeks' notice.

The lists should be reviewed at least once a year. Because Tier 1 is defined relative to "current" releases, most of the list updates itself. The review is mostly about Tier 2 and about whether new browsers have become popular enough to be named.

## Obligations of individual sites

Each official site should:

1. Link to the browser support page from its contributing documentation.
2. Prefer progressive enhancement. Core content should be in the HTML and readable without JavaScript where practical. Features that depend on newer platform capabilities should detect them and degrade.
3. Label bug reports that concern a specific browser so that tier-related triage is easy.

Sites may choose to support more than the minimum. Nothing here stops the docs.rs team from making extra effort for a browser that its users happen to need.

## Generated documentation

`rustdoc` output deserves particular care because it is not only hosted on official sites. Every crate author publishes it, often to internal servers and offline mirrors that users read in whatever browser is available. Changes to rustdoc's HTML, CSS, or JavaScript should therefore be checked against Tier 2 browsers before merging, not just Tier 1. The same applies to the mdBook theme used by the official books.

# Drawbacks

Writing down a tier list can be read as saying that people outside Tier 1 matter less. Some users of Tier 3 browsers may feel excluded. The alternative, though, is an unwritten tier list that is applied inconsistently. A written list at least gives those users something to argue with.

Maintaining the list takes time from a small infrastructure team. Collecting statistics has privacy implications that must be handled carefully, and may not be possible at all for some sites.

# Rationale and alternatives

**Support everything.** This is unrealistic for a volunteer project. Without a boundary, contributors either avoid useful features out of caution or break things unknowingly.

**Let each site decide.** This is roughly the current situation. It produces inconsistent experiences and leaves contributors guessing.

**Use a third-party definition** such as a "last two versions" query. This is easy to automate, and may be a good input for build tooling, but it does not reflect the specific audience of Rust sites and does not capture considerations such as accessibility proxies.

# Unresolved questions

- What source of statistics is acceptable from a privacy standpoint?
- Should the playground, which depends heavily on a code editor component, have its own exception for Tier 2?
- How should support for browser extensions that modify pages, such as ad blockers, be treated?
