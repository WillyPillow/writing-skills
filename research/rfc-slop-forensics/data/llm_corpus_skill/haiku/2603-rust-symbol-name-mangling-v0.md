# Rust RFC 2603: [TODO: title; the material gives "N/A"]

Document type: Rust language/tooling RFC
Status: [TODO: RFC status and tracking details]

## Context and scope

When the Rust compiler emits a function or a static, the emitted object needs a symbol name, which the linker uses to refer to it. Symbol name mangling is the encoding that turns the path of an item into such a name. The current Rust scheme has grown over time without a clear direction.

This RFC proposes a new mangling scheme, which the material calls v0, that describes the symbol names the Rust compiler generates.

[TODO: Whether the scheme covers every kind of generated symbol or only some of them.]

## Motivation

The RFC claims three advantages over the existing scheme. The new scheme is consistent. It depends less on compiler internals. The information it stores in a symbol name can be decoded again. The decodability serves users of external tools that work with Rust symbol names.

[TODO: The evidence for each advantage. The author should supply the evidence for consistency and for reduced dependence on compiler internals, because the material asserts both without support.]

[TODO: Which external tools need to decode symbol names, and what goes wrong for them under the current scheme. Give one concrete failure.]

## Goals

- A mangling scheme that is consistent. [TODO: What consistency means for this scheme, and how a reviewer would check it.]
- Names that depend less on compiler internals. [TODO: How this is measured or demonstrated.]
- Names from which the stored information can be decoded. [TODO: One example of a name and what it decodes to.]

## Non-goals

- Making the scheme part of the language specification now. The RFC says the new scheme "would not be part of the language specification or the specification of a stable Rust ABI" at this point.
- Stabilizing the scheme now. The RFC says it could be part of both specifications in the future, and that it is designed to be stable and extensible.

[TODO: The criteria for deciding, in the future, to include the scheme in the specifications.]

## Design

[TODO: The encoding rules of the v0 scheme. The material does not include them. The author should supply the rules and one symbol name in the existing scheme alongside the same item in v0.]

The RFC says the scheme is designed to be stable and extensible. [TODO: The mechanism that provides extensibility, such as a version marker or reserved encodings, and what it allows a later version to change.]

## Alternatives considered

[TODO: Alternatives the author evaluated. The material gives none. Do not record an alternative as considered until the author describes it.]

## Cost

[TODO: What the new scheme makes harder or gives up. For example, the author should say how tools that read the existing scheme are affected while both schemes are in use, if they are.]

## Reversibility

Symbol names are visible to external tools, and the RFC states that the scheme may later become part of a stable ABI. Once it is part of a stable specification, changing it is expensive. [TODO: The author's view on how reversible the choice is before stabilization, and which parts of the design are fixed now.]

## Rollout

[TODO: How the scheme is turned on, whether it is the default, whether it can be opted out of, and how a user would revert to the existing scheme.]

## Open questions

- [TODO: Questions the author wants reviewers to address, including whether any part of the scheme needs to be stabilized sooner.]
