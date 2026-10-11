# RFC: Procedural macros 1.1 (`rustc_macros`)

- Feature Name: `rustc_macros`
- Start Date: 2016-07-14
- RFC PR: rust-lang/rfcs#1681
- Rust Issue: rust-lang/rust#35900

## Summary

Extract a very small sliver of today's procedural macro system in the compiler, just enough to get basic features like custom derive working, to have an eventually stable API. Ensure that these features will not pose a maintenance burden on the compiler but also don't try to provide enough features for the "perfect macro system" at the same time. Overall, this should be considered an incremental step towards an official "macros 2.0".

## Motivation

Some of the most popular crates in the Rust ecosystem rely on the ability to generate code from type definitions. The `serde` family of crates serializes and deserializes arbitrary structs. Diesel derives database mappings. Many smaller crates derive builders, getters, or conversions. All of this has historically depended on one of two mechanisms.

The first is the compiler plugin system (`#![plugin]`, `rustc_plugin`), which gives a library direct access to the compiler's AST. This is powerful and completely unstable. Any change to the internal AST breaks every plugin, and so plugin-based crates are limited to nightly builds of the compiler. The `syntex` crate works around this by vendoring a copy of the parser and expanding macros in a `build.rs` script, which works on stable but has significant costs in build time and in ergonomics.

The second is `macro_rules!`, which is stable but cannot inspect the structure of a type definition in the way required for derive. Some derives have been implemented with elaborate patterns that wrap the entire type definition, but that approach is limited and unpleasant.

As a result, a large and growing share of the ecosystem is split. Users of stable Rust are forced to use `syntex`, with the associated cost, or avoid these libraries. Rust 1.0 promised stability without a stable story for one of its most important applications.

A complete redesign of the macro system, often called "macros 2.0", would solve this problem eventually, but it is a large effort touching hygiene, name resolution, and the AST. It will take considerable time. In the meantime, there is a narrow, well-understood use case, custom `#[derive]`, which can be served by a much simpler interface.

## Detailed design

### Overview

A new kind of crate, a *procedural macro crate*, is introduced. It is built with `crate-type = ["proc-macro"]` (in Cargo, `proc-macro = true` in the `[lib]` section). A crate of this type can export functions annotated with `#[proc_macro_derive(Name)]`. These functions are loaded by the compiler and called when `#[derive(Name)]` is encountered.

The functions have a single, simple signature:

```rust
extern crate proc_macro;
use proc_macro::TokenStream;

#[proc_macro_derive(Double)]
pub fn derive_double(input: TokenStream) -> TokenStream {
    // ...
}
```

The function receives the *token stream* of the item that carries the derive attribute, with the `#[derive]` attribute itself removed. It returns a token stream, which is parsed as zero or more items and added next to the original item. The original item is retained unchanged.

### The `proc_macro` crate

The compiler provides a new crate named `proc_macro`, containing:

- `TokenStream`: an opaque type representing a sequence of tokens. It implements `Display`, which renders the tokens as a string, and `FromStr`, which parses a string into tokens, returning a `LexError` on failure.
- `LexError`: an error type for the above.

This is deliberately minimal. The only supported way of examining or constructing a `TokenStream` is to convert it to or from a string. A macro author is expected to pass the string to a parser library such as `syn` (an external crate), process it, and generate output using string formatting or the `quote` crate.

Using strings as the interface is intentional. It has the following advantages:

1. The interface is trivial to stabilize. There is no AST type to commit to, and no token structure.
2. It is independent of the compiler's internal representation, so the parser can change at will.
3. It matches what the existing ecosystem is already doing through `syntex`, where macros operate on source text, so existing code can be ported easily.

Its disadvantage is that it loses span information, so error messages cannot point at the offending tokens in the input. This is accepted as a limitation of the first version.

### Hygiene

Generated code is not hygienic. Names in the output refer to whatever is in scope at the location of the derive. Macro authors are expected to use fully qualified paths, such as `::std::ops::Add`, to avoid collisions. This is the same approach taken by the current `#[derive]` implementations in the standard library, and by `macro_rules!` macros that use `$crate`.

### Execution model

The macro crate is compiled for the host, and loaded dynamically by the compiler, as plugins are today. Proc macro crates can depend on other crates, as well as on the standard library. The code runs inside the compiler's process with the privileges of the compiler. This is no different from `build.rs` scripts, which already can run arbitrary code.

Derive macros must be pure functions of their input. The compiler may cache or re-execute them, and nothing about the ordering of execution is guaranteed.

### Naming and imports

A derive macro is imported using `#[macro_use] extern crate foo;`, as with macro_rules macros. The name given in `#[proc_macro_derive(Name)]` is registered globally and can be used in `#[derive(Name)]`. Conflicts between two derive names are errors.

An optional list of helper attributes may be declared: `#[proc_macro_derive(Name, attributes(helper))]`. Those attributes are permitted on the fields or variants of the item without triggering the "unknown attribute" error. The macro receives them in the token stream and is responsible for interpreting them.

### Errors

A macro may report an error by panicking. The compiler catches the panic and reports it as an error at the location of the derive. The message is the panic message. Spans for the error point at the derive attribute. A richer diagnostic API is out of scope.

## How We Teach This

The Book gets a new section on custom derive, using a simple example, plus pointers to `syn` and `quote`. Because the interface is so small, documenting it takes little space. The more important documentation is in the external crates.

For macro authors, the message is: parse the input string with `syn`, generate output with `quote`, return `.parse().unwrap()`.

## Drawbacks

- It adds a public API to the compiler, however minimal, which has to be maintained indefinitely.
- The string-based interface is inelegant, and loses span information. Good error messages are hard to produce.
- It may delay or reduce motivation for a thorough macros 2.0 design, since the most urgent use case is already served.
- Plugin crates compiled to a dynamic library are tied to the compiler version in use, so their reliability depends on the toolchain being consistent.

## Alternatives

**Stabilize a subset of the existing plugin API.** The current API exposes too much of the compiler. Stabilizing any of it would constrain compiler development.

**Wait for macros 2.0.** This would leave the ecosystem in its current state for an unknown period. The cost of a modest interim step is low, and the experience gathered informs the later design.

**Provide a structured AST instead of strings.** This is the long-term direction, but designing a stable AST is a large effort. The string interface can be superseded by a token tree API in a backwards-compatible way, since `TokenStream` is opaque.

**Use a separate process.** Running macros in an external process would improve isolation but adds overhead and complexity, and offers little for this use case.

## Unresolved questions

- Should the helper attribute list be part of this RFC or a follow-up?
- Is panicking an acceptable error-reporting mechanism for the initial version, or should a `Result`-returning form be allowed?
- What should the crate be called, and should it be re-exported from `std`?
- Is there a path to attaching spans to tokens without breaking the string interface?
