# Design: signed-cookie web sessions

Status: proposed. Author: auth team (Priya). Reviewers: platform team. Security sign-off: pending (Marcus).

## Context and scope

A web session today lives in the memory of the app server that created it. HAProxy sends each user back to that server by reading the `srv` cookie (sticky routing). We run six app servers and deploy them one at a time, about 4 minutes per server.

Restarting a server drops every session in its memory, and those users are logged out. A full rolling deploy restarts all six servers, so it logs out every signed-in user. The March 12 deploy logged out about 40k users, and support received 1,100 tickets that day against a normal 150.

Sticky routing also spreads load unevenly, because a server keeps its users for the life of their sessions. In the week of September 8, the busiest server averaged 2.3 times the requests of the quietest (Grafana).

This doc proposes moving the session out of server memory and into a signed cookie that the browser sends with each request. Any server can then verify the session, so a restart logs no one out and HAProxy no longer needs to route by `srv`. "We" in this doc means the auth team, which will build the change.

## Goals and non-goals

Goals:

- A rolling deploy logs out no users. We check this by the count of forced logouts and by support ticket volume on deploy days.
- HAProxy no longer uses sticky routing, and the busiest server's request rate is within [TODO: target ratio] of the quietest's, measured over a week in Grafana as in the September 8 baseline.
- Session lifetime stays 12 hours, extended on activity, apart from the up-to-1-hour difference described in "Session lifetime".
- [TODO: is 'no new per-request dependency' a stated requirement?]

Non-goals:

- Changes to SSO.
- Mobile app tokens. The mobile app uses a separate system that already issues JWTs.

## Design

### Overview

At login, the app server builds the session payload, signs it with HMAC-SHA256, and sets it as a cookie. The signing key comes from Vault. On each request, whichever server HAProxy picks checks the signature and the expiry and reads the session from the cookie. It looks nothing up. When more than an hour has passed since the cookie was issued, the server issues a fresh one, which keeps sessions sliding as they do today.

Most of the design follows from keeping no session state on the server. The exception is revocation, which is not settled.

### Where the session lives

Deploys log users out because the session exists in one server's memory and nowhere else. Any fix has to put the session somewhere that survives a restart and that every server can read. We considered three places: Redis, a Postgres table, and the browser.

A Redis session store would put Redis on the login path. Redis had two outages last quarter, on July 3 (47 minutes) and August 19 (12 minutes). Today Redis is only a cache, so those outages made pages slow. With sessions in Redis, the same outages would have stopped users from logging in. [TODO: say whether existing sessions would also have failed during an outage.] Making Redis highly available enough for that role is work we have not staffed.

A Postgres sessions table would make every request read the session from the primary. That is about 9k reads per second at peak, and the DBA declined to take that load on the primary.

A signed cookie needs no shared store. A server verifies the session with a key it already holds, so no other service sits on the path of each request, and a server restart loses nothing. A Redis store would put a service with a recent outage record on the login path, and a Postgres table would put load on the primary that the DBA refused. The cookie depends on neither, and that is why we chose it.

