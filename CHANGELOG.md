# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.11.0] - 2025-02-13

### Dependencies
- Bump `gitpython` from 3.1.40 to 3.1.43 ([#115](https://github.com/Cray-HPE/cf-gitea-import/pull/115), [#116](https://github.com/Cray-HPE/cf-gitea-import/pull/116), [#117](https://github.com/Cray-HPE/cf-gitea-import/pull/117))
- List Python module versions in Dockerfile for the purposes of being logged during builds
- Pin major/minor versions of Python modules but use latest patch version
- Bump `wheel` from <0.41,>=0.40 to >=0.40,<0.46 ([#119](https://github.com/Cray-HPE/cf-gitea-import/pull/119), [#124](https://github.com/Cray-HPE/cf-gitea-import/pull/124))
- Bump `pip` from <23.3,>=23.2.1 to >=23.2.1,<24.4 ([#122](https://github.com/Cray-HPE/cf-gitea-import/pull/122))
- Bump `setuptools` from <68.1,>=68.0 to >=68.0,<75.5 ([#123](https://github.com/Cray-HPE/cf-gitea-import/pull/123), [#125](https://github.com/Cray-HPE/cf-gitea-import/pull/125))
- CASMCMS-9282: Bump Alpine version from 3.15 to 3.18, because 3.15 no longer receives security patches

## [1.10.0] - 2024-01-05

### Changed
- Disabled concurrent Jenkins builds on same branch/commit
- Added build timeout to avoid hung builds

### Dependencies
- Bump `pip` from 23.2 to 23.2.1 ([#93](https://github.com/Cray-HPE/cf-gitea-import/pull/93))
- Bump `actions/checkout` from 3 to 4 ([#96](https://github.com/Cray-HPE/cf-gitea-import/pull/96))
- Bump `gitpython` from 3.1.32 to 3.1.40 ([#97](https://github.com/Cray-HPE/cf-gitea-import/pull/97), [#98](https://github.com/Cray-HPE/cf-gitea-import/pull/98), [#99](https://github.com/Cray-HPE/cf-gitea-import/pull/99), [#101](https://github.com/Cray-HPE/cf-gitea-import/pull/101), [#104](https://github.com/Cray-HPE/cf-gitea-import/pull/104), [#105](https://github.com/Cray-HPE/cf-gitea-import/pull/105))
- Bump `smmap` from 5.0.0 to 5.0.1 ([#100](https://github.com/Cray-HPE/cf-gitea-import/pull/100))
- Bump `stefanzweifel/git-auto-commit-action` from 4 to 5 ([#102](https://github.com/Cray-HPE/cf-gitea-import/pull/102))
- Bump `semver` from 3.0.1 to 3.0.2 ([#103](https://github.com/Cray-HPE/cf-gitea-import/pull/103))
- Bump `gitdb` from 4.0.10 to 4.0.11 ([#106](https://github.com/Cray-HPE/cf-gitea-import/pull/106))

## [1.9.8] - 2024-01-04

### Fixed
- CASMCMS-8885: Fixed bug in semver version sorting

## [1.9.7] - 2023-11-07

### Changed
- CASMTRIAGE-6152: Copy files to target only if files exist in /shared directory.

## [1.9.6] - 2023-07-18

### Dependencies
- Bump `gitpython` from 3.1.31 to 3.1.32 (#88)
- Bump `semver` from 3.0.0 to 3.0.1
- Bump `PyYAML` from 6.0 to 6.0.1
- Pin `pip` version to 23.2
- Pin `setuptools` version to 68.0.0
- Pin `wheel` version to 0.40.0

## [1.9.5] - 2023-05-31

### Changed

- CASM-4231: Improved logging for [`argo_entrypoint.sh`](argo_entrypoint.sh) and [`import.py`](import.py) for use with IUF.

## [1.9.4] - 2023-04-14

### Fixed

- CASMINST-5876: Handle `CF_IMPORT_GITEA_REPO` properly when it is the empty string
- CASMINST-5843: Fixing permissions for certs directory for nobody user

## [1.9.3] - 2023-04-14

### Changed

- dependabot: Bump `semver` from 2.13.0 to 3.0.0
- CASMCMS-8540: Switch to CSM-curated alpine base image to resolve security vulnerabilities.

## [1.9.2] - 2023-04-11

### Changed

- dependabot: Bump `gitpython` from 3.1.27 to 3.1.31
- dependabot: Bump `gitdb` from 4.0.9 to 4.0.10
- dependabot: Bump `smmap` from 3.0.1 to 5.0.0

## [1.9.1] - 2023-02-10

### Fixed

- CASMINST-5954: Handle `git rm -rf *` gracefully for empty branch scenarios

## [1.9.0] - 2023-02-01

### Fixed

- CASMINST-5876: Handle `CF_IMPORT_GITEA_REPO` properly when it is the empty string
- CASMINST-5843: Fixing permissions for certs directory for nobody user

## [1.8.1] - 2023-01-30

### Changed

- CASMINST-5866: Adjust log levels for IUF CLI handling
- CASMINST-5866: Handle and skip non-semver branch names gracefully

## [1.8.0] - 2023-01-19

### Added

- Authentication to Artifactory

### Changed

- CASMCMS-8306: Integration IUF changes includes ignoring file read permissions during file uploads to gitea.
- Reformatting code using Black.
- Spelling corrections.
- CASMCMS-8237: Reverting from Github workflow actions back to Jenkins for image publishing
- Removal of istio sidecar check in argo_entrypoint.sh start, required for argo IUF development.
  This will keep the original behavior of entrypoint for backwards compatibility. Argo will override
  upon launch to use the argo_entrypoint.sh.

## [1.7.0] - 2022-08-08

### Fixed

- CRAYSAT-1512: Fixed a bug in which the VCS API URL was not formed correctly
  when the base URL contained path components in it.

### Added

- CRAYSAT-1512: Add an alternate entrypoint so that cf-gitea-import can be
  run directly without waiting on the envoy proxy.

## [1.6.2] - 2022-04-23

### Changed

- CASMINST-4500: Fix git workdir for changes to git behavior as part of fixing
  [a security vulnerability](https://github.blog/2022-04-12-git-security-vulnerability-announced/).

## [1.6.1] - 2022-03-23

### Added

- CASMCMS-7309: Add the 500 status code to the list of http codes to retry

- Update license text to comply with automatic license-check tool.

## [1.6.0] - 2022-03-08

### Added

- Handle repeated import attempts gracefully when the product version has not
  changed. Introduce `CF_IMPORT_FORCE_EXISTING_BRANCH` parameter (default false) to
  allow override of this behavior.

- Add test capabilities to bring up Gitea instance for manual testing. See
  `test/test_force_existing_branch.sh` for an example.

## [1.5.7] - 2022-03-04

### Changed

- Use github public ubuntu runner instead of self-hosted on public repos.

## [1.5.6] - 2022-03-03

### Changed

- Provide docker meta tags for major, major.minor, and major.minor.patch versions

## [1.5.5] - 2022-03-03

### Changed

- Update Dockerfile to use alpine:3.15 for CVE remediation.

## [1.5.4] - 2022-03-01

### Changed

- Update the image signing and software bill of materials github actions (Cray
  HPE internal actions) to use the preferred GCP authentication. The workflows
  in this repo already use a floating version, but workflow permissions need
  to be updated to allow for the new signing actions to work.

- [dependabot] Bump actions/checkout from 2 to 3

- [dependabot] Bump ffurrer2/extract-release-notes from 1.11.0 to 1.12.0

- [dependabot] Bump gitpython from 3.1.26 to 3.1.27

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

[Unreleased]: https://github.com/Cray-HPE/cf-gitea-import/compare/v1.11.0...HEAD

[1.11.0]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.11.0

[1.10.0]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.10.0

[1.9.8]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.8

[1.9.7]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.7

[1.9.6]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.6

[1.9.5]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.5

[1.9.4]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.4

[1.9.3]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.3

[1.9.2]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.2

[1.9.1]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.1

[1.9.0]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.9.0

[1.8.1]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.8.1

[1.8.0]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.8.0

[1.7.0]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.7.0

[1.6.2]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.6.2

[1.6.1]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.6.1

[1.6.0]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.6.0

[1.5.7]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.5.7

[1.5.6]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.5.6

[1.5.5]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.5.5

[1.5.4]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.5.4

[1.5.3]: https://github.com/Cray-HPE/cf-gitea-import/releases/tag/v1.5.3

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