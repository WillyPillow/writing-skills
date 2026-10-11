# RFC 1682: Field Init Shorthand

- Feature Name: `field_init_shorthand`
- Start Date: 2016-07-18
- RFC PR: rust-lang/rfcs#1682
- Rust Issue: rust-lang/rust#37340

## Summary

When initializing a data structure (struct, enum, union) with named fields, allow writing `fieldname` as a shorthand for `fieldname: fieldname`. This allows a compact syntax for initialization, with less duplication.

Example usage:

```rust
struct SomeStruct { field1: ComplexType, field2: AnotherType }

impl SomeStruct {
    fn new() -> Self {
        let field1 = {
            // Various initialization code
        };
        let field2 = {
            // More initialization code
        };
        SomeStruct { field1, field2 }
    }
}
```

## Motivation

A very common pattern in Rust constructors is to compute each field in a local variable and then assemble the struct at the end. Naming the local variable after the field is the natural choice, since the name already says what the value means. The result is code such as:

```rust
Point { x: x, y: y }
Config { path: path, verbose: verbose, retries: retries }
```

The repetition is pure noise. The reader learns nothing from the second occurrence of each name, and the writer must type it. The cost grows with the number of fields and with the length of their names. In a struct with ten fields, the constructor ends with ten lines in which every identifier appears twice.

Duplication also invites mistakes. When a field is renamed, the author must update both the field and the local variable, or leave them inconsistent. A reviewer scanning a long initializer must verify that each pair really matches, and a swapped pair like `Point { x: y, y: x }` can slip by unnoticed among the many correct ones.

Other languages have addressed the same pattern. JavaScript (ES2015) provides shorthand property names, `{ x, y }`. Haskell has the `NamedFieldPuns` extension. Both have proved popular and uncontroversial. Rust already has a closely related convention in patterns: a struct pattern can write `Point { x, y }` to bind variables named after the fields. This RFC makes the expression side match the pattern side, which gives the language a pleasing symmetry. What can be taken apart with a short form can be put back together with the same short form.

## Detailed design

### Syntax

In a struct expression, a field initializer of the form `ident` is permitted wherever `ident: ident` would be. The two forms are interchangeable, and they can be mixed in the same expression.

```rust
let a = 1;
let b = 2;
let s = S { a, b, c: 3 };
```

This is equivalent to `S { a: a, b: b, c: 3 }`.

The shorthand works in all contexts where a struct expression is valid:

- ordinary structs with named fields;
- struct-like enum variants, such as `Shape::Rect { width, height }`;
- unions, where exactly one field is initialized;
- tuple structs written with the field-index form, such as `Pair { 0: first, 1: second }`, are not covered, since the field names are numerals and cannot be the names of variables.

The shorthand combines with functional record update:

```rust
let t = Config { verbose, retries, ..Config::default() };
```

### Grammar

The grammar for a field initializer changes from

```
field-init ::= ident ':' expr
```

to

```
field-init ::= ident ':' expr
             | ident
```

The second form is only accepted when it is unambiguous that it names a field. Since a struct expression's braces enclose only field initializers, there is no ambiguity with a block or other expression.

### Name resolution

In the shorthand form, `ident` plays two roles: it is the name of the field, and it is the name of a variable (or other value expression) in scope. The variable is looked up in the ordinary value namespace, exactly as it would be for the full form `ident: ident`. If no such variable exists, the usual "unresolved name" error is reported, and the message should mention the field to help the user understand why the name is needed.

The shorthand also works for items other than local variables. A constant or a static whose name matches a field can be used:

```rust
const LIMIT: usize = 10;
struct Settings { LIMIT: usize }
let s = Settings { LIMIT };
```

This is a corner case, and the lint rules for naming conventions already discourage uppercase field names, but allowing it keeps the desugaring simple and uniform.

### Desugaring and semantics

The shorthand is purely syntactic sugar. It is desugared in the parser or in the early lowering step, and every later phase sees the full form. Consequently:

- type checking, borrow checking, and moves are identical to the full form. A shorthand field moves the variable, just as `field: field` does;
- evaluation order is unchanged: initializers are evaluated in the order written;
- macros see the shorthand forms as part of the token stream. In `macro_rules!`, a matcher using `$f:ident` can capture the shorthand, and an expression `$f` in transcription expands naturally to either form.

### Tooling

`rustfmt` should preserve the author's choice, and a clippy lint, off by default, can suggest converting `field: field` to `field`. Because the project has no strong convention here, making the lint opt-in avoids churn. A later decision could promote it if the community converges on the shorthand.

## Drawbacks

The syntax adds a second way to write a thing that was previously written one way. The language gains a small amount of additional surface area, and learners must be taught both forms.

There is a readability concern in the opposite direction. Where a local variable's name matches a field only by coincidence, the shorthand may hide the fact that the variable is being used as the field's value. The full form makes the connection explicit. Reviewers might argue that explicit assignments are clearer when the variable has a different role than the field. Since the author chooses when to use the shorthand, this is an editorial issue rather than a technical one.

Finally, the shorthand can cause confusion for a field named after a variable that has shadowed an earlier binding. If a local `x` was reassigned in a way the reader didn't notice, the struct receives the new value, and the shorthand makes this slightly less visible. This is no different from the full form, but the shorter text provides less visual cue.

## Alternatives

**Do nothing.** The repetition is annoying but not blocking. Existing code continues to work. However, the pattern is so widespread, and the precedent in other languages so strong, that doing nothing leaves a clear ergonomic gap.

**A different syntax**, such as `..name` or `name:` or `#name`. Any of these would need to be learned from scratch, while the bare identifier matches the pattern syntax already in the language, as well as JavaScript and others.

**A macro**, such as `init!(SomeStruct { field1, field2 })`. A macro hides the struct expression from tools and from readers, and cannot be used for enum variants or unions without special handling. Making it syntax lets everything work uniformly.

**Implicit initialization from same-named variables**, without even writing the names. This is far more magical and would silently pick up variables from the surrounding scope, which is dangerous.

## Unresolved questions

Should the shorthand be accepted for tuple struct expressions using numeric field names? Writing `Pair { 0, 1 }` makes no sense, so the current answer is no.

Should `rustfmt` ever rewrite the full form into the shorthand automatically? The RFC recommends against enabling this by default, to avoid creating large diffs in existing code bases. The community can revisit it once the shorthand has seen widespread use.
