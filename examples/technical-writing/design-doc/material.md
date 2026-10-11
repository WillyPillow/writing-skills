# Author's material: session storage design doc

Request: Write a design doc proposing that we move web sessions to signed cookies. Readers: the platform team, who review it next Tuesday, and the auth team, who will build it.

Notes from Priya (auth team lead):

- Today sessions live in the memory of the app server that created them. HAProxy routes by the `srv` cookie (sticky sessions).
- 6 app servers. Deploys are rolling, one server at a time, about 4 min per server.
- Problem: deploying a server drops every session on it, so its users get logged out. The March 12 deploy logged out about 40k users. Support got 1,100 tickets that day (normal is about 150).
- Sticky routing also makes load uneven. Week of Sept 8: the busiest server averaged 2.3x the requests of the quietest (Grafana).
- Proposal: the session goes in a cookie, signed with HMAC-SHA256, key from Vault. Payload: user id, org id, roles, CSRF token, issued-at, expiry.
- Session lifetime 12 h, same as today. Today's sessions are sliding (refreshed on activity). Keep that: reissue the cookie when more than 1 h has passed since it was issued.
- Session payload size, measured: average 1.1 KB, max 3.2 KB (users with many org roles). Browsers allow 4 KB per cookie.
- Considered a Redis session store. Rejected: it puts Redis on the login path. Redis had 2 outages last quarter (Jul 3, 47 min; Aug 19, 12 min). Today Redis is only a cache, so those outages just meant slow pages. Redis would also need HA work we haven't staffed.
- Considered a Postgres sessions table. Every request would hit the primary for a session lookup, about 9k req/s at peak. The DBA said no.
- Downside: we can't revoke a session before it expires. Security (Marcus) wants revocation for password change and "log out all devices". Idea: a per-user `session_epoch` integer in the users table; the cookie carries the epoch. But checking it needs a DB read per request, which is what we wanted to avoid. Maybe check only on sensitive actions, plus cache epochs in-process for 60 s? Not decided. Marcus hasn't signed off.
- Key rotation: two active keys; sign with the newest, accept both. Rotate quarterly.
- Rollout: dual-write phase where servers write both the in-memory session and the cookie and read in-memory first; then switch reads to the cookie; then remove stickiness. Rollback is flipping the flag back to in-memory reads while dual-write is still on.
- Not doing: SSO changes, mobile app tokens (separate system, already JWT).
- Open: cookie size will grow if roles grow; maybe store role ids instead of names.
