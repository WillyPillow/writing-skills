# RFC: trim-paths

- Feature Name: `trim-paths`
- Start Date: 2021-03-14
- RFC PR: (leave this empty)
- Tracking Issue: (leave this empty)

## Summary

Cargo should have a profile setting named `trim-paths` to sanitise absolute paths introduced during compilation that may be embedded in the compiled binary executable or library. `cargo build` with the default `release` profile should not produce any host filesystem dependent paths into binary executable or library. But it will retain the paths inside separate debug symbols file, if one exists, to help debuggers and profilers locate the source files.

To facilitate this, a new flag named `--remap-path-scope` should be added to `rustc` controlling the behaviour of `--remap-path-prefix`, allowing us to fine tune the scope of remapping, specifying paths under which context (in macro expansion, in debuginfo or in diagnostics) should or shouldn't be remapped.

## Motivation

### Absolute paths in binaries

When `rustc` compiles a crate, it embeds file paths in several places: in `panic!` messages and `file!()` expansions, in the debug information used by debuggers, and in the output of `std::backtrace`. Because Cargo invokes `rustc` with absolute paths, these embedded strings contain the full path of the source on the build machine, for example `/home/alice/projects/foo/src/main.rs`.

This causes three kinds of problems.

**Privacy.** Absolute paths leak the username, directory layout and sometimes the name of a client or employer in a project path. A developer publishing a binary may not realise this information is present. Anyone inspecting the binary with `strings` can read it.

**Reproducibility.** A build is reproducible if the same sources produce a bit-for-bit identical artifact regardless of where or by whom it is built. Embedded absolute paths defeat this: building the same commit in `/home/alice/foo` and `/build/foo` yields different binaries. Distributions that verify reproducibility, such as Debian and NixOS, currently pass `--remap-path-prefix` flags manually to hide the differences.

**Binary size.** Long, repeated paths take space, a particular concern for embedded targets.

### Existing tooling

`rustc` already has `--remap-path-prefix FROM=TO`, which rewrites a path prefix wherever it appears in output. Using it from Cargo is possible via `RUSTFLAGS`, but suffers from usability problems:

- The user must know the right prefixes for each dependency: the workspace root, the registry source directory (`~/.cargo/registry/src/...`), git checkouts, and the sysroot.
- `RUSTFLAGS` applies to all crates and changes the fingerprint, causing full rebuilds.
- Remapping applies to every kind of path, including those in debug information. This breaks debuggers and profilers, which use the recorded paths to find source files on disk. A developer who wants a debuggable local build cannot also have clean release paths.
- Remapping also applies to diagnostics, so compiler messages show the remapped path rather than the real one, which makes error output less clickable in editors.

What is wanted is a single switch in Cargo that does the right thing in the common cases, and a finer control in `rustc` that makes it possible.

## Guide-level explanation

### The Cargo profile setting

A new profile key, `trim-paths`, controls remapping:

```toml
[profile.release]
trim-paths = "all"
```

Accepted values:

- `"none"` or `false`: no remapping. This is the default for the `dev` profile.
- `"macro"`: remap paths that appear through macros such as `file!()` and `panic!`.
- `"diagnostics"`: remap paths in compiler diagnostics.
- `"object"`: remap paths in object files, including debug information.
- `"all"` or `true`: apply all of the above.

A list is also accepted, to combine scopes: `trim-paths = ["macro", "object"]`.

The default for the `release` profile is `"object"` with `"macro"`, that is, the paths embedded in the produced binary are trimmed, while diagnostics are unaffected since they never reach the binary.

### What the user sees

With trimming enabled, the project's own sources appear relative to the workspace root, for example `src/main.rs`. Sources of dependencies appear with a prefix identifying the package, like `foo-1.2.3/src/lib.rs` for a registry crate. The standard library's source appears under `/rustc/<commit-hash>/library/...` as it already does for distributed toolchains.

A panic message reads:

```
thread 'main' panicked at 'oops', src/main.rs:3:5
```

instead of one with an absolute `/home/alice/...` prefix.

