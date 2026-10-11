# Rust RFC 2930: read_buf

Status: Proposed. [TODO: confirm status and tracking issue]

## Summary

This RFC proposes an interface that lets implementors and consumers of the `Read` trait work with buffers whose contents are not yet initialized. The interface tracks which bytes have been initialized and which have been filled, so that a consumer never observes an uninitialized byte as if it were data.

## Motivation

The `Read` trait passes a buffer to its methods. The buffer must be initialized before the call, even though the reader is about to overwrite its contents. The initialization is wasted work. For a large buffer, it is a full pass over memory that the reader is going to replace. [TODO: quantify the cost with a measurement from the material, stating the buffer size, the reader, and the platform. Without a measurement, state only that the initialization is redundant.]

The design of `Read` is therefore nonoptimal for readers that fill a buffer from scratch. [TODO: name the in-tree readers or common downstream readers that pay this cost, with a concrete example.]

Working around the requirement is not safe in general. Code that wants to avoid the initialization has to reason about memory it does not own, and a mistake there lets safe code read bytes that were never written. This is the force that makes a new interface necessary: the optimization must be available without giving up the guarantee.

## Design

The new interface pairs a buffer with two counts. One count is the number of bytes that have been initialized, and the other is the number of bytes that have been filled with data. A reader writes into the part that is not yet filled. A consumer reads only the filled part. [TODO: give the exact names of the types and the methods, with signatures, since the design depends on them.]

The initialized count can only grow. Once a byte is initialized, it stays initialized for the life of the buffer. This property is what lets a reader avoid initializing bytes twice. [TODO: confirm this property, and state what operation, if any, can reset the count.]

The goal of the design is that safe code cannot obtain an uninitialized byte through the interface. We would know this goal was met if the interface's safe methods never return a slice over uninitialized memory. [TODO: name the mechanism that enforces this, and the unsafe methods that are exempt from it.]

## Compatibility with existing code

The existing methods of `Read` stay as they are. [TODO: confirm this, and say whether the new interface is a provided method with a default implementation, or a separate trait.]

Existing readers do not have to change. Readers that want the optimization implement the new method. [TODO: state what a reader that implements only the old method gets, and whether any existing code changes behavior. Do not claim compatibility without a test or an audit to support it.]

## Decisions

The first decision is to track initialization in the buffer type, rather than by convention in each caller. The force is the soundness goal above: a convention relies on every caller to get the reasoning right, and the type can enforce it. [TODO: confirm whether a convention-based alternative was considered and why it lost.]

The second decision is to split the buffer into a filled part and an unfilled part, so the consumer's view is always the filled part. The cost is one more type for implementors and consumers to learn, and more methods on `Read`'s companions. [TODO: state how many new public types and methods this adds.]

Reversibility: the new types and trait methods become public API. Once stabilized, their shape is hard to change. The initialization tracking is the part with the highest cost to reverse, so it deserves the most scrutiny. [TODO: list the specific reviewers' concerns the author expects, if any.]

## Alternatives considered

[TODO: the author must list the alternatives considered. Candidates the reader will ask about are keeping the current trait unchanged, and adding an unsafe method that skips initialization. Record for each why it lost.]

## Open questions

- [TODO: whether the unfilled part can be exposed to readers as a write-only view, and the cost of doing so]
- [TODO: the policy for readers that cannot benefit from the new method]
- [TODO: how the design interacts with buffers that are reused across calls]
