#
# MIT License
#
# (C) Copyright 2020-2023 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# Dockerfile for importing content into gitea instances on Shasta
FROM artifactory.algol60.net/csm-docker/stable/docker.io/library/alpine:3.15 as base
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
# CF_IMPORT_PRIVATE_REPO=true
# CF_IMPORT_GITEA_USER=crayvcs
# CF_IMPORT_GITEA_PASSWORD= (no default)

# Default environment variables, override as needed
ENV CF_IMPORT_CONTENT=/content \
    CF_IMPORT_BASE_BRANCH=semver_previous_if_exists \
    CF_IMPORT_PROTECT_BRANCH=true \
    CF_IMPORT_PRIVATE_REPO=true \
    CF_IMPORT_GITEA_ORG=cray \
    CF_IMPORT_GITEA_USER=crayvcs

RUN mkdir -p /content /shared /results
RUN apk add --upgrade --no-cache apk-tools &&  \
    apk update && \
    apk add --update --no-cache \
    gcc \
    python3-dev \
    libc-dev \
    git \
    python3 \
    py3-requests \
    curl \
    py3-pip && \
    apk -U upgrade --no-cache
ADD requirements.txt constraints.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt && \
    rm -rf requirements.txt constraints.txt && \
    mkdir -p /opt/csm && \
    chown nobody:nobody /opt/csm

# For update-ca-certificates at runtime
RUN chown nobody:nobody /etc/ssl/certs

USER nobody:nobody
RUN mkdir -p ${CF_IMPORT_CONTENT} /opt/csm/cf-gitea-import /results
ADD entrypoint.sh standalone_entrypoint.sh argo_entrypoint.sh import.py /opt/csm/cf-gitea-import/
ENTRYPOINT ["/opt/csm/cf-gitea-import/entrypoint.sh"]
