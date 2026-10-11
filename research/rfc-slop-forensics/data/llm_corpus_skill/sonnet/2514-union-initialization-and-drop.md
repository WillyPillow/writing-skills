# Rust RFC 2514: union_initialization_and_drop

## Summary

Unions do not allow fields of types that require drop glue. Drop glue is the code that the compiler runs automatically when a variable goes out of scope, which recursively drops the variable and all its fields. A union may still implement `Drop` itself. This RFC specifies when a program may move out of a union field and when the union's `drop` runs. It also restricts the use of `DerefMut` when unions are involved, so that no drop call happens by accident.

## Motivation

A union stores one of several fields in the same memory. The compiler does not know which field holds a valid value, so it cannot decide which field to drop when the union goes away. Rust avoids the problem by forbidding union fields whose types need drop glue. A field of type `u32` or a raw pointer is allowed, and a field of type `String` is not. [TODO: the author should confirm the escape hatch, such as `ManuallyDrop<T>`, that lets a program store a drop-needing type in a union. The abstract does not mention it.]

The rule about fields leaves three questions open, which the abstract names.

1. A union may implement `Drop`. When does its `drop` method run?
2. A program may read a field of a union and move the value out. When is that allowed?
3. A program may reach a field through `DerefMut`. What happens to the memory it points to?

Without answers, the behaviour of these operations is a matter of how the compiler happens to work, and programs that rely on it can break between compiler releases. [TODO: the author should cite an issue or a code sample where the current behaviour surprised someone. No instance was supplied.]

An example frames the first question.

```rust
union U {
    a: u32,
    b: f32,
}

impl Drop for U {
    fn drop(&mut self) { /* release a resource tied to the union */ }
}
```

The union has no field that needs drop glue, so the compiler has nothing to run for the fields. The user-written `drop` is the only action at the end of the scope. The question is whether it runs when the value has been partly moved or when the union has been assigned to.

## Guide-level explanation

The RFC adds three rules to the model of unions. They are described here by their effect on programs.

First, a union's own `drop` is called when the union value goes out of scope or is overwritten, in the same way as for a struct with an `impl Drop`. Because the compiler never drops union fields, `drop` is the only place where cleanup happens. [TODO: the author should state the rule for assignment to a field. The abstract says only that the RFC specifies "when the union's `drop` is called".]

Second, the RFC says when a program may move out of a union field. A struct that implements `Drop` forbids moving a field out, because the move would leave `drop` with a partly invalid value. A union is different in one way: the fields share memory, so a move out of one field leaves the others in a state the compiler cannot track. [TODO: the author should give the rule. Two natural candidates are to allow the move only for fields that are `Copy`, or to allow it for any field and to treat the whole union as moved. The abstract supplies neither, so these are suggestions for the author to evaluate.]

Third, the RFC restricts `DerefMut` in expressions that involve a union. This is the least obvious rule, and the abstract gives its purpose: "to avoid undesired implicit calls of drop". The next section explains what that means.

## Reference-level explanation

### Implicit drop through assignment

Assignment to a place normally drops the value that was in the place before. When the place is a union field of a type without drop glue, nothing is dropped. When the place is reached through a user-defined dereference, the old value is that of a different object, and assignment runs its drop.

Consider a union field of a smart pointer type that implements `DerefMut`, written as an expression `u.f.x = 1` where `f` is reached by the dereference. The compiler inserts a call to `deref_mut` on the field, which borrows the field as a reference. If the field has not been initialized, because the union currently holds another field, the call creates a reference to memory that holds no valid value. Assigning through the reference then drops that garbage. [TODO: the author should confirm that this is the scenario the RFC means. The abstract says only that the restriction avoids "undesired implicit calls of drop", and this draft reconstructs the mechanism from that phrase.]

The proposed rule is to reject, in the compiler, an assignment to a union field when the path to the place includes an implicit `DerefMut` call. [TODO: the author should give the precise condition, and whether an explicit `deref_mut` call remains allowed. The rule's reach determines how much existing code breaks.]

### Moves out of fields

The RFC states when a move out of a union field is accepted. [TODO: rule, as discussed in the guide-level section.] Whichever rule is chosen has to be checked by the borrow checker, and the checker needs to treat the union as one unit with several overlapping fields. After a move out of one field, the rule decides whether a read of another field is allowed.

### When `drop` runs

The union's `drop` runs at the end of the scope that owns the value, unless the value has been moved. If the union has been partly moved, the compiler does not call `drop`, because Rust does not call `drop` on partly moved values for any type that is allowed to be partly moved. [TODO: confirm the interaction with the move rule above. If every move out of a field moves the whole union, there are no partly moved unions and this paragraph can be deleted.]

## Drawbacks

The `DerefMut` restriction forbids code that is correct in some cases. A program that knows the field is initialized, and wants to write through a smart pointer in it, cannot use the shorthand and has to write out the dereference with explicit calls. [TODO: the author should estimate how much code is affected. Unions are rare in safe Rust, and the draft has no data on how many crates use them with `DerefMut` fields.]

Each new rule adds to what a user must learn about unions, and unions already carry a safety burden: reading a field is `unsafe`. [TODO: the author should say whether the rules in this RFC touch `unsafe` blocks, in particular whether writing to a field stays safe.]

The rules are hard to reverse once programs depend on them. A rule that allows an operation can be tightened only by breaking code, whereas a rule that forbids an operation can be relaxed later. This asymmetry favors the conservative choice for each open question, namely rejecting a move or a deref assignment that the RFC cannot show to be sound.

## Rationale and alternatives

The deciding reason in the abstract is that implicit drops are dangerous, and the RFC prefers to forbid the construct that causes them over adding a runtime check. [TODO: the author should confirm this reading and give the reasoning for not choosing a runtime check, such as drop flags.]

Alternatives, labelled as suggestions for the author to evaluate:

- Allow fields with drop glue, and add a rule that says which field is dropped. This needs the union to carry a tag, which turns the union into an enum.
- Forbid `impl Drop` for unions. This removes question one. It also removes the one tool a union has for cleaning up a resource that it manages.
- Leave the three questions unspecified and mark them as undefined behaviour. This spares the compiler work and leaves users without guidance.

## Prior art

[TODO: the author should cite the RFC that introduced unions and any discussions of drop behaviour in other languages. None were supplied.]

## Unresolved questions

- The exact rule for moves out of union fields. [TODO]
- The precise definition of "involves a union" for the `DerefMut` restriction, for example whether nested unions inside structs are covered. [TODO]
- Whether the restriction applies to `Deref` as well, since the abstract names only `DerefMut`.
