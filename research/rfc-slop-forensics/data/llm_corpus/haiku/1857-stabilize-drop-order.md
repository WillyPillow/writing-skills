# Rust RFC 1857: Stabilize drop order

**Type:** Language
**Status:** Proposed
**Area:** Language semantics

## Summary

This RFC proposes that Rust specify and stabilize the order in which values are dropped, rather than leaving it as an unstated property of the current implementation. The specified order would follow what the compiler does today. Fixing it in this way prevents programs from breaking because of unannounced changes to the compiler, and it leaves room for alternative drop orders to be introduced later through an explicit, opt-in mechanism.

## Motivation

Rust calls the destructor of a value when the value goes out of scope. For a single variable this is easy to reason about. For a function with several locals, a struct with several fields, or a vector of values, the order of the destructor calls becomes relevant. Programs can depend on that order in visible ways. A value might release a lock, close a file, or flush a buffer, and another value might assume that the first has already happened.

At present the order is determined by the compiler's implementation. Locals are dropped in the reverse order of their declaration, struct fields are dropped in declaration order, and elements of a collection are dropped from first to last. These rules are consistent in practice, and many programs rely on them. However, the language reference does not state them as guarantees. As a result, a future version of the compiler could change the order without violating any written promise, and code that depended on the old behavior would break silently.

Users have already run into this. Libraries that manage resources with guards have been surprised by the order in which guards are released when they are declared together. Some of these surprises came from rules that appeared natural to readers of the code but that the reference did not describe. The uncertainty makes it harder to write correct code, and it makes the compiler harder to change because nobody knows which behaviors are relied upon.

## Guide-level explanation

When a block ends, the values that were declared in it are dropped in reverse order of declaration. The last variable declared is the first to be dropped. This matches the way the variables were constructed and allows later values to depend on earlier ones.

A struct's fields are dropped in the order in which they appear in the definition. An array or a vector drops its elements from the first index to the last. A tuple drops its elements in order.

These rules describe what the compiler does today and what the reference will say once this RFC is accepted. Code written against these rules will continue to work after stabilization, and it will work under any future compiler that keeps the guarantee.

Temporaries are dropped at the end of the enclosing statement, unless their lifetime is extended by a binding. The reference will describe the extension rules in the same document as the ordering rules, so that the two can be read together.

## Reference-level explanation

The proposal has three parts.

The first part is a specification of the order in which the destructors of locals, fields, elements and temporaries are invoked. The specification follows the implementation as it exists at the time of writing. Where the implementation has an unusual case, such as a value that is moved out of a binding before the end of its scope, the specification describes the case explicitly so that it is not left to interpretation.

The second part is a statement that the specified order is part of the language's stability guarantee. Changes to the order would therefore require a new edition or an opt-in mechanism, in the same way as other breaking changes.

The third part is a reservation for future work. The specification leaves room for an alternative drop order to be selected by a user who wants it. Such an alternative would be chosen explicitly, for example through an attribute on a type or a setting on a crate, and the default would remain the specified order.

The implementation does not change under this RFC. The compiler already behaves in the way the specification describes, so no code generation changes are needed for stabilization. The work is to document the behavior, to add tests that pin it down, and to make sure that the tests cover the cases that are most likely to be depended upon.

## Drawbacks

Stabilizing an order limits future design choices. If the community later decided that a different order would be more useful, the change would require an opt-in mechanism and some migration, rather than a simple change to the default. The RFC accepts this cost on the grounds that the current order is already widely relied upon, and that a stable order is more valuable than the freedom to change it silently.

There is also a risk that the specification will be read as more precise than it is. Writers of compilers and tools may find that a rule which seemed clear in the text has an edge case that the text does not address. The RFC mitigates this by asking for tests that cover unusual cases, but some ambiguity may remain.

## Rationale and alternatives

The main alternative is to leave the order unspecified and to rely on the implementation's behavior remaining the same in practice. This keeps the language flexible, but it does not give users anything to rely on, and it means that breakage is discovered only after it reaches users.

A second alternative is to specify a different order, one that is arguably more intuitive or that makes certain patterns easier. This was rejected because it would change the behavior of existing programs. The stated goal of the RFC is to avoid breakage, and a new order would break code that depends on the current one.

A third alternative is to make the order a property of the type, so that each type declares how its fields are dropped. This could be useful, but it is a larger design question. The RFC leaves room for it without requiring it.

## Unresolved questions

The interaction between drop order and panics needs further specification. When a destructor panics during unwinding, the remaining values must still be dropped, and the order in which they are dropped in that case should be consistent with the normal order. The RFC proposes that it is, but the details should be checked against the implementation.

The treatment of values captured by closures is another open point. The order in which captured values are dropped when the closure itself is dropped should be stated, and the statement should match the implementation.

## Future possibilities

An opt-in mechanism for alternative drop orders could allow code that needs a specific release sequence, for example in a concurrent data structure, to request it directly rather than relying on field order. The mechanism would be designed in a separate RFC, and the stability of the default order would remain the same.

Documentation tooling could show the drop order of a function in the editor, which would help users who are learning the rules and reduce the number of surprises in code review.

## Conclusion

Specifying drop order is a small change to the language reference with a large effect on how confidently programs can be written. It records a behavior that people already depend on and protects it from accidental change. The RFC asks the project to make that promise explicitly and to keep it.
