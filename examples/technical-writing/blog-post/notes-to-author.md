# Notes to the author: CI speed-up blog post

You weren't available to answer questions, so I drafted from your notes alone. Anything I couldn't support from them is marked `[TODO: ...]` in the draft. The questions below match those markers.

## Planning notes

**Reader.** Engineers at other companies who own or suffer a slow CI pipeline. They know GitHub Actions, Docker and the idea of a build cache. They don't know our monorepo, our pipeline layout or Turborepo's filter syntax.

**The point.** Our PR CI got faster (median 41 to 12 minutes, p90 58 to 19) mainly because we shortened the critical path: we split the long serial integration job and cached the builds in front of it. Doubling runner size bought only 3 minutes. This claim could be wrong: if most of the gain came from something that faster hardware would also have delivered, the lesson "find the critical path before buying hardware" doesn't follow.

**The skeptic.**

1. "Couldn't you have just bought bigger machines?" The bigger-runner trial answers this: twice the cost, 3 minutes saved at the median. It sits in its own section in the middle of the post.
2. "Did you make CI faster by testing less?" For TypeScript we skip unaffected packages, but builds and tests still run for everything that changed and its dependents. For Go we tried skipping and backed out after two false greens, so Go tests always run in full. The flaky tests that sharding exposed were fixed or quarantined, not ignored. All of this has its own section.
3. "What did it cost?" Runner spend rose from $3,100 to $3,650 a month. The post states this plainly next to the bigger-runner cost.
4. "Is the before/after comparison fair?" The figures come from two different months (3,912 and 4,307 runs), not from a controlled experiment. The post says which months and how many runs, and makes no per-change attribution of the 29 minutes.

**Argument skeleton** (one line per paragraph, with its source):

- Opening: median PR CI went from 41 to 12 minutes, and p90 from 58 to 19, in two months (numbers from notes).
- Setup: a monorepo of about 380k lines of TypeScript and Go, GitHub Actions on self-hosted runners (notes).
- What dominated wall time: the Go integration tests ran as one 22-minute job. TS builds took 9 minutes and image builds 6 (notes). How the jobs depend on each other is TODO.
- Sharding: timings come from gotestsum `--junitfile`, a 60-line script bin-packs tests into 6 shards, and the slowest shard takes 5 minutes (notes).
- Bigger runners: 16 vCPU instead of 8, 2x cost, 3 minutes saved at the median because the serial integration job was the long pole, so we reverted (notes). When this trial ran relative to sharding is TODO.
- TS remote cache: Turborepo remote cache self-hosted on MinIO, a 71% hit rate on PRs, and the TS build median went from 9 to 2.5 minutes (notes).
- Docker layer order: `go mod download` before the source COPY, so an image build takes 1 minute instead of 6 when go.sum is unchanged (notes).
- TS affected-package filter: `turbo --filter=...[origin/main]` (notes).
- Go test selection rejected: `go list -deps` missed tests that read testdata from other packages, there were two false greens in one week, and Go tests now always run in full (notes).
- Flakes: sharding exposed 14 order-dependent tests (shared DB state); 11 were fixed and 3 quarantined (notes).
- Cost and survey: spend went from $3,100 to $3,650 a month, and "CI is a blocker" from 58% to 19% (n = 64) (notes).
- Lesson: find the critical path before buying hardware (notes).

**Dependency map.** The integration job's 22 minutes motivates both the sharding and the explanation of why bigger runners failed. Turborepo is used for both the remote cache and the filter, so it is introduced once in the cache section. The flaky-test finding depends on sharding (order changes) and is placed after it. The cost figure is used to compare against the 2x cost of bigger runners. There's no figure or table. A pipeline diagram (before and after) would support the critical-path argument, but I don't have the pipeline shape (see questions).

**Instances.** The 22-minute integration job, the bigger-runner trial, the two false greens from `go list -deps`, and the 14 order-dependent tests. I don't have the code for a concrete instance (the Dockerfile change, the sharding script, a false-green test). See questions.

## Questions for the author

