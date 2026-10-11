- Feature Name: `as_cell`
- Start Date: 2016-11-13
- RFC PR: (leave this empty)
- Rust Issue: (leave this empty)

# Summary

- Change `Cell<T>` to allow `T: ?Sized`.
- Guarantee that `T` and `Cell<T>` have the same memory layout.
- Add standard library conversions:
  - `&mut T -> &Cell<T>` where `T: ?Sized`
  - `&Cell<[T]> -> &[Cell<T>]`

> Note: RFC 1651 was accepted recently, so `Cell` methods that do not need it no longer require `T: Copy`.

# Motivation

Rust's borrowing rules forbid holding two references to the same data when one of them is mutable. That rule underpins Rust's safety guarantees, but it also rejects programs that are clearly correct, especially in single-threaded code that wants to update several elements of a collection while also reading from it.

A classic example is iterating over a slice while writing to elements other than the current one:

```rust
let mut v = vec![1, 2, 3, 4];
for i in &v {
    // error: cannot borrow `v` as mutable because it is also borrowed as immutable
    v[(*i as usize) % 4] += 1;
}
```

The usual fix is to iterate by index. That works but obscures what the code is doing, adds bounds checks, and does not compose with iterator adapters.

`Cell<T>` solves this in principle. It allows mutation through a shared reference by forbidding references *into* its contents: values can only be copied out, moved in, or swapped. Because no reference to the inside of a `Cell` can exist, mutating through `&Cell<T>` is safe in single-threaded code.

But `Cell` only helps if the data was put into a `Cell` from the start. If you have a `&mut [i32]` you got from somewhere else, there is no way to temporarily view it as `&[Cell<i32>]`, even though that would be completely sound. A `&mut T` already guarantees exclusive access, and giving up that exclusivity in return for shared mutation via `Cell` cannot cause any aliasing problem.

With the conversions in this RFC, the example becomes:

```rust
use std::cell::Cell;

let mut v = vec![1, 2, 3, 4];
let slice: &[Cell<i32>] = Cell::from_mut(&mut v[..]).as_slice_of_cells();
for i in slice {
    slice[(i.get() as usize) % 4].set(slice[(i.get() as usize) % 4].get() + 1);
}
```

No index loop, no `unsafe`, and the borrow checker is satisfied. After the `slice` borrow ends, `v` is available as a normal `Vec<i32>` again.

This pattern helps in several places:

- algorithms that update neighboring elements during iteration, such as cellular automata, graph relaxation, and in-place prefix sums;
- collections of nodes that hold indices into each other and need to update one another;
- interfaces that take `&[Cell<T>]` so they can be used from several places at once without requiring the caller to store data in `Cell`s permanently.

# Detailed design

## `Cell<T: ?Sized>`

Today `Cell` is declared as:

```rust
pub struct Cell<T> {
    value: UnsafeCell<T>,
}
```

`UnsafeCell<T>` already allows `T: ?Sized`. This RFC changes the declaration to:

```rust
pub struct Cell<T: ?Sized> {
    value: UnsafeCell<T>,
}
```

Most methods keep their implicit `T: Sized` bound, since they move values in or out (`get`, `set`, `replace`, `into_inner`). Methods that make sense for unsized types get a `?Sized` bound:

```rust
impl<T: ?Sized> Cell<T> {
    pub fn as_ptr(&self) -> *mut T;
    pub fn get_mut(&mut self) -> &mut T;
}
```

`Cell<T>` must also implement `CoerceUnsized` where `UnsafeCell` already does, so that, for example, `&Cell<[i32; 4]>` coerces to `&Cell<[i32]>`.

## Layout guarantee

This RFC guarantees that `Cell<T>` has the same size, alignment, and ABI as `T`, for every `T` including unsized types. In practice that is already true, since `Cell` is a single-field wrapper around `UnsafeCell`, which in turn wraps `T`. Making it a documented guarantee is what lets the conversions below be implemented soundly with pointer casts.

To make this explicit to the compiler, `Cell` and `UnsafeCell` should be marked `#[repr(transparent)]`, or, until that attribute exists, documented as having this property and tested.

## `Cell::from_mut`

```rust
impl<T: ?Sized> Cell<T> {
    pub fn from_mut(t: &mut T) -> &Cell<T> {
        unsafe { &*(t as *mut T as *const Cell<T>) }
    }
}
```

This is sound for three reasons:

1. The layout guarantee means the pointer cast produces a valid `&Cell<T>`.
2. The returned reference borrows `t` for the same lifetime, so the original `&mut T` cannot be used while the `&Cell<T>` exists.
3. `Cell` does not implement `Sync`, so the `&Cell<T>` cannot be shared across threads.

Together these make `&mut T` at least as strong as `&Cell<T>`. Anything `&Cell<T>` allows is something the holder of an exclusive `&mut T` could already do.

## `Cell::as_slice_of_cells`

```rust
impl<T> Cell<[T]> {
    pub fn as_slice_of_cells(&self) -> &[Cell<T>] {
        unsafe { &*(self as *const Cell<[T]> as *const [Cell<T>]) }
    }
}
```

This is sound because a `Cell<[T]>` and a `[Cell<T>]` have the same layout (each element `Cell<T>` has the layout of `T`) and the same permissions: both allow any element to be overwritten through a shared reference, and neither allows a reference into an element.

The two methods compose:

```rust
let slice: &mut [i32] = &mut [1, 2, 3];
let cells: &[Cell<i32>] = Cell::from_mut(slice).as_slice_of_cells();
```

## The reverse conversion

`&[Cell<T>] -> &Cell<[T]>` is also sound and might be added later. It is not proposed here because no compelling use case has come up.

# How we teach this

The documentation for `Cell` should get a section on "Converting from `&mut`", using the iterate-and-mutate example from the Motivation. The documentation for `from_mut` should explain informally why it is sound: exclusive access can always be downgraded to shared, single-threaded mutable access.

The Rust book's section on interior mutability could mention this as an alternative to restructuring code around indices.

# Drawbacks

- The layout guarantee constrains future changes to `Cell`. For example, `Cell` could never add a debugging field. Since `Cell` is meant to be zero-cost, this is unlikely to matter.
- It adds API surface to `Cell`, which is already a subtle type.
- Some users may reach for `Cell` conversions where restructuring the code would be clearer.

# Alternatives

- **Do nothing.** Users can write the pointer casts themselves in `unsafe` code, but they cannot rely on a layout that is not guaranteed, so such code is technically unsound today.
- **Provide the conversions in an external crate.** This still needs the layout guarantee from `std`, which is the core of this RFC.
- **Name the methods differently,** for example `Cell::from_mut_slice` taking `&mut [T]` and returning `&[Cell<T>]` directly. That covers the common case but is less general and does not compose.

# Unresolved questions

- Should the same treatment extend to `RefCell` or other cell types? `RefCell` contains a borrow flag, so the layout guarantee cannot hold for it.
- Should `Cell<[T; N]>` to `[Cell<T>; N]` conversions be added for arrays?
