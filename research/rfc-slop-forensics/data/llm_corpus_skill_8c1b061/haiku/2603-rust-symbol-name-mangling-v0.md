# RFC 2603: Symbol name mangling, version 0

- Status: [TODO: status and tracking issue link]
- Number: [TODO: confirm the RFC number; the draft is listed without one]

## Summary

This RFC proposes a new mangling scheme for the symbol names that the Rust compiler generates. The scheme describes what those names look like. It replaces an existing scheme that has grown over time without a clear direction.

## Motivation

A symbol name is the string the linker uses to match a function or a static to its definition. Tools also read these strings. Debuggers, profilers and linkers that inspect a binary can only show a human-readable name if they can decode the string.

The existing scheme has three problems, as this RFC describes them. It is not consistent, because it accumulated rules over time. It depends on compiler internals, so changing how the compiler stores information can change the names it produces. And the names do not reliably carry enough information to be decoded again, which makes life harder for external tools. [TODO: give one or two examples of names in the existing scheme that show each problem.]

The obstacle is the coupling to internals. A name that changes whenever the compiler's internal data changes is hard for any tool to depend on. [TODO: state whether the authors measured how often names changed across compiler versions, or whether this is a qualitative observation.]

## Design

The new scheme is consistent in its structure, depends less on compiler internals, and stores information in the name in a form that can be decoded. The decodability is the feature that serves external tools. [TODO: describe the structure of a name in this scheme, with one worked example.]

The RFC states that the new scheme is not part of the language specification, and it is not part of a stable Rust ABI at this point. In the future it could become part of both. The scheme is designed to be stable and extensible for that purpose. The force behind this design is therefore not stability today, but the ability to become stable later without a second rewrite. [TODO: confirm this framing with the authors.]

## Decision and cost

The decision is to adopt the new scheme in place of the existing one. Its deciding reason is the coupling to compiler internals, because that coupling is what makes the existing names unstable for tools. [TODO: state whether the authors considered keeping the existing scheme and adding a decoder, and why that option lost.]

The cost is that every tool that parses the existing names must be updated, and that the transition period has both schemes in use. [TODO: state how the compiler chooses which scheme to emit, and how long the two are expected to coexist.]

## Reversibility

Symbol names appear in compiled artifacts and in the tools that read them. While the scheme is not stable, the authors can change it with limited disruption. Once tools depend on decoding a particular form, changing that form becomes expensive. The RFC keeps the scheme outside the stable ABI for this reason. [TODO: confirm this is the authors' reason for leaving it outside the ABI.]

## Failure behavior

[TODO: state what an external tool should do when it meets a name in the new scheme that it cannot decode, and what the compiler does when a name cannot be encoded.]

## Open questions

- [TODO: the material breaks off at the point where the RFC discusses the status of the scheme for the time being. Supply the rest of that statement.]
- [TODO: decide which compiler versions must support both schemes.]