1. **Chronology of the bigger-runner trial.** Your list says "in order", with bigger runners third, after sharding. But the reason they didn't help was "the long pole was the serial integration job", which sharding had already removed. Did you try bigger runners before sharding, or was the 3-minute saving measured on the old pipeline? The post's lesson depends on this, so the draft has a TODO there.
2. **Pipeline shape.** Which jobs ran in sequence and which in parallel, before and after? For example, does the image build gate the integration tests, and does the TS build run alongside them? With this I can say what the critical path was and show it, ideally as a small before/after diagram. Right now the post can't say how 22 + 9 + 6 minutes relates to 41.
3. **How you found the critical path.** Did you read job timings from the Actions UI, use a script, or something else? Readers who take the lesson will want the method.
4. **Contribution of each change.** Do you have any measurement of how much each change cut from the median? The draft doesn't attribute the 29 minutes to individual changes.
5. **Bigger-runner cost.** Is "2x" the per-minute runner price, or the monthly spend you measured or projected? Did the 3-minute saving come from a trial period with a run count?
6. **Sharding script details.** How often are the timings refreshed, and what happens to a new test with no timing yet? Can we publish the script or an excerpt?
7. **Dockerfile change.** Can I show the actual before/after lines? It's a good concrete instance for readers.
8. **Turborepo on MinIO.** Is there a cache server in front of MinIO (Turborepo's remote cache speaks an HTTP API, not S3 directly)? If so, which one?
9. **False greens.** Can you describe one of the two cases: which test, which testdata it read, and how the breakage was found? Also, how did the 71% hit rate and the TS filter interact? Is the 71% measured on the packages that still build after filtering?
10. **Quarantine.** What does quarantine mean for the 3 tests (still run but non-blocking, or skipped)? Can I link the tracking issue?
11. **Survey.** Did both surveys have 64 respondents, and when did each run? Was it the same group of people?
12. **Byline and title.** Should the post go out under your name? I proposed a title. Change it if you like.

## Choices I made

- I did not present any alternative you didn't mention. The only rejected options in the post are the two you tried and reverted: bigger runners and Go test selection.
- I worked out two derived numbers: the cost increase is $550 a month (about 18%), and the median dropped by 29 minutes. Please check that you're happy to state them.
- The draft is about 1,150 words, TODO markers included. That is below the 1,200 to 1,800 you asked for. I didn't pad it. Your answers to questions 1 to 3 and 6 to 9 (the pipeline shape, how you found the critical path, the script, the Dockerfile and a false-green case) should bring it into range with real content.
- I made no claim about how much of the 29 minutes each change saved, and none that the critical path explains the whole gain (see question 4).

## After review

The revised post is in after.md. I applied every review finding that called for a change in the text, with these exceptions and variations:

- Finding 1 (runner-trial order): I added the reviewer's question to the TODO in the runners section. I did not mark "Twice the cores saved 3 minutes." in "The lesson", because finding 10 deleted that paragraph. The question itself is still open (question 1 above).
- Finding 4 ("Three steps took most of the time"): I used the TODO marker, not "Three steps were the slowest". Your notes give no durations for the other steps, so "slowest" is unsupported as well.
- Finding 7 (length): no change to the text, as the review recommends. With the lesson's restating paragraph and the signpost sentence removed, the post is now shorter, at roughly 900 words of prose. Your answers to questions 1 to 3 and 6 to 9 should add real content to reach 1,200 to 1,800 words.
- Finding 8 (placement of the runners section): not applied yet, because the right place depends on when the trial ran. The runners TODO now says to move the section above "Splitting the integration tests", and to open it with "Before sharding, we tried ...", if the trial came first. Until then, a first-time reader still sees "the serial integration job" right after the sharding section.
- Finding 9 (one term for the critical path): I defined the term at its first use, which is in the introduction, not in "The setup" (there it appears only inside a TODO). I replaced "long pole" with "the longest job on the critical path".
- Finding 13: I wrote "we needed" rather than "we need" to match the past tense of the sentences around it.

New questions:

1. What unit is the 71% cache hit rate measured in: Turborepo tasks, packages or runs?
2. Do the 3,912 and 4,307 runs cover all PR runs in July and September, or a sample?
