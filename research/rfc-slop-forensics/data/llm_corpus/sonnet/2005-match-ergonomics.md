# RFC: Pattern Binding Modes

- Feature Name: `pattern_binding_modes`
- Start Date: 2016-08-12
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

Improve the ergonomics of pattern matching on references. Today, matching on a reference requires a careful dance with `&` and `ref` patterns:

```rust
let x: &Option<String> = &Some("hello".to_string());

match *x {
    Some(ref s) => println!("{}", s),
    None => {}
}

// or

match x {
    &Some(ref s) => println!("{}", s),
    &None => {}
}
```

After this RFC, the above forms still work, but we also allow a simpler form:

```rust
match x {
    Some(s) => println!("{}", s),
    None => {}
}
```

This is accomplished through automatic dereferencing of the scrutinee and the introduction of *default binding modes*.

## Motivation

Rust's pattern matching is one of its most loved features, but matching through references is a persistent source of friction, especially for newcomers. Consider a function that inspects an optional value held behind a reference:

```rust
fn describe(opt: &Option<String>) -> &str {
    match opt {
        &Some(ref s) => s.as_str(),
        &None => "nothing",
    }
}
```

The programmer already wrote `&` in the type of the argument. They are matching on something that is plainly a reference. Yet the compiler demands that they repeat the reference in every arm, and then also add `ref` to the binding so that the string is not moved out of the borrowed data. Two distinct annotations, both of which communicate information the compiler could trivially infer, are required to get a program that does what the programmer meant.

The problems are as follows.

1. **The annotations are redundant.** In nearly every case there is exactly one thing the programmer could mean. If the scrutinee is a `&Option<String>` and the pattern is `Some(s)`, the only sensible reading is "look through the reference and borrow the string".
2. **The error messages are unhelpful.** Writing `Some(s)` against a `&Option<String>` yields a type mismatch error. The learner must then discover `&` patterns, and afterwards discover that `&Some(s)` fails with "cannot move out of borrowed content", and finally discover `ref`. This sequence is a rite of passage that teaches nothing useful about ownership.
3. **The syntax is noisy in nested code.** Deeply nested structures behind references need an `&` at every level of the pattern and a `ref` at each leaf. Refactoring a function from taking `Option<T>` to `&Option<T>` requires touching every pattern.
4. **`ref` is confusing.** A `ref` in a pattern is written on the left of an expression that creates a reference, which runs against the intuition that `&` on the left of a pattern *removes* a reference. People regularly mix up `&x` and `ref x`.

We want the common case to just work, while keeping the existing, explicit forms valid for code that wants them.

## Guide-level explanation

When you match on a reference, you can write patterns as though you were matching on the value it points to. The bindings in the pattern then become references.

```rust
let pair: &(String, u32) = &("age".to_string(), 30);

let (name, n) = pair;
// name: &String, n: &u32
```

You do not need to write `&(ref name, ref n)`. The compiler sees a non-reference pattern, `(name, n)`, meeting a reference type, `&(String, u32)`. It automatically dereferences the value, and remembers that it did so by switching to a *reference binding mode* for everything inside. In that mode, each identifier binds by reference rather than by move.

If the reference was mutable, the bindings become mutable references:

```rust
fn bump(entry: &mut (String, u32)) {
    let (_, count) = entry;
    *count += 1; // count: &mut u32
}
```

This extends through structures of arbitrary depth:

```rust
enum Tree {
    Leaf(i32),
    Node(Box<Tree>, Box<Tree>),
}

fn sum(t: &Tree) -> i32 {
    match t {
        Tree::Leaf(n) => *n,
        Tree::Node(l, r) => sum(l) + sum(r),
    }
}
```

Here `n` has type `&i32`, and `l` and `r` have type `&Box<Tree>`, which deref-coerce when passed to `sum`.

You can still use explicit forms. An explicit `ref` or `ref mut` binding is always allowed outside of a default reference mode, and `&` patterns still destructure references exactly as before. If you write a pattern that consists of a plain `&` against a reference, nothing about its meaning has changed.

### Moving back out

Sometimes you want to copy a value out rather than borrow it. For `Copy` types you can dereference the binding:

```rust
let Some(n) = &Some(5) else { return };
let n: i32 = *n;
```

If you wish to override the default, an explicit `&` pattern resets the binding mode to *move*:

