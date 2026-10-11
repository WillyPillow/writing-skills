# How we cut PR CI from 41 minutes to 12

In July 2026, a pull request in our monorepo waited a median of 41 minutes for CI, and one in ten waited more than 58. By September the median was 12 minutes and the p90 was 19. We got there by splitting one long test job, caching builds, and skipping TypeScript packages a change can't affect. We also tried doubling the size of our runners. That doubled the cost and saved 3 minutes, so we reverted it.

This post covers what we changed, what we tried and backed out, and what it cost. The short version: find the critical path before you buy hardware.

## The setup

Our monorepo holds about 380,000 lines of TypeScript and Go. CI runs on GitHub Actions with self-hosted runners. The July numbers come from 3,912 PR runs and the September numbers from 4,307. They are medians and 90th percentiles of wall time per run, measured over all PRs in each month, not a controlled experiment.

Three steps took most of the time. The Go integration tests ran as a single job that took 22 minutes. The TypeScript build took a median of 9 minutes. Building the Docker images for the integration tests took 6 minutes. [TODO: describe which of these jobs ran in sequence and which in parallel, before and after, so the reader can see the critical path. A small before/after diagram of the pipeline would fit here.]

[TODO: how we found the critical path, for example from the job timings in the Actions UI or a script.]

## Splitting the integration tests

The 22-minute integration job was a single job, so nothing else we did could bring a run below 22 minutes. We split it into six shards that run in parallel. The slowest shard takes 5 minutes.

Splitting the tests evenly needs to know how long each one takes. We already ran the tests with gotestsum, whose `--junitfile` flag writes a JUnit XML report with a duration for each test. A 60-line script reads those durations and bin-packs the tests into six shards of roughly equal total time. Each shard then runs only its own list of tests. [TODO: how often the timings are refreshed, and how a new test with no recorded timing is assigned. Link to the script or show an excerpt if we can publish it.]

## Bigger runners, tried and reverted

We also tried running CI on 16-vCPU runners instead of 8-vCPU ones. It cost twice as much and cut the median by 3 minutes. The serial integration job was still the long pole, and a run could not finish before that job did. We reverted to 8 vCPUs. [TODO: confirm whether this trial ran before the sharding above. If it ran after, the integration job was no longer serial and this explanation needs to change. Also say whether "twice the cost" is the per-minute price or measured spend, and how long the trial ran.]

## Caching the builds

We set up Turborepo's remote cache, self-hosted on MinIO, so that a build whose inputs match an earlier one downloads the outputs instead of rebuilding. [TODO: name the cache server in front of MinIO, if there is one.] On PRs, 71% of build tasks hit the cache, and the median TypeScript build went from 9 minutes to 2.5.

The Docker images for the integration tests had a simpler problem. The Dockerfile copied the source tree before it ran `go mod download`. Any change to a source file invalidated the layer cache from that point on, so the build downloaded all Go modules again. We moved `go mod download` before the copy of the source. When `go.sum` is unchanged, Docker reuses the cached module layer, and the image build takes 1 minute instead of 6. [TODO: show the before/after Dockerfile lines.]

## Running less, where it's safe

For TypeScript, we run builds and tests only for packages that a PR could affect. Turborepo's `--filter=...[origin/main]` selects the packages that changed relative to `origin/main`, plus every package that depends on them. A change to a leaf package builds that package alone. A change to a shared library still builds everything that imports it.

We tried the same thing for Go and turned it off. We selected the packages to test with `go list -deps`, which follows the import graph. Some of our tests read files from another package's `testdata` directory, and a file read at test time isn't an import. When a PR changed one of those files, the selection skipped the tests that read it. That gave us two false greens in one week: PRs that passed CI with a broken test that never ran. [TODO: describe one of the two cases, if we can.] A test selector that misses some dependencies turns CI from a check into a guess, so Go tests always run in full. With sharding, the slowest part of the full run takes 5 minutes.

## What sharding shook loose

Sharding changes the order in which tests run. That exposed 14 flaky tests that passed only in a particular order, because they depended on database state left behind by earlier tests. We fixed 11 of them. The other 3 are quarantined and tracked in an issue. [TODO: say what quarantine means here, for example still run but not blocking, and link the issue.]

If you shard a suite that has always run in one order, expect the same. A test that relies on order is broken whether or not it happens to pass in its old position, and sharding is what made us notice these 14.

## What it cost

More parallel jobs mean more runner time. Our runner spend went from $3,100 a month to $3,650, an increase of $550 or about 18%. For comparison, the bigger runners would have doubled the cost of every job and saved 3 minutes at the median.

Our developer survey asks whether CI gets in the way. The share of respondents who said "CI is a blocker for me" fell from 58% to 19% (n = 64). [TODO: confirm both surveys had 64 respondents, give when each ran, and say whether it was the same group.]

## The lesson

Before this work, one job ran for 22 minutes on its own, and no run could finish faster than that. Twice the cores saved 3 minutes. Sharding that job, caching builds and skipping unaffected TypeScript packages took the median from 41 minutes to 12, at about 18% more spend.

So, before you buy bigger machines, find the chain of jobs that sets your wall time and look at the longest one. If one job dominates, split it. If a step repeats work that hasn't changed, cache it. Skip work only when you know the result can't depend on it. Our Go test selection couldn't meet that bar, so we turned it off.
