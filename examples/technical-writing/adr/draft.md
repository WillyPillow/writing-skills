# ADR [TODO: number]: Use a Postgres table as the background job queue

- Status: Accepted
- Date: 2026-10-02 [TODO: confirm year]
- Deciders: Ana, Ben, Chen

## Context

Three kinds of background work run outside request handling: invoice PDF generation, email sends and webhook deliveries. Each one is a cron script that polls a database table every minute, and each script was written ad hoc. [TODO: link any incidents caused by the cron scripts, if there are some.]

Load averages about 20 jobs/s. It peaks at about 300 jobs/s at month-end, when webhook deliveries spike.

The replacement must meet four requirements:

1. At-least-once delivery: a job is never lost, though it may run more than once.
2. Retries with backoff for failed jobs.
3. In-order delivery of each customer's webhooks.
4. Seven days of job history, which finance requires for audit.

Our infrastructure runs on GCP. The primary Postgres instance is a db-custom-8 machine.

## Decision

Background jobs go into a Postgres table. Workers claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED`, which lets several workers take different rows without waiting on each other's locks. Completed jobs are kept for 7 days and then deleted. [TODO: confirm the job table lives on the application's primary instance rather than a separate one.]

We will revisit this decision if load stays above 1,000 jobs/s or primary CPU goes above 60%. [TODO: why these two thresholds; whether 60% is total primary CPU or the queue's share; primary CPU today without the queue.]

### Options compared

We considered three options: Kafka, Amazon SQS, and a Postgres table. [TODO: was keeping the cron scripts considered? If so, add why it lost.]

| | Kafka (MSK) | SQS FIFO | Postgres table |
|---|---|---|---|
| Throughput | [TODO: no figure in the material] | 300 messages/s per API action, 3,000 with batching (AWS docs) | 2,000 jobs/s with 8 workers before CPU reached 70% (prototype) |
| Per-customer ordering | Built in, per key | Built in, per message group | Not built; advisory lock per customer id proposed, untested |
| Runs on GCP | No: MSK is an AWS service [TODO: was a GCP-hosted Kafka considered?] | No | Yes, on our existing Postgres |
| Team experience | Nobody has run Kafka | [TODO] | We already run Postgres |
| Added cost | About $1,400/month minimum for MSK | [TODO] | No new service [TODO: cost of extra load and storage on the primary] |

**Capacity.** All three options cover the 300 jobs/s peak, but with different margins. SQS FIFO allows 300 messages/s per API action without batching, which is exactly the peak, and 3,000 with batching. Chen's prototype on the Postgres primary reached 2,000 jobs/s with 8 workers before CPU reached 70%, about 6.7 times the peak. [TODO: state whether the prototype ran on the production primary under production load or on a copy of the same machine type, and what work each job did.] Capacity alone therefore does not rule out any option.

**Per-customer ordering.** This requirement is where Postgres is weakest, and the other two options are strongest. Kafka orders messages within each key, and SQS FIFO orders them within each message group, so either would deliver one customer's webhooks in order with no extra code. The Postgres prototype does not order jobs per customer. Chen proposes taking a Postgres advisory lock on the customer id, so that only one worker at a time processes a given customer's webhooks. This approach is untested. [TODO: is the decision conditional on the advisory-lock approach working? What is the fallback if it does not, and when will it be tested?]

**Kafka** loses on operations and cost. Nobody on the team has run Kafka, and the minimum managed configuration on MSK costs about $1,400/month. That spending would buy built-in ordering, but not capacity we need: the prototype shows Postgres covers peak load several times over.

**SQS** loses because our infrastructure runs on GCP, and SQS would add a dependency on a second cloud. [TODO: the reason cross-cloud rules SQS out, such as egress cost, added latency, a second set of credentials and IAM, or a policy.]

**Postgres** is chosen. [TODO: confirm the deciding factor. The draft assumes this: Kafka and SQS each fail a constraint (Kafka on experience and cost, SQS on staying within GCP), while Postgres meets the load requirement with headroom on infrastructure we already run.] The cost of this choice is that per-customer ordering, the one requirement the brokers meet out of the box, is still unproven for Postgres.

## Consequences

**Ordering must be built and tested by us.** Until the advisory-lock approach is tested, the queue does not meet the per-customer ordering requirement. Webhook deliveries should not move to the queue before that test passes. [TODO: confirm this sequencing.]

**At-least-once delivery and retries are our code.** The job table provides none of this behaviour by itself. We have to define how a job claimed by a worker that then crashes becomes available again, and how backoff and the maximum number of attempts work. [TODO: the planned mechanism, for example a lease timeout on claimed rows, the backoff policy, the attempt limit and whether failed jobs go to a dead-letter state.]

**Queue load shares the primary.** Job claims and updates compete with application queries for the primary's CPU. The revisit thresholds of 1,000 jobs/s and 60% CPU are the signals that this sharing has become a problem. [TODO: how the two thresholds are monitored and who acts on them.]

**History adds about 24 GB a week.** At the 20 jobs/s average, a week produces about 12 million job rows (20 × 604,800 s). At about 2 KB per row, that is about 24 GB. Month-end weeks will be larger. [TODO: month-end estimate.] Deleting a week's worth of rows on a rolling basis creates dead tuples, and Ben has raised the risk of table bloat and vacuum falling behind. [TODO: whether history lives in the same table as pending jobs, and how expired rows are removed, such as batched deletes or dropping time-based partitions.]

**Moving off Postgres later.** The job table's schema and the workers' claim logic are ours, so moving to a broker later means rewriting the workers' claim, retry and ordering code against the broker's API. [TODO: confirm whether producers enqueue through a shared interface that would limit that rewrite to one place.]

## Open questions

1. Does an advisory lock per customer id give in-order webhook delivery under concurrent workers, retries and worker crashes?
2. How do expired history rows get removed without table bloat on the primary?
3. In what order do invoice PDFs, email sends and webhook deliveries move from their cron scripts to the queue, and can each one fall back to its cron script? [TODO: migration plan.]
