# Review: ADR, Postgres table as the background job queue

Reviewed against `material.md` only. Findings run top-down, most important first within each level. The draft has no derivations, so the Math level is left out.

## Substance

1. Substance, "Options compared", **Kafka** paragraph, "Kafka loses on operations and cost. ... That spending would buy built-in ordering, but not capacity we need: the prototype shows Postgres covers peak load several times over." The material records the facts about Kafka (nobody has run it; MSK costs about $1,400/month; ordering per key is built in) but not why it lost. The draft states a reason as decided history, along with a cost-versus-capacity argument that nobody made in the meeting. The **Postgres** paragraph's TODO admits that the deciding factor is assumed, but this paragraph asserts it without a marker. Fix: keep the two facts and mark the reason, for example: "Nobody on the team has run Kafka, and the minimum managed configuration on MSK costs about $1,400/month. [TODO: confirm these are why Kafka lost.]" Delete the "That spending would buy ..." sentence unless the author confirms it.

2. Substance, "Options compared", **Capacity**, "All three options cover the 300 jobs/s peak" and "Capacity alone therefore does not rule out any option." The material gives no throughput figure for Kafka, and the table says so ("[TODO: no figure in the material]"). The claim covers all three options but has support for only two. Fix: "SQS FIFO and the Postgres prototype both cover the 300 jobs/s peak. [TODO: Kafka throughput figure, if one was considered.]" Narrow the closing sentence to "Capacity does not rule out SQS or Postgres."

3. Substance, Consequences, **Queue load shares the primary**, "The revisit thresholds of 1,000 jobs/s and 60% CPU are the signals that this sharing has become a problem." This sentence gives a reason for the thresholds. The material gives none, and the Decision section itself asks "[TODO: why these two thresholds ...]". Fix: delete the sentence, or reduce it to "The revisit thresholds in the Decision section apply to this load." and keep the TODO about monitoring.

4. Substance, Consequences, **Queue load shares the primary**, "Job claims and updates compete with application queries for the primary's CPU." The Decision section marks the table's location as unconfirmed ("[TODO: confirm the job table lives on the application's primary instance ...]"), but this consequence states the location as fact. The material places only the prototype on the current primary. Fix: start the paragraph with "If the job table lives on the primary (see the TODO in Decision), job claims and updates compete ...", or move the TODO here.

5. Substance, Consequences, heading "History adds about 24 GB a week." Completed jobs are deleted after 7 days, so the 24 GB is the steady-state size of one week of history. It does not grow by that much every week. The material says "about 12M rows/week ... so about 24 GB". The heading suggests the table grows without bound. Fix: "History holds about 24 GB." The arithmetic in the paragraph is correct (20 × 604,800 ≈ 12.1M rows; × 2 KB ≈ 24 GB).

6. Substance, "Options compared", **Per-customer ordering**, "so either would deliver one customer's webhooks in order with no extra code." This is a cost claim with no support in the material. The material says only that ordering is built in per key or per group. Producers still have to set the key or message group, and retry handling can affect ordering. Fix: "so either provides per-customer ordering as a built-in feature."

7. Substance, table, row "Runs on GCP", Kafka cell "No: MSK is an AWS service". The material does not count GCP against Kafka; it raises cross-cloud only for SQS. The cell implies that Kafka also fails the GCP constraint, but the Kafka paragraph does not give that as a reason. A reader can't tell whether GCP was part of Kafka's rejection. Fix: change the cell to "[TODO: was hosting raised against Kafka? MSK is an AWS service.]" and keep the existing question about GCP-hosted Kafka. Alternatively, if the author confirms GCP counted against Kafka, add it to the Kafka paragraph.

8. Substance, Context, requirement 4, "which finance requires for audit." The material says "finance asked for it". "Requires" makes a request into a mandate. Fix: "which finance asked for, for audit."

## Argument

1. Argument, "Options compared", whole subsection. The Context lists four requirements, but the comparison covers only capacity and per-customer ordering. At-least-once delivery, retries with backoff and seven days of history appear in neither the table nor the prose. Yet the Consequences section says Postgres provides "none of this behaviour by itself" for the first two. A reviewer can't tell whether the brokers would have met them more cheaply. Fix: add table rows for at-least-once delivery, retries with backoff and 7-day history, each cell "[TODO]" unless the author has the facts. Alternatively, add one sentence saying these requirements did not separate the options, if the author confirms that.

2. Argument, Context against **Postgres** paragraph. The draft treats team experience, added cost and staying on GCP as the forces that decide. Of these, only GCP appears in the Context. The four listed requirements don't favor Postgres: it does not yet meet one of them, and it must build two others itself. So the Context lists forces that drive no decision, and the decision rests on forces the Context leaves out. Fix: once the author confirms the deciding factors (the existing TODO), add them to the Context as constraints, for example "Nobody on the team has run Kafka" and any budget limit [TODO], so that the decision follows from stated context.

3. Argument, Context, "The replacement must meet four requirements". No earlier sentence says that the cron scripts are being replaced, so "the replacement" has no referent. The material's first line gives one: "Need a queue for background jobs." Fix: before the load paragraph, add "The team needs a job queue to replace these scripts." and change "The replacement" to "The queue".

## Design

1. Design, Consequences, **Ordering must be built and tested by us**, "Webhook deliveries should not move to the queue before that test passes." This sequencing is not in the material. It is marked "[TODO: confirm this sequencing.]", which is acceptable, but the sentence states a decision. Fix: put it in the same conditional form as the TODO, "[TODO: confirm: webhook deliveries move to the queue only after the advisory-lock test passes.]", or keep the sentence once the author confirms it.

Otherwise the decision-record parts are present. Ordering, the central tension, gets the most space. Reversibility, failure on worker crash and history cleanup are raised with TODOs. Open questions are listed.

## Sentences

1. Sentences, table, SQS cells "Team experience: [TODO]" and "Added cost: [TODO]". Bare markers don't tell the author what is needed. Fix: "[TODO: has anyone run SQS?]" and "[TODO: SQS cost at 300 msg/s peak, plus cross-cloud egress, if known]".

2. Sentences, **Moving off Postgres later**, "The job table's schema and the workers' claim logic are ours, so moving to a broker later means rewriting the workers' claim, retry and ordering code against the broker's API." This sentence is about 31 words and repeats "claim". Fix: "The job table's schema and the claim logic are ours. Moving to a broker later means rewriting the workers' claim, retry and ordering code against the broker's API."

3. Sentences, **Per-customer ordering**, "Kafka orders messages within each key, and SQS FIFO orders them within each message group, so either would ..." This sentence is about 29 words. Fix: split it after "message group", and apply Substance finding 6 to the second half.
