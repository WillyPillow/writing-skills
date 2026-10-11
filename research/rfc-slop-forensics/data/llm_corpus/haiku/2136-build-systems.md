# Rust RFC 2136: Cargo build system integration

- Feature Name: `cargo_build_system_integration`
- Start Date: 2016-07-29
- RFC PR: (to be assigned)
- Rust Issue: (not applicable; this is an experimental RFC)

## Status

This is an **experimental RFC**. It lays out a high-level plan rather than a specific set of stable features. Its purpose is to open the door to unstable features in Cargo that let people try ideas in practice. Accepting this RFC does not stabilize any of the features it mentions. Each feature that moves toward stability will need its own follow-up RFC, with its own design, motivation, and review.

## Summary

This RFC proposes a set of hooks that let Cargo cooperate with other build systems and with build environments that Cargo does not control. The hooks range from small customizations, such as overriding how Cargo locates a single tool, to a mode in which an external build system drives nearly the entire compilation while Cargo supplies dependency resolution and metadata. Together, these hooks permit a wide spectrum of integration strategies, and the choice of strategy is left to the project.

## Motivation

Cargo is designed around a particular model. It resolves dependencies, computes a build graph, and invokes the compiler for each crate. That model suits most Rust projects, but it does not suit all of them. Large organizations often have build systems that already manage C and C++ components alongside Rust. Some have custom requirements for caching, sandboxing, or remote execution. Others want Rust code built with a toolchain that Cargo does not know how to drive.

Today these teams have limited options. They can wrap Cargo in scripts, which duplicates logic and loses information about the build graph. They can abandon Cargo and maintain a parallel set of build files, which splits the source of truth. Or they can accept the friction of running two systems side by side. None of these choices is satisfactory, and each makes it harder for Rust to coexist with the rest of a codebase.

The motivation of this RFC is to give those teams a path that keeps Cargo as the authority on dependencies and package metadata while letting them plug in their own execution model. The aim is not to replace Cargo, and it is not to make every project pay for flexibility it does not need.

## Guide-level explanation

Most projects will never need anything in this RFC. For a project that wants a small change, Cargo may allow a single tool to be overridden. For example, a team might point the compiler wrapper at a caching tool, or supply a particular linker. These overrides are configured in the project's Cargo configuration and do not change the structure of the build.

A project that wants a larger change may ask Cargo to emit a description of the build graph instead of executing it. The external system reads that description, performs the compilation with its own tools, and reports the outputs back. Cargo continues to own resolution and the package metadata, so that a crate published to a registry remains usable by anyone, whatever their build system.

A third mode lets an external system take control of the whole build, with Cargo reduced to a metadata provider. This mode is the most demanding and the most flexible. It is intended for organizations that have invested heavily in their own build infrastructure and need Rust to fit into it.

All three modes are marked unstable. Users who wish to try them must opt in explicitly, and the interface may change between releases.

## Reference-level explanation

### Tool overrides

Cargo will accept configuration keys that name external executables for specific roles, such as the compiler driver, the linker, and the archiver. Each override is a path, optionally with fixed arguments. Cargo passes the same arguments it would pass to the default tool and expects the same outputs. An override that does not behave identically is outside the contract, and Cargo does not attempt to detect it.

### Build graph export

The build graph export mode writes a machine-readable file describing every unit of work in the build. Each unit records its inputs, its outputs, the command that produces it, and its dependencies on other units. The format is versioned, and the version is part of the file. An external system reads the file and schedules the units according to its own policy.

The format describes what to do but not how to do it. An external system may run units in parallel, cache their outputs, or execute them on remote machines. It must preserve the dependency order and must report failures in a form that Cargo can read back if the user later asks Cargo to resume.

### Metadata-only mode

In metadata-only mode, Cargo performs resolution and emits the package metadata, including the set of targets, features, and dependencies for each package. It does not invoke the compiler. An external build system uses this information to decide what to compile and how. The metadata format is the same one that Cargo already provides for tooling, which means that existing editor integrations would continue to work.

### Stability and evolution

Each of these modes is gated behind an unstable flag. Changes to the format are expected during the experimental period, and the flag is the only promise. Stabilization requires a separate RFC for each mode, with the format fixed and documented. This RFC does not commit the project to any particular format.

## Drawbacks

The additional modes increase the surface that Cargo must test and maintain. Every new hook is a place where Cargo's assumptions about the build could be violated by an external system. The team must decide how much responsibility Cargo takes for correctness when an external tool produces output that does not match what Cargo would have produced.

There is also a risk of fragmentation. If several organizations build incompatible integrations, the Rust ecosystem may lose the shared experience that Cargo provides. A crate that builds under one integration may fail under another, and debugging that failure may require knowledge that most developers do not have.

## Rationale and alternatives

An alternative is to leave integration entirely to third parties. Some third-party tools already do this, and they have proven useful. The difficulty is that each tool must reverse-engineer Cargo's behavior, and changes to Cargo can break them without warning. An official interface gives those tools a stable target.

A second alternative is to adopt an existing build system outright and make it the default. That path would sacrifice the simplicity that most users value, and it would force a single model onto projects with very different needs. The layered design here allows each project to choose the smallest change that solves its problem.

## Prior art

Many build tools offer a similar split between resolution and execution. Some expose a graph of work to plugins, and others let a wrapper script take over. Experience with those systems suggests that the graph format is the most important part of the design, because it determines what external tools can express. This RFC adopts that lesson by treating the format as the central artifact.

## Unresolved questions

The format of the build graph has not been designed in detail. Questions remain about how to represent generated source files, build scripts that produce outputs at build time, and conditional compilation that depends on the target platform. Each of these must be answered before the export mode can be stabilized.

It is also unclear how external systems should report partial failure. Cargo can stop at the first error, but a large external build may prefer to continue and report all errors. The interface for that reporting is deferred to the follow-up work.

## Future possibilities

If the experimental modes prove useful, Cargo could offer a standard way to describe cross-language dependencies, so that a Rust crate could depend on a C library built by an external system. Such a feature would reduce the need for custom glue code and would make mixed-language projects easier to maintain.
