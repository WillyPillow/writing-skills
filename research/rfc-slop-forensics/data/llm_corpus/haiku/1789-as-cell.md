# Rust RFC 1789: as_cell

- Feature Name: `as_cell`
- Start Date: 2016-04-20
- Status: Accepted

## Summary

This RFC makes three changes to `std::cell::Cell`. First, it relaxes the type parameter so that `Cell<T>` may be instantiated with unsized types, that is, with `T: ?Sized`. Second, it guarantees that `T` and `Cell<T>` have the same memory layout, so that a reference to one can be reinterpreted as a reference to the other. Third, it adds conversions in the standard library that take a mutable reference to a value and produce a shared reference to a cell wrapping that value, and that convert a reference to a cell of a slice into a slice of cells. These conversions allow code to mutate data through shared references in a controlled way without copying.

## Motivation

`Cell<T>` provides interior mutability for values that can be copied or replaced as a whole. It allows a value to be changed through a shared reference, which is useful in many data structures where a reference is shared but a small piece of state must still be updated. The type is restricted in two ways that cause friction. It requires its contents to be sized, so a cell cannot hold a slice or a trait object directly. It also offers no way to view existing data as cells without first wrapping the data in a new cell.

Consider a function that processes a slice of counters and needs to update each one while also passing shared access to the slice to other code. Today the function must either copy the slice into a vector of cells, which costs time and memory, or use unsafe code to reinterpret the slice. The first option is wasteful and the second is error prone. A guaranteed conversion would let the function view the slice as a slice of cells with no copying and no unsafe code in the caller.

A similar difficulty arises with unsized contents. A structure that stores a boxed trait object cannot place that object in a cell without giving up the ability to use the cell's methods on the whole value. Allowing the cell to be unsized removes this limitation.

## Guide-level explanation

After this change, a `Cell` may be declared around a slice or another unsized type. Because the type is unsized, it cannot be constructed by value, but it can be produced by a conversion from a reference to an existing value. A programmer who has a mutable reference to a value may convert it into a shared reference to a cell, and then update the value through the cell while the shared reference is alive.

```rust
let mut count = 0u32;
let cell: &Cell<u32> = Cell::from_mut(&mut count);
cell.set(cell.get() + 1);
```

A programmer who has a shared reference to a cell of a slice may view it as a slice of cells, which allows each element to be updated individually.

```rust
let mut values = [1, 2, 3];
let cells: &[Cell<i32>] = Cell::from_mut_slice(&mut values);
cells[0].set(10);
```

These conversions do not copy the data. The cell and the value share the same memory, and the guarantee of identical layout makes the conversion sound.

## Reference-level explanation

The bound on the type parameter of `Cell` is relaxed to allow `?Sized`. Methods that require the value to be copied or moved remain restricted to sized types, because they need a size known at compile time. Methods that operate through a reference, such as the methods that read or replace the value, are available where the type permits.

The layout guarantee states that `Cell<T>` is represented in memory exactly as `T` is, for every `T` including unsized types. This is achieved by declaring the cell as a transparent wrapper around the contained value. The compiler and the standard library rely on this guarantee to define the conversions.

The conversions added to the standard library are the following. A function takes a mutable reference to a value and returns a shared reference to a cell of that value, with the lifetime of the input reference. A second function takes a mutable reference to a slice and returns a shared reference to a slice of cells with the same length. A third conversion takes a shared reference to a cell of a slice and returns a shared reference to a slice of cells.

Each conversion is safe. The mutable reference passed in is consumed, so no other access can occur while the returned cell is in use. The cell provides the only means of mutating the value during that time, and the interior mutability rules of the type ensure that the aliasing is sound.

The implementation of the slice conversion relies on the layout guarantee to reinterpret the pointer and length. Documentation for each function should state the guarantees explicitly, so that readers do not need to inspect the implementation to understand what is promised.

## Drawbacks

Relaxing the bound on `Cell` affects the type's signature, and some generic code that assumed the type was sized may need adjustment. The change is backward compatible for ordinary uses, but it may surprise users who rely on the type having a fixed size in their own generic functions.

The layout guarantee is a commitment that limits future changes to the type. If the cell ever needed additional state, the guarantee would prevent that change. The authors consider this acceptable, because the type is intentionally minimal.

## Rationale and alternatives

An alternative is to leave the cell as it is and provide conversions only through unsafe code in user crates. That is the current situation, and it is the reason the conversions are valuable. Putting them in the standard library lets the reasoning be done once, carefully, and reused everywhere.

Another alternative is to add a separate type for unsized cells. This would avoid changing the existing type, but it would duplicate the methods and would make the relationship between the two types harder to explain. Relaxing the bound on the existing type keeps a single concept.

The guarantee of identical layout could be omitted, with the conversions restricted to cases the compiler can verify. That would be more conservative but would not cover the slice conversion, which is the main motivation.

## Prior art

Rust already offers transparent wrappers in several places, most notably for types that are used to change how a value is treated without changing its representation. The conversions proposed here follow the same pattern. Other languages with interior mutability offer similar operations on arrays of mutable cells, typically without the aliasing discipline that Rust provides, so the design here is more restrictive but also more predictable.

## Unresolved questions

The RFC does not decide whether the conversions should be `const` at the time of stabilization. This depends on the state of constant evaluation for references, and it can be settled during implementation.

Questions remain about the exact wording of the documentation for the unsized methods, particularly about which methods remain available for unsized contents. These will be resolved in the stabilization report.

## Future possibilities

The same layout guarantee could support similar wrappers for other interior mutability types, such as those that provide thread-aware access. The conversions could also be extended to views of arrays and of nested structures, which would make it easier to update fields of data that is shared across several parts of a program. Each extension would need its own analysis, but the foundation laid here would make them straightforward to consider.