[TODO: Was any option that keeps in-memory sessions considered, such as draining a server's sessions before restarting it? If so, add it here with the reason it lost.]

The cookie gives up two things. First, the server can no longer delete a session: a cookie stays valid until it expires, even after the user logs out, unless we add a revocation check (see "Revocation"). Second, the browser sends the session with every request. At the measured average of 1.1 KB and about 9k requests per second at peak, that is roughly 10 MB/s of extra request traffic into HAProxy at peak (about 13 MB/s if 1.1 KB is the raw payload before base64). [TODO: confirm this is acceptable to the platform team.]

Once sticky routing is removed, going back to any server-side store means building that store, and going back to in-memory sessions means restoring sticky routing.

### What the cookie holds

The cookie carries the user id, org id, roles, CSRF token, issued-at time and expiry. These are the fields a server needs to authorize a request without a lookup.

Browsers allow 4 KB per cookie. We measured the payload at 1.1 KB on average and 3.2 KB at most. The largest payloads belong to users with many org roles. [TODO: are these sizes of the encoded cookie value including the signature, or of the raw payload? If raw, base64 encoding adds about a third, which would put 3.2 KB above 4 KB. Also confirm whether the 4 KB limit has to cover the cookie name and attributes.]

A payload over the limit cannot be set, so the largest payload decides how much room is left. Today that is 0.8 KB if the measured sizes are of the encoded cookie [TODO: see above], and it shrinks as users gain roles. Storing role ids instead of names would make the payload smaller; it is listed under "Open questions".

The payload is signed but not encrypted, so anyone holding the cookie can read the user id, org id and roles. [TODO: confirm that security accepts this, and whether encryption was considered.]

Because roles travel in the cookie, a change to a user's roles reaches their session only when the cookie is reissued. [TODO: does the hourly reissue read roles from the database, or copy them from the old cookie? If it copies them, a removed role stays in effect until the session expires.]

[TODO: list the cookie attributes (HttpOnly, Secure, SameSite, Domain), and whether CSRF protection changes now that the CSRF token lives inside the session cookie.]

[TODO: will the cookie carry a format version, so that a later change to the payload does not log users out?]

### Session lifetime

Sessions last 12 hours, as today, and slide on activity, as today. A server reissues the cookie, with a new issued-at and expiry, on a request that arrives more than 1 hour after the current cookie was issued. [TODO: why 1 hour rather than reissuing on every request?]

The 1-hour threshold changes lifetime slightly. A request less than an hour after the last reissue does not extend the session, so an active user's session ends between 11 and 12 hours after their last request. [TODO: confirm that today's sessions expire 12 hours after the last request] [TODO: confirm that up to 1 hour less is acceptable, or shorten the threshold.]

### Signing keys

Each server signs cookies with HMAC-SHA256 under a key from Vault. [TODO: why HMAC-SHA256? The mobile app already uses JWTs; say whether reusing that format or an asymmetric signature was considered, and why it lost.]

Two keys are active at a time. Servers sign with the newer key and accept cookies signed with either. We rotate quarterly: a new key becomes the signing key, the previous signing key stays accepted, and the oldest key is dropped. Every cookie expires within 12 hours of issue, so dropping a key a quarter after it stopped signing logs out no one. [TODO: why quarterly?]

During a rolling deploy, servers run with different key sets for about 24 minutes (six servers at about 4 minutes each). If an updated server signs with a new key that an old server does not yet accept, users routed to the old server are logged out. [TODO: confirm the rotation procedure, for example shipping the new key as accepted-only in one deploy and making it the signing key in the next.]

[TODO: when do servers fetch keys from Vault, at startup or at runtime, and what happens if Vault is unavailable then?]

[TODO: what is the procedure if a signing key leaks? Replacing both keys invalidates every cookie and logs out every user.]

### Revocation

This is the unresolved part of the design, and the design is not ready for approval until security (Marcus) signs off.

A signed cookie is valid until its expiry, whatever happens on the server. Logging out deletes the cookie from that browser, but a copy of it, for example one taken by an attacker, keeps working for up to 12 hours after its last use, and indefinitely if it is used at least every 12 hours, because each reissue extends it. Security (Marcus) wants revocation in two cases: when a user changes their password, and when a user chooses "log out all devices". Both cases revoke every session of one user, so a per-user check covers them.

The proposed mechanism adds an integer `session_epoch` to each row of the users table and copies it into the cookie at issue. Password change and "log out all devices" increment the user's epoch. A cookie whose epoch is lower than the user's current epoch is rejected. [TODO: does the server reissue the current session's cookie with the new epoch on a password change, so that only the user's other sessions end?]

The open question is when a server compares the two epochs, because each comparison reads the users table. The per-request check reads the users table about 9k times per second at peak. Two cheaper places to check have been suggested, and the table compares all three. They trade revocation delay against database load:

| Where the epoch is checked | Database reads | Time until a revoked cookie stops working |
|---|---|---|
| Every request | About 9k per second at peak | Immediate |
| Sensitive actions only | One per sensitive action [TODO: volume] | Immediate for sensitive actions; until the cookie expires for everything else, which an active user of the cookie can postpone indefinitely |
| Every request, with epochs cached in each server's memory for 60 s | At most one per active user per server per minute [TODO: estimate from active users] | Up to 60 seconds |

Checking on every request reads the database at the same rate as the Postgres sessions table, which the DBA refused [TODO: would the DBA's objection also apply to epoch reads, for example from a replica?], so it would undo the reason for choosing cookies. The two remaining options can be combined: check sensitive actions against the database, and other requests against the 60-second cache. Neither option has been chosen.

[TODO: which actions count as sensitive?]

[TODO: was checking the epoch only when the cookie is reissued, at most once an hour per session, considered? It would bound database reads by the reissue rate, with up to an hour of delay.]

[TODO: is revoking a single session, for example from a list of the user's devices, in scope? A per-user epoch cannot do it.]

To decide, we need from security the longest acceptable delay between a password change and the revocation of the user's other sessions, and the list of actions that must always see a current epoch.

## Failure behavior

Restarting or deploying an app server does not affect sessions, except a deploy that changes the signing keys (see "Signing keys"). The remaining failures are these, and most of their handling is not yet specified:

- Vault is unavailable. [TODO: whether servers need Vault only at startup or also at runtime, and what a server does if it cannot load keys.]
- A cookie has a bad signature, an unknown key or a past expiry. [TODO: confirm the server treats the request as logged out and sends the user to login, and whether these rejections are counted and alerted on, since a spike would show a key rollout gone wrong.]
- A payload exceeds the cookie size limit. [TODO: what happens at login for a user whose payload does not fit, and how we detect payloads approaching the limit.]
- The users table is unavailable during an epoch check. This applies only if revocation checks the database. [TODO: reject the request or accept the cookie; security should decide.]

## Rollout and rollback

A flag selects whether servers read sessions from memory or from the cookie. The rollout has three steps:

1. Ship dual-write: servers write both the in-memory session and the cookie, and read from memory first. Keep sticky routing on.
2. Flip the flag so servers read from the cookie.
3. Remove sticky routing from HAProxy.

While dual-write is on, rollback is flipping the flag back to in-memory reads.

The deploy that ships step 1 restarts every server under the current scheme, so it logs users out like any deploy today. [TODO: schedule it for a low-traffic window, or accept it.]

The same deploy means every session alive after step 1 was created with a cookie. [TODO: confirm that dual-write also reissues the cookie hourly, so that the cookie does not expire before the in-memory session it mirrors.]

[TODO: how long each step runs, and which metrics gate moving to the next.]

After step 3, rollback is no longer cheap. Once HAProxy stops routing by `srv`, requests land on servers that do not hold the user's in-memory session, so flipping the flag back would log users out. [TODO: confirm, and say whether dual-write is removed in a later step.]

## Open questions

- Revocation: where to check `session_epoch`, which actions count as sensitive, and the maximum acceptable revocation delay. Needs security's sign-off (Marcus). See "Revocation".
- Cookie growth: the payload grows with a user's roles, and the largest is 0.8 KB under the 4 KB limit if the measured sizes are of the encoded cookie [TODO: see "What the cookie holds"]. The encoded size may already exceed 4 KB. Storing role ids instead of names would shrink it; whether to do so before launch is open.
- Key rotation across a rolling deploy: how to introduce a new signing key without logging out users routed to servers that do not yet accept it. See "Signing keys".
- Unencrypted payload: whether security accepts that anyone holding the cookie can read the user id, org id and roles. See "What the cookie holds".
- Key leak: the procedure if a signing key leaks, given that replacing both keys logs out every user. See "Signing keys".
