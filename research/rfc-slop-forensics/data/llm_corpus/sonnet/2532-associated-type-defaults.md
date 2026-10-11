# RFC 2532: associated_type_defaults

- Feature Name: `associated_type_defaults`
- Start Date: 2018-08-22
- RFC PR: rust-lang/rfcs#2532
- Rust Issue: rust-lang/rust#29661

## Summary

Resolve the design of associated type defaults, first introduced in RFC 192, such that provided methods and other items may not assume type defaults. This applies equally to `default` with respect to specialization. Finally, `dyn Trait` will assume provided defaults and allow those to be elided.

## Motivation

RFC 192 allowed traits to give a default for an associated type:

```rust
trait Iterable {
    type Item = u8;
    type Iter: Iterator<Item = Self::Item>;
    fn iter(&self) -> Self::Iter;
}
```

An implementor may omit `Item`, in which case it takes the default `u8`. The feature was accepted in 2014 and partially implemented, but was never stabilized. The reason is that the original design left a soundness hole open and several questions unanswered.

The central problem is what the type checker may assume about `Self::Item` inside the trait. Consider:

```rust
trait Foo {
    type Bar = u8;

    fn make(&self) -> Self::Bar {
        0u8 // is this valid?
    }
}
```

If the default were assumed within the provided method, then `make` would type check on the grounds that `Self::Bar` is `u8`. But an implementor is free to override the default:

```rust
struct S;
impl Foo for S {
    type Bar = String;
}
```

Now `S` inherits `make`, whose body returns `0u8` where a `String` is expected. The program is ill-typed after the fact. Because the check happened in the trait and not at the impl, no error is reported. This is a type-soundness bug.

The simplest repair is to say that, inside the trait definition, `Self::Bar` is opaque: it is exactly as abstract as an associated type with no default. The default then matters only when an impl omits the item. This RFC adopts that rule and works through its consequences.

A related motivation is the ergonomics of `dyn Trait`. Trait objects must name every associated type, as in `Box<dyn Iterator<Item = u32>>`. When a trait provides a default, requiring users to repeat it is noise. This RFC allows the default to be used when the object type omits the associated type.

## Guide-level explanation

An associated type in a trait may be given a default:

```rust
trait Container {
    type Elem = u8;
    fn first(&self) -> Option<Self::Elem>;
}
```

An impl that does not mention `Elem` gets `u8`:

```rust
struct Bytes(Vec<u8>);

impl Container for Bytes {
    fn first(&self) -> Option<u8> {
        self.0.first().copied()
    }
}
```

An impl may also provide its own type, in which case the default is ignored:

```rust
struct Words(Vec<u32>);

impl Container for Words {
    type Elem = u32;
    fn first(&self) -> Option<u32> {
        self.0.first().copied()
    }
}
```

The default is a convenience for implementors. It is not a promise to the code inside the trait. In particular, a provided method cannot rely on it:

```rust
trait Container {
    type Elem = u8;

    fn zero(&self) -> Self::Elem {
        0u8 // ERROR: expected `Self::Elem`, found `u8`
    }
}
```

The error is reported at the trait definition, not at some distant impl. To write such a method, the author must add a bound, for example `where Self::Elem: From<u8>`, or leave the method required.

### Trait objects

When a trait has defaults for all of its associated types, the object type does not need to name them:

```rust
trait Container {
    type Elem = u8;
    fn first(&self) -> Option<Self::Elem>;
}

fn show(c: &dyn Container) { /* c: &dyn Container<Elem = u8> */ }
```

Here `dyn Container` means `dyn Container<Elem = u8>`. If the user wants a different element type, they write it out: `dyn Container<Elem = u32>`.

Observe that this only works because object types are fixed at the point they are written. The default is read from the trait definition, so adding a default to an existing trait is a way to make bare `dyn Trait` meaningful where it previously was an error.

## Reference-level explanation

### Typing rules inside the trait

Within the trait definition, including provided method bodies, default method signatures, `where` clauses and other associated items, the projection `<Self as Trait>::Assoc` is treated as an opaque type, regardless of whether a default is present. The type checker may use only bounds that are declared on the associated type, such as `type Assoc: Display`.

