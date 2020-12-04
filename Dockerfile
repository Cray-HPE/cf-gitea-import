# Dockerfile for importing content into gitea instances on Shasta
# Copyright 2020 Hewlett Packard Enterprise Development LP
FROM dtr.dev.cray.com/baseos/alpine:3.12.0
WORKDIR /

# Supported Environment Variables (see README in this repository)
# CF_IMPORT_PRODUCT_NAME= (no default)
# CF_IMPORT_PRODUCT_VERSION= (no default)
# CF_IMPORT_CONTENT=/content
# CF_IMPORT_BASE_BRANCH=semver_previous_if_exists
# CF_IMPORT_PROTECT_BRANCH=true
# CF_IMPORT_GITEA_URL= (no default)
# CF_IMPORT_GITEA_ORG=cray
# CF_IMPORT_GITEA_REPO=<CF_IMPORT_PRODUCT_NAME>-config-management
# CF_IMPORT_GITEA_USER=crayvcs
# CF_IMPORT_GITEA_PASSWORD= (no default)

# Default environment variables, override as needed
ENV CF_IMPORT_CONTENT=/content \
    CF_IMPORT_BASE_BRANCH=semver_previous_if_exists \
    CF_IMPORT_PROTECT_BRANCH=true \
    CF_IMPORT_GITEA_ORG=cray \
    CF_IMPORT_GITEA_USER=crayvcs

RUN mkdir -p /content /shared /results
RUN apk update && \
    apk add --update --no-cache git python3 py3-requests curl py3-pip
ADD entrypoint.sh requirements.txt constraints.txt import.py ./
RUN PIP_INDEX_URL=https://arti.dev.cray.com:443/artifactory/api/pypi/pypi-remote/simple \
    pip install --no-cache-dir -r requirements.txt
ENTRYPOINT ["/entrypoint.sh"]

