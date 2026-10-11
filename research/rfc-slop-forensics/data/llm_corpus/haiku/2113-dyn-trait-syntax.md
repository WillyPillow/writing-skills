# Rust RFC 2113: dyn-trait-syntax

- Feature Name: `dyn_trait_syntax`
- Start Date: 2016-07-27
- RFC PR: (to be assigned)
- Rust Issue: (to be assigned)

## Summary

This RFC introduces a new syntax for trait objects, `dyn Trait`, in which `dyn` is a contextual keyword. The existing "bare trait" form, in which a trait name stands alone in a type position to denote a trait object, is deprecated. In a future edition, `dyn` becomes a full keyword, and a lint that flags the bare form becomes deny-by-default. The change is made in stages so that existing code keeps compiling throughout the transition.

## Motivation

Rust has two ways to refer to a type that is known only by the traits it implements. The static form uses generics, and the dynamic form uses a trait object. Trait objects are written today by naming the trait directly in a type position, as in `Box<Display>`. The same spelling is used for a trait's name in other positions, such as bounds on a generic parameter, and this overlap confuses readers and tools.

The overlap has real costs. A reader meeting `Box<Display>` for the first time cannot tell whether the code is creating a trait object or referring to a type called `Display`. Compiler diagnostics must work harder to explain the difference, and the grammar must carry special cases to resolve the ambiguity. Future features that would extend trait objects, such as additional bounds or lifetimes, become harder to express cleanly while the bare form remains.

A dedicated keyword makes the intent explicit. `Box<dyn Display>` says exactly what it means: a boxed value whose concrete type is not known and which implements `Display`. Searching for trait objects also becomes simpler, because every one of them carries the same marker.

## Guide-level explanation

To write a trait object, place the `dyn` keyword before the trait name, as in:

```rust
fn print_all(items: &[Box<dyn Display>]) {
    for item in items {
        println!("{}", item);
    }
}
```

The keyword tells the reader that the type is dynamically dispatched. It also makes clear that the trait name refers to a trait, not to a type of the same name. Code that uses the bare form will continue to compile for now, but the compiler will warn about it, and the warning will suggest the `dyn` spelling as a replacement. The suggestion is machine-applicable, so tools can perform the migration automatically.

The keyword is contextual. It is recognized as a keyword only where a type is expected and only when followed by a trait path. Elsewhere, `dyn` remains an ordinary identifier, so existing programs that use the name for a variable or a module are unaffected.

## Reference-level explanation

### Grammar

A trait object type is written as the keyword `dyn` followed by one or more bounds, separated by `+`. The first bound may be a trait path, and the remaining bounds may be lifetimes or auto traits. The bare form is parsed as before, but the parser records that it has seen the deprecated spelling so that the lint can report it.

### Contextual keyword

During the transition, the parser treats `dyn` as a keyword only in type position when the token that follows can begin a trait path. In all other positions, the identifier is available. This rule ensures that no program that compiles today becomes unparsable because of the new keyword.

### Deprecation

The bare trait form produces a warning under a new lint, which is warn-by-default in the current edition. The warning includes a suggestion that inserts `dyn`. The lint is part of the standard set and can be silenced for a crate that wishes to keep the older spelling, although such silencing is discouraged.

### Future edition

In a later edition, `dyn` becomes a reserved keyword. The lint against the bare form is raised to deny-by-default, so that new code cannot use the old spelling. Code written for the older edition continues to compile under that edition, and the migration tool can rewrite it to the new form. The edition boundary is the only point at which the bare form becomes an error.

### Interaction with other features

The `dyn` form composes with lifetime bounds, so that `Box<dyn Trait + 'a>` denotes a trait object whose concrete type lives for at least `'a`. It also composes with auto traits, so that `Box<dyn Trait + Send>` is valid. The grammar places these additional bounds after the trait path, which matches the order that readers already expect.

## Drawbacks

The change adds a keyword, and every addition to the language has a cost. Some users will need to update their code, and the transition will take time. There is also a short period in which both spellings are valid, which may confuse newcomers reading older documentation.

The contextual approach avoids breaking existing code, but it introduces special rules that must be learned. Some readers may find the difference between a keyword in type position and an identifier elsewhere surprising.

## Rationale and alternatives

One alternative is to keep the bare form and improve diagnostics. That approach solves the confusion for readers who see error messages but does not address the grammatical ambiguity or the readability of the code itself. It also leaves future extensions hard to express.

A second alternative is to make `dyn` a full keyword immediately. This would break any code that uses the name as an identifier, and the breakage would be large enough to justify a long delay. The contextual approach allows the same clarity without breaking existing programs.

A third alternative is to use a different sigil, such as a prefix operator. Sigils are concise, but they are unfamiliar in Rust's type syntax, and they do not read as naturally as a word. The keyword form was preferred for its clarity.

## Prior art

Other languages with trait-like abstractions have faced similar choices. Several use an explicit keyword for dynamic dispatch, and experience from those languages suggests that the explicit marker helps readers, even when they already know the rules. The proposal follows that experience.

## Unresolved questions

The exact wording of the deprecation warning has not been settled. Contributors have asked whether the warning should mention the performance cost of dynamic dispatch, or whether it should focus only on the syntax. This is a matter for the implementation and will be decided during review.

It is also unclear how long the transition period should last. The RFC proposes that the change be made in the next edition, but the timing depends on the release schedule and on the availability of the migration tool.

## Future possibilities

With the `dyn` keyword in place, the language can introduce richer trait object features without adding further ambiguity. Examples include trait objects with generic methods in limited form, and explicit upcasting between trait objects. Each of these would be easier to design once the grammar distinguishes trait objects clearly from named types.
