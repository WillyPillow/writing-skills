- Feature Name: `rustc_macros` (macros 1.1)
- Start Date: 2016-07-14
- RFC PR: rust-lang/rfcs#1681
- Rust Issue: (none yet)

# Summary

Extract a very small sliver of today's procedural macro system in the compiler — just enough to get basic features like custom `#[derive]` working — and give it an API that can eventually be stabilized. Ensure that these features will not pose a maintenance burden on the compiler, and do not try to provide enough features for the "perfect macro system" at the same time. This should be considered an incremental step towards an official "macros 2.0".

# Motivation

Some of the most important crates in the ecosystem depend on procedural macros, and those macros only work on nightly Rust. Serde and Diesel are the clearest examples: they generate trait implementations from type definitions, which is precisely what `#[derive]` is for. On stable Rust, users must fall back to a build script that runs `syntex`, a copy of the compiler's parser, over their source files, and then `include!` the result. This is slow to compile, gives poor error messages with spans pointing into generated files, and breaks whenever the language grows new syntax that `syntex` has not yet learned.

The existing compiler plugin interface is not a candidate for stabilization. It exposes `libsyntax` directly: the AST types, the parser, the token types, the expansion context. Those are internal compiler data structures that change constantly. Stabilizing them would freeze compiler internals.

A full redesign of procedural macros — macros 2.0 — is underway, with hygiene, a token-based interface, and proper integration with name resolution. It will take time to get right. Meanwhile, the ecosystem's dependence on nightly for custom derive is one of the largest barriers to adopting stable Rust.

The observation behind this RFC is that custom derive needs almost nothing from the compiler. It needs to receive the item it is attached to, and to emit additional items. If the interface between the compiler and the macro is a string of Rust source code, the compiler's internals are not exposed at all.

# Detailed design

## A new crate type

A new crate type, `proc-macro`, is introduced. In Cargo:

```toml
[lib]
proc-macro = true
```

A `proc-macro` crate is compiled as a dynamic library that the compiler loads at compile time. It may export only procedural macro definitions; it may not export ordinary functions, types, or traits for use at runtime. This restriction keeps the separation between "code that runs in the compiler" and "code that runs in the program" clear, and simplifies cross-compilation, since the crate always targets the host.

## The `proc_macro` crate

A new crate, `proc_macro`, is shipped with the compiler. Its initial public API is intentionally tiny:

```rust
pub struct TokenStream { /* opaque */ }

impl FromStr for TokenStream {
    type Err = LexError;
    fn from_str(s: &str) -> Result<TokenStream, LexError>;
}

impl Display for TokenStream { /* ... */ }

pub struct LexError { /* opaque */ }
```

`TokenStream` is an opaque type. The only stable operations are converting it to a string and parsing a string into it. Its internal representation is free to change. In the future, the macros 2.0 work will add a structured token-tree API to the same type, so code written against this RFC will continue to compile and can migrate gradually.

## Defining a custom derive

A custom derive is a function annotated with `#[proc_macro_derive(Name)]`:

```rust
extern crate proc_macro;
use proc_macro::TokenStream;

#[proc_macro_derive(Serialize)]
pub fn derive_serialize(input: TokenStream) -> TokenStream {
    let source = input.to_string();
    let ast = my_parser::parse_item(&source);
    let expanded = generate_impl(&ast);
    expanded.parse().unwrap()
}
```

The function receives the item to which `#[derive(Serialize)]` was attached, with that derive attribute removed. It returns a token stream that replaces the input. In the initial design, the macro is expected to return the original item together with any new items (typically one or more `impl` blocks). This allows the macro to strip helper attributes it uses for configuration, such as `#[serde(rename = "...")]`, which would otherwise be rejected by the compiler as unknown.

## Using a custom derive

A consumer crate imports the macro crate and uses the derive as if it were built in:

```rust
#[macro_use]
extern crate serde_derive;

#[derive(Serialize)]
struct Point { x: i32, y: i32 }
```

Name resolution for derives is simple: all derives exported by `#[macro_use]` crates are placed in a single global namespace for the crate, and a conflict between two derives of the same name is an error.

## Expansion order

When the compiler encounters `#[derive(A, B, C)]` where some of the derives are built in and some are custom, it expands custom derives first, in the order listed, and then the built-in derives. Each custom derive sees the output of the previous one.

## Errors

If a custom derive panics, the compiler reports an error at the `#[derive]` attribute, including the panic message. This is crude but sufficient for the initial version. If the returned string fails to parse as Rust items, the compiler reports a parse error with a note that it originated in a custom derive.

## Spans and hygiene

All tokens produced by parsing a string are given the span of the `#[derive]` attribute. There is no hygiene: identifiers in the output are resolved as if written at the derive site. These limitations are accepted in exchange for a minimal stable surface. Both are explicitly in scope for macros 2.0.

## Stability

The `proc-macro` crate type, `#[proc_macro_derive]`, and the string-based `TokenStream` API are proposed for stabilization together. Everything else — function-like procedural macros, attribute procedural macros, and the structured token API — remains unstable.

# Drawbacks

- **String-based interfaces are inefficient.** The compiler pretty-prints the item to a string, the macro reparses it with its own parser, generates source, and the compiler parses the result. For large codebases this costs measurable compile time. In practice this is far cheaper than the current `syntex` approach, which reparses whole files.
- **Duplicated parsers.** Every macro crate will bring its own Rust parser (likely a shared ecosystem crate such as `syn`). These parsers must track language changes. However, they track changes on their own schedule and are versioned, which is far better than tracking unstable compiler internals.
- **Poor spans.** Error messages from generated code point at the derive attribute rather than the field or expression responsible. This is a known regression relative to what a full design could offer.
- **Locking in the shape of `TokenStream`.** Even an opaque type is a commitment. We believe a token stream is the right abstraction for macros 2.0, so this is a commitment we are comfortable making.

# Alternatives

**Wait for macros 2.0.** This is the cleanest outcome but leaves the ecosystem on nightly for an unknown period. The cost of waiting is high, and the API proposed here is a strict subset of what macros 2.0 plans to offer.

**Stabilize `syntex` as the official approach.** Build-script code generation works today, but its compile-time cost and poor ergonomics are the problems we are trying to solve.

**Expose a stable AST.** A stable AST would be more convenient for macro authors but would constrain the evolution of the language and compiler. Token streams are a much smaller commitment.

# Unresolved questions

- Should the macro return only new items rather than the full replacement? Returning the original item allows attribute stripping but also allows the macro to change the item arbitrarily, which may be surprising.
- How should helper attributes be declared, so that the compiler can recognize them without requiring the macro to remove them?
- How do `proc-macro` crates interact with cross-compilation in Cargo, and how are their dependencies built?
