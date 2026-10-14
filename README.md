<img src="https://github.com/opa334/Dopamine/assets/52459150/ed04dd3e-d879-456d-9aa3-d4ed44819c7e" width="64" />

# Synapse JB

A fork of [Dopamine](https://github.com/opa334/Dopamine) 3.0.11 — a rootless
semi-untethered jailbreak for iOS 15.0 - 17.3.1 (arm64e), iOS 15.0 - 18.7.1,
26.0 - 26.0.1 (A12/A13) and iOS 15.0 - 18.7.1 (arm64).

This fork changes the bundle identity and the artwork. Nothing in the jailbreak
mechanism itself has been touched.

| | Upstream | This fork |
|---|---|---|
| Bundle ID | `com.opa334.Dopamine` | `com.synapse.jb` |
| Display name | Dopamine | Synapse JB |
| Artwork | upstream icons | `branding/` |

## Build

Requires macOS with Xcode. There is no Windows or Linux path — the build uses
`xcodebuild`, `actool` and a Theos-provided iOS SDK.

### GitHub Actions

`.github/workflows/main.yml` builds on `macos-latest` and uploads
`Application/Dopamine.ipa` and `Application/Dopamine.tipa` as the `SynapseJB`
artifact. Push to any branch, or run it manually from the Actions tab.

Submodules are fetched recursively, so a plain clone is enough.

```sh
git clone --recurse-submodules <your fork url>
```

If you cloned without `--recurse-submodules`, run:

```sh
git submodule update --init --recursive
```

### Locally

```sh
brew install make libarchive
make -j$(sysctl -n hw.logicalcpu)
```

The tips need `ldid`, `findutils`, `sed`, `coreutils` and Theos with an iOS
SDK. `make update` then ships the result to a device already running a
jailbreak:

```sh
make update DEVICE=<ip>
```

## Artwork

See [`branding/README.md`](branding/README.md). Put masters in `branding/`,
run `python tools/generate_icons.py`, commit the result.

## Upstream

Please do not file version-support issues here. They belong upstream:
https://github.com/opa334/Dopamine

## License

MIT, same as upstream. Copyright (c) 2023-2024 Lars Fröder (opa334) — see
[LICENSE.md](LICENSE.md).
