#!/usr/bin/env sh
#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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

###############################################################################
# Use this script to setup a Gitea instance with an admin user, similar to what
# a full CSM system would look like. Be sure to docker kill it when finished.
# Instructions will be printed at the end to do so, or simply source the env
# var file below and run
#
#    $ docker kill $GITEA_TEST_INSTANCE
#
# Also, a file of name CF_GITEA_IMPORT.<unique id>.env will be populated with
# environment variables that will be useful for further testing of
# cf-gitea-import. Use:
#
#    $ source CF_GITEA_IMPORT.<unique id>.env
#
# to populate the variables.
###############################################################################

# Ensure this matches the gitea image used in CSM. See which Gitea images are
# available here: https://github.com/Cray-HPE/container-images/tree/main/.github/workflows
GITEA_IMAGE="docker.io/gitea/gitea:1.15.3-rootless"
GITEA_PORT=3000
GITEA_CONFIG_DIR=`pwd`/gitea

# Container engine, podman or docker
ENGINE=docker

# Cleanup previous runs
rm -f CF_GITEA_IMPORT.*.env

# Setup Gitea
$ENGINE pull ${GITEA_IMAGE}
INSTANCE=`date +%s | sha256sum | base64 | head -c 6 ; echo`
GITEA_INSTANCE_NAME=gitea-${INSTANCE}
$ENGINE run --rm -d -e GITEA_APP_INI=/var/lib/gitea/custom/conf/app.ini -v ${GITEA_CONFIG_DIR}:/var/lib/gitea/custom -p ${GITEA_PORT}:3000 --name ${GITEA_INSTANCE_NAME} ${GITEA_IMAGE}
sleep 5  # let app settle; create db tables; if this fails bump for slow systems

# Setup Admin User
# PASSWORD=`date +%s | sha256sum | base64 | head -c 32 ; echo`
PASSWORD=gitea
USER=cf-gitea-test-`date +%s | sha256sum | base64 | head -c 8 ; echo`
$ENGINE exec -u root ${GITEA_INSTANCE_NAME} gitea admin user create --username ${USER} --password ${PASSWORD} --admin --must-change-password=false --email ${USER}@example.com

echo "Waiting for DB to create gitea user ${USER} and test API access to http://localhost:${GITEA_PORT}/api/v1"
until curl http://localhost:${GITEA_PORT}/api/v1/admin/users;
  do
    echo Waiting for DB to create gitea user ${USER} and test API access to http://localhost:${GITEA_PORT}/api/v1
    sleep 2;
  done

# Print off info for the admin user
curl -s -u ${USER}:${PASSWORD} http://localhost:${GITEA_PORT}/api/v1/admin/users | jq

# Print off env vars for this instance of the test env
cat > CF_GITEA_IMPORT.${INSTANCE}.env << EOF
export CF_IMPORT_GITEA_URL=http://localhost:${GITEA_PORT}
export CF_IMPORT_GITEA_USER=${USER}
export CF_IMPORT_GITEA_PASSWORD=${PASSWORD}
export GITEA_TEST_INSTANCE=${GITEA_INSTANCE_NAME}
EOF

echo "Gitea environment variables have been saved in: CF_GITEA_IMPORT.${INSTANCE}.env "
echo "To stop this gitea instance, run: $ENGINE kill ${GITEA_INSTANCE_NAME}"
