# Rust RFC 1398: Allocator API

**Type:** Library
**Status:** Proposed
**Area:** Standard library, memory management

## Summary

This RFC proposes a standard interface for memory allocators and support for user-defined allocators in the standard library. The interface lets library code be written generically over the allocator it uses, so that collections and smart pointers can take distinct, possibly stateful allocators for each instance. It requires callers to supply the size and alignment of a block at the points where memory is allocated and released, which keeps the common path fast. It also introduces a high-level description of the layout of an object in memory.

## Motivation

Rust programs rely on a single global allocator in nearly all cases. The default allocator is good for general use, but it is not suitable for every workload. A program may want to place a particular data structure in a pool, use an arena that is freed all at once, keep memory in a region that a device can read, or count the bytes used by one part of the application. At present such choices require either replacing the global allocator for the whole program or writing unsafe code that bypasses the standard collections.

Neither option is satisfactory. Replacing the global allocator affects every allocation in the process, including those made by libraries that have no reason to be affected. Bypassing the collections means giving up the tested implementations of vectors, maps and smart pointers and writing new ones with the risks that entails.

A standard interface for allocators addresses both problems. Collections can accept an allocator as a parameter, so a caller can choose the allocator for a particular instance. Different instances can use different allocators within the same program. Libraries can be written once and used with any allocator that implements the interface.

## Guide-level explanation

An allocator is a value that implements a trait describing how to obtain and release blocks of memory. The trait is small. It has an operation to allocate a block with a given layout, an operation to release a block that was previously allocated, and optional operations to grow or shrink a block in place.

A layout describes the size and alignment of a block. A layout is produced from a type, or constructed directly from a size and an alignment. Because the layout is passed to the allocator on each call, the allocator does not need to store the size of each block, and it can be implemented efficiently.

A collection that is generic over an allocator takes it as a type parameter with a default. Users who do not care about allocators get the global allocator without changing their code. Users who do care can name the allocator they want when they create the collection.

Here is how the interface would be used in practice. A program creates an arena allocator that hands out blocks from a large buffer and frees them all at once. It then creates a vector that uses the arena. Every push to the vector obtains memory from the arena, and when the arena is dropped the memory is released together. The vector's code is unchanged from what it would be with the global allocator.

## Reference-level explanation

The trait for allocators declares the following operations. Allocation takes a layout and returns a pointer to a block that satisfies it, or an error if the request cannot be met. Deallocation takes a pointer and the layout that was used to allocate it, and returns the block to the allocator. The layout passed to deallocation must match the one passed to allocation; the caller is responsible for keeping them consistent.

Growing and shrinking have default implementations that allocate a new block, copy the contents and release the old block. Allocators that can resize in place may override them. This keeps the common case simple while permitting efficient implementations where they are available.

The type of a layout records a size and a power-of-two alignment. The constructors check that the alignment is valid and that the size does not overflow when rounded to the alignment. The type is designed so that an invalid layout cannot be constructed through the safe interface.

Collections are parameterized over the allocator type with a default of the global allocator. The default ensures that existing code compiles unchanged. Implementations of the collections are written to use the allocator they are given for every allocation and deallocation they perform, and they store the allocator in the container so that it is available when the container needs to grow or be dropped.

Smart pointers that own a value follow the same pattern. An owning pointer stores its allocator and uses it to release the value when the pointer is dropped.

The specification also says what happens when an allocator fails. The failure is reported to the caller as an error that the collection can handle, rather than as an immediate abort, so that code which can recover from memory exhaustion has the opportunity to do so.

## Layout as a concept

The layout type is a separate part of the proposal and has value on its own. It gives a name to the size and alignment that unsafe code otherwise computes by hand, and it reduces the number of places where a miscalculation can cause memory corruption. A type that wants to describe its own layout can do so through the standard constructors, which removes an entire class of errors from manual code.

## Drawbacks

An allocator parameter adds complexity to every generic collection. The signatures of the collection types grow, and error messages may become longer when a type mismatch involves an allocator. The RFC accepts this cost, but it asks the implementers to keep the default in place so that most users never see the parameter.

The interface requires careful attention from implementers of allocators. An allocator that returns a block with the wrong alignment, or that accepts a layout that does not match the one it issued, can cause undefined behavior. The safety conditions must be documented clearly, and the unsafe trait must be implemented with care.

Stateful allocators complicate some operations. A collection that is moved to another thread must carry an allocator that is safe to use there, and the trait bounds must reflect this. The RFC expects these bounds to be expressed through the existing marker traits.

## Rationale and alternatives

One alternative is to keep the global allocator as the only option and to provide hooks for replacing it. Hooks are simpler but do not allow different instances to use different allocators, which is the main purpose of the proposal.

A second alternative is to define the allocator interface without the layout parameter on deallocation, so that the allocator stores the size of each block. This was rejected because storing the size costs memory and time on every allocation, and because the caller always knows the layout at the point of release.

A third alternative is to make the allocator a runtime value rather than a type parameter. This avoids the complexity of generics but adds a dynamic dispatch cost to every operation and complicates the type system's guarantees about which allocator a value uses.

## Future possibilities

The design leaves room for allocators to integrate with a garbage collector. The RFC describes a way to add such integration later, while ensuring that existing code cannot opt in by accident and risk unsound behavior. The specification of that integration is deferred to a later RFC, and nothing in this proposal depends on it.

Other future work includes standard allocators for common cases, such as a bump allocator and a pool allocator, which could be provided in a separate crate and evaluated for inclusion later.

## Unresolved questions

The exact set of operations in the trait should be settled during implementation, particularly the default behavior of the optional operations and the naming of the error type. The treatment of allocators that are not thread safe needs more review, since it touches the auto-trait rules that the compiler applies to generic types.

## Conclusion

A standard allocator interface lets Rust code choose how memory is obtained without giving up the standard collections or the guarantees the language provides. The design is conservative. It keeps the default path fast, it makes the common cases simple, and it leaves the door open for more ambitious integration later.
