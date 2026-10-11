- Feature Name: `trim-paths`
- Start Date: 2021-05-24
- RFC PR: rust-lang/rfcs#3127
- Rust Issue: rust-lang/rust#111540, rust-lang/cargo#12137

# Summary

Add a Cargo profile setting, `trim-paths`, that sanitises absolute host paths introduced during compilation which would otherwise end up embedded in the compiled executable or library. With the default `release` profile, `cargo build` should no longer write any host-filesystem-dependent path into the output binary. Paths are still kept in a separate debug information file when one exists, so that debuggers and profilers can find source files.

To support this, add a `--remap-path-scope` flag to `rustc` that controls where `--remap-path-prefix` applies: in macro expansion, in debug information, in diagnostics, or some combination.

# Motivation

Rust binaries routinely contain absolute paths from the machine that built them. They come from several places:

- `file!()`, `panic!()` and `#[track_caller]` locations embed the path of the source file as a string in the binary.
- Debug information records the compilation directory and the paths of every source file.
- Dependencies built from the Cargo registry live under `$CARGO_HOME/registry/src/<index>-<hash>/`, which usually includes the user's home directory, for example `/home/alice/.cargo/registry/src/...`.

This causes three problems.

**Privacy.** A release binary reveals the builder's username and directory layout. People distributing software are often surprised to find their home directory in a published executable.

**Reproducibility.** Two builds of the same source in different directories produce different binaries. Reproducible builds are increasingly expected for security audits and supply-chain verification. Today achieving them requires manually passing `--remap-path-prefix` through `RUSTFLAGS`, which is error-prone and invalidates Cargo's build cache when changed.

**Size.** Long absolute paths, repeated in panic locations across many crates, add up.

`rustc` already offers `--remap-path-prefix FROM=TO`, but it is all or nothing: it rewrites paths everywhere, including in compiler diagnostics and in split debug info. Users who want clean binaries but still want clickable error messages in their terminal and working debuggers cannot get both. Cargo does not expose any way to set it per profile.

# Guide-level explanation

Add to a profile in `Cargo.toml`:

```toml
[profile.release]
trim-paths = true
```

With this setting, paths in the compiled output are rewritten:

- Paths to files in the current workspace become relative to the workspace root, for example `src/main.rs`.
- Paths to dependencies from a registry or git become `<crate-name>-<version>/src/lib.rs`.
- The path to the Rust standard library sources becomes `/rustc/<commit-hash>/library/...`, which is already the convention for the precompiled standard library.

Diagnostics printed during the build are not affected; error messages still show real paths so that editors and terminals can jump to them.

`trim-paths` accepts finer-grained values:

```toml
trim-paths = "none"           # do not trim (default for dev)
trim-paths = "object"         # trim in the binary and in split debuginfo
trim-paths = ["macro"]        # trim only in file!() and panic locations
trim-paths = ["macro", "split-debuginfo-path"]
trim-paths = "all"            # trim everywhere, including diagnostics
```

The default for the `release` profile becomes `"object"` in the next edition, applied when debug info is split into a separate file, and `"macro"` otherwise. The default for `dev` is `"none"`.

You can override it from the command line as with any profile setting:

```
cargo build --release --config 'profile.release.trim-paths="none"'
```

# Reference-level explanation

## rustc: `--remap-path-scope`

A new flag `--remap-path-scope=<scopes>` takes a comma-separated list of:

- `macro`: paths produced by `file!()`, `panic!` locations and `Location::caller()`.
- `diagnostics`: paths in compiler warnings and errors.
- `unsplit-debuginfo`: paths in debug information embedded in the binary.
- `split-debuginfo`: paths in debug information written to a separate file (`.dwo`, `.dwp`, `.pdb`, `.dSYM`).
- `split-debuginfo-path`: the path the binary records to locate its split debug information file.
- `object`: shorthand for `macro,unsplit-debuginfo,split-debuginfo-path`.
- `all`: all of the above.

`--remap-path-prefix` mappings are applied only in the selected scopes. If `--remap-path-scope` is not given, the default is `all`, preserving current behaviour.

## Cargo mapping

When `trim-paths` is anything other than `"none"`, Cargo passes:

- `--remap-path-prefix=<workspace-root>=` so workspace paths become relative.
- `--remap-path-prefix=<cargo-home>/registry/src/<index>/=` for registry crates, giving `<name>-<version>/...`.
- `--remap-path-prefix=<cargo-home>/git/checkouts/<repo>/<rev>/=<name>-<version>` for git dependencies.
- `--remap-path-prefix=<sysroot>/lib/rustlib/src/rust=/rustc/<hash>` for the standard library source, if the `rust-src` component is installed.
- `--remap-path-scope=<value>` corresponding to the profile setting.

Cargo also sets the working directory recorded in debug information to a fixed value when trimming, and stops passing absolute paths as the input file to `rustc` for workspace members.

Changing `trim-paths` changes the profile's fingerprint, so builds with different settings are cached separately rather than invalidating each other.

## Debuggers

Debuggers locate sources using the recorded paths. With trimmed paths, a debugger run from the workspace root will find workspace files, and `/rustc/<hash>` paths can be mapped with the debugger's source-map feature. Cargo can emit a hint file with the necessary mappings. When debug info is split and the `split-debuginfo` scope is not selected, the separate file keeps absolute paths and debugging works without configuration.

## Interaction with `RUSTFLAGS`

User-supplied `--remap-path-prefix` flags in `RUSTFLAGS` are passed after Cargo's own, so they take precedence for overlapping prefixes.

# Drawbacks

- Trimmed paths make some debugging workflows harder when debug info is embedded, since tools will not find sources without extra configuration.
- Panic messages show shorter relative paths, which some users may find less helpful when running a binary outside the workspace.
- The scope list is fairly fine-grained and adds concepts to `rustc`'s interface.
- Changing the release default changes behaviour, which is why it is tied to an edition.

# Rationale and alternatives

- **Document `RUSTFLAGS`.** This is the status quo. It is hard to get right, changes cache keys for all crates, and cannot keep diagnostics readable.
- **Trim unconditionally in release.** Simpler, but breaks debugging for users who embed debug info.
- **Strip strings after linking.** Post-processing cannot change the length of strings safely and does not handle all formats.

# Prior art

GCC and Clang provide `-ffile-prefix-map`, `-fdebug-prefix-map` and `-fmacro-prefix-map`, which separate macro and debug scopes in a similar way. Go's `-trimpath` flag removes file system paths from compiled executables and is widely used for reproducible builds.

# Unresolved questions

- Should `trim-paths` also affect `env!("CARGO_MANIFEST_DIR")` and build script outputs?
- What is the best way to ship source-path mapping hints for debuggers on each platform?
