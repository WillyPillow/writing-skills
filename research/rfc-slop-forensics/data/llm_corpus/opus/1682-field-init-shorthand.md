- Feature Name: `field_init_shorthand`
- Start Date: 2016-07-18
- RFC PR: rust-lang/rfcs#1682
- Rust Issue: rust-lang/rust#37340

# Summary

When initializing a data structure (struct, enum variant, or union) with named fields, allow writing `fieldname` as a shorthand for `fieldname: fieldname`. This gives a compact initialization syntax with less duplication.

```rust
struct SomeStruct {
    field1: ComplexType,
    field2: AnotherType,
}

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

# Motivation

A common pattern in Rust is to compute each field of a struct into a local variable with the same name as the field, then build the struct at the end of a function. Constructors, builders, and conversion functions do this constantly. The result is code like:

```rust
Config {
    path: path,
    verbose: verbose,
    timeout: timeout,
    retries: retries,
}
```

Each line says the same thing twice. The repetition adds no information: anyone reading the code can see the names match. It does make the code longer, and it makes it harder to spot the one line in a long initializer where the names do *not* match, which is usually the line worth paying attention to.

Rust already supports the reverse shorthand in patterns. A struct pattern can write `Config { path, verbose, .. }` to bind local variables named `path` and `verbose` to the corresponding fields. Destructuring and construction are meant to be duals of each other, and the asymmetry between them is a small surprise that every Rust programmer runs into eventually. Several people have written macros to emulate the shorthand in expressions.

Other languages have adopted the same feature. JavaScript (since ES2015) allows `{ x, y }` as shorthand for `{ x: x, y: y }` in object literals. Haskell's `NamedFieldPuns` extension does the same for records. Experience in those languages suggests the feature is easy to learn and widely used once available.

# Detailed design

## Grammar

In a struct expression, the grammar for a field currently is:

```
field_init : ident ':' expr ;
```

This RFC extends it to:

```
field_init : ident ':' expr
           | ident
           ;
```

A field initializer consisting of a bare identifier `f` is equivalent to `f: f`. The identifier on the right-hand side is resolved as an ordinary path expression in the current scope, following the usual name resolution rules. In practice that means it refers to a local variable, but it could also refer to a constant or a static in scope, exactly as `f: f` would.

Shorthand and longhand fields can be mixed freely in the same expression, in any order:

```rust
Point3 { x, y: compute_y(), z }
```

The shorthand also works together with functional record update:

```rust
Config { verbose, ..Config::default() }
```

## Where it applies

The shorthand is allowed anywhere a struct expression is allowed, including:

- struct expressions: `S { a, b }`
- enum variants with named fields: `Shape::Rect { width, height }`
- unions: `U { a }`
- struct expressions using a path through a type alias or `Self`: `Self { a, b }`

It is not allowed with numeric field names. `Tuple { 0, 1 }` is not valid, because `0` is not an identifier and would not resolve to a local variable anyway. Tuple-struct initialization with braces and explicit indices (`Tuple { 0: a, 1: b }`) remains valid in its longhand form.

## Interaction with ownership

The shorthand expands to a plain path expression, so it moves or copies the variable exactly as `f: f` would. There is no implicit borrowing, cloning, or referencing. A user who wants a reference must write `f: &f`.

## Interaction with macros

Inside `macro_rules!`, a field shorthand whose identifier comes from a macro argument resolves with the hygiene context of that identifier, just as the longhand form does. Because the field name and the variable name are the same token, there is no case in which the field name would be taken from one hygiene context and the variable from another.

## Diagnostics

If the identifier does not resolve, the compiler should report the error in terms the user wrote. Rather than "cannot find value `foo` in this scope" pointing at a phantom right-hand side, the error should point at the shorthand field and suggest either declaring a local variable named `foo` or writing `foo: <expr>` explicitly.

The compiler should also offer a lint (allowed by default initially) that suggests the shorthand when it sees `f: f`. Code formatters may want to normalize to the shorthand. Neither is required by this RFC.

# Drawbacks

The shorthand makes field initializers that depend on the name of a local variable. Renaming a local variable can now produce a type error in a struct expression elsewhere in the function, where previously the struct expression would simply have referred to a variable that no longer exists. In practice both cases produce a compile error pointing at the same line, so the difference is small.

A reader unfamiliar with the feature might find `S { a, b }` ambiguous. It could look like a pattern, or like a set literal from another language. Context almost always disambiguates, since a struct expression appears in expression position, and the pattern form already means the analogous thing.

Like any new syntax, it is one more thing to learn. Given that the pattern form already exists, the incremental cost is low.

# Alternatives

**Do nothing.** Users continue writing `f: f`, or write macros. The duplication is mild, but it is pervasive, and the asymmetry with patterns remains.

**Use a different marker**, such as `S { ..a, ..b }` or `S { =a }`. These avoid any possible confusion with patterns, but they invent new syntax for something the pattern grammar already spells as a bare identifier. Reusing the existing spelling is simpler to teach.

**Allow arbitrary expressions with an inferred field name**, such as `S { self.a }` meaning `a: self.a`. This is more powerful but less predictable. It requires deciding which part of an expression supplies the name, and it encourages initializers whose field names are hidden in the middle of expressions. It could be considered as a later extension.

# Unresolved questions

- Should the default-allowed lint for `f: f` be made warn-by-default after the feature has been stable for a while? That question can be answered later and does not block this RFC.
