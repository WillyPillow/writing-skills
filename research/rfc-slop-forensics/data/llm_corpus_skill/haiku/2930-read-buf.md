# Uninitialized buffers for `Read`

Status: proposed. [TODO: author to confirm the status field and the RFC number format used by the venue.]

## Summary

The `Read` trait takes a buffer and fills it with bytes. Its methods require that the buffer be initialized before the call, even though the implementation will overwrite its contents immediately. This RFC proposes an interface that lets implementors and consumers of `Read` types work with uninitialized buffers, robustly and soundly.

## Motivation

The current design is nonoptimal for one specific reason. A consumer that wants to read into fresh storage must first initialize that storage, usually by writing zeros, and the reader then overwrites those zeros. [TODO: state the cost of the initialization, measured or estimated, with the inputs shown. Without a measurement the claim that the cost is significant is not supported.]

The force is the gap between what the trait requires and what the operation does. Initialization is required by the signature, not by the work. [TODO: author to name the workloads or callers that pay this cost in practice, such as a particular kind of I/O loop, so that readers can see where the cost arises.]

A second force is safety. Code that wants to avoid the initialization may reach for uninitialized memory directly, and it then has to reason about soundness on its own. [TODO: author to state whether this has produced known incidents or bugs in the material. If none exist, the text should not claim that it has.]

The obstacle, then, is that the present signature leaves two options: pay for initialization that does no useful work, or take on the soundness burden without help from the trait. The RFC aims to remove the choice between them.

## Guide-level explanation

The proposal gives readers a way to hand a `Read` implementation a buffer whose contents are not yet known to be initialized, and to receive back how much of it was filled. [TODO: describe the interface in one or two sentences, using the names the author intends. The material supplied names no types or methods.]

A consumer that adopts the interface passes storage without initializing it first. An implementor that adopts it writes into the storage and reports how many bytes it produced. [TODO: insert a short example of each side. The author should write both examples so that the names match the reference section.]

Implementors that do not adopt the interface keep the existing behavior. [TODO: confirm this claim against the final design. It holds only if the interface is additive and has a default that calls the existing methods.]

## Reference-level design

The interface has the following parts. [TODO: name the buffer type, the methods that expose its initialized and filled regions, and the method that performs the read.] Each part should carry a stated invariant. For example, the buffer should state which bytes are initialized and which are filled, and the invariant that connects the two. [TODO: author to state the invariants exactly.]

Soundness is the central requirement, and the abstract names it directly. A reader of this section should be able to check that no safe caller can observe uninitialized memory through the interface. [TODO: author to give the argument for this, or the exact list of unsafe operations a caller must perform and the conditions each requires.]

Implementors must be able to write into uninitialized storage without reading it first. [TODO: state which operations the implementor may perform on the buffer, and which it may not.] If the implementation returns the count of bytes it wrote, the interface must say what happens when the implementation reports more bytes than the buffer holds. [TODO: specify this case.]

## Why the design takes this shape

The central tension is between the performance of avoiding initialization and the soundness of the resulting code. The abstract resolves this by giving the soundness requirement priority, since it says the interface must work "robustly and soundly." The shape of the interface follows from that priority. [TODO: author to state whether a faster design that is less sound was considered, and why it lost.]

A design that tracks initialization in the type system is one way to make the invariants checkable. A design that relies on documentation alone is another. [TODO: author to say which of these the RFC adopts, and what each costs. The drafter does not know which was considered.]

## Compatibility

Existing `Read` implementations and existing callers should continue to compile and behave as before. [TODO: this is a compatibility claim. Support it with the default method argument, or with the list of existing implementations checked. Without support, narrow the claim.]

## Alternatives

The following alternatives are suggestions for the author to evaluate. The drafter has not verified that any of them was considered.

The first alternative is to leave the trait unchanged and let consumers initialize their buffers. This preserves compatibility and gives no new soundness burden, but it keeps the cost the RFC targets. [TODO: author to state whether this was considered and why it was rejected.]

The second alternative is to add an unsafe method that accepts uninitialized storage and leaves all invariants to the caller. This is the smallest change, but it moves the entire soundness burden onto every caller. [TODO: author to say whether this was considered.]

## Drawbacks

The interface adds a second way to read, which implementors and consumers must learn. [TODO: state the expected cost in documentation and in maintenance of implementations.] Each invariant the interface adds is a rule that must be documented and tested. [TODO: author to name the tests or checks that will enforce the invariants.]

## Reversibility

Changes to a public trait are costly, since every implementor depends on the method set. The method names and the invariants are the parts that cannot easily be revised once stabilized. [TODO: author to state which parts can be changed later and which cannot.] These parts need the strongest justification in the RFC.

## Open questions

The exact interface is open for review. The invariants and the cases of overreporting are open. The measured cost of initialization in the motivating workloads is open, because the material supplied gives no measurement. [TODO: author to supply the measurement, with its setup, or to remove the performance claim.]
