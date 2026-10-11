# RFC 2582: raw_ref_op

- Feature Name: `raw_ref_op`
- Start Date: 2018-11-01
- RFC PR: rust-lang/rfcs#2582
- Rust Issue: rust-lang/rust#64490

## Summary

Introduce new variants of the `&` operator: `&raw mut <place>` to create a `*mut <T>`, and `&raw const <place>` to create a `*const <T>`. This creates a raw pointer directly, as opposed to the already existing `&mut <place> as *mut _`/`&<place> as *const _`, which create a temporary reference and then cast that to a raw pointer. As a consequence, the existing expressions `<term> as *mut <T>` and `<term> as *const <T>` where `<term>` has reference type are equivalent to `&raw mut *<term>` and `&raw const *<term>`, respectively. Moreover, emit a lint for existing code that could use the new operator.

## Motivation

Today, the only way to obtain a raw pointer to a place is to first create a reference and then cast it:

```rust
let p = &mut x as *mut i32;
let q = &x.field as *const u8;
```

The intermediate reference is not a harmless detail. Creating a reference asserts a number of properties about the memory it points to. A `&T` must be aligned, non-null, dereferenceable for `size_of::<T>()` bytes, and point to a valid, initialized `T`. A `&mut T` must additionally be unique for its lifetime. The compiler is permitted to rely on these assumptions for optimization, and tools such as Miri check them. In consequence, using `&` or `&mut` on a place which does not satisfy these properties is undefined behavior, even if the reference is immediately converted into a raw pointer and never dereferenced.

This matters in several real cases.

**Packed structs.** A field of a `#[repr(packed)]` struct may be misaligned. Writing `&packed.field as *const _` creates a misaligned reference, which is undefined behavior, and the compiler now rejects the reference form with a hard error for most types. But the legitimate goal, to compute the address of a field for use with `ptr::read_unaligned`, has no stable direct expression. Users resort to `addr_of!`-like workarounds with pointer arithmetic on casts of the struct pointer, which is error-prone.

**Uninitialized memory.** Given a `MaybeUninit<Foo>`, one wants to initialize each field separately through a pointer. `&mut (*ptr).field` would create a reference to uninitialized data, which is also instant undefined behavior for most types under the current rules.

**Dangling or one-past-the-end addresses.** In FFI and in data structures like intrusive lists, one often wants the address of a field of an object that is not fully alive, or of a place derived from a pointer which is not dereferenceable for the whole type.

**Unsized and external types.** For a place of dynamically sized type, the address computation depends on a vtable or length that a reference would carry, and a raw pointer should carry as well. Users want to project through a pointer to a struct with a trailing slice without ever materializing a `&`.

Today's workaround is the `ptr::addr_of!` pattern based on pointer arithmetic, `offset_of`-like macros with `mem::uninitialized`, or reliance on the optimizer to remove the intermediate. All of these are fragile, and some of them are themselves undefined behavior. Rust needs a primitive operation that says "compute the address of this place, and do not create a reference".

## Guide-level explanation

Rust adds two new forms of expression: `&raw const place` and `&raw mut place`. They evaluate the place expression and produce its address as a raw pointer, of type `*const T` and `*mut T` respectively, without creating an intermediate reference.

```rust
#[repr(C, packed)]
struct Packed { tag: u8, value: u32 }

let p = Packed { tag: 1, value: 42 };
let ptr: *const u32 = &raw const p.value;
let v = unsafe { ptr.read_unaligned() };
assert_eq!(v, 42);
```

Here `&p.value` would be an error, since the field may be unaligned. `&raw const p.value` is accepted because it never claims that the pointee is aligned. The resulting pointer can be passed to `read_unaligned`.

The same notation can be applied to places reached through raw pointers:

```rust
use std::mem::MaybeUninit;

struct Pair { a: u32, b: String }
let mut slot = MaybeUninit::<Pair>::uninit();
let base = slot.as_mut_ptr();
unsafe {
    (&raw mut (*base).a).write(1);
    (&raw mut (*base).b).write(String::from("x"));
}
let pair = unsafe { slot.assume_init() };
```

No reference to uninitialized memory is created at any step.

Rules of thumb: use `&` and `&mut` when you want a reference with its validity guarantees. Use `&raw const` and `&raw mut` when you want only an address. When you are about to write `&mut x as *mut _`, write `&raw mut x` instead; it is shorter and has fewer preconditions.

The keyword `raw` is contextual. It is recognized only directly after `&` and before `const` or `mut`, so existing code that uses `raw` as an identifier is unaffected.

## Reference-level explanation

### Syntax

The grammar of borrow expressions is extended:

```
BorrowExpression :
      (& | &&) Expression
   |  (& | &&) mut Expression
   |  &raw const Expression
   |  &raw mut Expression
```

