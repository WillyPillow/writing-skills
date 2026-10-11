- Feature Name: `match_default_bindings`
- Start Date: 2017-02-06
- RFC PR: rust-lang/rfcs#2005
- Rust Issue: rust-lang/rust#42640

# Summary

Make pattern matching on references more ergonomic. Today, matching a value behind a reference forces the programmer to write `&` patterns and `ref` bindings so the patterns line up with the type being matched:

```rust
match *opt {
    Some(ref s) => println!("{}", s),
    None => {}
}

// or, equivalently
match opt {
    &Some(ref s) => println!("{}", s),
    &None => {}
}
```

With this RFC both of those forms keep working, and the following simpler form is also accepted:

```rust
match opt {
    Some(s) => println!("{}", s),
    None => {}
}
```

Here `opt` has type `&Option<String>` and `s` is bound as `&String`. The compiler dereferences the matched value automatically when a non-reference pattern meets a reference, and it tracks a *default binding mode* that decides whether plain identifier bindings bind by value, by shared reference, or by mutable reference.

# Motivation

Pattern matching is one of the parts of Rust people like most, but references make it noisy in a way that confuses newcomers and annoys experienced users. The rules are simple to state: a pattern has to have the same shape as the value. If the value is `&Option<T>`, the pattern has to start with `&`. If you want to avoid moving out of borrowed content, you must write `ref`. In practice these rules surface as compiler errors that are hard to read and fixes that look arbitrary.

Common examples:

- Iterating over a slice of tuples: `for &(ref name, ref age) in people.iter()`.
- Matching on `self` inside a method taking `&self`: `match *self { Foo::A(ref x) => ..., Foo::B(ref y) => ... }`.
- Matching on a field reached through a reference: `if let Some(ref v) = self.cache { ... }`.

In every case the programmer already knows what they want: look inside the borrowed value, and get references to its parts. The `*`, `&` and `ref` are bookkeeping that the compiler could work out on its own.

The errors are also a teaching problem. "cannot move out of borrowed content" is one of the first errors new Rust users meet, and the fix (add `ref`) introduces a keyword that is used almost nowhere else in the language. Users frequently report that `ref` is the part of patterns they understand least.

Other parts of Rust already insert dereferences and borrows for you: method call autoref and autoderef, and deref coercions at function arguments. Patterns are an odd exception. This RFC brings them closer to the rest of the language while keeping their behaviour predictable.

# Guide-level explanation

When you match a reference against a pattern that is not itself a reference pattern, Rust looks through the reference for you. Bindings inside the pattern then become references to the matched parts instead of trying to move them out.

```rust
let pair: &(String, u32) = &(String::from("a"), 1);
let (name, count) = pair;
// name: &String, count: &u32
```

The same applies to mutable references:

```rust
fn bump(v: &mut Option<u32>) {
    if let Some(n) = v {
        *n += 1; // n: &mut u32
    }
}
```

And it works through several layers:

```rust
let x: &&Option<u8> = &&Some(3);
match x {
    Some(n) => {} // n: &u8
    None => {}
}
```

You can still write the explicit forms. Code written today does not change meaning.

The mental model to teach is: *when you match through a reference, you get references out*. If you match through a `&mut`, you get `&mut` out, unless somewhere along the way you passed through a shared reference, in which case you get `&`.

# Reference-level explanation

## Default binding modes

Every point in a pattern is checked under a *default binding mode*, which is one of `move`, `ref`, or `ref mut`. Matching starts in `move` mode at the top of each pattern.

When the type checker compares a pattern against a type, it follows these rules:

1. If the pattern is a *non-reference pattern* and the type being matched is a reference `&T` or `&mut T`, the compiler auto-dereferences the value and continues matching the same pattern against `T`. The default binding mode is updated:
   - If the reference was `&T`, the mode becomes `ref`.
   - If the reference was `&mut T` and the current mode is `move`, the mode becomes `ref mut`.
   - If the reference was `&mut T` and the current mode is `ref`, it stays `ref`.
   - If the reference was `&mut T` and the current mode is `ref mut`, it stays `ref mut`.

   This step repeats until the type is no longer a reference.

2. Non-reference patterns are all patterns except bindings, wildcards (`_`), constants whose type is a reference, and reference patterns (`&p`, `&mut p`). In other words, struct, tuple, tuple-struct, enum-variant, slice, literal (of non-reference type) and range patterns.

