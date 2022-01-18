# cf-gitea-import

`cf-gitea-import` is a base image that can be used by product teams to import
their configuration content (Ansible plays and roles for use with CFS) into
a Gitea repository running on a Cray Shasta EX-1 system installed with CSM.

Users should provide a Dockerfile that installs their content (via RPMs or
however their content is packaged) and then use this base image to take
advantage of the import script to put it in Gitea. The resulting image
can be used in a Helm Chart/Kubernetes job to install and/or upgrade the
content for the system.

## Base Image

The `cf-gitea-import` base Docker image is built with Alpine Linux and includes
the dependencies required for the import script, namely python3, py3-requests,
and git. A few Python packages not in the Alpine distro are installed via the
included `requirements.txt` file in this repo.

## How This Works

For content that is managed by Git and stored in Gitea on EX-1 systems,
initial installation and upgrades of the content need to be handled carefully.
Shasta product content (like COS, CSM, Analytics, etc) needs to be refreshed
from time to time in such a way that new content can come in and not conflict
with changes made by the site admin.

Therefore, Shasta content will be pushed to "pristine" branches and protected
against further modification. This will allow HPE to update its products and
will allow the customer to modify the content in the git repository by using
their own site-defined git workflow, whether merging, rebasing or otherwise.
The diagram below describes the branch structure in each product's git
repository.

![Product Content Git Workflow](branch_workflow.png "Product Content Git Workflow")

