#!/bin/sh
#
# MIT License
#
# (C) Copyright 2022-2023 Hewlett Packard Enterprise Development LP
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
# Entrypoint for running cf-gitea-import as a standalone image, e.g.
# via podman.
#
# This is different from the default entrypoint in the following ways:
# Unlike the default entrypoint, this does not wait on the envoy
# proxy sidecar. Additionally, it does not wait for the Gitea API
# to be available, as this is already in import.py. There is no
# use of the /shared directory as this is specified as a volumeMount
# in the cray-import-config Helm chart, not something in the base
# image. Finally, there is a step to import the host's CA certificates,
# required when running outside of Kubernetes.

set -e
#
# update-ca-certificates reads from /usr/local/share/ca-certificates
# and updates /etc/ssl/certs/ca-certificates.crt
# REQUESTS_CA_BUNDLE is used by python
#
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
update-ca-certificates 2>/dev/null

# Import configuration content
python3 /opt/csm/cf-gitea-import/import.py
