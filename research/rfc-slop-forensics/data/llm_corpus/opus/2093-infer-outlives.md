- Feature Name: `infer_outlives`
- Start Date: 2017-08-02
- RFC PR: [rust-lang/rfcs#2093](https://github.com/rust-lang/rfcs/pull/2093)
- Rust Issue: [rust-lang/rust#44493](https://github.com/rust-lang/rust/issues/44493)

# Summary

Remove the need for explicit `T: 'x` annotations on structs and enums. The compiler will infer them from the types of the fields. In short, if a struct contains a reference to `T` with lifetime `'x`, directly or indirectly, the compiler infers `T: 'x` as a requirement of the struct. Explicit annotations remain allowed, both because they control trait object lifetime defaults and for backwards compatibility.

```rust
// Today
struct Ref<'a, T: 'a> {
    field: &'a T,
}

// With this RFC
struct Ref<'a, T> {
    field: &'a T,
}
```

# Motivation

Writing a struct that holds a reference to a generic type requires an outlives annotation:

```rust
struct Iter<'a, T: 'a> {
    slice: &'a [T],
    pos: usize,
}
```

The `T: 'a` bound is required because the type `&'a [T]` is only well-formed if `T` lives at least as long as `'a`. The compiler already knows this. Rejecting the struct without the annotation does not catch a bug; it only makes the user write down something the compiler could have worked out.

These annotations are among the more confusing parts of learning Rust:

- They look like they add a constraint, but they actually restate one that is already implied.
- The error message when they are missing ("the parameter type `T` may not live long enough") is hard to connect to a fix, especially for beginners.
- They spread. A struct containing an `Iter<'a, T>` also needs `T: 'a`, and so does a struct containing that, and so on.

In a survey of crates on crates.io, a large fraction of structs with lifetime parameters carry at least one `T: 'a` bound, and almost none of them have meaning beyond "the field types require this."

Functions already infer these bounds. RFC 1214 established that a function's signature implies the well-formedness of its argument types:

```rust
fn first<'a, T>(x: &'a [T]) -> &'a T { &x[0] }   // no T: 'a needed
```

Structs are the odd one out. Making them behave the same way removes an inconsistency and a common source of friction.

# Guide-level explanation

When you define a struct or enum with a lifetime parameter and a type parameter, you no longer have to write `T: 'a` if the requirement follows from the fields:

```rust
struct Wrapper<'a, T> {
    inner: &'a T,          // implies T: 'a
}

struct Pair<'a, 'b, T> {
    first: &'a T,          // implies T: 'a
    second: &'b mut T,     // implies T: 'b
}

struct Nested<'a, T> {
    w: Wrapper<'a, T>,     // Wrapper requires T: 'a, so Nested does too
}
```

The inferred bounds behave exactly as if you had written them. Users of the struct see them in the same way: `Wrapper<'a, T>` is only a valid type when `T: 'a` holds, and code that names it gets that fact for free.

You can still write the bound explicitly. Doing so is never an error, and there is one case where it matters: the default lifetime for trait objects. In

```rust
struct Holder<'a, T: 'a + ?Sized> {
    r: &'a T,
}
```

the explicit `T: 'a` means that `Holder<'a, dyn Trait>` defaults to `Holder<'a, dyn Trait + 'a>`. Without an explicit bound, the default would be `dyn Trait + 'static`. Inferred bounds do not affect trait object defaults, so that existing code keeps its meaning.

# Reference-level explanation

## What is inferred

For each struct, enum, or union `S` with generic parameters, the compiler computes a set of *inferred outlives predicates* of the form `T: 'a` or `'b: 'a`, where `T` and `'b`, `'a` are parameters of `S`. These are computed as follows:

1. For each field type, compute the outlives requirements needed for that type to be well-formed, per the rules of RFC 1214.
   - `&'a T` and `&'a mut T` require `T: 'a`.
   - A path type `Other<'x, U>` requires whatever `Other`'s own predicates (explicit and inferred) require, after substitution.
   - Projections like `<T as Trait>::Assoc` contribute nothing directly, as the components rules in RFC 1214 specify.
2. Keep only those requirements that relate the generic parameters of `S` to each other. Requirements involving `'static` are kept. Requirements on concrete types are discarded, since they are either always true or a separate error.
3. Repeat for all types in the crate until a fixed point is reached, since a struct's inferred bounds can depend on other structs' inferred bounds, including recursively.

The fixed point always exists, since the set of possible predicates over a finite set of parameters is finite and the process only adds predicates.

## How inferred predicates are used

Inferred predicates are added to the struct's predicate set. They are:

- *assumed* inside the struct's own definition and within impls whose self type is the struct, and
- *required* wherever the struct type is named and must be well-formed.

In other words, they act exactly like explicit where-clauses for type checking.

## Cross-crate behavior

Inferred predicates are recorded in crate metadata. Downstream crates see them as part of the type's predicates. Changing a field in a way that changes the inferred predicates is therefore a potentially breaking change, just as changing an explicit bound would be. This is generally visible only for public fields of public types, or when the type's generic parameters are used in new ways.

## Trait object lifetime defaults

Defaults for `dyn Trait` lifetimes continue to be computed from *explicit* bounds only. Inferred predicates are not consulted. This guarantees that this RFC does not change the meaning of any existing program.

## Lint

An allow-by-default lint, `explicit_outlives_requirements`, is added. It reports explicit outlives bounds that would be inferred anyway, so that projects that want to remove them can find them automatically. `rustfix` can apply the suggestion.

# Drawbacks

- The requirements of a struct become less visible in its source. A reader who wants to know whether `T: 'a` holds must look at the fields rather than the header. Rustdoc will show the inferred bounds to address this.
- It makes it slightly easier to change a type's requirements without noticing, since editing a private field can alter the public predicates.

# Rationale and alternatives

**Keep the status quo.** The annotation conveys no new information, and its absence is a recurring stumbling block. Keeping it buys little.

**Infer bounds for all where-clauses, including trait bounds.** Inferring `T: Clone` from field usage would be a much larger change with real semver concerns. Outlives bounds are special because they follow mechanically from type structure, and nobody writes them for documentation purposes.

**Infer only for direct references.** Simpler to explain, but it would leave the "spreading" problem in place for nested structs, which is where the annotations are most irritating.

# Prior art

Rust functions already infer outlives requirements from argument types (implied bounds, RFC 1214). This RFC extends the same idea to type definitions.

# Unresolved questions

- Whether `'static` requirements should be inferred or require annotation.
- The best way for rustdoc to display inferred predicates.
