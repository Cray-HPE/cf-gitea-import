# cf-gitea-import

This is a base image that can be used by product teams to import their content
(usually Ansible plays and roles for use with CFS) into a Gitea repository
running on a Shasta EX-1 system.

Users should provide a Dockerfile that installs their content (via RPMs or
however their content is packaged) and then use this base image to take
advantage of the import script to put it in Gitea. The resulting image
can be used in a Helm Chart/Kubernetes job to install and/or upgrade the content
for the system.

## Base Image

The cf-gitea-import base Docker image is built with Alpine Linux and includes
the dependencies required for the import script, namely python3, py3-requests,
and git. A few Python packages not in the Alpine distro are installed via the
included `requirements.txt` file in this repo.

## How This Works

For content that is managed by Git and stored in Gitea on Shasta systems,
initial installation and upgrades of the content need to be handled carefully.
Shasta product content (like COS, NCNs, Analytics, etc) needs to be refreshed
from time to time in such a way that new content can come in and not conflict
with changes made by the site admin.

Therefore, Shasta content will be pushed to "pristine" branches and protected
against further modification. This will allow HPE to update its products and
will allow the customer to modify the content in the git repository by using
their own site-defined git workflow, whether merging, rebasing or otherwise.
The diagram below describes the branch structure in each product's git
repository.

![Product Content Git Workflow](branch_workflow.png "Product Content Git Workflow")

