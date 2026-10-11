# Design: Move web sessions to signed cookies

**Status:** Draft, for platform team review (Tuesday)
**Builders:** Auth team
**Source:** Notes from Priya (auth team lead)
**Open before approval:** Session revocation design; security sign-off (Marcus)

## Summary

Each web session is held in the memory of the app server that created it, so every deploy logs out the users on the server being restarted. We propose storing the session in a cookie signed with HMAC-SHA256, using a key from Vault. Any app server can then check any request, deploys no longer log users out, and we can drop sticky routing. The main cost is that a signed cookie can't be revoked before it expires. Security has asked for revocation, and that part of the design isn't settled yet (see [Open questions](#open-questions)).

## Background

- Sessions live in the memory of the app server that created them.
- HAProxy routes each user back to that server using the `srv` cookie (sticky sessions).
- We run 6 app servers. Deploys are rolling, one server at a time, about 4 minutes per server.
- A session lasts 12 hours and is sliding: activity refreshes it.

## Problem

**Deploys log users out.** Restarting a server drops every session in its memory. The March 12 deploy logged out about 40,000 users, and support received 1,100 tickets that day against a normal 150. This happens on every deploy, in proportion to the users on each server.

**Load is uneven.** Sticky routing pins users to servers no matter how busy those servers are. In the week of September 8, the busiest server averaged 2.3 times the requests of the quietest (Grafana).

## Goals

- A deploy or server restart doesn't log anyone out.
- Any app server can handle any request, so HAProxy can stop using sticky routing and balance load.
- Session lifetime and sliding behavior stay as they are today.
- No new dependency on the request path that can take logins down.

## Non-goals

- Changes to SSO.
- Mobile app tokens. They're a separate system and already use JWTs.

## Proposal

### Cookie contents

The session cookie carries:

| Field | Purpose |
|---|---|
| User ID | Who the user is |
| Org ID | Which org the session belongs to |
| Roles | Authorization without a lookup |
| CSRF token | CSRF protection, as today |
| Issued-at | Used to decide when to reissue |
| Expiry | Absolute end of the session |

The payload is signed with HMAC-SHA256. It's signed, not encrypted, so the client can read the contents but can't change them. Nothing in the list above is secret from the user it belongs to.

### Verification

On each request, the server checks the signature and the expiry. If both are valid, the request is authenticated without any network call or database read.

### Lifetime and sliding refresh

Sessions last 12 hours, as today. To keep them sliding, the server reissues the cookie, with a new issued-at and a new 12-hour expiry, on any request that arrives more than 1 hour after the current cookie was issued. This way active users stay logged in, and we only rewrite the cookie at most once an hour per user rather than on every request.

One side effect: a session can now run out up to 1 hour earlier than it would with a refresh on every request (11 hours after the last reissue, if the user then goes idle). We think that's acceptable, but it's a small change in behavior.

### Signing keys

Keys come from Vault. Two keys are active at any time: servers sign with the newer one and accept either. We rotate quarterly. On rotation, the new key becomes the signing key and the oldest key is retired. Since sessions last at most 12 hours, any cookie signed with the retired key will have expired long before it's retired.

### Size

We measured current session payloads at an average of 1.1 KB and a maximum of 3.2 KB. The largest are users with many org roles. Browsers allow about 4 KB per cookie, and that limit includes the cookie name and attributes. The figures above don't say whether they include encoding and the signature, and that needs checking before we build. If they don't, the largest sessions may already be close to or past the limit. See [Open questions](#open-questions).

## Alternatives considered

### Redis session store

Rejected. This puts Redis on the login path for every request. Redis had two outages last quarter: July 3 (47 minutes) and August 19 (12 minutes). Today Redis is only a cache, so those outages made pages slow. As a session store, the same outages would have stopped everyone from being authenticated. Making Redis reliable enough for this would need high-availability work we haven't staffed.

### Postgres sessions table

Rejected. Every request would need a session lookup on the primary, about 9,000 requests per second at peak. The DBA declined to take on that load.

## Rollout

1. **Dual-write.** Servers write both the in-memory session and the cookie, and keep reading from memory. Behavior for users doesn't change. This phase tests cookie issuing, size and signing in production.
2. **Switch reads.** A flag switches reads to the cookie. In-memory writes continue.
3. **Remove stickiness.** HAProxy stops routing on `srv`, and we remove the in-memory write path.

**Rollback.** While dual-write is still on (steps 1 and 2), we can roll back by switching the flag to in-memory reads again. After step 3, that's no longer possible: memory sessions are no longer written and requests aren't routed to the server that would hold them. A rollback after step 3 would log users out.

Points to settle before step 2:

- **Sessions that predate dual-write.** A session created before step 1 has no cookie. Either we wait at least 12 hours after dual-write is fully deployed before switching reads, or the cookie read falls back to memory when there's no cookie.
- **Deploys during step 1 still log users out**, since reads still come from memory. The fix only takes effect from step 2.

## Risks

- **No early revocation.** A cookie stays valid until it expires, even after logout, a password change or a role change. A stolen cookie can be used for up to 12 hours, longer if the attacker keeps refreshing it. This is the main security cost of the design and is the subject of the first open question.
- **Stale roles.** Roles are copied into the cookie, so a role change only takes effect when the cookie is reissued (up to 1 hour for an active user) or the session ends. If that isn't acceptable for removing permissions, it's the same problem as revocation.
- **Cookie size.** See [Size](#size). If role lists keep growing, some users could exceed the browser limit. Browsers handle that by dropping the cookie, which logs the user out with no clear error.
- **Key compromise.** Anyone with a signing key can mint a session for any user. The key is protected by Vault and quarterly rotation, but we need a procedure to rotate out a leaked key straight away. Doing that will log out everyone whose cookie was signed with it.

## Open questions

1. **Revocation (blocking; needs Marcus's sign-off).** Security wants to revoke sessions on password change and for "log out all devices". The current idea is a per-user `session_epoch` integer in the users table. The cookie carries the epoch, and incrementing it invalidates every older cookie. Checking it on every request would bring back the database read per request this design is meant to avoid. Options being considered:
   - Check the epoch only on sensitive actions.
   - Cache epochs in each process for 60 seconds, so revocation takes effect within about a minute.
   - A combination of the two.

   No decision has been made. We'd like the platform team's input on Tuesday, but this needs security's approval before we build.
2. **Cookie size headroom.** Confirm whether the 3.2 KB maximum includes encoding and the signature. Decide whether to store role IDs instead of role names to reduce size now and leave room for growth.
3. **Pre-dual-write sessions.** Decide between waiting 12 hours and adding a memory fallback (see [Rollout](#rollout)).
