# RFC 3127: Trimming Host Paths from Release Builds

- Feature Name: `trim_paths`
- Start Date: 2023-02-06
- Status: Proposed

## Summary

This RFC adds a profile setting named `trim-paths` to Cargo, which removes absolute host filesystem paths from the compiled output of a build. A default `release` build should not embed the path of the machine on which it was compiled, either in the executable or in the library. The debug symbols that accompany a build still record the source paths, since debuggers and profilers need them to locate source files. To implement this, the RFC adds a flag named `--remap-path-scope` to `rustc`. The flag controls which contexts the existing `--remap-path-prefix` option applies to, so that the build can remap paths in macro expansions, in debug information, and in diagnostics independently.

## Motivation

A compiled Rust binary often contains strings that reveal where it was built. Panic messages include the path of the source file that panicked, and the standard library's file paths may appear in backtraces. These strings are embedded in the binary by default, and they reveal the username, the directory layout, and sometimes the name of a private project. Some build systems produce reproducible artifacts, where two builds from the same source should be byte-identical, and the embedded paths make this impossible when the build directories differ.

Developers have worked around this with the existing `--remap-path-prefix` flag, which rewrites a path prefix in the output. The workaround is effective, but it must be set up by hand in a build script or a shell environment, and it applies to every context at once. Rewriting paths in debug information is undesirable when the user needs those paths to find sources, and rewriting them in diagnostics may hide information the developer needs during compilation. The lack of control forces a trade-off that most users should not have to make.

The goal is to make the common case work without configuration. A release build should be free of host paths in the artifact, while the debug symbols retain the paths needed for debugging. Users who want a different balance should be able to adjust it with a clear setting.

## Guide-level explanation

A Cargo profile may set `trim-paths` to a value that describes which paths should be removed from the build output. The default for the `release` profile is to remove host paths from the compiled code while keeping them in the separate debug symbol file, when one exists. A user who wants a fully reproducible binary can set the value to remove paths everywhere, and a user who wants no change can disable the feature.

```toml
[profile.release]
trim-paths = "object"
```

The value "object" removes paths from the code and data of the binary, but not from the debug information. Other values allow the user to select the scope more precisely, using the names of the contexts that the compiler recognizes.

At the `rustc` level, the flag `--remap-path-scope` takes a comma-separated list of contexts. Each context names a place where paths may appear: macro expansion, debug information, the output of the compiler's diagnostics, and the code and data of the final artifact. The flag specifies the contexts to which the `--remap-path-prefix` mapping applies. Cargo sets this flag from the profile setting, so most users never need to write it directly.

The effect of the setting is visible in the output. A panic message in a trimmed build shows a path relative to the package root, not an absolute path beginning with the user's home directory. Debuggers still find the sources, because the debug symbols contain the original paths.

## Reference-level explanation

The `trim-paths` profile setting accepts a set of contexts, which may be one of the predefined names or a list. The predefined names are `none`, which disables the feature, `diagnostics`, `macro`, `debuginfo`, `object`, and `all`, which enables every context. The default for the `release` profile is `object`, and the default for other profiles is `none`.

The compiler flag `--remap-path-scope` accepts the same context names. When the flag is absent, the behavior of `--remap-path-prefix` is unchanged, which preserves the meaning of existing invocations. When the flag is present, the prefix mapping applies only to the listed contexts.

Remapping in the macro context affects the paths that the compiler embeds through the `file!` macro and through the expansion of other macros that record a location. Remapping in the debuginfo context affects the paths in the debug symbols. Remapping in the diagnostics context affects the paths printed to the user during compilation. Remapping in the object context affects the paths embedded in the generated code and data, including the strings used for panic messages.

Cargo passes the remapping prefix for the package root and for the registry directories, so that paths in dependencies are also trimmed. The standard library's source path is remapped to a stable placeholder, so that the same standard library does not produce different output on different machines.

The debug symbol file is generated from the unmapped debug information when the configuration requests it, so that debuggers retain the ability to locate sources. The RFC specifies that the debug symbol file is not affected by the object scope, which is what makes the default safe for debugging.

## Drawbacks

The feature changes the output of the release profile, which may affect users who parse panic messages or who compare binaries across builds. Tools that depend on exact paths in the binary will need updating. The RFC expects these cases to be rare, but it recognizes that they exist.

The additional flag adds to the surface area of the compiler. Each context must be tested in combination with the others, and the test matrix grows. The authors consider the growth manageable, since the contexts are few and the interactions are simple.

Users who strip debug symbols and then distribute the binary will find that the paths are no longer present anywhere. This is the intended result, but it may surprise users who expected the paths to remain available for remote debugging.

## Rationale and alternatives

The main alternative is to leave the default unchanged and document the existing flag. This preserves the behavior of every build, but it places the work of removing paths on each user, and most users will not do it.

A second alternative is to remove all paths in every profile, including debug. This would make debugging harder, and it would prevent debuggers from finding sources without an explicit mapping, which is a poor trade for most developers.

A third alternative is to keep a single remapping flag and not add the scope control. This is simpler, but it forces the same behavior in every context, and it does not allow the debugging use case to coexist with the reproducibility use case.

The chosen design keeps the default safe and reproducible, preserves the information needed for debugging, and gives advanced users precise control over each context.

## Prior art

Several compilers provide a path remapping option that rewrites file paths in their output. The design here follows that approach, and it adds the per-context scope that the existing tools lack. Reproducible build efforts in other ecosystems have used similar techniques, and their experience informs the default.

## Unresolved questions

- The exact placeholder used for the standard library path should be chosen so that it does not collide with user paths.
- The interaction between trimming and incremental compilation needs to be verified, since cached artifacts may retain older paths.
- The name of the `object` context may change if it proves confusing to users.

## Future possibilities

The scope mechanism can be extended to cover other kinds of host information, such as environment variables recorded at build time. The same design would allow those to be removed selectively, without changing the rest of the build.
