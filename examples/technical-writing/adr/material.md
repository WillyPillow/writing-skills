# Author's material: job queue ADR

Request: Write an architecture decision record for the job queue decision, for the `docs/adr` folder.

Meeting notes, Oct 2 (Ana, Ben, Chen):

- Need a queue for background jobs: invoice PDF generation, email sends, webhook deliveries. Today these are cron scripts that poll tables every minute, each written ad hoc.
- Load: peak about 300 jobs/s (webhooks at month-end), average 20 jobs/s.
- Requirements: at-least-once delivery, retries with backoff, one customer's webhooks delivered in order, 7 days of job history for audit (finance asked for it).
- Options discussed: Kafka, SQS, a Postgres table with SELECT ... FOR UPDATE SKIP LOCKED.
- Kafka: nobody on the team has run it. Managed Kafka (MSK) minimum config costs about $1,400/month (Ben looked it up). Per-key ordering is built in.
- SQS: FIFO queues give per-group ordering. 300 messages/s per API action without batching, 3,000 with batching (Chen checked the docs). But we are on GCP, so this would be cross-cloud. Ana: no.
- Postgres: Chen prototyped it. 2,000 jobs/s on the current primary (db-custom-8) with 8 workers before CPU reached 70%. Ordering: the prototype doesn't do per-customer ordering yet. Chen thinks an advisory lock per customer id works; untested.
- Decision: Postgres table. Revisit if load is sustained above 1,000 jobs/s or primary CPU goes above 60%.
- History: keep completed jobs 7 days, then delete. Estimate: average 20/s is about 12M rows/week, about 2 KB each, so about 24 GB. Ben is worried about table bloat and vacuum.
- Status: accepted.
