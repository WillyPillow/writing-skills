# RFC 1869: `eprintln`

- Status: [TODO: status and tracking issue link]
- Implementation: an implementation exists. [TODO: link to the implementation and its pull request.]

## Summary

This RFC adds two macros to the global prelude, `eprint!` and `eprintln!`. They behave exactly like `print!` and `println!`, respectively, except that they write to standard error instead of standard output.

## Motivation

Programs often write diagnostic output, such as progress messages, warnings and errors, that should not mix with the data they produce on standard output. Writing that output to standard error is the usual way to keep the two apart. [TODO: state how programs currently write to standard error, and give the code they must use. The material does not show this, so it is not written here.]

The obstacle is the length and the friction of the current approach. A program that writes to standard error needs more code than one that writes to standard output, and the extra code obscures the intent. [TODO: give a concrete example from the material, such as a common pattern that programs repeat, and state how often it appears.]

## Design

The two macros are added to the prelude, so they are available in every program without an import. Their formatting rules are the rules of `print!` and `println!`, and their destination is standard error. The RFC makes no other change.

The choice to match the existing macros exactly is the central decision. A program that switches a line from `println!` to `eprintln!` should see the same formatting and the same newline behavior, and should need no other change. The force behind this is that the output of a program should not depend on which stream a message goes to. [TODO: confirm this is the authors' reason, and state whether they considered a different name or a different interface.]

The choice to place the macros in the prelude, rather than in a module that must be imported, follows from the same motivation. A macro that must be imported is more friction for a diagnostic that programs use in many places. [TODO: state whether the authors considered the module alternative, and the reason it lost.]

## Alternatives considered

[TODO: list the alternatives the authors considered, for example a single macro with a stream argument, a function in the standard library, or leaving the choice to external crates. The material does not record them, so they are not presented here as considered or rejected.]

## Cost accepted

Every program gains two names in its prelude. A user-defined macro with the same name may conflict with them. [TODO: state how the authors expect name conflicts to be resolved, and whether they checked for conflicts in existing code.]

## Reversibility

Items in the prelude are hard to remove once stabilized, because removing one breaks every program that uses it without an import. The names should therefore be settled before stabilization. [TODO: confirm the authors have settled the names.]

## Drawbacks

[TODO: state the drawbacks the authors see, or state that none apply and why.]

## Unresolved questions

- [TODO: decide whether the macros should be documented alongside `print!` and `println!`, or in a separate section.]
- [TODO: decide whether any further change to the output stream, such as buffering, should be specified here.]
