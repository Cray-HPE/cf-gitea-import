# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.3] - 2022-02-15

### Added

- Push all tags to registry, not just the semver+builddate+sha tag.

## [1.5.2] - 2022-02-08

### Changed

- Use the csm-gitflow-mergeback action instead of defining it in this repo

## [1.5.1] - 2022-02-07

### Changed

- Fix changelog to point to proper repository, github releases @rkleinman-hpe

## [1.5.0] - 2022-02-07

### Changed

- Convert repo to gitflow development process; add GH actions workflows @rkleinman-hpe

## [1.4.64] - 2021-11-19

### Added

- CASMINST-3525: remove branch protections instead of enabling push by @rkleinman-hpe  (CSM 1.0)

## [1.4.54] - 2021-08-25

### Added

- CASMCMS-7443: non-root user for container image (CSM 1.2)

## [1.3.36] - 2021-08-24

### Added

- CASMCMS-7443: non-root user for container image (CSM 1.1)

## [1.2.20] - 2021-11-19

### Added

- CASMINST-3525: remove branch protections instead of enabling push by @rkleinman-hpe  (CSM 1.0)

## [1.2.0] - 2021-02-24

### Added

- CASMCMS-6564: Introduce `CF_IMPORT_PRIVATE_REPO`, all repos set to private by default @rkleinman-hpe

## [1.1.3] - 2021-02-08

### Changed

- CASMCMS-6619: Wait for Gitea to be available before attempting to import to Gitea @rkleinman-hpe

## [1.0.4] - 2020-11-20

### Added

- CASMCMS-6111: Add protection of pristine branches, results output for product catalog @rkleinman-hpe

## [1.0.3] - (no date)

### Changed

- CASMCMS-5896: BUGFIX switch git checkout -b to -B @rkleinman-hpe

## [1.0.2] - 2020-08-18

### Added

- CASMCMS-5795: Add PyYAML @rkleinman-hpe

## [1.0.1] - 2020-09-01

### Added

- CASMCMS-5552: Enable override of version by file; /shared overwrite @rkleinman-hpe

## [1.0.0] - (no date)

### Added

- Initial implementation @rkleinman-hpe

[Unreleased]: https://github.com/Cray-HPE/cf-gitea-import/compare/v1.5.2...HEAD

[1.5.2]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.5.2

[1.5.1]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.5.1

[1.5.0]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.5.0

[1.4.64]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.4.64

[1.4.54]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.4.54

[1.3.36]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.3.36

[1.2.20]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.2.20

[1.2.0]: https://github.com/Cray-HPE/cf-gitea-import/compare/v1.1.3...v1.2.0

[1.1.3]: https://github.com/Cray-HPE/cf-gitea-import/compare/v1.0.4...v1.1.3

[1.0.4]: https://github.com/Cray-HPE/cf-gitea-import/compare/v1.0.3...v1.0.4

[1.0.3]: https://github.com/Cray-HPE/cf-gitea-import/compare/v1.0.2...v1.0.3

[1.0.2]: https://github.com/Cray-HPE/cf-gitea-import/compare/v1.0.1...v1.0.2

[1.0.1]: https://github.com/Cray-HPE/cf-gitea-import/compare/v1.0.0...v1.0.1
