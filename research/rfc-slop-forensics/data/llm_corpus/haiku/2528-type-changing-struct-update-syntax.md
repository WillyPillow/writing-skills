- Feature Name: `type_changing_struct_update_syntax`
- Start Date: 2017-12-01
- RFC PR: [rust-lang/rfcs#2528](https://github.com/rust-lang/rfcs/pull/2528)
- Rust Issue: [rust-lang/rust#86555](https://github.com/rust-lang/rust/issues/86555)

# Summary

Extend struct update syntax, also known as functional record update (FRU), so that it works for instances of the same struct whose types differ because of generic type or lifetime parameters. Fields whose types differ between the base and the new value must be listed explicitly in the struct expression. Fields that share a name and a type can still be moved from the base with the `..base` form.

The change lets a program produce a value of a different instantiation of a struct while reusing the parts that are unchanged, without writing every field out by hand.

# Motivation

Struct update syntax is useful when a value differs from an existing one in only a few fields. A typical example is a configuration record with many options, where a caller wants the defaults except for one setting. The syntax reads clearly and avoids repetition.

Today the syntax only works when the result has exactly the same type as the base. Consider a struct with a generic parameter `T` that is used by one field and not by others. A caller who wants to change `T` must rebuild the entire struct, even though most fields are identical in both values. In practice this forces either verbose code or the use of helper constructors that duplicate the field list.

The restriction is not necessary from the point of view of memory safety. When a field is moved out of the base into the new value, the compiler already tracks which fields have been consumed. Fields of a type that does not depend on the changed parameter are the same in both values, and moving them is as safe as it is for the existing case. The restriction exists because the implementation was written for the simplest case, not because the underlying semantics require it.

# Guide-level explanation

Suppose a struct is defined with two fields and a generic parameter:

```rust
struct Foo<T> {
    field1: T,
    field2: i32,
}
```

An instance `base` of type `Foo<&str>` can be turned into an instance of type `Foo<String>` as follows:

```rust
let base = Foo { field1: "hello", field2: 3 };
let updated = Foo { field1: String::from("hello"), ..base };
```

Here `field1` must be listed explicitly because its type changes from `&str` to `String`. The field `field2` has type `i32` in both values, so it is taken from `base` by the update syntax. After this line, `base.field2` is considered moved only if it is not `Copy`, which for `i32` it is not a concern.

The rule is simple to state. Every field whose type is the same in the base and in the new value may be supplied by the update syntax. Every field whose type differs must be given explicitly. The compiler reports an error that names the field and both types when a field is omitted and its type has changed.

The same rule applies to lifetime parameters. A struct whose field type mentions a lifetime can be updated to a value that uses a different lifetime, provided the other fields are unaffected.

Programmers reading this code should be able to see at a glance which fields are new and which are carried over. The explicit fields mark the points of change, and the `..base` form shows the rest.

# Reference-level explanation

The type checker currently requires that the type of the base expression equal the type of the struct expression. This proposal relaxes that requirement. The base must be an instance of the same struct definition, possibly with different generic arguments. For each field that is not listed explicitly, the type checker compares the declared type of the field under the base substitution with its declared type under the result substitution. If the two types are equal, the field is taken from the base. If they differ, the field must be listed explicitly, and the compiler reports an error otherwise.

The comparison is done after substitution, so a field whose declared type is `T` is treated as the same type in both values only when the two generic arguments for `T` are equal. A field whose declared type does not mention any changed parameter is always equal.

For lifetime parameters, the comparison is done up to region inference. Two lifetimes are treated as equal for this purpose if they are the same lifetime variable after inference. Regions that are constrained to be equal by the rest of the expression are considered equal. This avoids rejecting programs that a human reader would consider unchanged.

The move semantics are unchanged. Each field taken from the base is moved, and the base is treated as partially moved afterward, following the existing rules for partial moves. Fields that are `Copy` are copied and leave the base intact.

The change is confined to type checking and to the lowering of struct expressions. No new syntax is introduced. The MIR produced for an update expression is the same shape as before, with the moved fields selected from the base and the explicit fields evaluated in order.

# Drawbacks

The change adds a case to the type checker that must be explained to users. A programmer who is accustomed to the existing rule may be surprised that the base can have a different type. The error messages must be clear enough to guide the user to list the changed fields.

The relaxation also makes some refactorings less obvious. Adding a generic parameter to a struct can now change which fields are required in an update expression, and that change is not visible from the update site alone.

# Rationale and alternatives

The main alternative is to do nothing. Programmers who need the change can write out every field, or write a helper function that copies the unchanged fields. Both work, but they are noisy, and the noise grows with the size of the struct.

A second alternative is to introduce a new syntax for type-changing updates, such as a distinct operator. This would avoid the question of how existing code is affected, but it would add a second way to do a single thing, and it would not match the mental model that programmers already have of the update syntax.

A third alternative is to allow any field to be taken from the base, relying on the type checker to reject unsound moves. This is unsafe in the obvious sense, because a field of the old type cannot be placed into a value of the new type. It is rejected.

The proposed rule is the smallest change that is consistent and sound. It reuses the existing notion of field equality and it adds no new concepts to the language. It also keeps the explicit fields as the places where a reader should look for change.

# Prior art

Other languages handle record updates in different ways. Some functional languages allow a record update to change the type of a parameter, provided the update is total on the fields that depend on it. Those languages typically do not have partial moves, so the analysis is simpler. The approach taken here is closer to what the borrow checker already does for partial moves out of structs.

Within Rust, the existing struct update syntax is the only precedent. The design aims to extend it without changing its meaning for the cases it already supports.

# Unresolved questions

The exact treatment of region variables that are inferred late in the body needs more study. The proposal assumes that region equality can be decided before move checking, and this assumption should be confirmed against the implementation.

It is also unclear whether the error message for a missing explicit field should suggest the name of the field or the full expression to write. The authors would prefer to decide this during implementation, with input from the diagnostics team.

# Future possibilities

A later proposal could allow the same relaxation for enum variants, so that a value of one instantiation of an enum can be converted to another while reusing the unchanged payload fields. This is out of scope here because enum variants have different layout considerations.

A further extension could permit the update syntax to change the type of a field that is itself a generic struct, provided the change can be expressed as a fresh field expression. This would require more careful design of the inference rules and is left for future work.
