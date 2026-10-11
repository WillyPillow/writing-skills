# Review: "Design: signed-cookie web sessions" (draft.md)

Checked against material.md. Every number in the draft matches the material or is arithmetic on it: 40k, 1,100 against 150, 2.3x, 47 and 12 minutes, 9k/s, 1.1 and 3.2 KB, 4 KB, 6 x 4 = 24 minutes, 4 - 3.2 = 0.8 KB, 1.1 KB x 9k/s ≈ 10 MB/s. The draft marks its gaps with `[TODO: ...]` instead of explaining them in the prose. It also marks the alternatives the drafter suggested (draining, JWT/asymmetric signing, checking the epoch at reissue) as questions, not as rejected options. The findings below are listed from most to least serious.

## Substance

1. Substance, "Revocation", paragraph 2, "a copy of it, for example one taken by an attacker, keeps working for up to 12 hours"; also the table row "Sensitive actions only", "up to 12 hours for everything else". Sessions slide: any request more than an hour after issue gets a fresh cookie with a new 12-hour expiry ("Session lifetime"). An attacker who keeps using a stolen cookie therefore keeps getting new ones, and the copy never expires. The 12-hour bound holds only for a copy that goes unused. This makes revocation look less urgent than it is, and revocation is the decision security has to sign off. Fix: "keeps working for up to 12 hours after its last use, and indefinitely if it is used at least every 12 hours, because each reissue extends it". In the table, change the cell to "until the cookie expires, which an active user of the cookie can postpone indefinitely".

2. Substance, "Failure behavior", first sentence, "Restarting or deploying an app server no longer affects sessions, since no session state lives on it". "Signing keys" contradicts this. A rolling deploy that ships a new signing key logs out users who are routed to servers that have not yet been updated. The universal claim also undercuts the first goal ("A rolling deploy logs out no users") until the rotation procedure is settled. Fix: "Restarting or deploying an app server does not affect sessions, except a deploy that changes the signing keys (see "Signing keys")". Add the key-rollout case to the failure list or the open questions.

3. Substance, "Goals and non-goals", fourth goal, "No new service is added to the path of every request". The material gives no such goal. The goal is inferred from the reasons Redis and Postgres lost. Stated as a goal, it becomes a requirement that the author did not set and that the "Where the session lives" decision then appears to satisfy. Fix: confirm the goal with the author, or replace it with "[TODO: is 'no new per-request dependency' a stated requirement?]".

4. Substance, "Where the session lives", paragraph 4, "Both store-based options make every request depend on a service that either has a recent outage record or cannot take the load". The material rejects Redis because "it puts Redis on the login path". It does not say that every request would depend on Redis. Paragraph 2 of the same section says "login path" correctly, so the summary sentence widens the claim beyond its source. Fix: "A Redis store would put a service with a recent outage record on the login path, and a Postgres table would put load on the primary that the DBA refused. The cookie depends on neither."

5. Substance, "What the cookie holds", paragraph 3 ("Today that is 0.8 KB"), and "Open questions", second bullet ("the largest is 0.8 KB under the 4 KB limit"). The TODO just above these sentences says the 3.2 KB maximum may be a raw size, and that base64 encoding would put the cookie over 4 KB. Both sentences state the 0.8 KB of headroom as fact anyway, and the open-questions bullet repeats it with no caveat. Fix: in both places write "0.8 KB if the measured sizes are of the encoded cookie [TODO: see above]". In the open-questions bullet, also list "the encoded size may already exceed 4 KB".

6. Substance, "Where the session lives", paragraph 5, "roughly 10 MB/s of extra request traffic". This estimate uses the 1.1 KB average, which the TODO in "What the cookie holds" says may be a raw size. If it is, the encoded traffic is about a third higher. Fix: add "(about 13 MB/s if 1.1 KB is the raw payload before base64)", or point to the size TODO.

7. Substance, "Session lifetime", paragraph 2, "Today it ends 12 hours after their last request". The material says only that today's sessions are "sliding (refreshed on activity)". It does not say that every request refreshes the session. The "up to 1 hour less" conclusion depends on this claim, and so does the third goal, which cites it. Fix: "[TODO: confirm that today's sessions expire 12 hours after the last request]".

