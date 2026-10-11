# Rust RFC 1985: Tiered browser support for official web content

- Start Date: (draft)
- RFC PR: (pending)
- Rust Issue: (pending)

## Summary

Official web content produced by the Rust teams for consumption by Rust users should work in the majority of browsers that Rust users are visiting these sites in. This RFC proposes that the project maintain a published list of browsers and versions, grouped into tiers of support, and that each tier carry a defined expectation about how much testing and fixing the teams commit to.

## Motivation

The Rust project publishes a substantial amount of web content. This includes the main website, the book and other learning resources, the documentation generated for the standard library and crates, the package registry front end, and various project dashboards. Users reach this content from a wide range of devices and browsers, and the set of browsers in use changes over time.

The Rust compiler supports a finite number of targets, and each target has a documented level of support. The reasons are familiar: the project has limited time, limited expertise in each platform, and limited testing resources. The same constraints apply to web content. No team can test every version of every browser, and no team can guarantee that its pages render correctly everywhere a visitor might arrive.

Without a stated policy, each team makes its own ad hoc decisions. One team may test only the latest release of a single browser, while another may spend effort on old versions that very few users still run. Contributors have no way to know whether a bug report from an obsolete browser deserves attention. Users have no way to know which browsers the project is aiming to support.

A published tier list addresses these problems. It gives contributors a shared reference for what to test, lets them prioritize fixes, and tells users what to expect. It also makes the trade-offs visible, so that the community can discuss whether a given browser belongs in a higher tier.

## Guide-level explanation

The project will maintain a document listing browsers and version ranges, each assigned to one of several tiers. A browser in the highest tier is one that the project actively tests, and for which a regression is treated as a bug that should be fixed before a site change is released. A browser in a middle tier is one that the project expects to work for core functionality, with less rigorous testing and more tolerance for cosmetic problems. A browser in the lowest tier is one that the project does not test, and for which it accepts reports but does not commit to a fix.

Content authors should check the tier list when they add a feature that depends on a newer platform capability. If the feature would break a browser in the top tier, the author must either provide a fallback or get agreement to exclude the feature. If the feature would break only a lower tier, the author may proceed with a note in the change description.

Users who encounter a problem should first check whether their browser appears in the list, and if it does, report the problem through the usual channel. The tier shown in the list indicates how the project will respond.

## Reference-level explanation

The tier list is stored in the repository of the web team and is reviewed whenever the set of supported browsers is changed. Each entry names a browser, gives a version or version range, and states the tier. The list also records the date of the most recent review so that readers can judge how current it is.

The initial proposal defines three tiers. Tier one covers the current and immediately preceding release of the major desktop and mobile browsers, weighted by usage share among Rust users as measured by the project's own analytics where available and by public statistics otherwise. Tier two covers older versions that still have meaningful usage and the current release of smaller browsers that are used by a noticeable minority. Tier three covers everything else.

For tier one browsers, the web team commits to running automated tests in CI where practical, to including the browser in manual review before a major release, and to treating a rendering or functional regression as a release blocker. For tier two, the team commits to a periodic manual check and to fixing functional breakage on a best-effort basis. For tier three, the team commits only to considering reports and to documenting known limitations where a fix is not feasible.

The team may move a browser between tiers. A browser moves up when its usage among Rust users grows enough to justify the testing cost, and down when its usage falls. Any change must be announced in the same place as the list, with the reason stated.

## Drawbacks

A tier system imposes a cost on the teams that maintain the content. Testing a larger set of browsers takes time, and the tier list gives reviewers a concrete obligation to check. Some contributors may feel that the list excludes users they care about, particularly those on older or less common platforms. The RFC acknowledges that usage data is imperfect and that a browser with a small share can still be important to a particular audience, such as users in a region where it dominates.

There is also a risk that the list becomes a substitute for good engineering. A page that works in tier one browsers but degrades badly elsewhere may still be acceptable under this policy, and the policy does not require graceful degradation. The authors consider this a reasonable limit on scope, since graceful degradation is a separate concern that the web team can address in its own guidelines.

## Rationale and alternatives

One alternative is to commit to supporting all browsers that are still in use. The authors rejected this because it is not achievable with the available resources and because it would make every change expensive to review.

A second alternative is to support only the latest release of each browser. This is simpler to state and to test, but it leaves out users on operating systems that cannot upgrade their browser, a group that tends to include users in less wealthy regions and on older hardware. The tiered approach keeps a path for those users without requiring full support.

A third alternative is to let each team choose its own list. This preserves autonomy, but it recreates the inconsistency that the RFC aims to fix. A single list shared across the project gives every team the same starting point.

## Prior art

Several large web projects publish browser support policies of this kind. Some use a similar grade system with three or four levels, and others define support in terms of a rolling window of recent versions. The Rust proposal borrows the tiered structure from these examples and adapts it to a project whose content is mostly documentation and static pages rather than a complex application.

## Unresolved questions

The first open question is how the project should measure usage among Rust users, since the available data is partial and may be biased toward visitors who are more technical. The RFC proposes using whatever the project already collects and supplementing it with public statistics, but leaves the exact method to the team.

The second question is how to handle assistive technology, such as screen readers, which may depend on browser versions that look unimportant by usage share. The authors suggest that accessibility concerns should be able to raise a browser's tier regardless of its share, and that this rule be written into the policy explicitly.

The third question is how often the list should be reviewed. The authors suggest an annual review with an interim check whenever a major browser releases a version that changes an important capability.

## Future possibilities

The tier list could be extended to cover feature detection guidance, so that authors know which capabilities are safe to use in each tier without a fallback. It could also be linked from the documentation footer so that users can see the support level of the browser they are using. Over time, the project could publish its usage data in aggregate, which would make the tier decisions easier to audit.
