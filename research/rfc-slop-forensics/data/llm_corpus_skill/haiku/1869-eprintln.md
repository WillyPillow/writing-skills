# Rust RFC 1869: eprintln

Document type: Rust language/tooling RFC
Status: [TODO: RFC status and tracking details]

## Context and scope

The prelude is the set of names that are in scope in every module without an import. This RFC proposes adding two macros to the prelude: `eprint!` and `eprintln!`.

The macros are exactly the same as `print!` and `println!`, respectively, except that they write to standard error instead of standard output.

[TODO: How a program writes to standard error today, and what that costs in code. The author has not supplied this.]

## Motivation

[TODO: A concrete case in which a program needs to write a diagnostic to standard error and the current way of doing it is inconvenient. The material gives the proposal but no case.]

## Goals

- Provide `eprint!` and `eprintln!` in the global prelude.
- Give them the behavior of `print!` and `println!`, with output going to standard error. [TODO: A checkable criterion, such as a test showing that the same format string produces the same text on each stream.]

## Non-goals

[TODO: Anything a reader might expect from this addition that the RFC deliberately excludes. The author has not stated any.]

## Design

The two macros take the same arguments as the macros they mirror and produce the same text. Only the output stream differs.

[TODO: Whether argument handling and error behavior match exactly for both pairs of macros, and where the author has checked this.]

## Compatibility

Adding names to the prelude changes which names are in scope everywhere. Code that already defines a macro or item with the name `eprint` or `eprintln` may be affected, depending on how the names resolve. The material does not address this.

[TODO: How the prelude addition interacts with user code that already uses these names, and the evidence for the answer.]

## Implementation status

The RFC says that an implementation already exists. [TODO: The link to the implementation, and what it covers. The material refers to one but does not include the link.]

## Alternatives considered

[TODO: Alternatives the author evaluated, in their strongest form. The material gives none.]

A reviewer may ask whether existing standard library interfaces already let a program write to standard error, and why a pair of macros is preferred to them. The author should answer this, since it bears directly on the motivation.

## Cost

[TODO: What the addition costs, including the names it takes from the prelude and any effect on code that defines the same names.]

## Reversibility

Names in the prelude are part of the public surface that programs depend on. [TODO: Whether the author regards these names as expensive to remove once they are stable.]

## Rollout

[TODO: The path to stabilization and any feature gate.]

## Open questions

- [TODO: Questions the author wants reviewers to address.]
