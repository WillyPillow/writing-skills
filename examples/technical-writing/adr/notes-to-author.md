# Notes to the author: job queue ADR

These are my planning notes and my questions. You were not available, so I drafted the ADR anyway (draft.md) and marked each open gap in it with `[TODO: ...]`. Answering the questions below should let you resolve those markers.

## Planning notes

**Reader.** Three readers: the team members who must accept the record (Ana, Ben, Chen and anyone reviewing the `docs/adr` change); the engineers who will move invoice PDFs, email sends and webhook deliveries onto the queue; and a future maintainer who finds a `jobs` table on the primary and asks why the team did not use a real message broker.

**The point.** Background jobs move from ad hoc cron scripts to one job queue, built as a Postgres table that workers claim rows from with `SELECT ... FOR UPDATE SKIP LOCKED`. Kafka and SQS were rejected. The decision is revisited if load is sustained above 1,000 jobs/s or primary CPU goes above 60%.

**The skeptic.**

1. "Why not a purpose-built queue? Kafka has per-key ordering built in." Answered in the Kafka comparison: the team has no Kafka operating experience, and the managed minimum costs about $1,400/month for a load the prototype shows Postgres handles with large headroom. Weak point: the $1,400 figure is for MSK, which is an AWS service, so it has the same cross-cloud problem as SQS (question 2).
2. "Per-customer webhook ordering is a requirement, and the chosen option is the only one that does not provide it." This is the central tension of the decision. Kafka and SQS FIFO give ordering out of the box; the Postgres prototype does not, and the advisory-lock plan is untested. The draft spends the most space here and lists it as an open question and a cost.
3. "You are putting queue load and 24 GB/week of churn on the primary database that serves the application." Answered in part by the prototype numbers and the revisit triggers; Ben's bloat/vacuum concern is not answered in the material and is listed as open.

**Argument skeleton (one claim per paragraph, with source).**

- Context 1: Today each job type is a separate cron script polling a table every minute (meeting notes).
- Context 2: Load is about 20 jobs/s on average and about 300 jobs/s at peak, from month-end webhooks (meeting notes).
- Context 3: Requirements are at-least-once delivery, retries with backoff, in-order webhook delivery per customer, and 7 days of job history for finance's audit (meeting notes).
- Context 4: We run on GCP (meeting notes, SQS item).
- Decision: Postgres table with SKIP LOCKED; revisit triggers (meeting notes).
- Comparison, capacity: Postgres prototype 2,000 jobs/s at 70% CPU with 8 workers; SQS FIFO 300/s per API action unbatched, 3,000 batched; Kafka no number in the material (meeting notes).
- Comparison, ordering: Kafka per-key built in; SQS FIFO per message group; Postgres not yet, advisory lock per customer id proposed and untested (meeting notes).
- Comparison, operations and cost: Kafka nobody has run it, MSK minimum about $1,400/month; SQS cross-cloud, rejected by Ana; Postgres runs on the existing primary (meeting notes).
- Deciding reason: [needs the author] the notes record the decision and each option's drawbacks, but not which factor decided. I wrote it as: the two broker options each fail a constraint (no Kafka experience plus cost; SQS is cross-cloud), and Postgres covers peak load with headroom on infrastructure the team already runs. Please confirm.
- Consequences: ordering unproven; queue load shares the primary; history adds about 24 GB/week with bloat/vacuum risk; retry and crash-recovery behaviour must be built by us.

**Dependency map (requirement or constraint -> decision it drives).**

- Peak 300 jobs/s -> capacity comparison; rules out nothing on its own (all options cover it, SQS unbatched only exactly).
- Per-customer webhook ordering -> the main weakness of the chosen option; drives the advisory-lock plan and an open question.
- At-least-once delivery -> drives nothing in the notes. [Gap: how a job claimed by a crashed worker is retried.]
- Retries with backoff -> drives nothing in the notes. [Gap.]
- 7-day history -> retention policy (delete after 7 days) and the 24 GB estimate; Ben's bloat concern.
- On GCP -> rejects SQS (and, arguably, MSK).
- No Kafka experience, $1,400/month -> rejects Kafka.
- Prototype 2,000 jobs/s at 70% CPU -> supports Postgres; sets context for the revisit triggers.
- Revisit triggers (1,000 jobs/s, 60% CPU) -> no stated derivation. [Gap: why these numbers.]