`raw` is a weak keyword. The sequence `&raw const` and `&raw mut` is unambiguous, because `&raw` followed by `const` or `mut` cannot be the beginning of any currently valid expression. A bare `&raw` followed by anything else continues to parse as a borrow of a variable named `raw`.

The operand must be a place expression. Applying `&raw` to a value expression is an error, with a suggestion to bind it first, as it would otherwise create a pointer to a temporary.

### Semantics

`&raw const place` has type `*const T` where `T` is the type of the place. `&raw mut place` requires that the place be mutable, with the same rules as `&mut place`, and has type `*mut T`. The evaluation of the operand follows the usual rules for place expressions: field projections, indexing, and dereferences of raw pointers are evaluated to compute an address without loading from it.

The operation does not read or write the pointee. Its only requirement on the memory is that the computation of the address is in bounds: if a field projection or array index is applied to a raw pointer, the offset computation follows the rules of `ptr::offset`, so the result stays within the same allocated object. This is what allows the address of a field of an uninitialized object to be taken. For indexing of a slice through a raw pointer, the index is bounds-checked against the length of the slice metadata, as it is for any other slice index.

The alignment requirement of the pointee type is not imposed. Dereferencing, reading or writing through the resulting pointer is subject to the usual rules, and reading from a pointer to a packed field requires an unaligned read.

### MIR

In MIR, `&raw const` and `&raw mut` correspond to a new `Rvalue::AddressOf(Mutability, Place)`. This replaces the pattern in which a `Rvalue::Ref` is followed by a cast to a raw pointer. Optimizations that previously had to recognize this pattern, and the Miri interpreter, can treat `AddressOf` directly. It carries no borrow, so the borrow checker generates no loan for it, and it does not conflict with other borrows.

### Interaction with `as` casts

The existing expression `x as *const T` where `x: &T` is equivalent to `&raw const *x`, and `x as *mut T` for `x: &mut T` to `&raw mut *x`. The operand is already a valid reference, so no new constraints appear. The equivalence gives a clear semantic for these casts, which formerly lacked one in the aliasing model.

By contrast, `&mut place as *mut T`, with `place` not itself a dereferenced reference, creates a reference first and then reborrows it as a pointer. This form remains legal, and keeps its present meaning, including that it asserts validity.

### Lint

A new lint, `borrow_as_ptr`, warns on code of the form `&place as *const _` and `&mut place as *mut _` where `place` is not a dereference of a reference, and suggests the `&raw` form. The lint is allow-by-default initially, and may be promoted to warn-by-default in a later edition. A machine-applicable suggestion is provided, so `cargo fix` can rewrite occurrences.

## Drawbacks

This adds new syntax, which means more surface area in the language and in tools such as `rustfmt`, syntax highlighters and macro parsers. The `raw` weak keyword is another thing to teach.

There is a risk of users reaching for `&raw` casually and misunderstanding that it does not make dereferencing safe. Since pointer dereference is still `unsafe`, the risk is mostly one of documentation.

The existence of both `&mut x as *mut _` and `&raw mut x` leaves two spellings of near-identical operations. The lint is intended to guide users toward the new one, but old code will persist.

## Rationale and alternatives

Alternatives considered:

**A macro such as `addr_of!(place)`.** This avoids new syntax and can be provided immediately in the standard library. Its main drawbacks are that macros produce worse error messages, cannot be parsed identically by all tools, and make the primitive look like a library function when it is a core operation. A macro can be offered as a transitional shim, expanding to `&raw const`.

**Different syntax**, such as `&&mut`, `&mut raw`, or `ptr_of!`. The chosen form keeps the `&` prefix, signalling "address of", and puts the distinguishing word where it is easy to find. `&raw const` and `&raw mut` parallel `*const` and `*mut`, the types they produce.

**Making `&x as *const _` have the weaker semantics.** One could define the cast as a single operation without validity requirements. This would silently change the meaning of existing code, and the compiler would have to apply the rule only when the cast follows a borrow directly, which is fragile and easily broken by refactoring through a local variable.

**Doing nothing.** The undefined behavior would remain impossible to avoid for packed structs and uninitialized fields.

## Prior art

C's `&` operator on an lvalue yields a pointer without any claim of validity; `offsetof` is built on this. C++ provides `std::addressof` for the same purpose as an overloaded `&` workaround. Other safe languages offer no analogous operation because they have no raw pointers.

## Unresolved questions

Should `&raw` be usable in `const` contexts from the start? The operation involves no memory access, so it seems fine, but the const evaluator must support `AddressOf`.

What should be the exact wording of the aliasing rules for the result? The RFC leaves precise semantics to the unsafe code guidelines, noting that the pointer inherits the provenance of the place it was derived from.

Should a `&raw` form of `ref` patterns be added, so that matching on a packed struct can bind raw pointers? This is out of scope and may be considered in a follow-up.
