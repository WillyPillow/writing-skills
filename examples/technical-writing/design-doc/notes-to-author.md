# Notes to the author: session storage design doc

The author was not available, so I drafted without answers. Every unanswered gap is marked `[TODO: ...]` in the draft. The planning notes and questions are below so Priya can correct them before the platform team's review on Tuesday.

## Planning notes

### Reader

Three readers. The platform team reviews and approves the doc next Tuesday; they run HAProxy, the deploy pipeline and Postgres, so they care about load, routing and new dependencies. The auth team builds it and needs the cookie format, key handling and rollout steps. A future maintainer will ask why sessions live in the browser and why revocation works the way it does. "We" in the doc means the auth team.

### The point

Problem: sessions live in the memory of the app server that created them, so every rolling deploy logs out every signed-in user (about 40k on March 12, with 1,100 support tickets against a normal 150), and the sticky routing that in-memory sessions require leaves load uneven (2.3x between busiest and quietest server, week of Sept 8).

Decisions: store the session in an HMAC-SHA256-signed cookie keyed from Vault; keep the 12 h sliding lifetime by reissuing after 1 h; rotate between two active keys quarterly; roll out through a dual-write phase behind a flag. Revocation is the unresolved part and needs security sign-off.

### Central tension

Statelessness against revocation. The design's value comes from no server-side lookup per request; Marcus's requirement (revoke on password change and "log out all devices") needs exactly such a lookup. This gets the most space in the draft. Cookie size against the 4 KB limit is the second tension.

### The skeptic

1. "Why not a shared server-side store (Redis or Postgres)? Signed cookies give up revocation." Answered in the session-storage decision: Redis would put a store with two outages last quarter on the login path and needs unstaffed HA work; Postgres would add about 9k req/s at peak to the primary and the DBA refused.
2. "You can't revoke a stolen or logged-out session." Answered in the revocation section, which states the gap plainly and lists it as open, not solved.
3. "Max payload is 3.2 KB against a 4 KB limit; what happens when roles grow?" Answered in the cookie-contents section and open questions. I suspect the headroom is smaller than it looks (see question 4).

### Argument skeleton

- Context: in-memory sessions + sticky `srv` cookie; 6 servers, rolling deploys at about 4 min per server. (notes)
- Deploys drop sessions: March 12, about 40k users, 1,100 tickets vs about 150. (notes)
- Sticky routing makes load uneven: 2.3x, week of Sept 8, Grafana. (notes)
- Goals: no logouts from deploys; remove stickiness; same lifetime semantics. Non-goals: SSO, mobile tokens. (notes)
- Decision 1, where the session lives: cookie wins because it adds no per-request dependency; Redis loses on login-path availability (Jul 3 47 min, Aug 19 12 min) and unstaffed HA; Postgres loses on 9k req/s to the primary. Cost: no revocation, bytes on every request. (notes)
- Decision 2, signing: HMAC-SHA256, key from Vault, two active keys, quarterly rotation. Why HMAC and why signed-only are not in the material. (notes; TODO)
- Decision 3, contents and size: six fields; average 1.1 KB, max 3.2 KB; 4 KB limit. (notes)
- Decision 4, sliding lifetime: 12 h, reissue after 1 h. (notes)
- Revocation: requirement from Marcus; `session_epoch` idea; per-request check reintroduces the DB read; sensitive-actions-only and 60 s in-process cache are candidates; undecided. (notes)
- Rollout: dual-write, switch reads, remove stickiness; rollback by flag while dual-write is on. (notes)
- Open questions: revocation, cookie growth. (notes)

### Dependency map

| Constraint or requirement | Decisions it drives |
|---|---|
| Deploys drop in-memory sessions (March 12) | Move session state off the app server |
| Sticky routing skews load (2.3x) | Remove stickiness in the last rollout step |
| No new dependency on the login path (Redis outage record) | Cookie over Redis |
| Primary cannot take about 9k req/s more (DBA) | Cookie over Postgres; per-request epoch check is ruled out for the same reason |
| 4 KB per-cookie browser limit; max payload 3.2 KB | Payload contents; open question on role ids |
| Keep 12 h sliding lifetime | Reissue after 1 h |
| Security wants revocation (Marcus) | `session_epoch` proposal, undecided |
| Rolling deploys, need for a safe rollback | Dual-write phase behind a flag |

