#
#  MIT License
#
#  (C) Copyright 2022 Hewlett Packard Enterprise Development LP
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
#  OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#  ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#  OTHER DEALINGS IN THE SOFTWARE.

# Dockerfile for updating content in gitea instances on Shasta
FROM artifactory.algol60.net/docker.io/alpine:latest as base
WORKDIR /

# Default environment variables
ENV CF_UPDATE_GITEA_USER=crayvcs

# Package installations
RUN apk add --upgrade --no-cache apk-tools && \
    apk update && \
    apk add --update --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    curl \
    git && \
    apk -U upgrade --no-cache
# ADD requirements.txt constraints.txt ./
# RUN pip3 install --no-cache-dir -r requirements.txt && \
#     rm -rf requirements.txt constraints.txt && \
#     mkdir -p /opt/csm && \
#     chown nobody:nobody /opt/csm


# FROM base as prod
# USER nobody:nobody
# RUN mkdir -p /opt/csm/cf-gitea-update
# ADD entrypoint.sh update_content.py /opt/csm/cf-gitea-update/
# ENTRYPOINT ["/opt/csm/cf-gitea-update/entrypoint.sh"]


# Run app as debug
# Can use any IDE remote debugger attach to use breakpoints in the IDE
FROM base as debug
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

### Testing Git stuff ###
ENV CF_UPDATE_GITEA_URL=http://localhost:3000
ENV CF_UPDATE_GITEA_USER=cf-gitea-test-
ENV CF_UPDATE_GITEA_PASSWORD=gitea
ENV CF_UPDATE_GITEA_ORG=cray
ENV PRISTINE_BRANCH=test-pristine
ENV CUSTOMER_BRANCH=test-customer
ENV CF_UPDATE_PRODUCT_NAME=foo-product
ENV CF_UPDATE_PRODUCT_VERSION=1.0.5

RUN pip3 install debugpy
EXPOSE 5678 5000
# Install pip requirements
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python3", "update_content.py"]