### Debug symbols

When Cargo is producing a separate debug file (split debuginfo, such as `.dwp`, `.dSYM` or `.pdb`), the paths inside the *debug file* are not remapped, so debuggers find sources. Only the main binary has its paths trimmed. If the debuginfo is embedded in the binary, there is no separate file, and trimming applies to it as set by the user.

## Reference-level explanation

### New `rustc` flag: `--remap-path-scope`

`--remap-path-scope=<scopes>` accepts a comma-separated list of the following:

- `macro`: apply remapping to paths produced by `file!()`, `panic!`, `assert!` and similar macros.
- `diagnostics`: apply remapping to paths in compiler messages.
- `debuginfo`: apply remapping to paths in debug information.
- `object`: apply remapping to paths written into object files, including debuginfo.
- `all`: all of the above.

When the flag is absent, `--remap-path-prefix` applies to all scopes, which is the current behaviour, so existing users are not affected.

With the flag, a prefix mapping is applied only in the named contexts.

### Cargo behaviour

When `trim-paths` is enabled for a unit, Cargo passes to `rustc`:

1. `--remap-path-prefix` mapping the workspace root to an empty string, so workspace files become relative.
2. For each dependency from a registry, `--remap-path-prefix` mapping the package's source directory to `<name>-<version>`.
3. For git dependencies, a similar mapping to `<name>-<version>` or the short commit hash.
4. For path dependencies outside the workspace, a mapping to the package name.
5. A `--remap-path-scope` option corresponding to the user's choice.

Cargo also sets the working directory of `rustc` so that relative paths resolve.

Because the options depend on the profile, they are part of the unit fingerprint. Changing `trim-paths` triggers a rebuild of the affected units, as with any profile setting.

### Interaction with build scripts and proc macros

Build scripts run on the host and may embed paths in generated code; those that use `file!()` are remapped when compiled with trimming. Paths passed via environment variables such as `OUT_DIR` and `CARGO_MANIFEST_DIR` are not rewritten, as they are strings provided to programs, not compiler output. Documentation will explain that authors who embed such variables via `env!` or `include!` should be aware that the values contain absolute paths. A future feature might offer relative variants.

### Interaction with the sysroot

Distributed toolchains already remap the standard library's paths. For a self-built toolchain, the sysroot paths may not be remapped. This RFC does not change that.

### Compatibility with debuggers

The recommended workflow for debugging a release binary is to retain split debuginfo. Because that file keeps real paths, no extra configuration is needed. For embedded debuginfo, users who need to debug can set `trim-paths = false`, or tell their debugger to substitute paths.

## Drawbacks

- Panics and backtraces in trimmed builds report relative paths, which may be ambiguous when several crates define files with the same relative name. The package prefix reduces but does not remove this.
- More profile options, more documentation and more testing.
- Remapped paths mean that tools that open the reported file directly from the path, such as editors consuming panic output, can no longer do so without knowing the root.
- Complexity in `rustc`: scopes require tracking where each path came from.

## Rationale and alternatives

**Rely on users to pass `--remap-path-prefix`.** Works today, but is error-prone and does not allow scope control.

**Always trim by default for all profiles.** This harms the development experience, where absolute paths are useful.

**Make trimming a `rustc`-only feature.** Cargo knows the layout of the workspace and the dependencies, which `rustc` doesn't. Cargo is the right place for the policy.

**Use a boolean only.** Simpler, but doesn't let a user keep diagnostic paths while trimming others. The list form is a small addition.

## Prior art

GCC and Clang provide `-ffile-prefix-map`, `-fdebug-prefix-map` and `-fmacro-prefix-map`, which are separated by scope in the same way. Go has `-trimpath`, a single switch that removes file system paths from the executable. The design here is closest to Go's user experience, with the flexibility of the C compilers.

## Unresolved questions

- What exactly is the prefix for git dependencies: commit hash or revision name?
- Should `trim-paths` in `dev` be possible to enable without breaking incremental compilation?
- How should path dependencies outside the workspace be named when package names collide?
