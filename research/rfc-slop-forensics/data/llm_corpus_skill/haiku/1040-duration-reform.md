# Stabilize a reduced-scope `Duration`

Status: proposed. [TODO: author to confirm the status field and the RFC number format used by the venue.]

## Summary

This RFC proposes stabilizing a `Duration` type with a deliberately reduced scope. The reduced type exists to pass spans of time to the system calls that take timeouts. It leaves out a large number of conversion methods on `Duration`, because those methods have subtle caveats. The conversions are not rejected. They are deferred, so that they can be revisited together later.

## Motivation

System calls that wait on events take a timeout. A caller that makes such a call must express the wait as a span of time that the system call accepts. [TODO: name the system calls and platforms this proposal targets, and state which of them take a timeout today and in what form.]

Callers currently represent this span in [TODO: describe the representations in use and what they lack that a shared type would supply.] The force behind the proposal is therefore the need for one type that is accepted at the boundary with the operating system. [TODO: give a count of call sites or crates that need this, if the author has one. Without a count, the claim that the need is widespread is not supported by the material.]

The abstract names a second force, which is the set of conversions that the RFC does not stabilize. Those conversions are the ones with caveats. A stabilized conversion keeps its behavior fixed across later releases, so a conversion with an unresolved caveat cannot be stabilized without deciding that caveat now. [TODO: author to state each caveat, one per excluded conversion, with a short case in which it matters.]

The question this RFC answers is how much of `Duration` can be stabilized now without making decisions that a fuller later revision might need to reverse. The reduced surface is the answer to that question, and the rest of the document explains why the answer is safe.

## Guide-level explanation

A `Duration` represents a span of time. [TODO: state the representation the author intends, including precision and range. The proposal depends on it and the material does not give it.] A caller that needs a timeout constructs a `Duration` and passes it to the call. [TODO: insert a short example with the stabilized constructor and a timeout-taking function. The author should write this example.]

Readers should understand that the stabilized surface is small on purpose. Methods not named in this RFC are not part of the proposal. Code that needs them must wait for the later revision or use [TODO: name the existing workaround, if one exists].

## Reference-level design

The stabilized surface consists of the following items. [TODO: list each constructor, accessor and trait implementation with its signature.] Each item should be tied to the timeout use case. An item that no timeout caller needs does not belong in the reduced surface. The author should say which caller needs each item.

Boundary behavior is where caveats usually sit, so this section must say what the stabilized items do in the cases that those caveats concern. [TODO: specify the behavior on overflow, on values the system call cannot represent, and on zero.] A reader who finds the behavior unstated in any of these cases should treat it as an open question, not as a settled property of the type.

The excluded conversions are not stabilized here, and this RFC does not otherwise change them. [TODO: author to confirm whether the excluded items remain unstable, are removed from the unstable surface, or are left as they are.]

## Why the scope is reduced

The central tension of this RFC is between shipping a type that callers can use now and getting every conversion right on the first attempt. The abstract resolves the tension in favor of shipping now. Its reason is that the excluded conversions are to be revisited "more holistically." That phrase implies that the conversions depend on one another, so that settling them one at a time could fix choices that conflict when taken together. [TODO: author to confirm this reading and to give at least one concrete pair of conversions whose decisions depend on each other.]

If that dependency is real, stabilizing a subset now is safe only if the subset does not constrain the later decisions. The reduced surface must therefore avoid any item whose behavior would fix a choice the later revision might make differently. [TODO: author to state which items were checked against this condition, and how each was checked.]

Without the dependency, the case for reduction is weaker. A set of independent conversions could be stabilized one by one, each with its own review. The abstract does not claim that the conversions are dependent in every case, so the author should say which conversions are independent and why they are excluded anyway.

## Status of the proposal

The RFC decides two things: the reduced surface is stabilized, and the excluded conversions are not stabilized here. The exact list of items and the boundary behavior are proposed and open to comment. Whether the later revision is scheduled, and what its scope is, is open. [TODO: author to confirm this classification and to correct any item placed in the wrong category.]

## Alternatives

The drafter has not verified that any of the alternatives below was considered. The author should say which were considered, in their strongest form, and why each lost. Until the author does so, these are suggestions for evaluation, not options that were rejected.

One alternative is to stabilize the whole conversion API now. This would avoid a second stabilization, but it would fix the caveats the RFC defers. [TODO: author to state whether this was considered and why it was rejected.]

A second alternative is to keep the type unstable until the fuller revision. This makes no compatibility promise, but timeout callers would lack a shared type for an open-ended period. [TODO: author to state whether this was considered.]

A third alternative is to stabilize a single conversion, such as one to a raw integer. [TODO: author to say whether this was considered and whether it would constrain the later decisions.]

## Migration and compatibility

Adding a new type does not change code that already exists. [TODO: confirm that the type name does not collide with an existing public item, and state whether any existing API takes or returns a type that would change.] Callers that opt in do so by naming the new type. No caller is moved automatically.

## Drawbacks

Callers that need an excluded conversion must wait for the later revision or use a workaround. [TODO: name the workaround and state how common the need is.] A reduced type also means that stabilization happens in more than one step, and each step carries its own review cost. The RFC accepts these costs because it serves the timeout use case first. [TODO: author to confirm that this is the trade-off the RFC intends.]

## Reversibility

Stabilized items are costly to change, because callers depend on them. The items with the highest cost to reverse are the constructors and the boundary behavior, since every timeout caller depends on both. [TODO: author to state whether any item can be changed later without a breaking release.] Those items need the most justification, and the author should say what evidence supports each one.

## Open questions

The exact list of stabilized items is open for review. The boundary behavior for each case is open for review. Whether any excluded conversion should be stabilized with this RFC is open, and the material does not settle it. [TODO: author to decide or confirm.] Whether the revisit should have a date or a trigger is open. [TODO: author to supply.]
