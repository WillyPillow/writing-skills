# RFC 2514: Union Initialization and Drop

- Feature Name: `union_initialization_and_drop`
- Start Date: 2017-09-25
- Tracking Issue: (to be assigned)
- Status: Proposed

## Summary

Unions in Rust do not allow fields whose types require drop glue, which is the code that runs automatically when a value goes out of scope and recursively drops the value and its fields. However, a union may still implement `Drop` itself. This RFC specifies when a value may be moved out of a union field, and when the union's `drop` method is called. It also restricts the use of `DerefMut` when unions are involved, in order to avoid implicit calls to drop that the programmer did not intend.

## Motivation

Unions are a low-level feature. A union stores one of several fields at a time, and the compiler does not track which field is active. This makes unions useful for interoperating with C code, for reinterpreting bytes, and for certain memory layouts in embedded and systems programming. The price of this flexibility is that the compiler cannot know which field to drop when the union goes out of scope, and for this reason fields that require drop glue are excluded.

The exclusion covers the fields themselves, but it does not prevent the union from having its own destructor. Some unions need one. A union that wraps a resource, or that must release memory in a particular way depending on a tag stored outside it, can implement `Drop` to perform that work. The existing language permits this, but the rules for when the destructor runs and what it may assume about the active field have not been stated precisely.

Two questions need answers. The first is when a field may be moved out of a union. Moving a value out of a field invalidates the union's contents, and the compiler must know that the union is no longer responsible for that value. The second is when the union's `drop` is invoked, and what happens when the union is assigned or goes out of scope. Without clear rules, programs could double free resources or skip cleanup that the programmer relied on.

A third question concerns `DerefMut`. A union that implements `DerefMut` may have its fields reached through a method call that looks like an ordinary assignment. If the assignment triggers a drop of the old value, the programmer may not realize that a destructor ran. The restriction proposed here avoids this situation for unions.

## Guide-level explanation

A union may implement `Drop` as an ordinary type does:

```rust
union Slot {
    count: u64,
    handle: u64,
}

impl Drop for Slot {
    fn drop(&mut self) {
        // Release the resource identified by the active field.
    }
}
```

Because the union does not know which field is active, the programmer is responsible for ensuring that the destructor interprets the contents correctly. The destructor runs when the union goes out of scope, as it does for other types with destructors.

A field may be moved out of a union only when the move is done through a pattern or an expression that reads the field as a whole value, and the field's type is one that can be copied or moved without running drop glue. Moving out of a field that requires drop glue is not possible, since such fields are not allowed in unions in the first place.

The change to `DerefMut` is simple to state. A union that implements `DerefMut` does not have an implicit drop inserted during assignment through the dereference. The assignment must be written in a way that makes the replacement of the old value explicit, so that a reader can see where a destructor might run.

## Reference-level explanation

A union type may implement the `Drop` trait. The `drop` method of such a union is called when a value of the union type goes out of scope, unless the value has been moved out of or explicitly forgotten. The method receives a mutable reference to the union. The contents of the union at that time are whatever was last written, and the method is responsible for interpreting them.

A field of a union may be moved out only when the move reads the entire field by value and the field's type does not require drop glue. The compiler records the move and does not call the union's `drop` for a field that has been moved, since the value no longer belongs to the union. Partial moves of the union itself are not permitted, because the union does not track which parts are valid.

Assignments to a union field do not drop the previous contents of the field, since fields of unions do not require drop glue. Assignments to the union as a whole do call the union's `drop` on the previous value, if the union implements `Drop`. This matches the behavior for other types with destructors.

The restriction on `DerefMut` applies when the dereferenced type is a union. An assignment through a dereference of such a type is accepted only if the compiler can determine that no implicit drop is required, or if the programmer has written an explicit call that performs the drop. Other uses of `DerefMut`, such as borrowing through the dereference, are unaffected.

Pattern matching on unions remains restricted to reading fields in an unsafe context, as it is today. The rules here do not change that requirement.

## Drawbacks

The restriction on `DerefMut` may be inconvenient for code that uses unions with smart-pointer-like behavior, and such code may need to be rewritten to make drops explicit. The rules for moving out of fields are also more intricate than the rules for other types, and programmers must keep track of which field is active when relying on a destructor. These costs fall on a small group of users, but they are real.

## Rationale and alternatives

One alternative is to forbid `Drop` on unions entirely. This would remove the need for the rules, but it would prevent unions from managing resources in cases where that is necessary. Another alternative is to allow partial moves out of unions and track the active field in the type system. This is far more complex and would require a significant change to how unions are represented.

The proposed rules keep the union model simple. The compiler does not track the active field. The programmer is responsible for correctness, and the rules make clear when the compiler will run code on the programmer's behalf. The restriction on `DerefMut` is narrow and targets a specific source of surprise.

## Prior art

Languages with untagged unions generally leave the management of their contents to the programmer, and the destructor story varies. Some forbid destructors on unions entirely, while others allow them with conditions similar to those proposed here. The experience in those languages suggests that explicit rules about moves and drops are important for avoiding resource errors.

## Unresolved questions

- Whether moves out of union fields should be permitted in safe code, or only in unsafe code where the programmer takes responsibility for the active field.
- The exact set of expressions that count as reading a field as a whole value.
- Whether the `DerefMut` restriction should extend to other types that have fields with special drop behavior.

## Future possibilities

A later RFC could introduce a tagged union form in which the compiler knows the active variant, which would allow a safer model for drop and move. The rules here could then be refined so that the restrictions relaxed for tagged unions do not apply to untagged ones. Further work could also examine how unions interact with the drop check used for generic types, which is outside the scope of this proposal.