Every decision has a driving constraint except the choice of HMAC-SHA256 and of signing without encryption, which the material states without a reason (questions 2 and 3). The quarterly rotation period also has no stated driver (question 6).

### Instances

- March 12 deploy: about 40k users logged out, 1,100 tickets (normal about 150).
- Week of Sept 8: busiest server 2.3x the requests of the quietest.
- Redis outages: Jul 3 (47 min), Aug 19 (12 min).
- Peak request rate about 9k req/s (DBA's refusal of the Postgres table).
- Payload sizes: average 1.1 KB, max 3.2 KB, users with many org roles.

## Questions for the author

1. **Status quo with fixes.** Was any option that keeps in-memory sessions considered, for example draining a server's sessions or waiting for them to expire before restarting it? Reviewers will ask. If it was considered, why did it lose? If not, I will drop the TODO in the alternatives section.
2. **Why HMAC-SHA256?** The mobile app already uses JWTs. Was reusing that format or an asymmetric signature considered? If so, why did it lose?
3. **Signed, not encrypted.** The payload (user id, org id, roles, CSRF token) is readable by anyone who holds the cookie. Is that acceptable to security, and was encryption considered?
4. **Cookie size.** Are the measured sizes (1.1 KB average, 3.2 KB max) the encoded cookie value including the signature, or the raw payload? If raw, base64 encoding adds about a third, which would put the largest sessions near or over 4 KB. Does the 4 KB budget also have to cover the cookie name and attributes?
5. **Role changes.** When an admin removes a user's role, how long until the cookie reflects it? Does the 1 h reissue re-read roles from the database, or copy them from the old cookie?
6. **Reissue threshold and rotation period.** Why 1 h for reissue and quarterly for key rotation? What is the procedure if a signing key leaks (replacing both keys logs everyone out)?
7. **Vault failure.** Do servers fetch keys at startup only, or at runtime? What happens if Vault is unavailable during a deploy or a rotation?
8. **Cookie attributes.** Which attributes will the cookie carry (HttpOnly, Secure, SameSite, Domain)? Does anything change for the CSRF token now that it lives in the session cookie?
9. **Revocation.** What does Marcus need to sign off: a maximum delay between password change and revocation? Which actions count as "sensitive"? Did anyone consider checking the epoch only at the hourly reissue? Is single-session logout (as opposed to all devices) in scope?
10. **Rollout details.** How long does each phase last, and which metrics gate the next one? Does dual-write reissue the cookie hourly, so the cookie does not expire before the in-memory session it mirrors? (The step 1 deploy itself drops all existing sessions, so I assumed every later session has a cookie from login.) Once stickiness is removed, can we still roll back, and when is dual-write removed?
11. **Load goal.** What busiest-to-quietest ratio would count as fixed? I left it as a TODO in the goals.
12. **Payload versioning.** Will the cookie carry a format version, so that changing the payload later (for example to role ids) does not log users out?

## After review

I applied all 18 review findings to after.md, each with the smallest edit that fixes it. Two of them change the substance, and Priya should check them. First, finding 1 changes what a stolen cookie can do: because each reissue extends the session, a copy that keeps being used never expires. Second, finding 3 replaces the goal "no new service on the path of every request" with a question, because the material never states that goal. Findings 2 and 14 also add three items to the open questions: key rotation across a rolling deploy, the unencrypted payload and the response to a leaked key. The review asked for the key-rollout case to go in either the failure list or the open questions, and I put it in the open questions only. For finding 13 I deleted the sentence and skipped the optional "point of no return" addition, because "Rollout and rollback" already says that rollback stops being cheap after step 3.

New questions for the author, raised by the review:

1. **Per-request dependency as a goal.** Is "no new service on the path of every request" (or on the login path) a requirement you set? If so, I will restore it as a goal.
2. **Today's expiry.** Does every request refresh today's in-memory sessions, so a session expires 12 hours after the last request? The "up to 1 hour less" difference in "Session lifetime" depends on the answer.
3. **Password change and the current session.** When a user changes their password, does the server reissue that browser's cookie with the new epoch, so that only the user's other sessions end?
4. **Epoch reads and the DBA.** Does the DBA's refusal of 9k reads per second on the primary also cover epoch lookups by key, for example ones served from a replica?
