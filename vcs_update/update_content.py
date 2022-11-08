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

import logging
import os
import re
import sys
import tempfile
import time
from typing import Tuple
from urllib.parse import ParseResultBytes, quote, urlparse, urlunparse

import requests
from git import Repo
from git.exc import GitCommandError
from packaging.version import Version
from packaging.version import parse as parse_version
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry

LOGGER = logging.getLogger("cf-gitea-update")

# Figure out how to best pass parameters and options to this python script so the admin can choose what to do
# Most likely read from ENV vars passed from argo invocation
# will pass vcs secrets user/pass via argo

# Should we use a config file parser like John's example? in ShastaUpdate
def get_remote_refs(repo: Repo, branch_prefix: str) -> list[Tuple[str, str]]:
    """
    Lists all remote refs in the given repository and returns a list of tuples containing
    the full reference, and the stripped versioning of the reference.

    Args:
        `repo (Repo)`: git.Repo
        `branch_prefix (str)`: prefix of the branches to allow cleaning of versions in branch names

    Returns:
        `list[Tuple[str, str]]`: tuple example `(remote reference name origin/somename-0.0.1, 0.0.1)`
    """
    branch_matches: list[str, str] = []
    remote_branch_prefix = "origin/" + branch_prefix
    for ref in repo.git.branch("-r").split():
        if ref.startswith(branch_prefix):
            branch_matches.append((ref, ref.lstrip(remote_branch_prefix)))
        LOGGER.debug("Branch %r matches target branch pattern", ref)
    return branch_matches