`cf-gitea-import` comes into play by being the mechanism that takes the pristine
content from Shasta build sources and imports it in the git repository.
Product content must be versioned with a [SemVer version](https://semver.org).
The `cf-gitea-import` utility assumes this fundamentally.

Furthermore, when a new version of a product is being imported, the utility has
the ability to find the previous semantic version and base the new content on
that pristine branch (see the `CF_IMPORT_BASE_BRANCH` =
`semver_previous_if_exists` environment variable). If none exists, the base
branch of the repository is used. This is the default and will rarely be
changed under normal circumstances.

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
FROM dtr.dev.cray.com/baseos/sles15sp1 as product-content-base
WORKDIR /
RUN zypper ar --no-gpgcheck http://car.dev.cray.com/artifactory/shasta-premium/SHASTA-OS/sle15_sp1_ncn/x86_64/dev/master shasta-os && \
    zypper ar --no-gpgcheck http://car.dev.cray.com/artifactory/shasta-premium/SCMS/sle15_sp1_ncn/x86_64/dev/master      shasta-scms && \
    zypper ar --no-gpgcheck http://car.dev.cray.com/artifactory/sma/CAR/sle15_sp1_ncn/x86_64/dev/master                  shasta-sma && \
    zypper ar --no-gpgcheck http://car.dev.cray.com/artifactory/shasta-premium/NWMGMT/sle15_sp1_ncn/x86_64/dev/master    shasta-ncmp && \
    zypper ar --no-gpgcheck http://car.dev.cray.com/artifactory/shasta-premium/CRAYCTL/sle15_sp1_ncn/x86_64/dev/master   shasta-dst && \
    zypper refresh
RUN zypper in -y cme-premium-cf-crayctldeploy-site

# Use the cf-gitea-import as a base image with CLE content copied in
FROM dtr.dev.cray.com/cray/cf-gitea-import:latest
WORKDIR /
#ADD .version /product_version  # Use this if your version exists in a file instead of setting an env var
COPY --from=product-content-base /opt/cray/crayctl/configuration_framework/cme-premium/1.3.0/ /content/
ENV CF_IMPORT_PRODUCT_NAME=cle \
    CF_IMPORT_PRODUCT_VERSION=1.3.0
```

Build this Docker image with the following command:

```bash
$ docker build -t dtr.dev.cray.com/cray/cle-config-import:1.3.0 .
...
Successfully built b278021cbd56
Successfully tagged dtr.dev.cray.com/cray/cle-config-import:1.3.0
```

## Example Usage (Kubernetes Job)

Using the content image based on the cf-gitea-import image above, a Kubernetes
job to use the it is provided below. This job would likely be incorporated into
a Helm Chart. This Job assumes the image will be used on a Shasta system with a
working Gitea installation in the services namespace.

```yaml
---
apiVersion: batch/v1
kind: Job
metadata:
  name: cle-config-import-1.3.0
  namespace: services
spec:
  template:
    spec:
      containers:
      - env:
        - name: CF_IMPORT_GITEA_URL
          value: http://gitea-vcs
        - name: CF_IMPORT_GITEA_ORG
          value: cray
        - name: CF_IMPORT_BASE_BRANCH
          value: semver_previous_if_exists
        - name: CF_IMPORT_GITEA_USER
          valueFrom:
            secretKeyRef:
              name: vcs-user-credentials
              key: vcs_username
        - name: CF_IMPORT_GITEA_PASSWORD
          valueFrom:
            secretKeyRef:
              name: vcs-user-credentials
              key: vcs_password
        image: dtr.dev.cray.com/cray/cle-config-import:1.3.0
        imagePullPolicy: Always
        name: content-import
        resources:
          limits:
            cpu: "2"
            memory: 256Mi
          requests:
            cpu: 100m
            memory: 64Mi
```

Note that a Helm base chart has also been created to run Jobs like the example
above and adds functionality such as the ability to run initContainers and
other containers alongside the main cf-gitea-import container. See the
[SCMS/cray-product-install-charts cray-import-config chart](https://stash.us.cray.com/projects/SCMS/repos/cray-product-install-charts/browse/charts/cray-import-config)
for more information on the base chart and [SCMS/uan Helm Chart](https://stash.us.cray.com/projects/SCMS/repos/uan/browse/kubernetes/cray-uan-config)
for an example of how the base chart is used.

## Environment Variables

All configuration options to the cf-gitea-import utility are provided as
environment variables. Some of these vary based on the product and its version
and can be specified in the product's Docker image (see example Dockerfile
above), and some of them will need to be specified on the system where the image
is running since they are environment specific.

### Product Environment Variables

* `CF_IMPORT_PRODUCT_NAME` = (no default)

> The name of the Cray/Shasta product that is being imported

* `CF_IMPORT_PRODUCT_VERSION` = (no default)

> The SemVer version of the Cray/Shasta product that is being imported, e.g. `1.2.3`. This can be overridden with a file located at `/product_version`.

* `CF_IMPORT_CONTENT`=  `/content`

> The filesystem location of the content that will be imported. When using
  cf-gitea-import as a base docker image, ensure that you put the importable
  content in this directory.

### Branching Environment Variables

* `CF_IMPORT_BASE_BRANCH` = `semver_previous_if_exists`

> Branch in the git repository that will serve as the base branch to the
  branch that will be created. Takes a branch name or the special value
  `semver_previous_if_exists` which will search the repository for a
  branch of the same format as the `CF_IMPORT_TARGET_BRANCH` for a version
  that is immediately previous in SemVer semantics. If nothing is
  provided, the gitea repository default branch will be assumed.

* `CF_IMPORT_PROTECT_BRANCH` = `true`

> Protect the branch from modification in Gitea after it has been pushed to
  the repository using the Gitea REST API. This should probably always be true,
  but as of this writing Gitea only supports this via the UI. In version 1.12.0,
  Gitea will allow for this via the REST API.
  
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
  clone_url: https://vcs.thanos.dev.cray.com/vcs/cray/uan-config-management.git
  commit: 59dd762e08b3cf310183befe4007b30e42dc1cf0
  import_branch: cray/uan/2.0.0
  ssh_url: git@vcs.thanos.dev.cray.com:cray/uan-config-management.git
```

This information is typically used to populate the cray-product-catalog
(see https://stash.us.cray.com/projects/SCMS/repos/cray-product-install-charts/browse/charts/cray-product-catalog).

## Versioning

`cf-gitea-import` itself uses SemVer, go figure.

## Contributing

CMS folks, make a branch. Others, make a fork.

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

## License

Copyright 2020-2021 Hewlett Packard Enterprise Development LP