**Instances.** Month-end webhook peak of about 300 jobs/s. Chen's prototype: 2,000 jobs/s on db-custom-8 with 8 workers before CPU reached 70%. Ben's price check: MSK minimum about $1,400/month. Chen's doc check: SQS FIFO 300 messages/s per API action, 3,000 with batching. History estimate: 20/s for a week is about 12M rows, at about 2 KB each, about 24 GB.

## Questions for the author

1. **Deciding reason.** Which factor decided for Postgres: cost, the team's lack of Kafka experience, staying on GCP, or the prototype result? The notes record the decision and each option's drawbacks but not which one carried it.
2. **Kafka on GCP.** The $1,400/month figure is for MSK, an AWS service, so it would be cross-cloud in the same way SQS is. Was a GCP-hosted Kafka (managed or self-run) priced or considered? If Kafka was rejected mainly for being cross-cloud, the record should say so.
3. **Why cross-cloud rules out SQS.** The notes record "Ana: no". What is the reason: egress cost, latency, a second set of credentials and IAM to manage, a policy? The ADR should state it so a future reader can tell whether it still holds.
4. **Per-customer ordering.** Is the decision accepted on the condition that the advisory-lock approach works, or is ordering expected to be solved some other way if it does not? What is the fallback if the test fails? When and how will it be tested?
5. **Prototype conditions.** Did the 2,000 jobs/s run on the production primary under production load, or on a copy of the same machine type? What did each job do (payload size, work per job)? This decides how much headroom 2,000 jobs/s really means.
6. **Revisit triggers.** Why 1,000 jobs/s and 60% CPU? Is 60% total primary CPU, or CPU attributable to the queue? What is the primary's CPU today without the queue?
7. **Same primary.** Will the job table live on the same primary that serves the application, or on a separate instance? The notes imply the same primary but do not say so.
8. **At-least-once and retries.** How does a job claimed by a worker that then crashes get retried (for example, a lease or timeout on the claimed row)? What is the backoff policy and the maximum attempts? Is there a dead-letter state? None of the options is compared on these requirements in the notes.
9. **History and bloat.** Does the 7-day history live in the same table as pending jobs, or is it moved to a separate table? How will the daily deletes be done (batched DELETE, partition drop, other)? Ben's bloat/vacuum concern has no answer in the notes. Also, the 24 GB estimate uses the 20 jobs/s average; month-end weeks will be larger. Do you have a month-end figure?
10. **Status quo.** Was keeping the cron scripts considered? If so, why did it lose (beyond "each written ad hoc")? If the cron scripts have caused incidents, a reference would strengthen the context.
11. **Migration.** In what order will the three job types move to the queue, and can each one fall back to its cron script if needed?
12. **ADR metadata.** The ADR number in `docs/adr`, and the year of the Oct 2 meeting (I assumed 2026).

## Rules set aside

None. The draft follows the ADR shape (status, context, decision, consequences) as the skill and the request specify, with the option comparison inside the decision section.

## After review

All findings in review.md were applied; none was left out. Two were applied in a form that needs your input:

- Argument 1: the new table rows for at-least-once delivery, retries and 7-day history carry `[TODO: compared?]` for Kafka and SQS, because the material has no facts on how either broker meets them. If these requirements did not separate the options, say so and the rows can become one sentence.
- Argument 2: the Context now states that the team runs Postgres and has not run Kafka. Whether these, a budget limit or something else decided the choice still depends on question 1.

New questions:

1. Did at-least-once delivery, retries with backoff or 7-day history come up when comparing Kafka and SQS with Postgres? If so, how did each broker do?
2. Was there a budget limit for a new service? If so, what was it?
