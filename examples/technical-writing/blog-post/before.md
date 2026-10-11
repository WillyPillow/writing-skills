# How we cut CI time from 41 minutes to 12

In July, the median pull request in our monorepo waited 41 minutes for CI. One in ten waited 58 minutes or longer. By September the median was 12 minutes and the 90th percentile was 19. This post explains what we changed, what we tried and reverted, and what it cost.

Here is the short version. Most of the time a PR spent in CI went to one job. Speeding up that job, and the steps that fed it, did far more than buying faster machines. If you take one thing from this post, take this: **find the critical path before you buy hardware.**

## The setup

Our monorepo holds about 380,000 lines of TypeScript and Go. CI runs on GitHub Actions with self-hosted runners. A typical PR run builds the TypeScript packages, builds Docker images for the integration tests, and runs the Go unit and integration suites. Many jobs run in parallel, so a PR's wall time is set by the longest chain of dependent steps, not by the total work.

The numbers in this post come from two samples of PR runs: 3,912 runs in July 2026 (before) and 4,307 runs in September 2026 (after).

| | July 2026 | September 2026 |
|---|---|---|
| Median PR CI wall time | 41 min | 12 min |
| p90 PR CI wall time | 58 min | 19 min |
| Runs sampled | 3,912 | 4,307 |
| Runner spend | $3,100/month | $3,650/month |

## The long pole: one 22-minute integration job

The Go integration tests ran as a single job that took 22 minutes. Every other part of the pipeline could get faster, but no PR could finish faster than that job plus the image build in front of it. That job was the critical path.

We split it into shards using historical test timings. `gotestsum` can write JUnit XML with its `--junitfile` flag, and that output records how long each test took. We collect those files and feed them to a 60-line script that bin-packs tests into shards so that each shard gets roughly the same total runtime. Splitting by timing matters: splitting by package or alphabetically leaves one shard holding the slow tests, and that shard becomes the new long pole.

The integration suite now runs as 6 shards, and the slowest takes 5 minutes.

### Sharding exposed flaky tests

When the tests ran together in one process, they always ran in the same order. Once we split them up, each shard saw a different order, and 14 tests started failing intermittently. All 14 depended on test order: they relied on database state left behind by earlier tests.

We fixed 11 of them so each sets up the state it needs. The other 3 are quarantined and tracked in an issue. If you shard a suite that has only ever run in one order, expect something like this. The tests were already broken; sharding made it visible.

## Caching the TypeScript build

The TypeScript build step took 9 minutes at the median. We set up a Turborepo remote cache, hosted on our own MinIO instance. When a package's inputs haven't changed, Turborepo pulls the build output from the cache instead of rebuilding it.

On PRs the cache hit rate is 71%. The median TypeScript build step dropped from 9 minutes to 2.5.

## Caching Docker layers for the integration images

The integration tests run inside Docker images, and building those images took 6 minutes. The cause was an ordering problem in the Dockerfile. We copied the source tree before running `go mod download`, so any source change invalidated the layer that downloads dependencies, and every build fetched every module again.

We moved `go mod download` ahead of the source `COPY`, copying only `go.mod` and `go.sum` first:

```dockerfile
COPY go.mod go.sum ./
RUN go mod download
COPY . .
```

Now the dependency layer is reused whenever `go.sum` hasn't changed, which is most PRs. In that case the image build takes 1 minute instead of 6. This matters more than its size suggests, because the image build sits directly in front of the integration shards on the critical path.

## Skipping what a PR didn't touch

For TypeScript, we run tasks only for packages affected by the PR:

```sh
turbo run test --filter=...[origin/main]
```

The `[origin/main]` part selects packages that changed relative to `main`, and the leading `...` adds the packages that depend on them. Turborepo knows the dependency graph from the workspace's package manifests, so this selection is reliable.

We tried the same idea for Go and turned it off. We used `go list -deps` to work out which packages a change could affect and ran only their tests. The problem is that `go list` sees import dependencies, and some of our tests read files from other packages' `testdata` directories. A change to those files doesn't appear as an import change, so the tests that read them were skipped. In one week this gave us two false greens: PRs that passed CI while breaking tests that should have run.

A green CI run has to mean the tests passed. A faster run that sometimes lies is worse than a slower one that doesn't, so Go tests always run in full. Sharding made that affordable.

## What didn't work: bigger runners

We also tried the obvious fix: bigger machines. We moved from 8-vCPU runners to 16-vCPU runners. That doubled the cost and cut the median by only 3 minutes, so we reverted it.

The reason is the critical path. The serial integration job was the long pole, and a single serial job doesn't get much faster when you give it more cores. Bigger runners sped up work that wasn't holding anything up. Spending money on hardware only helps if the hardware speeds up the steps that set the wall time, and you can't know that until you've looked at what those steps are.

## What it cost

Runner spend went from $3,100 a month to $3,650, an increase of $550 (about 18%). The increase comes from running more jobs in parallel: six integration shards instead of one job means more runner time in flight at once, even though each PR finishes sooner.

For comparison, the bigger-runner experiment would have doubled the bill and saved 3 minutes. The changes we kept raised the bill by under a fifth and saved 29 minutes at the median.

## Did developers notice?

We surveyed developers before and after (n = 64). The share who agreed that "CI is a blocker for me" fell from 58% to 19%. Wall-clock numbers tell us CI is faster; the survey tells us people stopped waiting on it.

## What we'd tell another team

**Find the critical path first.** Before changing anything, work out which chain of jobs decides when a PR's CI finishes. Our 22-minute integration job, plus the image build in front of it, mattered more than anything else. Bigger runners failed because they didn't target it.

**Shard by measured time.** Split long test jobs using recorded per-test durations, not package names. `gotestsum --junitfile` gave us the data, and a short script did the rest.

**Cache what doesn't change.** A remote build cache and a reordered Dockerfile removed most of the build time on PRs where dependencies didn't change.

**Only skip tests when the dependency graph is complete.** Turborepo's filter works for us because the package graph is explicit. For Go, import analysis missed tests that read other packages' `testdata`, and we chose correctness over speed.

**Expect sharding to expose order-dependent tests.** Budget time to fix them, and quarantine the ones you can't fix right away, with an issue to track them.

CI is now fast enough that most of our developers don't consider it a blocker. The biggest gains came from looking at where the time actually went.
