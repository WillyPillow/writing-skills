- Feature Name: `type_changing_struct_update_syntax`
- Start Date: 2018-08-22
- RFC PR: [rust-lang/rfcs#2528](https://github.com/rust-lang/rfcs/pull/2528)
- Rust Issue: [rust-lang/rust#86555](https://github.com/rust-lang/rust/issues/86555)

# Summary

Extend struct update syntax (also called functional record update, or FRU) to allow the base expression to be an instance of the *same* struct with *different* generic type or lifetime arguments. Fields whose types differ between the base and the result must be listed explicitly in the constructor. Fields whose types are the same may be moved from the base using `..base`.

```rust
struct Foo<T, U> {
    field1: T,
    field2: U,
}

let base: Foo<String, i32> = Foo {
    field1: String::from("hello"),
    field2: 1234,
};

let updated: Foo<f64, i32> = Foo {
    field1: 3.14,
    ..base
};
```

Here `base` and `updated` are both `Foo`, but `base` is `Foo<String, i32>` and `updated` is `Foo<f64, i32>`. The update syntax works for `field2` because its type is `i32` in both.

# Motivation

Today, the expression `S { a: x, ..base }` requires `base` to have exactly the type of the struct being constructed. For a non-generic struct this is unremarkable. For a generic struct it forbids a pattern that comes up frequently: changing one type parameter while keeping every other field.

## Typestate builders

The most common case is the typestate builder pattern. A builder carries a marker type parameter that records which required fields have been set, so that `build()` is only callable once the builder is complete:

```rust
pub struct Missing;
pub struct Present<T>(T);

pub struct RequestBuilder<Url> {
    url: Url,
    method: Method,
    headers: HeaderMap,
    timeout: Option<Duration>,
    body: Option<Body>,
}

impl RequestBuilder<Missing> {
    pub fn url(self, url: Url) -> RequestBuilder<Present<Url>> {
        RequestBuilder {
            url: Present(url),
            method: self.method,
            headers: self.headers,
            timeout: self.timeout,
            body: self.body,
        }
    }
}
```

Every transition method has to list every field. Adding a field to the builder means updating each transition. Forgetting one is a compile error, so it is not a correctness hazard, but it is pure noise, and it grows with the product of fields and states. With this RFC the body becomes:

```rust
RequestBuilder { url: Present(url), ..self }
```

## Configuration with a generic component

Structs that hold a pluggable component (an allocator, a hasher, a logger, a clock) have the same shape. Swapping the component should be a one-field change:

```rust
impl<C> Scheduler<C> {
    pub fn with_clock<C2>(self, clock: C2) -> Scheduler<C2> {
        Scheduler { clock, ..self }
    }
}
```

## Lifetimes

The same restriction applies to lifetime parameters. Converting a struct borrowing from one buffer into one borrowing from another, or shortening a lifetime to fit an API, currently requires spelling out every field even though only one reference changes.

## Why not a macro

Crates such as `derive_builder` generate the boilerplate, but they do so by fixing a particular builder design. Hand-written typestate code and generic configuration structs gain nothing from them. The underlying restriction is in the language, and the natural fix is in the language.

# Guide-level explanation

Struct update syntax lets you build a new struct value by taking some fields from an existing value:

```rust
let p2 = Point { x: 10, ..p1 };
```

The fields you write explicitly are used as given. Every other field is moved (or copied) out of the base expression `p1`.

With this RFC, when the struct is generic, the base expression may have different generic arguments from the value you are constructing, as long as every field you take from the base has the same type in both. Fields whose types change must be written out.

```rust
struct Pair<A, B> { a: A, b: B, label: &'static str }

let p: Pair<u8, char> = Pair { a: 1, b: 'x', label: "p" };
let q: Pair<String, char> = Pair { a: "one".into(), ..p };   // ok
let r: Pair<String, u32> = Pair { a: "one".into(), ..p };    // error
```

The last line is an error because `b` has type `char` in `p` but would need to be `u32` in `r`, and `b` is not listed explicitly. The compiler reports which field has a mismatched type and suggests writing it out.

# Reference-level explanation

## Type checking

Given an expression

```rust
S { f1: e1, ..., fn: en, ..base }
```

where `S` is a struct with generic parameters `P`, type checking proceeds as follows.

1. The type of the whole expression is `S<P'>` for some arguments `P'`, determined by the expected type and the explicitly given fields as usual.
2. The type of `base` must be `S<P''>` for some arguments `P''`. The struct *constructor* must match: `base` cannot be a different struct, even one with identical fields.
3. For each field `g` of `S` not among `f1..fn`, the declared type of `g` instantiated with `P''` must be equal to the declared type of `g` instantiated with `P'`.

Previously, step 2 required `P'' = P'`. Step 3 replaces that requirement with a per-field check.

Generic parameters that appear only in explicitly listed fields are therefore unconstrained by `base`. Parameters that appear in any field taken from `base` are constrained by it in the obvious way.

## Inference

The current implementation unifies the type of `base` with the expected type before examining fields. Under this RFC, the type of `base` is inferred independently and then each remaining field type is unified. This can change inference in programs that currently compile, because `base` no longer supplies the type of the whole expression. For example:

```rust
let x = Foo { field1: Default::default(), ..base };
```

today infers `field1`'s type from `base`. After this change, `field1`'s type parameter is not constrained by `base` and the expression may become ambiguous.

To avoid breaking such code, the type checker will first attempt the old rule (unify `base` with the result type). Only if that would produce a type error does it fall back to the per-field rule. In practice this means existing programs keep their inferred types, and new programs gain the additional flexibility.

## Phantom data and private fields

`PhantomData<T>` fields are ordinary fields. If a struct has `marker: PhantomData<T>` and `T` changes, `marker` must be listed explicitly, typically as `marker: PhantomData`. This is consistent and occasionally annoying; a follow-up could special-case zero-sized fields whose type mentions only changed parameters, but this RFC does not.

Struct update syntax already requires that every field taken from `base` be visible at the use site. This is unchanged.

## Lifetimes

Lifetime parameters are handled the same way as type parameters. A field whose type mentions a lifetime that differs between base and result must be listed explicitly. Subtyping still applies when a lifetime can be shortened by variance, so many cases already work today; this RFC extends support to cases variance does not cover.

## Drop

Moving fields out of `base` via update syntax is already a partial move. The restriction that `base` must not implement `Drop` when fields are moved out is unchanged.

# Drawbacks

- The inference fallback adds complexity to the type checker for a feature that is purely convenience.
- Error messages for update syntax become more involved, since the compiler must explain which fields caused a mismatch rather than reporting a single type mismatch on `base`.
- Some users may find it surprising that `..base` can produce a value of a different type than `base`.

# Rationale and alternatives

**Do nothing.** Users continue to list every field. This is workable but scales poorly, and the problem is common enough to justify a language change.

**Allow any base struct with compatible field names.** This would let `..base` copy fields from a different struct type. It turns field names into a structural interface, which Rust deliberately avoids. Restricting to the same struct constructor keeps update syntax nominal.

**Require explicit type annotation.** One could require the result type to be written out whenever generics change. The per-field rule already prevents ambiguity in the cases that matter, so the annotation is unnecessary.

# Prior art

OCaml and Haskell record update syntax allow updating a field to a different type when the record is polymorphic in that field's type, using essentially the same rule: fields not mentioned must have types that do not depend on the changed parameters. GHC's record update has done this for decades.

# Unresolved questions

- Should the inference fallback be removed in a future edition, making the per-field rule the only rule?
- Should zero-sized `PhantomData` fields be filled in automatically when their parameter changes?

# Future possibilities

Combining this feature with default field values would allow builders that are almost entirely declarative. Allowing `..` with no base expression, filling unspecified fields from defaults, is a separate proposal.