3. When a binding pattern `x` without an explicit `ref`, `ref mut` or `mut` annotation is reached, it uses the current default binding mode. In `move` mode it binds by value as today. In `ref` mode it binds as if written `ref x`; in `ref mut` mode as if written `ref mut x`.

4. Explicit binding annotations interact with the default mode as follows: an explicit `ref` or `ref mut` is an error when the default mode is not `move`, to avoid confusing double-reference bindings. An explicit `mut x` is permitted in `move` mode and, for now, reset the binding to `move` mode in other modes. Because that behaviour is surprising, the compiler should lint on `mut` bindings under a non-`move` default mode, and we expect to revisit it.

5. Wildcards and bindings are not non-reference patterns, so they do not trigger auto-dereferencing. `let x = &5;` still binds `x: &i32`.

6. Explicit reference patterns `&p` and `&mut p` are matched as today and do not change the default binding mode. Mixing explicit `&` patterns inside a region that is already in `ref` mode is allowed but may require care; see Unresolved Questions.

## Examples of the algorithm

Matching `&(Some(a), b)`-typed values with the pattern `(Some(a), b)` against `&(Option<String>, u8)`:

- `(Some(a), b)` is a tuple pattern, type is `&(...)`: deref, mode = `ref`.
- `Some(a)` against `Option<String>`: not a reference, mode stays `ref`.
- `a` binding in `ref` mode: `a: &String`.
- `b` binding in `ref` mode: `b: &u8`.

Matching `Some(n)` against `&mut &Option<u8>`:

- deref `&mut`, mode = `ref mut`.
- deref `&`, mode = `ref`.
- `n: &u8`.

## Literals and constants

Literal patterns of non-reference type participate in auto-deref, so `match &5 { 5 => ... }` now works. String literal patterns have type `&str`, so they are reference-typed and do not trigger auto-deref; matching `&&str` against `"foo"` dereferences once to reach `&str`.

## Backwards compatibility

All programs accepted today keep their meaning. Every case where auto-dereferencing fires is one where a non-reference pattern meets a reference type, which is a type error today. No existing program exercises the new rules.

# Drawbacks

- The rules introduce implicit behaviour. A reader can no longer see from the pattern alone whether a binding is a value or a reference; they need to know the type of the scrutinee. In practice the IDE and the compiler can show this, and the same is already true of method calls.
- Users who rely on type errors to notice that they are matching against a reference lose that signal. If they meant to copy a value out and instead got a reference, the error moves to the use site.
- The interaction with explicit `mut` bindings is awkward. A user who writes `Some(mut x)` while matching through a reference gets a moved value, not a mutable reference, which differs from what nearby bindings receive.
- There are now two ways to write many patterns, and style guides will need to choose.

# Rationale and alternatives

## Do nothing

The status quo is coherent, but its costs are paid by every user on every day, and especially by beginners. The ergonomics initiative identified this as one of the most common sources of friction.

## Only remove `ref`

We could keep requiring `&` in patterns but infer `ref` for bindings. This removes half the noise but keeps the structural mismatch, which is the more confusing part.

## Infer binding mode from use

An alternative is to bind by value or by reference depending on how the binding is later used. This is more powerful but makes type checking of patterns depend on code far from the pattern, and complicates the borrow checker's view. The rule in this RFC is purely local: it depends only on the pattern and the scrutinee's type.

## Why per-pattern default modes

Tracking the mode as we descend gives a consistent answer for nested structures and handles mixed `&` and `&mut` layers soundly. Taking `ref` whenever any shared reference was crossed is required to prevent obtaining `&mut` access through a `&`.

# Prior art

Method call autoref and autoderef, deref coercions, and the `?` operator's conversions are all places where Rust inserts implicit operations driven by types. OCaml and Haskell do not have references in the same sense, so they offer little direct guidance. C++ structured bindings use `auto&` to request reference bindings explicitly, which is close to today's Rust.

# Unresolved questions

- Should explicit `mut` in a non-`move` default mode be an error rather than a lint, reserving the syntax for a future meaning?
- How should explicit `&` patterns behave when the default mode is already `ref`? One option is to make them reset the mode to `move`; another is to forbid them there.
- Should a lint suggest removing redundant `ref`, `&` and `*` from existing code once the feature is stable?
