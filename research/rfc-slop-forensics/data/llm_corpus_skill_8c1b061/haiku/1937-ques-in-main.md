# Rust RFC 1937: ques_in_main

Status: Proposed. [TODO: confirm status and tracking issue]

## Summary

This RFC allows the `?` operator in `main`, in `#[test]` functions, and in doctests. To make this possible, the return type of these functions is generalized from `()` to a new trait, provisionally called `Termination`. The standard library implements `Termination` for a set of types. [TODO: list the types the standard library implements `Termination` for. The source material says the list is partly to be decided.] Applications can implement `Termination` for their own types.

## Motivation

Today the `?` operator cannot be used in `main`, because `main` returns `()`. A program that calls a fallible function must handle the error with a `match` or an `unwrap`, even when the right response to an error is to report it and exit. [TODO: give a concrete example of a `main` that is forced into this pattern, drawn from the author's material.]

The same limit applies to test functions and doctests. [TODO: state how often this comes up in the tests the author has seen, if the material records it.]

## Design

The return type of `main`, of `#[test]` functions, and of doctests becomes any type that implements `Termination`. The trait decides what the runtime does with the value. [TODO: state what the trait's required method returns, and how a failing value is reported to the user.]

There is no compiler magic. A user who wants `?` in `main` writes the return type explicitly, for example `-> Result<(), ErrorT>`. The compiler does not rewrite the signature for them. [TODO: give the exact `main` example from the author's material.]

Doctests need a hidden function head before they can use `?`. This is a temporary cost. The deployment plan says that the default doctest template will change so that the head is no longer needed in most cases. [TODO: give the deployment plan in full. The material says it is described below in the source, and the author must supply it.]

## Goals and non-goals

Goal: `?` works in `main`, in `#[test]` functions, and in doctests with a return type the user writes. We would know this goal was met when a `main` that returns `Result` compiles and reports its error on failure. [TODO: confirm the reporting behavior for each case.]

Non-goal: changing function signatures in the compiler. Users who want the feature write the signature themselves, and the RFC does not infer one.

## Decisions

The first decision is to generalize the return type through a trait. The force is that the three kinds of function need different reporting behavior, and one trait can cover all of them. [TODO: confirm the reason for a trait over a fixed list of allowed return types, and whether the fixed-list option was considered.]

The second decision is to keep the signature explicit. The reason is that the user should see the return type that governs the function. [TODO: confirm this reason. Do not present it as settled until the author supplies it.]

The cost of the first decision is that the reporting logic lives in a trait that applications may implement. A bad implementation can report errors poorly, and the standard library cannot check it. [TODO: state whether the RFC addresses this, and how.]

The cost of the second decision is that users must write the return type. The doctest template is a second cost until the default is changed.

Reversibility: `Termination` becomes public API once it is stabilized. Its method signature and the set of standard library implementations are the expensive parts to change. Implementations added later are cheap to add. Removing one is a breaking change.

## Alternatives considered

[TODO: the author must list the alternatives considered. The reader will ask about allowing any `Result`-like type with no trait, and about a compiler rewrite of the signature. Record for each why it lost.]

## Open questions

- [TODO: the final list of types that implement `Termination` in the standard library]
- [TODO: the exact deployment steps for the doctest template change]
- [TODO: how a non-`Result` return type should report failure]
