# Rust RFC 2514: union_initialization_and_drop

## Summary

Unions do not allow fields of types that need drop glue. Drop glue is the code the compiler runs automatically when a variable goes out of scope: it drops the variable and, recursively, all its fields. A union may still implement `Drop` for itself. This RFC specifies when a program may move out of a union field and when the union's `drop` is called. To prevent unwanted implicit calls to `drop`, it also restricts the use of `DerefMut` where unions are involved.

## Motivation

A union stores several fields in the same memory. At any moment only one field is meaningful, and the language does not track which. This is why a union cannot own a field with drop glue: when the union goes out of scope, the compiler would not know which field to drop, or whether any field holds a valid value.

The language therefore requires union fields to be types without drop glue. Still, the union itself may have a `Drop` implementation. The union type is the place where the programmer knows which field is active, and its `drop` can act on that knowledge. Two questions then need answers.

The first question is about moves. Moving a value out of a union field is a bitwise copy of memory that may hold something else. When does the compiler allow it, and does the move count as using up the union?

The second question is about when `drop` runs. Consider a union that implements `Drop`, and a statement that assigns to one of its fields:

```rust
union U {
    a: u32,
    b: [u8; 4],
}

impl Drop for U {
    fn drop(&mut self) { /* knows which field is live */ }
}

let mut u = U { a: 1 };
u.b = [0; 4];
```

For a struct, assigning to a field drops the old value of that field. For a union field, the old contents may not be a valid value of the field's type, so dropping them is not sound. Which of the operations here, if any, calls the union's `drop`?

[TODO: the material gives neither the rules the compiler follows today nor a bug report that motivated the RFC. Add the current behaviour and a concrete failure, if any.]

## Guide-level explanation

The RFC adds three rules that a programmer needs to know.

### Moving out of a field

Reading a field of a union is allowed only in `unsafe` code, because the field may hold bytes that are not a valid value of its type. [TODO: confirm this is existing behaviour and not a change made by the RFC.] When the field's type is `Copy`, reading it copies the bits and leaves the union intact. The RFC specifies what happens for fields whose type is not `Copy`. [TODO: the abstract says the RFC specifies "when one may move out of a union field" but does not give the rule. The author should state it, for example whether a move from a non-`Copy` field is permitted and whether it leaves the union usable.]

### When the union's `drop` runs

[TODO: the author should state the rule. The question is whether `drop` runs at the end of scope, after a move out of a field, after a partial move, and on assignment to the whole union or to a field. Without the rule, this section cannot be written.]

### Assignment through `DerefMut`

The third rule concerns `DerefMut`. Suppose a union has a field whose type implements `DerefMut`, for example `ManuallyDrop<Vec<u8>>`, and the programmer writes an assignment through it:

```rust
union V {
    v: ManuallyDrop<Vec<u8>>,
    n: usize,
}

let mut x = V { n: 0 };
unsafe { *x.v = vec![1, 2, 3]; }
```

The assignment `*x.v = ...` goes through `DerefMut::deref_mut` of `ManuallyDrop`, which returns a mutable reference to the `Vec`, and then drops the `Vec` that was there before the assignment. In `x` the old contents are the bytes of `n`, which are not a valid `Vec`. The program drops garbage. The RFC's restriction prevents the implicit `deref_mut` call in this situation, so that the programmer must write the assignment so that no drop of the old value happens, for instance by writing a whole new `ManuallyDrop` into the field.

[TODO: the abstract says only that the use of `DerefMut` is restricted "when unions are involved." The exact condition, such as "when the place expression goes through a union field", needs to come from the author. The example above shows the problem the abstract describes, and is the writer's illustration, not an example from the author's material.]

## Reference-level explanation

[TODO: the author's material is a summary only. The reference-level rules below are shown as questions the author must answer, because stating them would require inventing behaviour.]

1. **Field types.** A union field must be `Copy`, `ManuallyDrop<T>`, or a reference, or a type with no drop glue as determined by the compiler. [TODO: confirm the exact condition; the abstract says "do not allow fields of types that require drop glue".]
2. **Move out of a field.** The rule for when a move from a field is allowed, and what the compiler regards as moved afterwards.
3. **Implicit drop of the union.** The points in the control flow at which the compiler inserts a call to the union's `Drop::drop`.
4. **Place expressions with `DerefMut`.** The class of expressions that the compiler rejects.

### Interaction with the borrow checker

A move out of one field of a union overlaps the memory of every other field. The borrow checker therefore has to treat a move from one field as a use of all of them, or else document that it does not. [TODO: ask the author how the RFC treats this. The abstract does not mention it.]

## Drawbacks

Restricting `DerefMut` assignments makes some code that works today stop compiling. Whether that code is correct is a separate question: the example above shows code that drops invalid data. The cost is a compile error in programs that used the pattern without realizing the problem, and in programs that used it correctly because the programmer knew the old contents were valid.

[TODO: the author should say whether the change breaks any existing code, and how that was checked. Do not state that no code is affected without a source.]

The rules add to what a union user has to know. A union already needs `unsafe` for reads and has no tracking of the active field. The new rules do not change that, but they add details about moves and drops.

## Rationale and alternatives

The central constraint is that the compiler cannot know which field of a union is live. Every rule in the RFC follows from that. The decision to let the union itself implement `Drop` places responsibility with the type that does know, which is the programmer's wrapper around the union.

Alternatives a reviewer will ask about:

- Forbid `Drop` on unions entirely. This is simple, and it removes the second question from the Motivation. It also removes the only place where a union can run cleanup. [TODO: ask the author whether this was considered, and why it was rejected.]
- Permit drop glue in union fields and drop none of them. [TODO: ask.]
- Leave `DerefMut` unrestricted and document that assignments through it are the programmer's responsibility. [TODO: ask.]

Reversibility: loosening a restriction later is backward compatible, and tightening it is not. Starting restrictive and relaxing is the cheaper path, if that was the intent. [TODO: confirm that the author chose restrictive rules for this reason.]

## Prior art

[TODO: the author's material cites none. If other languages with unions or tagged unions and destructors were consulted, name them and state how this proposal relates.]

## Unresolved questions

- The exact move and drop rules.
- The exact condition for the `DerefMut` restriction.
- Whether the restriction is a hard error or begins as a lint.
- How the borrow checker treats overlapping fields.

## Future possibilities

None are proposed. A safe abstraction over unions, one that tracks the active field, would make most of these rules unnecessary for its users, but that is a separate design.
