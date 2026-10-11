- Feature Name: `type_changing_struct_update_syntax`
- Start Date: 2018-10-24
- RFC PR: [rust-lang/rfcs#2528](https://github.com/rust-lang/rfcs/pull/2528)
- Rust Issue: [rust-lang/rust#86555](https://github.com/rust-lang/rust/issues/86555)

# Summary
[summary]: #summary

Extend struct update syntax (a.k.a. functional record update (FRU)) to support instances of the *same* struct that have different types due to generic type or lifetime parameters. Fields of different types must be explicitly listed in the struct constructor, but fields of the same name and same type can be moved with struct update syntax.

This will make the following possible. In this example, `base` and `updated` are both instances of `Foo` but have different types because the generic parameter `T` is different. Struct update syntax is supported for `field2` because it has the same type `i32` in both `base` and `updated`:

```rust
struct Foo<T, U> {
    field1: T,
    field2: U,
}

let base: Foo<String, i32> = Foo {
    field1: "hello".to_owned(),
    field2: 1,
};

let updated: Foo<f64, i32> = Foo {
    field1: 3.14,
    ..base
};
```

# Motivation
[motivation]: #motivation

Today, struct update syntax requires that the base expression have exactly the same type as the struct being constructed. This is a restriction that is stricter than it needs to be. The compiler already knows, field by field, which values are being moved from the base and which are explicitly written, and it can check the types of each field independently.

The restriction is most painful with the "typestate" or "builder" pattern, in which a generic parameter changes as the value passes through a configuration step. Consider a builder with a type parameter tracking whether a required field has been supplied:

```rust
struct Config<Name> {
    name: Name,
    retries: u32,
    timeout_ms: u64,
    verbose: bool,
    // ... many more fields
}

impl Config<()> {
    fn with_name(self, name: String) -> Config<String> {
        Config {
            name,
            retries: self.retries,
            timeout_ms: self.timeout_ms,
            verbose: self.verbose,
            // ... every remaining field copied by hand
        }
    }
}
```

Every time a field is added, each method that changes the type parameter must be updated, and the compiler gives no help when a field is forgotten unless the field is of a mismatched type. With the proposed change this becomes:

```rust
impl Config<()> {
    fn with_name(self, name: String) -> Config<String> {
        Config { name, ..self }
    }
}
```

The same problem arises with lifetime parameters. A struct that borrows data for a lifetime `'a` cannot currently be rebuilt with a different lifetime using update syntax, even when none of the fields whose type mentions `'a` are taken from the base.

Another motivating case is changing a marker type such as `PhantomData<T>`, which is common in strongly typed identifiers and units of measure. Changing the marker should be a one-line operation.

Finally, users who hit this limitation find the error message confusing. The code looks like it should work, since the explicitly listed fields cover everything that differs. The error, "mismatched types", points at the base expression without explaining that it is the whole struct type being compared rather than the individual fields.

# Guide-level explanation
[guide-level-explanation]: #guide-level-explanation

You already know that struct update syntax lets you create a new value by taking some fields from another one:

```rust
let a = Point { x: 1, y: 2, z: 3 };
let b = Point { x: 10, ..a };
```

Here `b.x` is `10`, and `b.y` and `b.z` are taken from `a`.

With this RFC, the base value does not need to have exactly the same type as the value being constructed, as long as every field that is taken from the base has the same type in both. If a field's type differs between the two, you must write that field out explicitly.

```rust
struct Wrapper<T> {
    label: &'static str,
    count: usize,
    payload: T,
}

let strings = Wrapper { label: "a", count: 1, payload: String::from("x") };
let numbers = Wrapper { payload: 42u8, ..strings };
```

The type of `strings` is `Wrapper<String>` and that of `numbers` is `Wrapper<u8>`. The `payload` field has a different type, so it is given explicitly. `label` and `count` have the same type in both, so they are moved from `strings`.

If you forget to list a field whose type differs, the compiler tells you:

```rust
let broken = Wrapper { ..strings }; // error if the target type is Wrapper<u8>
```

```
error[E0308]: mismatched types
  --> src/main.rs:12:30
   |
   |     let broken: Wrapper<u8> = Wrapper { ..strings };
   |                                         ^^^^^^^^^ expected `u8`, found `String`
   |
   = note: field `payload` has a different type in the base expression; list it explicitly
```

All the ordinary rules of struct update syntax continue to apply. Fields that are moved from the base are moved (or copied, if they are `Copy`). Fields that are not moved remain in the base value, which may still be used partially. The base expression is evaluated once, after the explicitly listed fields.

# Reference-level explanation
[reference-level-explanation]: #reference-level-explanation

Let `S<P1..Pn>` be a struct with generic parameters, including lifetime parameters. Today, in `S { f1: e1, .., ..base }`, the type of `base` must be exactly the type being constructed.

Under this RFC, `base` must have type `S<Q1..Qn>` for some, possibly different, instantiation of the parameters. Type checking proceeds as follows:

1. The type of the constructed expression is determined as it is today from the expected type and the explicitly listed fields. Call it `S<P1..Pn>`.
2. The type of the base expression is inferred separately, as `S<Q1..Qn>`, where the `Qi` are fresh inference variables unified with the actual type of `base`.
3. For each field `f` of `S` that is not explicitly listed, the type of `f` in `S<P1..Pn>` must be equal to the type of `f` in `S<Q1..Qn>`. This produces equality constraints between the `Pi` and `Qi` that appear in the types of those fields.
4. Any parameter that appears only in explicitly listed fields is unconstrained by the base, and so is free to differ.

Because the constraints are per-field, a parameter that appears in both a listed and an unlisted field will be forced to be equal in both structs by the unlisted field.

The struct must be the same struct definition. This RFC does not allow updating from a different struct type, even one with identical fields.

## Interaction with `Drop`

Struct update syntax cannot move fields out of a type that implements `Drop`, and that restriction is unchanged. The rule applies to the base's type, not to the constructed type.

## Interaction with default type parameters and inference

Inference must be careful not to over-constrain. Where the base expression's type contains inference variables that appear only in listed fields of the result, they may remain unresolved, and the usual "type annotations needed" error is produced. Implementations should prefer to report the annotation request on the base expression.

## Lifetimes

Lifetime parameters are handled in the same way as type parameters: lifetimes appearing only in the types of listed fields are unconstrained, while those appearing in unlisted fields must satisfy the usual subtyping and outlives relations between the base's field type and the target's field type. Since region checking happens after type checking, the constraints are emitted as regular region obligations.

## Desugaring

The expression is equivalent to the following, where the temporary is introduced only conceptually:

```rust
{
    let tmp = base;
    S { f1: e1, .., g1: tmp.g1, g2: tmp.g2 }
}
```

The order of evaluation of explicitly listed fields relative to the base is unchanged.

# Drawbacks
[drawbacks]: #drawbacks

- Changes to the type checker are required, and the diagnostics around mismatched struct update expressions must be updated to avoid regressions in error quality.
- It may enable accidental type changes. A user who intended to preserve a type parameter might now silently change it because they listed a field they did not mean to. In practice the explicit listing makes this unlikely, and the new type must still be consistent with the annotation or use site.
- Programmers who learned that update syntax requires an identical type may be surprised that it has become more permissive, although no previously valid program changes meaning.

# Rationale and alternatives
[rationale-and-alternatives]: #rationale-and-alternatives

The main alternative is to do nothing and continue to require manual field copying. This works but is verbose, and it becomes a maintenance hazard as structs grow.

A second alternative is to provide a derive macro that generates conversion methods. This is a heavier solution that requires a procedural macro dependency and does not give the call-site flexibility of update syntax.

A third alternative is to allow updating between different struct types that share field names. This is more powerful but raises many more questions about privacy, field ordering and `Drop`, and is better handled in a separate proposal.

A fourth option, requiring users to opt in with a special marker like `..base as Foo<_, i32>`, would add syntax without adding any information the compiler cannot already derive.

# Prior art
[prior-art]: #prior-art

Functional record update exists in several languages. OCaml's `{ r with field = v }` allows the type of the record to change when the changed field is the only one mentioning a given type variable. Haskell's record update syntax similarly permits changing a type parameter if every field mentioning it is updated. This RFC adopts the same principle.

# Unresolved questions
[unresolved-questions]: #unresolved-questions

- Should the compiler suggest listing the mismatched field in the diagnostic automatically?
- How should the feature interact with potential future variance or const-generic changes? Const generic parameters should behave exactly as type parameters, and the implementation should treat them uniformly.

# Future possibilities
[future-possibilities]: #future-possibilities

The principle could later be extended to updates between distinct struct types with a shared layout, or to enum variants. A lint could also be added to warn when a type parameter changes silently.
