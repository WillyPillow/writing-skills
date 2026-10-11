# RFC 1789: as_cell

- Feature Name: `as_cell`
- Start Date: 2016-11-13
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

## Summary

- Change `Cell<T>` to allow `T: ?Sized`.
- Guarantee that `T` and `Cell<T>` have the same memory layout.
- Enable the following conversions through the std lib:
  - `&mut T -> &Cell<T> where T: ?Sized`
  - `&Cell<[T]> -> &[Cell<T>]`

> Note: https://github.com/rust-lang/rfcs/pull/1651 has been accepted recently, so no `T: Copy` bound is needed anymore.

## Motivation

Rust's aliasing rules are strict. A `&mut T` is the unique way to reach a value for as long as it lives. Shared references `&T` are numerous but immutable. `Cell<T>` is the standard escape hatch for shared mutability of small, plain values: it allows `get` and `set` through a shared reference, and it is safe because it never hands out a reference to its content.

The difficulty is that `Cell` is awkward to introduce into code that began with ordinary references. Suppose a function receives a slice `&mut [i32]` and wants to run an algorithm in which several parts of the code hold views into the slice and modify it in an interleaved fashion. The borrow checker will not allow multiple `&mut` references, and it will not allow a `&[i32]` to be mutated. The natural remedy is to treat the elements as cells: `&[Cell<i32>]` can be freely copied, and each element can be updated through any copy.

Today there is no safe way to get there. A `Cell<[i32]>` cannot exist, since `Cell<T>` requires `T: Sized`. And even where `Cell<T>` can be named, no conversion is provided from an existing `&mut T` to `&Cell<T>`. The only way out is to allocate a new `Vec<Cell<i32>>` and copy into it and out of it, which costs time and memory, or to use `unsafe` code with a transmute. Such `unsafe` code is easy to get subtly wrong, and relies on a layout equivalence that the standard library does not promise.

An example of the kind of problem this solves is a stencil computation on a grid. For each element we want to read its neighbors and write to the element in place. With `&mut [f64]`, we cannot hold a reference to a neighbor while writing to the current cell. With `&[Cell<f64>]` we can, and we can use `.iter()` and window-style iteration directly over cells.

Another example is graph algorithms, where nodes refer to each other by index and update a per-node value during traversal. Another is a recursive data structure in an arena where nodes are stored in a slice and mutated in place.

## Detailed design

### Relaxing the `Sized` bound

Change the definition of `Cell` to:

```rust
pub struct Cell<T: ?Sized> {
    value: UnsafeCell<T>,
}
```

`UnsafeCell<T>` already allows `T: ?Sized`. The methods on `Cell` are divided into those that need `T: Sized`, because they move values in or out by value, and those that do not.

The following methods remain available only for `T: Sized` (and, where applicable, `T: Copy`):

- `Cell::new`
- `Cell::set`
- `Cell::replace`
- `Cell::into_inner`
- `Cell::get`
- `Cell::take`
- `Cell::update`

The following are available for `T: ?Sized`:

- `Cell::as_ptr`, which returns `*mut T`.
- `Cell::get_mut`, which returns `&mut T`.
- The new conversion methods below.

Existing code compiles unchanged, since a bound of `T: Sized` is the default for type parameters everywhere else, and since the methods that require it still do.

### Layout guarantee

`Cell<T>` is documented to have the same size, alignment and representation as `T`. This is equivalent to marking the struct `#[repr(transparent)]`, and given the current lack of that attribute, the guarantee is documented in prose and tested. Concretely, a pointer to a `T` may be cast to a pointer to a `Cell<T>`, and the reverse, for any `T`, including unsized types such as `[U]` and `dyn Trait`, subject to the metadata remaining the same.

This guarantee is what makes the conversions below sound. It is also a commitment for the future: the type cannot add fields, for instance a borrow flag, without a breaking change. Since `Cell` is deliberately a zero-overhead abstraction, this is in keeping with its purpose.

### New conversion methods

Add to `Cell`:

```rust
impl<T: ?Sized> Cell<T> {
    /// Returns a `&Cell<T>` from a `&mut T`
    pub fn from_mut(t: &mut T) -> &Cell<T>;
}

impl<T> Cell<[T]> {
    /// Returns a `&[Cell<T>]` from a `&Cell<[T]>`
    pub fn as_slice_of_cells(&self) -> &[Cell<T>];
}
```

The first converts a unique reference into a shared reference to a cell. The second transposes a cell containing a slice into a slice of cells.

Because the first function consumes the `&mut T`, nothing else can access the `T` for as long as the resulting `&Cell<T>` lives. The `&Cell<T>` may then be copied freely, since `Cell` is not `Sync` and so cannot cross threads. The implementation is a pointer cast:

```rust
pub fn from_mut(t: &mut T) -> &Cell<T> {
    unsafe { &*(t as *mut T as *const Cell<T>) }
}
```

The second function is also a pointer cast, with the length preserved:

```rust
pub fn as_slice_of_cells(&self) -> &[Cell<T>] {
    unsafe { &*(self as *const Cell<[T]> as *const [Cell<T>]) }
}
```

### Combining them

The combination is the useful case. Given `&mut [T]`, a user can write:

```rust
let slice: &mut [i32] = &mut [1, 2, 3];
let cells: &[Cell<i32>] = Cell::from_mut(slice).as_slice_of_cells();
```

Now elements may be read and updated through `cells`, in any order and through any number of copies of the reference:

```rust
let a = &cells[0];
let b = &cells[2];
a.set(b.get() + 1);
b.set(a.get() + 1);
```

When the borrow ends, the original slice is usable again and reflects the changes.

### Soundness

The key claims are:

1. `&mut T` to `&Cell<T>`: the exclusive reference guarantees that no other access exists during the lifetime of the output. The output allows mutation, but only through `Cell` methods which never create a reference to the interior. So no aliasing rule is violated.
2. `&Cell<[T]>` to `&[Cell<T>]`: layout equivalence holds because `Cell<[T]>` and `[Cell<T>]` are both arrays of `T`-sized elements. Each `Cell<T>` has the same layout as `T`, and `[T]` has no padding between elements.
3. `Cell<T>` is `!Sync`, which prevents data races across threads.

For `T: ?Sized`, the types for which `Cell` can be constructed from a reference include trait objects. `Cell<dyn Trait>` supports no `get` or `set`, but `as_ptr` and `get_mut` remain available, and it can be passed around where a `&Cell<dyn Trait>` is needed.

## How we teach this

The documentation for `Cell` should be revised to describe the `?Sized` generalization and the layout guarantee, and to link to the examples. A section titled "Converting between references and cells" should introduce the pattern with a short example such as the one above. The explanation of why this is safe, summarized as "the exclusive borrow turns into a shared one", is concise enough to include in the docs for `from_mut`.

For readers who know `RefCell`, a note should emphasize that `Cell` is cheaper, since there is no runtime check, and that the trade-off is that it can only copy values in and out.

## Drawbacks

- `Cell<T>` can no longer change its representation. The guarantee is a restriction on future implementation freedom, though there is no known reason to change it.
- Relaxing `T: Sized` adds a small amount of complexity to the type's documentation, since some methods now require extra bounds.
- It exposes an additional pattern that can make code harder to reason about: mutation through shared references requires attention to where values are read and written.

## Alternatives

**Do nothing.** Users would continue to rely on `unsafe` transmutes or to copy data into a new collection. This is error-prone and slow.

**A `Cell::from_mut_slice` method.** A single method that converts `&mut [T]` straight to `&[Cell<T>]` would cover the most common case and require less change. The two-step form is more general, since `from_mut` is also useful for non-slice types, and the pieces compose.

**A trait-based approach.** A trait such as `AsCell` implemented for appropriate types would generalize further, but would need further design to decide which types implement it.

**Add `#[repr(transparent)]` first.** Making the guarantee through the attribute would be cleaner than prose, but the attribute is not yet available.

## Unresolved questions

- Should `Cell::from_mut` be named differently to avoid confusion with other `from_*` constructors?
- Should an analogous conversion be provided for `RefCell`? It has additional state, so the layout cannot match, and the answer is probably no.
- Should `as_slice_of_cells` be extended to arrays?
