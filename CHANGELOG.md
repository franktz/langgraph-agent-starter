# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [0.1.1] - 2026-03-15

### Changed

- Upgraded `dynamic-config-nacos` from `0.1.0` to `0.1.1`.
- Pinned `nacos-sdk-python` to `2.0.11` to align the runtime with the expected `sdk_v2` import path.

### Fixed

- Improved Nacos startup compatibility for local Windows development by avoiding the `nacos-sdk-python 3.x` import mismatch (`import nacos` vs `v2.nacos`).
- Kept the package metadata and lockfile aligned for the `0.1.1` release.
