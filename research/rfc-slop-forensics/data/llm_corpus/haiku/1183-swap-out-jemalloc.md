# Rust RFC 1183: allocator

- Feature Name: `allocator`
- Start Date: 2015-08-04
- Status: Superseded by RFC 1974

## Summary

This RFC proposes two related changes to the way Rust chooses a memory allocator. First, the compiler should accept a declaration that overrides the default allocator, so that a program or library can select a different allocator without modifying the standard library. Second, the default allocator used by dynamic and static libraries should change from the bundled jemalloc to the system `malloc`. The first change gives users a supported mechanism. The second removes an assumption that is awkward for libraries intended to be embedded in other programs.

Note that this RFC has been superseded by RFC 1974, which replaces the proposed mechanism with a more general design. The text below is retained as a record of the reasoning at the time.

## Motivation

Rust programs have, for most of the language's history, used an allocator bundled with the runtime. That allocator was jemalloc, chosen for its performance on multithreaded workloads and its low fragmentation. For many programs the choice is a good one. The difficulty is that the allocator is part of the default build for every program, and programs that have particular needs cannot easily change it.

A program that wants to use a different allocator must currently either patch the runtime or work around it by intercepting allocation at the system level. Neither approach is supported. Embedded developers often have a specific allocator that fits their memory constraints. Game developers may want a pool allocator. Tools that track memory usage need to observe every allocation. Each of these users is forced into a fragile setup.

The default allocator matters for libraries as well as for programs. When a Rust library is linked into a program written in another language, the library brings its own allocator along with it. Memory allocated by the library and freed by the host program then crosses an allocator boundary, which can corrupt the heap or lead to subtle failures. Using the system allocator in libraries avoids most of these problems, because the host and the library then share the same underlying malloc.

## Guide-level explanation

Under the proposal, a crate may declare a global allocator by marking a static item with an attribute. The item must implement the allocation interface defined by the standard library. Once a crate declares an allocator, every allocation in the program, including those made by the standard library, goes through that allocator.

A program that does not declare an allocator receives the default. For executables, the default remains the bundled allocator. For dynamic and static libraries, the default becomes the system allocator, so that library code does not impose its choice on the host.

Only one allocator may be declared in a program. If two crates both declare one, the build fails with an error that names both declarations. This rule keeps the behavior of the program predictable.

## Reference-level explanation

The compiler recognizes a new attribute on a static item of a type implementing the allocation trait. The compiler checks that the item is a constant expression, that the type is `Sync`, and that it is defined in the final crate of the link. It then emits code that routes all allocation calls through the declared item rather than through the default functions.

Linking is adjusted so that the default allocator symbols are provided by the runtime only when no override is present. This is done through a weak symbol mechanism on platforms that support it, and through an explicit selection by the linker driver on platforms that do not.

For libraries, the build system omits the bundled allocator from the link line and relies on the host to provide the system malloc. The change is limited to the default configuration. A library can still request a different allocator through the same attribute, and the attribute takes precedence over the default.

The RFC does not change the allocation interface itself. The existing functions for allocating, deallocating, and reallocating memory are kept, and a new function for zeroed allocation is available to implementers who wish to provide a faster path.

## Drawbacks

Allowing the allocator to be replaced adds a new source of failure. A program that declares an allocator incorrectly may crash or leak memory in ways that are difficult to diagnose. The compiler checks cannot prevent all such errors, because the correctness of an allocator depends on its implementation.

Changing the default for libraries will alter performance for some users. Programs that relied on jemalloc inside a library may see slower allocation on certain workloads, and the change may be surprising. Documentation and release notes must describe the change clearly.

## Rationale and alternatives

The alternative of keeping jemalloc as the universal default was considered and rejected. It makes the library boundary problem worse and gives users no way to avoid a choice they did not make. Another alternative was to remove the bundled allocator entirely and require every program to choose one. That would impose a decision on users who are satisfied with the default, which seemed unnecessarily disruptive.

The attribute-based design was chosen because it is explicit and local. A reader can see which allocator a program uses by looking for the declaration, and the mechanism does not require changes to the build configuration for each platform.

## Prior art

Several C and C++ projects allow the allocator to be replaced at link time by providing symbols with the standard names. This approach is widely used and well understood, though it relies on conventions that are not enforced by the language. Other systems languages have adopted explicit global allocator declarations, which the proposal follows in spirit.

## Unresolved questions

The RFC leaves open how the attribute should interact with allocators that are themselves provided by a dynamic library. It also does not decide how allocation statistics should be exposed when a custom allocator is in use. Both questions were expected to be resolved during implementation.

## Future possibilities

The mechanism could be extended to allow allocators to be selected per crate, rather than globally, which would allow finer control. Better tooling for detecting allocator mismatches across library boundaries would help users who link several languages together. Over time the default allocator could also be tuned for common platforms without changing the public interface.

Status note: the design described in this RFC was superseded by RFC 1974, which adopted a different approach to the same problem while keeping the goal of allowing users to replace the global allocator.
