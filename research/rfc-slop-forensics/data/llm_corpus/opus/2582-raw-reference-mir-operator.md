- Feature Name: `raw_ref_op`
- Start Date: 2018-11-01
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

Add two new forms of the `&` operator: `&raw mut <place>`, which produces a `*mut T`, and `&raw const <place>`, which produces a `*const T`. These create a raw pointer directly, without first creating a reference. Today the only way to get a raw pointer to a place is `&mut <place> as *mut _` or `&<place> as *const _`, which creates a reference and then casts it.

As a consequence, the existing expressions `<term> as *mut T` and `<term> as *const T`, where `<term>` has a reference type, are defined to mean `&raw mut *<term>` and `&raw const *<term>`. Also add a lint that suggests the new operator for code that creates a reference only to cast it to a raw pointer.

# Motivation

A Rust reference carries promises. A `&T` must point to memory that is aligned, dereferenceable and holds a valid `T`. A `&mut T` must, in addition, not be aliased. These promises hold from the moment the reference is created, even if it is immediately cast to a raw pointer and never used as a reference again. If any of them is false at that moment, the program has undefined behavior.

That makes some common patterns unsound, with no sound way to write them.

**Packed structs.** A field of a `#[repr(packed)]` struct may be unaligned:

```rust
#[repr(packed)]
struct Packet { tag: u8, len: u32 }

let p = Packet { tag: 1, len: 7 };
let ptr = &p.len as *const u32;   // UB: creates an unaligned &u32
```

There is no way to get a pointer to `p.len` without going through a reference. The compiler warns about borrowing packed fields but cannot offer an alternative.

**Uninitialized memory.** When initializing a struct field by field through `MaybeUninit`, you need a pointer to each field:

```rust
let mut slot = MaybeUninit::<Config>::uninit();
let base = slot.as_mut_ptr();
let name_ptr = &mut (*base).name as *mut String;   // UB: &mut to uninit String
unsafe { name_ptr.write(String::new()); }
```

The `&mut (*base).name` creates a `&mut String` to memory that does not yet hold a valid `String`. Whether that is UB depends on validity rules that are not settled, and the safe answer today is to assume it is.

**Aliasing models.** Under Stacked Borrows, the proposed aliasing model, creating a `&mut` gives it a fresh tag and invalidates other pointers to the same memory. Code that makes a raw pointer via `&mut x as *mut _` and then uses an older raw pointer to `x` can be flagged as UB, even though the reference was only a stepping stone.

In each case, the programmer never wanted a reference. They wanted the address of a place. Rust has no syntax for that.

# Guide-level explanation

`&raw const place` and `&raw mut place` evaluate to the address of `place`, as a `*const T` or `*mut T`. No reference is created, so none of the reference rules apply. The place does not need to be aligned, initialized or free of aliases.

```rust
let ptr: *const u32 = &raw const p.len;          // fine for packed fields
let name_ptr: *mut String = &raw mut (*base).name;  // fine for uninit memory
```

The place expression itself still has to be valid to evaluate. Writing `&raw const (*ptr).field` still dereferences `ptr` to compute the field address, so `ptr` must point inside an allocation. What changes is that the result is not asserted to be a valid reference.

`&raw mut` requires the place to be mutable, the same as `&mut`. You cannot write `&raw mut` on a field of an immutable local binding.

As a rule: if you are writing `&x as *const _` or `&mut x as *mut _`, write `&raw const x` or `&raw mut x` instead. The compiler will suggest this.

# Reference-level explanation

## Syntax

```
BorrowExpression :
    ...
  | & raw const Expression
  | & raw mut Expression
```

`raw` is a contextual keyword here. `&raw` followed by anything other than `const` or `mut` continues to parse as a borrow of a variable named `raw`, so existing code such as `&raw` or `&raw.field` keeps compiling.

The operand must be a place expression. If it is a value expression, such as a function call, it is an error; taking the raw address of a temporary is almost always a mistake, because the temporary is dropped at the end of the statement.

## Semantics

In MIR, the operator lowers to a new rvalue, `AddressOf(Mutability, Place)`, alongside the existing `Ref`. Borrow checking treats `AddressOf` as a use of the place, not a borrow: it does not start a loan and therefore does not restrict later uses of the place. That matches how raw pointers are treated after a cast today.

Const evaluation and Miri evaluate `AddressOf` by computing the place's address without checking alignment or validity and without retagging.

## Casts

The cast `e as *const T`, where `e: &T`, is redefined as `&raw const *e`, and `e as *mut T`, where `e: &mut T`, as `&raw mut *e`. Since `e` is already a reference, this changes nothing observable for existing code. It does mean that the reference-to-raw coercion is a reborrow through `AddressOf` rather than a separate cast operation, which simplifies MIR.

## Lint

A new lint, warn-by-default, fires on `&place as *const _` and `&mut place as *mut _` where `place` is a place expression rather than a dereference of an existing reference, and suggests the `&raw` form. It does not fire when the reference is used for anything other than the cast.

The existing `safe_packed_borrows` warning will point to `&raw const` as the fix.

# Drawbacks

- New syntax is a cost. `&raw` is a little cryptic, and readers have to learn that `raw` is special in this position.
- Two ways of getting a raw pointer from a reference, cast and `&raw`, now coexist. The lint mitigates this.
- `raw` as a contextual keyword adds a small amount of parser complexity.

# Rationale and alternatives

**A macro**, such as `ptr::raw_const!(place)`, avoids new syntax. It is likely to ship first as a stable wrapper over the unstable syntax. Long term, address-of is a basic operation and deserves an operator, as in C.

**Making `&x as *const _` special** so that it never creates a reference was considered. It would make the meaning of `&x` depend on what follows it, which is surprising and fragile under refactoring, for example if the cast moves into a helper function.

**Relaxing reference rules** so that unaligned or uninitialized references are allowed until used would weaken the guarantees that let the compiler optimize ordinary safe code.

**Other spellings** such as `&const`, `&*const` and `&unsafe` were suggested. `&raw const`/`&raw mut` keeps the parallel with `*const`/`*mut` and leaves room for both mutabilities.

# Prior art

C's `&` operator yields a pointer and makes no promise about validity. C++ has `std::addressof`. Rust's own `ptr::addr_of!` proposals in the ecosystem, such as the `memoffset` crate's field-address helpers, exist because this operator is missing.

# Unresolved questions

- Should `&raw const *ptr` be allowed on a dangling `ptr`? This depends on whether in-bounds field projection is required.
- Should `&raw` on a value expression be a hard error or a lint?
- Final name and default level of the new lint.