8. Substance, "Revocation", paragraph 2, "Security requires revocation in two cases". The material says Marcus "wants" revocation for these cases and has not signed off. "Requires" states a settled requirement that the material does not record. Fix: "Security (Marcus) wants revocation in two cases".

9. Substance, "What the cookie holds", paragraph 2, "because roles are stored by name". The material records that the largest payloads belong to users with many org roles, and it suggests role ids as a possible fix. It does not say that storing roles by name causes the size. Fix: "The largest payloads belong to users with many org roles." The idea of role ids is already in paragraph 3.

## Argument

10. Argument, "Revocation", paragraphs 2 and 3, and the last paragraph. The mechanism increments the user's epoch on a password change, which rejects every cookie the user holds, including the one in the browser that made the change. The last paragraph instead speaks of "the revocation of the user's other sessions". The reader cannot tell whether the session that changed the password survives. Fix: add "[TODO: does the server reissue the current session's cookie with the new epoch on a password change, so that only the user's other sessions end?]".

11. Argument, "Revocation", paragraph after the table, "Checking on every request reads the database at the same rate as the Postgres sessions table, which the DBA refused". The DBA refused about 9k reads per second on the primary. An epoch check is a smaller read by key and might be served from a replica. The material does not say whether the DBA's refusal covers that case. As written, the sentence rules out the first option by analogy, not by evidence. Fix: "...at the same rate as the Postgres sessions table [TODO: would the DBA's objection also apply to epoch reads, for example from a replica?]".

12. Argument, "Revocation", paragraph 3, "Three places to check have been proposed". The passive voice hides who proposed the options. The material also records only one proposal: check sensitive actions plus a 60-second cache. Checking on every request is the cost it was trying to avoid, not a proposal. Fix: "The per-request check reads the users table about 9k times per second at peak. Two cheaper places to check have been suggested, and the table compares all three."

## Design

13. Design, "Where the session lives", last paragraph, "This decision is the most expensive to reverse in the doc". This sentence uses the decision-record term as prose, where the skill asks for domain terms. The sentence that follows already says the same thing concretely. Fix: delete the sentence and open the paragraph with "Once stickiness is removed, ...". If the ranking matters, add "so step 3 of the rollout is the point of no return" to the end of the paragraph.

14. Design, "Open questions". The list has two items, but the body leaves other design questions open that affect stated goals. The key-rotation procedure across a rolling deploy affects the "no logouts" goal. Security has not accepted the unencrypted payload. The response to a leaked key is unspecified. A reviewer who reads only this section will think the design is more settled than it is. Fix: add one bullet each for the rotation procedure, unencrypted payload acceptance and key-leak response, each pointing to its section.

All the other design checks pass. Revocation, the central tension, gets the most space and is marked as unresolved. The storage decision gives its force, the options, the reason the chosen option wins and the costs. The non-goals are real. Failure behavior is mostly TODO, but it says so instead of promising monitoring.

## Math

The doc has no derivations, so there is nothing to check at this level.

## Sentences

15. Sentences, "Signing keys", paragraph 2, "A cookie signed with the old key is reissued under the new one within an hour of activity, and every cookie expires within 12 hours". The first clause is imprecise. A cookie is reissued on the first request more than an hour after it was issued, not "within an hour of activity". The clause is also unnecessary, because 12-hour expiry alone shows that no cookie signed with a quarter-old key survives. Fix: "Every cookie expires within 12 hours of issue, so dropping a key a quarter after it stopped signing logs out no one."

16. Sentences, "Revocation", paragraph 1, "This is the unresolved part of the design, and it is not ready for approval until security (Marcus) signs off". "It" could refer to this part or to the design. Fix: "...and the design is not ready for approval until security (Marcus) signs off."

17. Sentences, throughout. The draft uses "sticky sessions" (Context), "sticky routing" (Context, Rollout) and "stickiness" (Overview, Goals, Rollout) for one concept. Fix: say "sticky routing" everywhere, and define it once in Context: "HAProxy sends each user back to that server by reading the `srv` cookie (sticky routing)."

18. Sentences, "Rollout and rollback", the numbered steps. Steps 2 and 3 are imperative, but step 1 mixes an imperative with descriptions ("Servers write both ..."). This is minor. Fix: "1. Ship dual-write: servers write both the in-memory session and the cookie, and read from memory first. Keep sticky routing on."