```rust
let &(a, b) = &(1u32, 2u32); // a: u32, b: u32
```

For non-`Copy` data this will produce the usual "cannot move out of borrowed content" error, which is the correct result: the pattern asked for ownership and the data cannot provide it.

## Reference-level explanation

### Binding modes

Every identifier pattern is associated with a *binding mode*. Until now the mode was determined solely by the presence or absence of `ref` or `ref mut` keywords on that identifier. We define three binding modes:

- `move`, the default at the top of a pattern;
- `ref`;
- `ref mut`.

During type checking of a pattern, the checker carries a *current default binding mode*, which begins as `move`.

### Auto-dereferencing rule

When the checker meets a *non-reference pattern* while the expected type is a reference type `&T` or `&mut T`, it performs the following steps:

1. Replace the expected type with the pointee type `T`, recording an implicit dereference adjustment on the pattern.
2. Update the default binding mode: if the reference is `&T`, the mode becomes `ref`; if the reference is `&mut T` and the current mode is `move` or `ref mut`, the mode becomes `ref mut`; if the current mode is already `ref`, it stays `ref`.
3. Repeat, since `T` may itself be a reference.

A *non-reference pattern* is any pattern that is not a binding, a wildcard `_`, a constant of reference type, or an explicit reference pattern `&p`. This covers struct, tuple, tuple struct, slice and literal patterns.

### Identifier patterns

An identifier pattern with no explicit annotation binds according to the current default binding mode. If it carries an explicit `ref` or `ref mut` while the default mode is not `move`, that is an error, as the combination is ambiguous and almost certainly a mistake. An identifier with `mut` while the default mode is not `move` is likewise rejected, because a `mut` binding cannot also be a reference binding.

### Reference patterns

A reference pattern `&p` always matches a value of reference type, regardless of default binding mode, and it resets the default binding mode to `move` for the sub-pattern `p`.

### Lowering

Implicit dereferences are inserted during type checking and recorded in the HIR so that later passes (borrow checking, MIR construction) see fully explicit patterns. This means no changes are required in the borrow checker beyond handling the adjusted patterns, and the generated code is identical to the code produced by the equivalent hand-written pattern.

### Examples

| Pattern | Scrutinee type | Result |
|---|---|---|
| `Some(x)` | `&Option<T>` | `x: &T` |
| `Some(x)` | `&mut Option<T>` | `x: &mut T` |
| `Some(x)` | `&&Option<T>` | `x: &T` |
| `&Some(x)` | `&Option<T>` | `x: T` (move) |
| `(a, ref b)` | `&(A, B)` | error, `ref` in non-move mode |

## Drawbacks

**Less explicit.** A reader can no longer tell from the pattern alone whether a binding is a reference. The type of the scrutinee is now required to determine this. We believe that the type is almost always plainly visible near the match, and editors and `rustdoc`-style tooling can surface it.

**Interaction with shadowed constants.** A pattern identifier that happens to resolve to a constant must be treated as a constant pattern, not a binding. The auto-dereference rule must apply to such constants as appropriate; the existing name resolution rules already settle this before type checking.

**Teaching.** Two ways to write the same match now exist. We expect the new form to become idiomatic and the older form to remain primarily in legacy code, but guides will have to explain both.

**Surprising mixing.** Because `&` resets the binding mode, a pattern that mixes explicit `&` with auto-dereferencing may behave in ways that some users find unintuitive. Lints may eventually help.

## Rationale and alternatives

The minimal alternative is to do nothing. Experienced users learn the idiom, and the language remains explicit. However, the cost of the idiom falls most heavily on newcomers, and it adds noise forever.

Another alternative is to implement only top-level auto-dereference, so that `match x { Some(s) => ... }` works but nested references are still explicit. This is simpler but creates a cliff: patterns work until one level too deep. The default binding mode generalizes cleanly.

A third option is to introduce a new sigil for "borrowing match". We reject this as it adds a concept without removing one.

We also considered making the reference mode sticky through explicit `&` patterns instead of resetting. Resetting is easier to specify and keeps `&` meaning what it has always meant: destructure a reference and bind the interior by value.

## Unresolved questions

- Should a future lint warn when explicit `ref` bindings could be elided?
- Should `mut` identifiers in a non-move mode be permitted to mean "mutable local holding a reference"?
- How should diagnostics describe the inferred binding mode to users who hit a move error caused by an explicit `&`?
