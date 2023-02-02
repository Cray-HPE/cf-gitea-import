#!/bin/sh
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

# Argo specific entrypoint due to istio sidecar incompatibilities.
# Wait for the Gitea API to be available

set -e
#
# update-ca-certificates reads from /usr/local/share/ca-certificates
# and updates /etc/ssl/certs/ca-certificates.crt
# REQUESTS_CA_BUNDLE is used by python
#
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
update-ca-certificates --fresh 2>/dev/null

until curl --head ${CF_IMPORT_GITEA_URL}; \
do
  echo Waiting for Gitea API to be available; \
  sleep 3; \
done; \
echo Gitea API available;

# Overwrite content before import
cp -r "/shared/"* ${CF_IMPORT_CONTENT}/ && echo "overwriting /content success" || echo "overwriting /content failed"

# Import the configuration content
cd /opt/csm/cf-gitea-import
python3 ./import.py
