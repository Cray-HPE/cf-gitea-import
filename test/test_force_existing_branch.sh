#!/usr/bin/env bash
#
# MIT License
#
# (C) Copyright 2021-2023 Hewlett Packard Enterprise Development LP
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
#

# Go build a test image first, provide the name here
TEST_IMAGE=cf-gitea-import:dev
ENGINE=docker

# Cleanup previous tests, add some files to the imported content
rm -r `pwd`/content
rm -r `pwd`/test-results
mkdir -p `pwd`/content `pwd`/test-results
cp -r `pwd`/base_content/* `pwd`/content/

# Run ./setup_gitea.sh first to setup a Gitea instance and export env vars!
# Kill any other gitea's running first
$ENGINE ps --filter name="gitea-*" --filter status=running -aq | xargs $ENGINE kill
source `pwd`/setup_gitea.sh
source CF_GITEA_IMPORT.*.env
echo "Gitea User: ${CF_IMPORT_GITEA_USER}"
echo "Gitea Password: ${CF_IMPORT_GITEA_PASSWORD}"
sleep 5

# Setup some initial conditions

## Run the container, create version 1.2.3
$ENGINE run --rm -v `pwd`/content:/content:ro \
    -v `pwd`/test-results:/results \
    -e CF_IMPORT_PRODUCT_NAME=test \
    -e CF_IMPORT_PRODUCT_VERSION=1.2.3 \
    -e CF_IMPORT_GITEA_USER=${CF_IMPORT_GITEA_USER} \
    -e CF_IMPORT_GITEA_PASSWORD=${CF_IMPORT_GITEA_PASSWORD} \
    -e CF_IMPORT_GITEA_URL=${CF_IMPORT_GITEA_URL} \
    --network="host" \
    --entrypoint python3 \
    ${TEST_IMAGE} \
    /opt/csm/cf-gitea-import/import.py

## Run the container, create version 1.2.4 based on 1.2.3
touch `pwd`/content/test_File_1.2.4
$ENGINE run --rm -v `pwd`/content:/content:ro \
    -v `pwd`/test-results:/results \
    -e CF_IMPORT_PRODUCT_NAME=test \
    -e CF_IMPORT_PRODUCT_VERSION=1.2.4 \
    -e CF_IMPORT_GITEA_USER=${CF_IMPORT_GITEA_USER} \
    -e CF_IMPORT_GITEA_PASSWORD=${CF_IMPORT_GITEA_PASSWORD} \
    -e CF_IMPORT_GITEA_URL=${CF_IMPORT_GITEA_URL} \
    --network="host" \
    --entrypoint python3 \
    ${TEST_IMAGE} \
    /opt/csm/cf-gitea-import/import.py

## Run the container, try to create version 1.2.4 again, don't force it
## Should be no change to the 1.2.4 branch
$ENGINE run --rm -v `pwd`/content:/content:ro \
    -v `pwd`/test-results:/results \
    -e CF_IMPORT_PRODUCT_NAME=test \
    -e CF_IMPORT_PRODUCT_VERSION=1.2.4 \
    -e CF_IMPORT_GITEA_USER=${CF_IMPORT_GITEA_USER} \
    -e CF_IMPORT_GITEA_PASSWORD=${CF_IMPORT_GITEA_PASSWORD} \
    -e CF_IMPORT_GITEA_URL=${CF_IMPORT_GITEA_URL} \
    -e CF_IMPORT_FORCE_EXISTING_BRANCH=false \
    --network="host" \
    --entrypoint python3 \
    ${TEST_IMAGE} \
    /opt/csm/cf-gitea-import/import.py

## Run the container, try to create version 1.2.4 again, force it
## Should be a commit change to the 1.2.4 branch
$ENGINE run --rm -v `pwd`/content:/content:ro \
    -v `pwd`/test-results:/results \
    -e CF_IMPORT_PRODUCT_NAME=test \
    -e CF_IMPORT_PRODUCT_VERSION=1.2.4 \
    -e CF_IMPORT_GITEA_USER=${CF_IMPORT_GITEA_USER} \
    -e CF_IMPORT_GITEA_PASSWORD=${CF_IMPORT_GITEA_PASSWORD} \
    -e CF_IMPORT_GITEA_URL=${CF_IMPORT_GITEA_URL} \
    -e CF_IMPORT_FORCE_EXISTING_BRANCH=true \
    --network="host" \
    --entrypoint python3 \
    ${TEST_IMAGE} \
    /opt/csm/cf-gitea-import/import.py

