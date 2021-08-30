#!/usr/bin/env python3
# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# (MIT License)
#
# import.py
#
# Import the contents of the specified directory into Gitea, given an optional
# base branch. Optionally, protect the new branch that is created as well.

import datetime
from distutils.dir_util import copy_tree
import logging
from operator import itemgetter
import os
import os.path
import sys
import tempfile
import time
from urllib.parse import urljoin, urlparse, urlunparse, quote
import yaml

from git import Repo
from git.exc import GitCommandError
import requests
from requests import Session
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.util.retry import Retry
import semver

LOGGER = logging.getLogger('cf-gitea-import')


def create_gitea_org(org, gitea_url, session):
    """ Create an organization in Gitea; idempotent """
    url = '{}/orgs'.format(gitea_url)
    LOGGER.info("Attempting to create gitea org: %s", url)
    resp = session.post(url, json={'username': org})
    if resp.status_code == 422:
        rjson = resp.json()
        if 'message' in rjson and "user already exists" in rjson['message']:
            LOGGER.info("Gitea org %r already exists", org)
            return
    resp.raise_for_status()


def create_gitea_repository(repo_name, org, gitea_url, repo_privacy, session):
    """ Create a Gitea repository; idempotent """
    url = '{}/org/{}/repos'.format(gitea_url, org)
    repo_opts = {
        'auto_init': True,
        'name': repo_name,
        'private': repo_privacy,
    }
    LOGGER.info("Attempting to create gitea repository: %s", url)
    resp = session.post(url, json=repo_opts)

    if resp.status_code == 409:  # repo already exists
        LOGGER.info("Gitea repo %r already exists", repo_name)

        # Ensuring repo is set to repo_privacy (previous to Shasta 1.4.1,
        # repo were public by default), but now are private by default due to
        # CAST-24744.
        url = '{}/repos/{}/{}'.format(gitea_url, org, repo_name)
        LOGGER.info(
            "Attempting to set repo visibility to %s: %s", repo_privacy, url
        )
        resp = session.patch(url, json={'private': repo_privacy})
        if resp.status_code == 422:  # no permissions to set privacy
            LOGGER.warning(
                "Repo visibility was not set properly. Server message: %s.",
                resp.text
            )
            pass  # not a fatal error
        return
    resp.raise_for_status()
    return