The default value itself is type checked in isolation. It may refer to other associated types of the same trait and to the trait's generic parameters, and it must satisfy any bounds declared on the associated type, assuming that `Self: Trait`. That is, given

```rust
trait Foo {
    type Bar: Clone = Vec<u8>;
}
```

the compiler verifies that `Vec<u8>: Clone` holds. If the default depends on a parameter, it verifies the bound for all instantiations permitted by the trait's where clauses.

### Impls

If an impl omits an associated type that has a default, the impl behaves as if it had written `type Assoc = <default>;`, with the default substituted using the impl's own `Self` type and generic arguments. The bounds on the associated type are re-checked at the impl, since the substituted type may satisfy them in the abstract but not once `Self` is fixed.

### Interaction with specialization

Specialization (RFC 1210) introduced `default` items in impls. A `default type Assoc = ...;` in an impl is a default that a more specialized impl may override. The same hazard exists there: a `default fn` that assumed `Assoc = T` would break when specialized.

This RFC applies the same rule. Within a `default fn` or any other item in the same impl, the associated type is opaque if it is marked `default`. The type checker may rely on it only where it is not marked `default`. This makes the treatment of trait-level defaults and impl-level `default` items uniform.

### Trait objects

For an object type `dyn Trait<Args>`, for each associated type `A` of `Trait` and its supertraits that lacks a binding in the written type, the compiler consults the trait definition. If a default exists, it is substituted. If no default exists, the type is ill-formed as before.

The defaults are applied after resolving `Self` as the erased type. A default that mentions `Self` is therefore not usable in this way, since `Self` is not known; such a default does not provide an elision, and an explicit binding is still required. This restriction avoids defining what `Self` means in a type with no concrete `Self`.

### Object safety

Defaults do not alter object safety. A trait that is not object safe remains so.

## Drawbacks

The opacity rule means that a default is somewhat less useful than users might intuitively expect. A programmer who writes `type Bar = u8;` and then writes a provided method returning `0u8` will receive an error and might find it surprising. The diagnostic should explain the reason and suggest alternatives.

Another drawback is that adding a default is not a purely backwards compatible change for `dyn Trait` users in some corner cases, since it permits code that previously failed to compile and thereby alters the meaning of previously unwritable types. This is considered acceptable because only erroneous programs are affected.

Finally, the feature still requires a nightly-only implementation to be completed and tested before it is stabilized.

## Rationale and alternatives

**Allow assuming the default.** This was the original intent of RFC 192 in some readings. It is unsound as shown above, unless the language also forbids overriding, in which case the default is not a default but a definition, and a plain type alias would serve.

**Require a `final` marker.** One could permit assuming the default only if the associated type is marked non-overridable. This addresses the concern but adds a keyword and a new concept for little benefit; users who want a fixed type can write a free type alias.

**Remove the feature.** The feature is partially implemented and some crates on nightly use it. Removing it would lose the convenience for implementors, particularly in traits with many associated types, such as those in futures and parsing libraries.

**Do nothing about trait objects.** The elision for `dyn Trait` is separable from the main fix. It is included here because it is a natural consequence of treating the default as the value of the type when nothing else is stated, and it gives the feature a use at the call-site level.

## Prior art

Swift protocols allow associated types to have defaults, and conforming types that do not specify the type receive the default. Swift's protocol extension methods likewise cannot assume the default for the same soundness reasons, though the mechanisms differ. Haskell's associated type synonym defaults, available through `TypeFamilies`, behave similarly: the default is an instance-level fallback and does not constrain class-level code.

## Unresolved questions

* Should defaults that mention `Self` be supported for trait objects in a future extension, perhaps by substituting the trait object type itself?
* What diagnostics are most helpful for the opacity rule?
* Should the compiler lint when a trait provides a default that cannot be used in any impl because it violates the bounds in every case?

## Future possibilities

Associated const defaults already follow a similar pattern and could be reviewed against the same rule. With generic associated types, defaults could depend on the GAT's own parameters, which will require extending the isolation check described above.
