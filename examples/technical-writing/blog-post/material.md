# Author's material: CI speed-up blog post

Request: A post for the engineering blog about how we sped up CI. About 1,200 to 1,800 words.

Notes from Dana (dev-infra):

- Monorepo, about 380k lines of TypeScript and Go. CI on GitHub Actions, self-hosted runners.
- Before: median PR CI wall time 41 min, p90 58 min (July 2026, 3,912 runs).
- After: median 12 min, p90 19 min (September 2026, 4,307 runs).
- What we did, in order:
  1. Sharded the Go integration tests by historical timing. They were one job taking 22 min; now 6 shards, slowest 5 min. Collected timings from gotestsum's `--junitfile` output; a 60-line script bin-packs tests into shards.
  2. Remote build cache for the TypeScript builds: Turborepo remote cache, self-hosted on MinIO. Cache hit rate 71% on PRs. TS build step went from 9 min to 2.5 min median.
  3. Tried bigger runners (16 vCPU instead of 8). Cost 2x, saved only 3 min median, because the long pole was the serial integration job. Reverted.
  4. Docker layer caching for the integration test images: moved `go mod download` before the COPY of the source. Image build 6 min → 1 min when go.sum is unchanged.
  5. Skipped unaffected TypeScript packages with `turbo --filter=...[origin/main]`. For Go we didn't: we tried selecting packages with `go list -deps`, but it missed tests that read testdata from other packages. Two false greens in one week, so we turned it off. Go tests always run in full.
- Flakes: sharding surfaced 14 flaky tests that depended on test order (shared DB state). Fixed 11; quarantined 3, tracked in an issue.
- Cost: runner spend went from $3,100/month to $3,650/month (more parallel jobs).
- Developer survey (n = 64): "CI is a blocker for me" went from 58% to 19%.
- The lesson I want people to take away: find the critical path before buying hardware.