def get_sorted_non_semver_branches(
    branch_to_versions: list[Tuple[str, str]]
) -> list[Tuple[str, str]] | list:
    """
    Given a list of tuples of git remotes and versions of semver variation (major.minor) X.Y
    Sort by major.minor X.Y versioning of given branch tuples.

    Args:
        `branch_to_versions` (list[Tuple[str, str]]): tuple of the (remote reference name, stripped version X.Y version)

    Returns:
        list[str]: _description_
    """
    major_minor_regex = re.compile(
        "^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )
    major_minor_matches: list = []
    for _, (branch_name, branch_ver) in enumerate(branch_to_versions):
        if major_minor_regex.match(branch_ver):
            major_minor_matches.append((branch_name, branch_ver))

    sorted_major_minor: list[Tuple[str, str]] = sorted(
        major_minor_matches, key=lambda x: Version(x[1])
    )

    return sorted_major_minor


def get_sorted_semver_branches(
    branch_to_versions: list[Tuple[str, str]]
) -> list[Tuple[str, str]] | list:
    """
    Given a list of tuples of git remotes and versions of semver X.Y.Z major.minor.patch
    Sort by using semver.

    Args:
        `branch_to_versions` (list[Tuple[str, str]]): tuple of the (remote reference name, stripped version X.Y version)

    Returns:
        list[str]: _description_
    """
    semver_regex = re.compile(
        "^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )
    semver_matches: list = []
    for _, (branch_name, branch_ver) in enumerate(branch_to_versions):
        if semver_regex.match(branch_ver):
            semver_matches.append((branch_name, branch_ver))

    sorted_semver: list[Tuple[str, str]] = sorted(
        semver_matches, key=lambda x: Version(x[1])
    )

    return sorted_semver


def connect_to_gitea_api(
    url: str,
    user: str,
    password: str,
    product_name: str,
    product_version: str,
) -> Session:
    """Setup communication with the Gitea REST API, auth, user-agent, retries"""
    retry_config: Retry = Retry(
        total=50, backoff_factor=1.1, status_forcelist=[500, 502, 503, 504]
    )
    session: Session = Session()
    session.auth = (user, password)
    session.headers.update(
        {"User-Agent": "cf-gitea-update {}/{}".format(product_name, product_version)}
    )

    while True:
        try:
            response: requests.Response = session.get(url)
            response.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                break
            LOGGER.error(f"error: {e}")
            LOGGER.info(f"Sleeping for 10s waiting for {url} to be ready")
            time.sleep(10)
            continue

    # Enable retries now that Gitea is up
    session.mount(url, HTTPAdapter(max_retries=retry_config))
    return session


# TODO: remove after testing
def create_gitea_org(org, gitea_url, session) -> requests.Response:
    """Create an organization in Gitea; idempotent"""
    url = "{}/orgs".format(gitea_url)
    LOGGER.info("Attempting to create gitea org: %s", url)
    response = session.post(url, json={"username": org})
    # 422 is still valid
    if response.status_code == 422:
        rjson = response.json()
        if "message" in rjson and "user already exists" in rjson["message"]:
            LOGGER.info("Gitea org %r already exists", org)
            return response

    response.raise_for_status()
    return response


# TODO: remove after testing
def create_gitea_repository(repo_name, org, gitea_url, repo_privacy, session):
    """Create a Gitea repository; idempotent"""
    url = "{}/org/{}/repos".format(gitea_url, org)
    repo_opts = {
        "auto_init": True,
        "name": repo_name,
        "private": repo_privacy,
    }
    LOGGER.info("Attempting to create gitea repository: %s", url)
    response: requests.Response = session.post(url, json=repo_opts)

    if response.status_code == 409:  # repo already exists
        LOGGER.info("Gitea repo %r already exists", repo_name)

        # Ensuring repo is set to repo_privacy (previous to Shasta 1.4.1,
        # repo were public by default), but now are private by default due to
        # CAST-24744.
        url = "{}/repos/{}/{}".format(gitea_url, org, repo_name)
        LOGGER.info("Attempting to set repo visibility to %s: %s", repo_privacy, url)
        response = session.patch(url, json={"private": repo_privacy})
        if response.status_code == 422:  # no permissions to set privacy
            LOGGER.warning(
                "Repo visibility was not set properly. Server message: %s.",
                response.text,
            )
            pass  # not a fatal error
        return
    response.raise_for_status()
    return


def get_gitea_respository(
    repo_name: str, org: str, url: str, session: requests.Session
):
    """Retrieve the repository metadata from the Gitea API"""
    url = "{}/repos/{}/{}".format(url, org, repo_name)
    LOGGER.info("Attempting to fetch gitea repository: %s", url)
    response: requests.Response = session.get(url)
    response.raise_for_status()
    return response.json()


def clone_repo(
    org: str,
    gitea_user: str,
    gitea_password: str,
    url: str,
    product_name: str,
) -> Repo:
    """
    Clones and returns the gitea repo
    Returns: Repo
    """
    repo_name: str = product_name + "-config-management"
    git_workdir = tempfile.gettempdir() + "/" + product_name
    parsed_url: ParseResultBytes = urlparse(url)
    clone_url = urlunparse(
        (
            parsed_url.scheme,
            f"{gitea_user}:{gitea_password}@" + parsed_url.netloc,
            parsed_url.path + "/" + org + "/" + repo_name + ".git",
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )
    LOGGER.info("Cloning repository: %s", repo_name)
    try:
        return Repo.clone_from(clone_url, git_workdir)
    except GitCommandError as e:
        LOGGER.error("Failed to clone repository: %s", e)
        raise e


def find_customer_branch(
    session: Session, url: str, org: str, repo_name: str, customer_branch: str
) -> bool:
    """
    Checks to see the provided customer branch is found in git this will be a direct match query.
    Returns: bool
    """
    LOGGER.info("Looking for existing customer branch: %s", customer_branch)
    url: str = "{}/repos/{}/{}/branches/{}".format(
        url, org, repo_name, quote(customer_branch, safe="")
    )
    response: requests.Response = session.get(url)
    if response.status_code == 200:
        LOGGER.info("Existing customer branch found: %s", customer_branch)
        return True
    elif response.status_code == 404:
        LOGGER.info("No previous instance of target branch found: %s", customer_branch)
        return False
    elif not response.ok:
        response.raise_for_status()
    else:
        LOGGER.error(
            "Unexpected response from Gitea API locating target branch: %s",
            response.text,
        )
        return False


def guess_previous_customer_branch(
    sorted_non_semver_branches: list[Tuple[str, str]],
    sorted_semver_branches: list[Tuple[str, str]],
) -> Tuple[str, str]:
    """
    Checks to see which branch was the most recently used as the customer branch if provided
    does not exist in the repo. This requires that the branches are conformed to semantic versioning
    as X.Y.Z
    """
    # check if X.Y exists first, then check semver versions exists
    if not sorted_non_semver_branches and not sorted_semver_branches:
        LOGGER.error(
            f"No customer branches have been found in the repository. "
            "Please assure that branch names are following versioning conventions."
        )
        raise NoCustomerBranchesFoundException()
    elif sorted_semver_branches and not sorted_non_semver_branches:
        return sorted_semver_branches[-1]
    elif sorted_non_semver_branches and not sorted_semver_branches:
        return sorted_non_semver_branches[-1]

    # compare the two forms of versioning X.Y to X.Y.Z
    major_minor_parsed_version: Version = parse_version(
        sorted_non_semver_branches[-1][1]
    )
    semver_parsed_version: Version = parse_version(sorted_semver_branches[-1][1])
    if semver_parsed_version >= major_minor_parsed_version:
        return sorted_semver_branches[-1]
    else:
        return sorted_non_semver_branches[-1]
    
def merge_pristine_into_customer_branch():
    pass


class RequiredParameterException(KeyError):
    pass


class NoCustomerBranchesFoundException(Exception):
    pass


def get_value_or_raise(data: dict, key: str):
    """dict.get() wrapper for init"""
    value = data.get(key)
    if value is None:
        raise RequiredParameterException(
            "parameter: %s not present in the required environment variables" % key
        )
    return value


def _setup_logging():
    """Setup stdout logging for this script"""
    LOGGER.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)


def _report_environment(env: dict[str, str]):
    """Report the CF_IMPORT_* environment variables for debugging"""
    CF_IMPORT_ENVIRONMENT = {
        k: v for k, v in env.items() if "CF_IMPORT" in k and "PASSWORD" not in k
    }
    LOGGER.info("cf-gitea-update runtime environment:")
    for k, v in CF_IMPORT_ENVIRONMENT.items():
        LOGGER.info("   %s=%s", k, v)


def main():
    ENV = os.environ.copy()
    VCS = "api-gw-service-nmn.local"
    _setup_logging()
    _report_environment(ENV)

    gitea_base_url = get_value_or_raise(ENV, "CF_UPDATE_GITEA_URL").strip()
    gitea_url = f'{gitea_base_url.rstrip("/")}/api/v1'
    gitea_user = get_value_or_raise(ENV, "CF_UPDATE_GITEA_USER").strip()
    gitea_password = get_value_or_raise(ENV, "CF_UPDATE_GITEA_PASSWORD").strip()
    gitea_org = get_value_or_raise(ENV, "CF_UPDATE_GITEA_ORG").strip()
    pristine_branch = get_value_or_raise(ENV, "PRISTINE_BRANCH").strip()
    customer_branch = get_value_or_raise(ENV, "CUSTOMER_BRANCH").strip()
    product_name = get_value_or_raise(ENV, "CF_UPDATE_PRODUCT_NAME").strip()
    product_version = get_value_or_raise(ENV, "CF_UPDATE_PRODUCT_VERSION")
    customer_branch_prefix = "/".join([gitea_org, product_name]) + "/"
    repo_name = product_name + "-config-management".strip()

    session = connect_to_gitea_api(
        gitea_url, gitea_user, gitea_password, product_name, product_version
    )

    # TODO: remove create_gitea_org, create_gitea_repository after testing locally
    create_gitea_org(gitea_org, gitea_url, session)
    create_gitea_repository(repo_name, gitea_org, gitea_url, False, session)
    git_repo = get_gitea_respository(repo_name, gitea_org, gitea_url, session)
    repo = clone_repo(
        gitea_org, gitea_user, gitea_password, gitea_base_url, product_name
    )

    #     Recommended customer branch naming convention: integration-X.Y[.Z]

    # Checkout a copy of the VCS repository for the product.
    # Ascertain if the customer branch exists.
    # If it does, merge pristine branch to customer branch, and you're done.
    # If it does not exist, try to locate the previous customer branch. (Guess the previous version.)
    # List all of the branches available.
    # Apply a regex with a version to identify each branch by its version.
    # Sort the branches by their versions and pick the latest version number from that list.
    # Take this previous customer branch, and branch off of it and create a new branch.
    # Then, merge the pristine branch into this newly created branch.

    if find_customer_branch(  # if this direct branch is found then this is a final state
        session, gitea_url, gitea_org, repo_name, customer_branch
    ):
        merge_pristine_into_customer_branch()
    else:  # if we do NOT have a direct branch we must find the best guess / previous branch
        guess_previous_customer_branch()
        merge_pristine_into_customer_branch()


if __name__ == "__main__":
    main()