def clone_repo(gitea_base_url, org, repo_name, workdir, username, password):
    """ Clone the repository from Gitea to the workdir """
    parsed = urlparse(gitea_base_url)
    clone_url = urlunparse((
        parsed.scheme,
        f'{username}:{password}@' + parsed.netloc,
        parsed.path + '/' + org + '/' + repo_name + '.git',
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    LOGGER.info("Cloning repository: %s", repo_name)
    return Repo.clone_from(clone_url, workdir)


def get_gitea_repository(repo_name, org, gitea_url, session):
    """ Retrieve the repository metadata from the Gitea API """
    url = '{}/repos/{}/{}'.format(gitea_url, org, repo_name)
    LOGGER.info("Attempting to fetch gitea repository: %s", url)
    resp = session.get(url)
    resp.raise_for_status()
    return resp.json()


def find_base_branch(base_branch, git_repo, gitea_repo, product_version, branch_prefix):  # noqa: E501
    """
    Find a base branch based on the `product_version` assuming it is of the
    supported format. This function is used when the calling script chooses
    'semver_previous_if_exists' for the base branch.
    """
    if base_branch == '':  # no branch specified, use gitea default branch
        LOGGER.info("No base branch specified, using Gitea default branch.")
        return gitea_repo['default_branch']
    elif base_branch != "semver_previous_if_exists":
        return base_branch
    else:
        LOGGER.info("Searching for a previous branch by semver version.")
        base_branch = None  # zeroing out, find a base branch based on semver

    # Strip out branches that do not contain a valid semver somewhere in them
    semver_branch_matches = []
    remote_branch_prefix = 'origin/' + branch_prefix
    for ref in git_repo.git.branch('-r').split():
        if ref.startswith(remote_branch_prefix):
            semver_branch_matches.append((
                ref, ref.lstrip(remote_branch_prefix)
            ))
            LOGGER.debug("Branch %r matches target branch pattern", ref)

    # Sort the branches by semver and find the one that is just before the
    # current version
    semver_branch_matches.sort(key=itemgetter(1))
    for index, (branch_name, branch_semver) in enumerate(semver_branch_matches):  # noqa: E501
        compare = semver.compare(branch_semver, product_version)

        # other version higher than product version (edge case)
        if compare >= 0:
            name, semver_match = semver_branch_matches[index-1]
            LOGGER.info("Found branch by semantic versioning: %s", name)
            base_branch = branch_prefix + semver_match
            break
        # product version higher than all others
        elif compare < 0 and index + 1 == len(semver_branch_matches):
            name, semver_match = semver_branch_matches[-1]
            LOGGER.info("Found branch by semantic versioning: %s", name)
            base_branch = branch_prefix + semver_match
            break
        elif compare < 0:  # this branch is lower than the current version
            continue
        elif compare == 0:  # this branch already exists!
            raise ValueError("Branch with the product version already exists!")
    else:
        if base_branch is None:
            LOGGER.info(
                "No base branch found with a previous semantic version with "
                "the branch format specified. Using the repository's default "
                "branch."
            )
            return gitea_repo['default_branch']

    return base_branch


def enable_gitea_branch_push(branch, repo_name, org, gitea_url, session):
    """ Set a Gitea branch to not be protected from pushes """
    url = '{}/repos/{}/{}/branch_protections/{}'.format(
        gitea_url, org, repo_name, quote(branch, safe='')
    )
    opts = { 'enable_push': True }
    LOGGER.info("Allowing branch push: %s", url)
    resp = session.patch(url, json=opts)
    if not resp.ok:
        LOGGER.warning("Enabling branch push failed with status=%s, ignoring...", resp.status_code)
        LOGGER.info("Ignoring...")
        return


def protect_gitea_branch(branch, repo_name, org, gitea_url, session):
    """ Set a Gitea branch to protected """
    url = '{}/repos/{}/{}/branch_protections'.format(gitea_url, org, repo_name)
    opts = {
        'branch_name': branch,
        'enable_push': False,
    }
    LOGGER.info("Protecting branch from modification: %s", url)
    resp = session.post(url, json=opts)
    if resp.status_code == 403:
        if 'Branch protection already exist' in resp.json()['message']:
            # This branch was repushed. Instead of creating protections,
            # update the existing ones
            url = '{}/repos/{}/{}/branch_protections/{}'.format(
                gitea_url, org, repo_name, quote(branch, safe='')
            )
            opts = { 'enable_push': False }
            LOGGER.info("Allowing branch push: %s", url)
            resp = session.patch(url, json=opts)
            if not resp.ok:
                resp.raise_for_status()
    elif not resp.ok:
        resp.raise_for_status()


def update_content(base, target, git_repo, content_dir, msg, user):
    """
    Load the content from the `product_content_dir` into the `git_repo`'s
    `target` branch using `base` as the base branch. Push the `target` branch
    to the `git_repo` with the commit `msg`.
    """
    git_repo.git.checkout(base)
    LOGGER.info("Checking out target_branch: %s", target)
    git_repo.git.checkout('-B', target)
    git_repo.git.rm('-rf', '*')
    copy_tree(content_dir, git_repo.working_dir)
    git_repo.git.add('--all', '.')
    git_repo.git.config('--local', 'user.email', '%s@%s' % (user, user))
    git_repo.git.config('--local', 'user.name', '%s - cf-gitea-import' % user)
    LOGGER.info("Committing changes to branch with message: %s", msg)
    try:
        git_repo.git.commit('-m', msg)
    except GitCommandError as giterr:
        if 'nothing to commit, working tree clean' not in giterr.stdout:
            raise giterr
        else:
            LOGGER.info("No changes detected; pushing branch anyway.")
    LOGGER.info("Pushing content to target branch: %s", target)
    git_repo.git.push('--set-upstream', 'origin', target, force=True)


def _setup_logging():
    """ Setup stdout logging for this script """
    LOGGER.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # noqa: E501
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)


def _report_environment():
    """ Report the CF_IMPORT_* environment variables for debugging """
    CF_IMPORT_ENVIRONMENT = {
        k: v for k, v in os.environ.items()
        if 'CF_IMPORT' in k and "PASSWORD" not in k
    }
    LOGGER.info("cf-gitea-import runtime environment:")
    for k, v in CF_IMPORT_ENVIRONMENT.items():
        LOGGER.info("   %s=%s", k, v)


# Main Program
if __name__ == "__main__":

    _setup_logging()
    _report_environment()

    # Set required variables from environment
    product_name = os.environ.get('CF_IMPORT_PRODUCT_NAME')
    product_version = os.environ.get('CF_IMPORT_PRODUCT_VERSION')
    if os.path.exists('/product_version'):
        with open('/product_version', 'r') as f:
            product_version = f.read().strip()
    gitea_password = os.environ.get('CF_IMPORT_GITEA_PASSWORD')
    gitea_base_url = os.environ.get('CF_IMPORT_GITEA_URL')
    if product_name is None:
        sys.exit("'CF_IMPORT_PRODUCT_NAME' is required and cannot be empty")
    if product_version is None:
        sys.exit("'CF_IMPORT_PRODUCT_VERSION' is required and cannot be empty")
    if gitea_password is None:
        sys.exit("'CF_IMPORT_GITEA_PASSWORD' is required and cannot be empty")
    else:
        gitea_password = gitea_password.strip()
    if gitea_base_url is None:
        sys.exit("'CF_IMPORT_GITEA_URL' is required and cannot be empty")

    # Set optional/derived variables from environment
    product_content_dir = os.environ.get('CF_IMPORT_CONTENT', '/content').strip()
    base_branch = os.environ.get('CF_IMPORT_BASE_BRANCH', 'semver_previous_if_exists').strip()  # noqa: E501
    protect_branch = True if os.environ.get('CF_IMPORT_PROTECT_BRANCH', 'true').strip().lower() == "true" else False  # noqa: E501
    repo_privacy = True if os.environ.get('CF_IMPORT_PRIVATE_REPO', 'true').strip().lower() == "true" else False  # noqa: E501
    gitea_url = urljoin(gitea_base_url, '/api/v1')
    org = os.environ.get('CF_IMPORT_GITEA_ORG', 'cray').strip()
    repo_name = os.environ.get('CF_IMPORT_GITEA_REPO', product_name + '-config-management').strip()  # noqa: E501
    gitea_user = os.environ.get('CF_IMPORT_GITEA_USER', 'crayvcs').strip()
    target_branch = "/".join([org, product_name, product_version])
    base_branch_prefix = "/".join([org, product_name]) + '/'

    # Setup talking to the Gitea REST API, auth, user-agent, retries
    retries = Retry(
        total=50, backoff_factor=1.1, status_forcelist=[502, 503, 504]
    )
    session = Session()
    session.auth = (gitea_user, gitea_password)
    session.headers.update(
        {'User-Agent': 'cf-gitea-import {}/{}'.format(product_name, product_version)}  # noqa: E501
    )

    # Wait until the gitea_url is responsive
    while True:
        try:
            resp = session.get(gitea_url)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                break  # 404 is fine, the server is responding
            LOGGER.error('error: %s' % err)
            LOGGER.info('Sleeping for 10s waiting for %s to be up', gitea_url)
            time.sleep(10)
            continue

    # Enable retries on the session now that we know Gitea is up
    session.mount(gitea_url, HTTPAdapter(max_retries=retries))

    # Create the Gitea organization if it doesn't exist
    create_gitea_org(org, gitea_url, session)

    # Create the Gitea repository and initialize if it doesn't exist
    create_gitea_repository(repo_name, org, gitea_url, repo_privacy, session)
    gitea_repo = get_gitea_repository(repo_name, org, gitea_url, session)

    # Create a local git workspace
    git_workdir = tempfile.gettempdir()

    # Clone the repository
    git_repo = clone_repo(
        gitea_base_url, org, repo_name, git_workdir, gitea_user, gitea_password
    )

    # Find base branch, if requested
    base_branch = find_base_branch(
        base_branch, git_repo, gitea_repo, product_version, base_branch_prefix
    )
    LOGGER.info("Using base branch: %s", base_branch)

    # Do the work to import the content to the repository, if the branch
    # already exists and is protected, remove the protections first.
    enable_gitea_branch_push(target_branch, repo_name, org, gitea_url, session)
    commit_msg = "Import of %r product version %s" % (product_name, product_version)  # noqa: E501
    update_content(
        base_branch, target_branch, git_repo, product_content_dir,
        commit_msg, gitea_user
    )

    # Protect the new branch, if requested
    if protect_branch:
        protect_gitea_branch(target_branch, repo_name, org, gitea_url, session)

    # Report the findings to a records file
    records = {
        "configuration": {
            "clone_url": gitea_repo["clone_url"],
            "import_branch": target_branch,
            "import_date": datetime.datetime.now(),
            "ssh_url": gitea_repo["ssh_url"],
            "commit": git_repo.head.object.hexsha
        }
    }
    LOGGER.info(yaml.dump(records))
    with open('/results/records.yaml', 'w') as results_file:
                yaml.dump(records, results_file)

# Done!