`cf-gitea-import` comes into play by being the mechanism that takes the product
content from Shasta build sources and imports it in the git repository.
Product content must be versioned with a [SemVer version](https://semver.org).
The `cf-gitea-import` utility assumes this fundamentally.

Furthermore, when a new version of a product is being imported, the utility has
the ability to find the previous semantic version and base the new content on
that pristine branch (see the `CF_IMPORT_BASE_BRANCH` =
`semver_previous_if_exists` environment variable). This is the default and will
rarely be changed under normal circumstances. If no base branch exists, the
default branch of the repository is used. 

For this to work, `cf-gitea-import` also assumes the format of the pristine
branches to be:

```text
<gitea organization> / <product name> / <product (semantic) version>
```

## Example `DockerFile`

The example Dockerfile below shows how RPM content can be installed into an
image layer and then used with the cf-gitea-import image. This specific example
is for CLE content built on SLES SP1, version 1.3.0 from master repositories.

```Dockerfile
# Dockerfile for importing content into gitea instances on Shasta
FROM artifactory.algol60.net/registry.suse.com/suse/sle15:15.3 as product-content-base
WORKDIR /
ARG SLES_MIRROR=https://slemaster.us.cray.com/SUSE
ARG ARCH=x86_64
RUN \
  zypper --non-interactive rr --all &&\
  zypper --non-interactive ar ${SLES_MIRROR}/Products/SLE-Module-Basesystem/15-SP3/${ARCH}/product/ sles15sp3-Module-Basesystem-product &&\
  zypper --non-interactive ar ${SLES_MIRROR}/Updates/SLE-Module-Basesystem/15-SP3/${ARCH}/update/ sles15sp3-Module-Basesystem-update &&\
  zypper --non-interactive clean &&\
  zypper --non-interactive --gpg-auto-import-keys refresh
RUN zypper in -f --no-confirm <YOUR DEPENDENCIES>


# Use the cf-gitea-import as a base image with CLE content copied in
FROM artifactory.algol60.net/csm-docker/stable/cf-gitea-import:latest as cf-gitea-import-base
USER nobody:nobody
WORKDIR /
ENV CF_IMPORT_PRODUCT_NAME=<your product name>

# Use a version file if not using an environment variable, see CF_IMPORT_PRODUCT_VERSION
ADD .version /product_version

# Copy in dependencies' Ansible content
COPY --chown=nobody:nobody --from=product-content-base /opt/cray/ansible/roles/      /content/roles/

# Copy in local repository Ansible content
COPY --chown=nobody:nobody ansible/ /content/

# Base image entrypoint takes it from here
```

Build this Docker image with the following command:

```bash
$ docker build -t <registry>/<project>/<product>-config-import:<product-version> .
...
Successfully built b278021cbd56
Successfully tagged <registry>/<project>/<product>-config-import:<product-version>
```

## Example Usage (Kubernetes Job)

Using the content image based on the `cf-gitea-import` image above, a Kubernetes
job to use the it is provided below. This job would likely be incorporated into
a Helm Chart. This `Job` assumes the image will be used on an EX-1 system with a
working Gitea installation in the services namespace via CSM.

See the example for the CSM configuration content itself [here](https://github.com/Cray-HPE/csm-config/tree/master/kubernetes/csm-config).

## `cray-import-config` Helm Base Chart

Note that a Helm base chart has also been created to run Jobs like the example
above and adds functionality such as the ability to run initContainers and
other containers alongside the main cf-gitea-import container. See the
[cray-product-install-charts cray-import-config chart](https://github.com/Cray-HPE/cray-product-install-charts/tree/master/charts/cray-import-config)
for more information on the base chart and [the csm-config chart](https://github.com/Cray-HPE/csm-config/tree/master/kubernetes/csm-config)
for an example of how the base chart is used.

## Environment Variables

All configuration options to the cf-gitea-import utility are provided as
environment variables. Some of these vary based on the product and its version
and can be specified in the product's Docker image (see example Dockerfile
above), and some of them will need to be specified on the system where the image
is running since they are environment specific (in the helm chart `values.yaml`
file).

### Product Environment Variables

* `CF_IMPORT_PRODUCT_NAME` = (no default)

> The name of the product that is being imported

* `CF_IMPORT_PRODUCT_VERSION` = (no default)

> The SemVer version of the product that is being imported, e.g. `1.2.3`. This
> can be overridden with a file located at `/product_version`, which takes priority.

* `CF_IMPORT_CONTENT`=  `/content`

> The filesystem location of the content that will be imported. When using
  `cf-gitea-import` as a base docker image, ensure that you put the importable
  content in this directory.

### Branching Environment Variables

* `CF_IMPORT_BASE_BRANCH` = `semver_previous_if_exists`

> Branch in the git repository that will serve as the base branch to the
  branch that will be created. Takes a branch name or the special value
  `semver_previous_if_exists` which will search the repository for a
  branch of the same format as the `CF_IMPORT_TARGET_BRANCH` for a version
  that is immediately previous in SemVer semantics. If nothing is
  provided, the repository default branch will be assumed.

* `CF_IMPORT_PROTECT_BRANCH` = `true`

> Protect the branch from modification in Gitea after it has been pushed to
  the repository using the Gitea REST API. This should probably always be true.
  
### Gitea Environment Variables

* `CF_IMPORT_GITEA_URL` = (no default)

> Base URL to Gitea such that the Gitea REST API exists at
  `CF_IMPORT_GITEA_URL` + `'/api/v1'`. This should be overridden when the image
  is used on a system or in development since it will be different for every
  environment.

* `CF_IMPORT_GITEA_ORG` = `cray`

> Gitea Organization where the `CF_IMPORT_GITEA_REPO` is/will be located

* `CF_IMPORT_GITEA_REPO` = <`CF_IMPORT_PRODUCT_NAME`>-config-management

> Gitea repository where the content will be imported.

* `CF_IMPORT_PRIVATE_REPO` = `true`

> The privacy of the Gitea repository, set to private by default so credentials
  are necessary to clone, commit, and push. This should be set to `true` for
  almost all repositories, especially those provided by Cray products.

* `CF_IMPORT_GITEA_USER` = `crayvcs`

> Gitea REST API user with sufficient permissions

* `CF_IMPORT_GITEA_PASSWORD` = (no default)

> Password for the `CF_IMPORT_GITEA_USER`. This should be overridden when the
  image is used on the system or in development since it will be different for
  every environment and NOT in a Docker image build.

## Overwriting Configuration Content

Files placed in `/shared` in this container are copied recursively into
`$CF_IMPORT_CONTENT` before the git import process starts. This allows
for Helm charts to run initContainers that can add or modify the content
before it is imported if that use case is necessary.

## Reporting Results

As of version 1.0.4, the import script will write a YAML file with the
record of what was imported to `/results/records.yaml`. The contents
are as follows:

```yaml
configuration:
  clone_url: https://vcs.system.dev.cray.com/vcs/cray/uan-config-management.git
  commit: 59dd762e08b3cf310183befe4007b30e42dc1cf0
  import_branch: cray/<product>/<product-version>
  ssh_url: git@vcs.system.dev.cray.com:cray/<product>-config-management.git
```

This information is typically used to populate the [cray-product-catalog](https://github.com/Cray-HPE/cray-product-catalog).

## Build Helpers
This repo uses some build helpers from the 
[cms-meta-tools](https://github.com/Cray-HPE/cms-meta-tools) repo. See that repo for more details.

## Local Builds
If you wish to perform a local build, you will first need to clone or copy the contents of the
cms-meta-tools repo to `./cms_meta_tools` in the same directory as the `Makefile`. When building
on github, the cloneCMSMetaTools() function clones the cms-meta-tools repo into that directory.

For a local build, you will also need to manually write the .version, .docker_version (if this repo
builds a docker image), and .chart_version (if this repo builds a helm chart) files. When building
on github, this is done by the setVersionFiles() function.

## Versioning
The version of this repo is generated dynamically at build time by running the version.py script in 
cms-meta-tools. The version is included near the very beginning of the github build output. 

In order to make it easier to go from an artifact back to the source code that produced that artifact,
a text file named gitInfo.txt is added to Docker images built from this repo. For Docker images,
it can be found in the / folder. This file contains the branch from which it was built and the most
recent commits to that branch. 

For helm charts, a few annotation metadata fields are appended which contain similar information.

For RPMs, a changelog entry is added with similar information.

## New Release Branches
When making a new release branch:
    * Be sure to set the `.x` and `.y` files to the desired major and minor version number for this repo for this release. 
    * If an `update_external_versions.conf` file exists in this repo, be sure to update that as well, if needed.

## Contributing

[Code owners](https://github.com/Cray-HPE/cf-gitea-import/blob/master/.github/CODEOWNERS): make a branch. Others, make a fork.

## Blamelog
* _1.2.0_ - CASMCMS-6564: Introduce `CF_IMPORT_PRIVATE_REPO`, all repos set to private by default - Randy Kleinman (randy.kleinman@hpe.com)
* _1.1.3_ - CASMCMS-6619: Wait for Gitea to be available before attempting to import to Gitea - Randy Kleinman (randy.kleinman@hpe.com)
* _1.0.4_ - CASMCMS-6111: Add protection of pristine branches, results output for product catalog - Randy Kleinman (randy.kleinman@hpe.com)
* _1.0.3_ - CASMCMS-5896: BUGFIX switch git checkout -b to -B - Randy Kleinman (randy.kleinman@hpe.com)
* _1.0.2_ - CASMCMS-5795: Add PyYAML - Randy Kleinman (randy.kleinman@hpe.com)
* _1.0.1_ - CASMCMS-5552: Enable override of version by file; /shared overwrite - Randy Kleinman (randy.kleinman@hpe.com)
* _1.0.0_ - initial implementation - Randy Kleinman (randy.kleinman@hpe.com)

## Built on

* Alpine Linux
* Python 3
* Python Requests
* GitPython
* SemVer
* Docker
* Good intentions

## Copyright and License

This project is copyrighted by Hewlett Packard Enterprise Development LP and is under the MIT
license. See the [LICENSE](LICENSE) file for details.

When making any modifications to a file that has a Cray/HPE copyright header, that header
must be updated to include the current year.

When creating any new files in this repo, if they contain source code, they must have
the HPE copyright and license text in their header, unless the file is covered under
someone else's copyright/license (in which case that should be in the header). For this
purpose, source code files include Dockerfiles, Ansible files, and shell scripts. It does
**not** include Jenkinsfiles or READMEs.

When in doubt, provided the file is not covered under someone else's copyright or license, then
it does not hurt to add ours to the header.
