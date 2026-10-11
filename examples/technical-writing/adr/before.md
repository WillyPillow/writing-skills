# ADR: Use a Postgres table as the background job queue

- **Status:** Accepted
- **Date:** 2026-10-02
- **Deciders:** Ana, Ben, Chen

## Context

Three kinds of background work run outside the request path: invoice PDF generation, email sends, and webhook deliveries. Today each one is a cron script that polls its own table every minute. Each script was written separately, so retry, failure handling, and logging work differently in each one, and a job can wait up to a minute before it starts.

We want one queue that all three can use.

### Load

- Average: about 20 jobs/s.
- Peak: about 300 jobs/s, driven by webhook deliveries at month-end.

### Requirements

1. **At-least-once delivery.** A job that was enqueued runs at least once. Handlers must therefore be idempotent.
2. **Retries with backoff.** Failed jobs are retried after increasing delays.
3. **Per-customer ordering for webhooks.** One customer's webhooks are delivered in the order they were enqueued. Ordering across customers is not required.
4. **7 days of job history.** Finance asked for a 7-day audit trail of jobs.

## Options considered

### Kafka (managed, via Amazon MSK)

- Per-key ordering is built in: partition by customer id and requirement 3 is met.
- Throughput is far beyond what we need.
- Nobody on the team has run Kafka.
- The minimum MSK configuration costs about $1,400/month.
- MSK runs on AWS; we run on GCP.

### Amazon SQS (FIFO queues)

- FIFO queues order messages within a message group, so a group per customer meets requirement 3.
- Throughput limit: 300 messages/s per API action without batching, 3,000 with batching. Our month-end peak of 300 jobs/s sits at the unbatched limit, so we would need batching from the start.
- SQS is an AWS service and we run on GCP. Using it means running cross-cloud, which Ana rejected.

### Postgres table with `SELECT ... FOR UPDATE SKIP LOCKED`

Jobs are rows in a table on our existing Postgres primary. Workers claim rows with `SELECT ... FOR UPDATE SKIP LOCKED`, so concurrent workers do not pick up the same job.

- No new infrastructure, vendor, or cloud. The team already operates Postgres.
- Jobs can be enqueued in the same transaction as the business data that produces them.
- Chen's prototype reached 2,000 jobs/s on the current primary (`db-custom-8`) with 8 workers before primary CPU reached 70%. That is about 6.7 times our month-end peak.
- The prototype does **not** yet provide per-customer ordering (see Open issues).
- History retention keeps a large, high-churn table on the primary (see Consequences).

## Decision

Use a Postgres table on the existing primary as the job queue, with workers claiming jobs via `SELECT ... FOR UPDATE SKIP LOCKED`. Invoice PDF generation, email sends, and webhook deliveries move to this queue and their cron scripts are retired.

Completed jobs are kept for 7 days to meet the audit requirement, then deleted.

We chose Postgres because it meets the measured throughput with headroom, adds no new system for the team to learn and operate, and avoids both the cost of MSK and a cross-cloud dependency on AWS.

### When to revisit

Revisit this decision if either of the following holds:

- Load is sustained above 1,000 jobs/s.
- Primary CPU goes above 60%.

## Consequences

### Positive

- One mechanism for retries, backoff, and failure handling instead of three ad hoc scripts.
- Jobs start as soon as a worker is free, instead of waiting for the next one-minute poll.
- No new infrastructure cost and no new technology to learn.
- Enqueueing can be transactional with the data that triggers the job.

### Negative and risks

- **Load on the primary.** The queue shares CPU, I/O, and connections with the application's main database. Heavy queue traffic can slow the application, and the other way round. The 60% CPU trigger is meant to catch this before it hurts.
- **Table size and bloat.** At the average rate of 20 jobs/s, 7 days of history is about 12 million rows. At about 2 KB per row, that is about 24 GB. Rows are inserted, updated as they change state, and deleted after 7 days, which produces dead tuples steadily. Ben raised the concern that vacuum may not keep up, leading to table bloat and slower claim queries. Deleting old rows in bulk also produces vacuum work of its own.
- **Idempotency.** At-least-once delivery means a job can run more than once, for example when a worker crashes after doing the work but before marking the job done. Every handler, especially webhook delivery and email sends, must tolerate duplicates.
- **Scaling ceiling.** If load grows past what one primary can handle, moving to a dedicated queue system will mean a migration. The revisit triggers above are there to start that work early.

## Open issues

1. **Per-customer ordering is not implemented or tested.** Chen proposes taking a Postgres advisory lock per customer id, so only one worker processes a given customer's webhooks at a time. This is untested. Before webhooks move to the queue, we need to confirm that it preserves order (including across retries, where a failed job must block later jobs for the same customer) and measure its effect on throughput.
2. **Bloat mitigation is not designed.** Options include tuning autovacuum for the jobs table, partitioning the table by day so that old history is removed by dropping partitions instead of deleting rows, or moving completed jobs to a separate history table. A choice should be made before the table reaches full 7-day size.
3. **Benchmark conditions.** The 2,000 jobs/s figure comes from a prototype. It should be rechecked with per-customer ordering in place, realistic payload sizes, and the primary carrying its normal application load.
