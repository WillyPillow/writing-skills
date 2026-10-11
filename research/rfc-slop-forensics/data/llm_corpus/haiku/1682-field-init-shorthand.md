# Rust RFC 1682: Field init shorthand

- Start Date: (draft)
- RFC PR: (pending)
- Rust Issue: (pending)

## Summary

When initializing a data structure (struct, enum, union) with named fields, allow writing `fieldname` as a shorthand for `fieldname: fieldname`. This allows a compact syntax for initialization, with less duplication.

## Motivation

Constructors for structs with several fields often follow a repetitive pattern. Each field is computed or received as a local variable, and then the struct literal repeats each name twice: once as the field label and once as the expression that supplies its value. In a struct with many fields, the initializer becomes a column of duplicated words that adds length without adding information.

The repetition has a real cost beyond visual noise. When a field is renamed, the programmer must change both occurrences, and a mismatch can produce a confusing error or, in some cases, silently assign the wrong value if another variable with the old name happens to be in scope. Reducing the number of places a name must be written reduces the chance of such errors.

Other languages have addressed this problem with similar syntax. Several mainstream languages support a form in which a bare identifier inside a record literal is interpreted as both the label and the value. The authors observed that programmers coming from those languages often expect the form in Rust, and that the lack of it is a frequent small irritation in code reviews.

The change is small, but it touches a common construct, so the RFC takes care to specify its interaction with existing syntax, which is the main subject of the reference section.

## Guide-level explanation

With this RFC, a struct literal may use a shorthand for any field whose value is a variable with the same name as the field. The following two forms are equivalent.

```rust
struct Point {
    x: i32,
    y: i32,
}

fn make(x: i32, y: i32) -> Point {
    Point { x: x, y: y }
}

fn make_short(x: i32, y: i32) -> Point {
    Point { x, y }
}
```

The shorthand can be mixed with the ordinary form in the same literal, so a programmer can write `Point { x, y: compute_y() }` when only one field needs a computed value. The rule applies only to the names written in the literal, so the shorthand does not affect the meaning of any other part of the code.

The shorthand also works in patterns when destructuring a struct in a `let` or `match`, where it binds the field value to a variable of the same name. This RFC extends the literal form and the pattern form together so that the two remain symmetric, which makes them easier to learn.

## Reference-level explanation

In a struct expression, a field initializer may consist of a single identifier. The compiler treats such an initializer as if the field name and the identifier were written in the explicit form `name: name`. The identifier is resolved in the usual way, looking up the nearest binding in scope. If no binding of that name exists, the compiler reports an error that names the field, so that the user sees the intent clearly.

The shorthand applies to tuple-like struct expressions only in the named form. Tuple structs and tuple variants have positional fields and do not take field labels, so the shorthand is not applicable to them.

For struct patterns, the shorthand allows a pattern such as `Point { x, y }` to bind the fields `x` and `y` to new variables of the same names. The binding mode is the same as for an explicit `x: x` pattern, so the rules for `ref` and `ref mut` continue to apply when those keywords precede the field name.

The shorthand may be combined with the struct update syntax, `..base`, so that a programmer can write `Config { verbose, ..Default::default() }`. The update syntax is unaffected and continues to fill in any fields not named in the literal.

The grammar change is minimal. A field initializer may now be an identifier alone, in addition to the existing forms. Because a bare identifier in that position was previously a syntax error, no valid existing program changes its meaning.

## Drawbacks

Some readers find the shorthand less clear when the variable has a name that differs in context from the field. For example, a field named `count` initialized from a variable named `count` reads well, but a reader scanning quickly may not notice that the value came from a different computation than expected. The RFC argues that the shorthand is only ever applied when the names match, so the value always comes from the variable of the same name, and that a reader who wants a different value must write the explicit form.

A second drawback is that a new feature adds to the surface that a learner must understand. The authors judge this cost to be small, since the feature is simple to explain and appears in many codebases.

## Rationale and alternatives

The alternative of doing nothing was considered and rejected on the grounds that the repetition is common enough to justify a small syntactic addition.

A second alternative is a more general form that allows any expression to be written with the name omitted, inferring the field from the expression. The authors rejected this because it would make the meaning of a literal hard to determine by looking at it, and because it would be ambiguous for expressions that are not simple identifiers.

A third alternative is to restrict the shorthand to struct literals and not to patterns. The authors preferred symmetry, since a programmer who learns one form will expect the other to work the same way.

## Prior art

As noted in the motivation, several languages accept a bare identifier as a field initializer with the same meaning. The RFC adopts a rule that matches the common behavior, limited to the case where the identifier is the field name.

## Unresolved questions

The main open question at the time of drafting concerned how the shorthand should interact with macros that generate struct literals. The authors proposed that the shorthand be expanded in the same way as the explicit form, so that macros which produce field names from input tokens would work without change, but acknowledged that the exact hygiene rules need confirmation during implementation.

A second question is whether a lint should warn when a shorthand refers to a variable that shadows another binding of the same name in an outer scope. The authors suggested that such a lint could be added separately and need not be part of the stabilization.

## Future possibilities

The shorthand opens the door to related conveniences, such as allowing the same syntax in function call arguments for named parameters, although that would require a separate design. The authors also note that the form pairs naturally with the struct update syntax and with destructuring, so later work on either could build on this change without requiring new syntax.
