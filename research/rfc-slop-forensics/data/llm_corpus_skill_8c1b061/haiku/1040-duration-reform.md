# Rust RFC 1040: duration

Status: Proposed. [TODO: confirm status and tracking issue]

## Summary

This RFC proposes to stabilize a reduced-scope `Duration` type. The reduced type covers what system calls need in order to take timeouts. It leaves out a large set of conversion methods, because several of them have caveats that are not yet settled. We plan to revisit those conversions as a whole in a later RFC.

## Motivation

Many operating system interfaces accept a timeout. A caller passes a span of time and the call waits at most that long. The span needs a whole-seconds part and a sub-second part, and it has to be expressed in a form that the call can accept without loss. Today each library that needs this choice picks its own representation, so a timeout built in one crate often has to be converted before it can be handed to another. [TODO: list the concrete system calls and library interfaces that take timeouts, with their current parameter types.]

The conversion methods are the part of the type that causes trouble. [TODO: name the conversion methods that are left out and state the caveat for each, with one concrete case where the caveat matters.] Stabilizing them now would fix behavior that we do not yet trust, so this RFC leaves them out.

## Design

The stabilized type represents a non-negative span of time as whole seconds plus nanoseconds below one second. The constructors and accessors it exposes are the ones the timeout use case needs. [TODO: list the stabilized constructors and accessors with their signatures.]

A caller that wants a timeout builds a value of this type and passes it to the interface. The interface does not need to know how the value was built. [TODO: give one short example of a call site before and after the change, if the material has one.]

## Goals and non-goals

Goal: a stable type that can carry a timeout into a system call without a conversion step. We would know this goal was met if the interfaces listed in the motivation accept the stabilized type directly. [TODO: confirm that this check is the right test, and name any interface that would still need a conversion.]

Non-goal: stabilizing the conversion methods that have caveats. This is a deliberate exclusion for this RFC. It does not say that these methods are wrong or will never be stable.

## Decisions

The first decision is to stabilize a subset of the type. The force behind it is the timeout use case, which needs the constructors and accessors above and nothing more. The alternative of stabilizing the full API would bring in the conversions that are not yet settled. [TODO: confirm whether the full API was considered in discussion, and if so, why it was set aside.]

The second decision is to defer the conversions to a later RFC. A user who needs a conversion now has to write it by hand or use an unstable path. [TODO: state the workaround users have today, if any.]

The cost of both decisions falls on users who need more than timeouts. They must wait, or write their own conversions, until the later RFC lands.

Reversibility: adding a method to a stable type is cheap. Removing one, or changing the meaning of an existing one, breaks code that depends on it. Stabilizing a constructor or accessor is therefore the expensive step, and the RFC limits those to the timeout use case for that reason.

## Alternatives considered

[TODO: the author must list the alternatives considered for this RFC. Two candidates that the reader will ask about are leaving the type unstable, and stabilizing the full set of methods. Record for each why it lost.]

## Open questions

- [TODO: which conversion methods will be revisited, and in what order]
- [TODO: the process and timing for the later RFC on conversions]
- [TODO: whether any of the caveats can be documented now without stabilizing the methods]
