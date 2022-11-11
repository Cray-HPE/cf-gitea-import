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
import pprint
import re
import sys
import tempfile
import time
from typing import Optional, Tuple, Union
from urllib.parse import ParseResult, urlparse, urlunparse

import requests
from git.exc import GitCommandError
from git.repo import Repo
from packaging.version import LegacyVersion, Version
from packaging.version import parse as parse_version
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry

LOGGER = logging.getLogger("cf-gitea-update")


class TestCode:
    # TODO: Remove this class
    """
    Test code class for using local docker gitea server for setup and integration testing.
    Delete this after done testing
    """

    def testing_create_gitea_org(self, org, gitea_url, session) -> requests.Response:
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

    def testing_create_gitea_repository(
        self, repo_name, org, gitea_url, repo_privacy, session
    ):
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
            LOGGER.info(
                "Attempting to set repo visibility to %s: %s", repo_privacy, url
            )
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

    def testing_create_branches(
        self, repo_name, org, gitea_url, session: Session, branch_name: str
    ):
        url = "{}/repos/{}/{}/branches".format(gitea_url, org, repo_name)
        payload = dict(new_branch_name=branch_name)
        response: requests.Response = session.post(url, json=payload)
        LOGGER.info(f"Creating test branches in gitea {url} with payload {payload}")
        # response.raise_for_status()
        return

    def testing_populate_pristine_branch(
        self, repo, branch_prefix, pristine_branch, product_name
    ):
        pristine_remote_ref = "origin/" + branch_prefix + pristine_branch
        repo.git.checkout("-B", pristine_branch, pristine_remote_ref)
        repo_dir = tempfile.gettempdir() + "/" + product_name
        repo.git.fetch()
        new_file = open(repo_dir + "/test.txt", "w")
        new_file.write("some pristine_branch contents")
        repo.git.add("--all", "test.txt")
        repo.git.config("--local", "user.email", "jesse.viola@hpe.com")
        repo.git.config("--local", "user.name", "jesse")
        repo.git.commit("-m", "first commit message")
        repo.git.branch("--track", "origin", pristine_remote_ref)
        # repo.git.pull("origin", pristine_remote_ref)
        # repo.git.push("origin", "HEAD:" + pristine_remote_ref)


def get_remote_ref_versions(
    repo: Repo, branch_prefix: str
) -> list[Tuple[str, str, str]]:
    """
    Lists all remote refs in the given repository and returns a list of tuples containing
    the full reference name, prefix stripped name, and the stripped versioning of the reference.

    Args:
        `repo (Repo)`: git.Repo
        `branch_prefix (str)`: prefix of the branches to allow cleaning of versions in branch names

    Returns:
        `list[Tuple[str, str, str]]`: tuple example `(remote reference name origin/cray/cos/1.0.1, cray/cos/1.0.1, 1.0.1)`
    """
    branch_matches: list[Tuple[str, str, str]] = []
    remote_branch_prefix = "origin/" + branch_prefix
    remote_refs: list[str] = [ref.strip() for ref in repo.git.branch("-r").split("\n")]
    for ref in remote_refs:
        if ref.startswith(remote_branch_prefix):
            branch_matches.append(
                (
                    ref,
                    ref.removeprefix("origin/"),
                    ref.removeprefix(remote_branch_prefix),
                )
            )
            LOGGER.debug("Branch %r matches target branch pattern", ref)
    return branch_matches


def get_sorted_non_semver_branches(
    branch_to_versions: list[Tuple[str, str, str]]
) -> list[Tuple[str, str, str]] | list:
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
    for _, (remote_branch_name, branch_name, branch_ver) in enumerate(
        branch_to_versions
    ):
        if bool(major_minor_regex.match(branch_ver)):
            major_minor_matches.append((remote_branch_name, branch_name, branch_ver))

    sorted_major_minor: list[Tuple[str, str, str]] = sorted(
        major_minor_matches, key=lambda x: Version(x[-1])
    )

    return sorted_major_minor


def get_sorted_semver_branches(
    branch_to_versions: list[Tuple[str, str, str]]
) -> list[Tuple[str, str, str]] | list:
    """
    Given a list of tuples of git remotes and versions of semver X.Y.Z major.minor.patch
    Sort by using semver.

    Args:
        `branch_to_versions` (list[Tuple[str, str]]): tuple of the (remote reference name, stripped version X.Y version)

    Returns:
        list[Tuple[str, str]]: List of tuples of (full remote name, X.Y.Z version)
    """
    semver_regex: re.Pattern = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )
    semver_matches: list = []
    for _, (remote_branch_name, branch_name, branch_ver) in enumerate(
        branch_to_versions
    ):
        if bool(semver_regex.match(branch_ver)):
            semver_matches.append((remote_branch_name, branch_name, branch_ver))

    sorted_semver: list[Tuple[str, str, str]] = sorted(
        semver_matches, key=lambda x: Version(x[-1])
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
    Locally clones a repository from gitea and stores it in a tmp directory.

    Args:
        org (str): Gitea organization
        gitea_user (str): vcs_user
        gitea_password (str): vcs_password
        url (str): url to gitea server
        product_name (str): name of product to update the contents of

    Raises:
        GitCommandError: git command failed

    Returns:
        Repo: GitPython.Repo object
    """
    repo_name: str = product_name + "-config-management"
    git_workdir = tempfile.gettempdir() + "/" + product_name
    parsed_url: ParseResult = urlparse(url)
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
    repo: Repo, customer_branch: str, branch_prefix: str
) -> Optional[str]:
    """
    Checks the repository for the specified customer branch and returns whether it exists.
    Will check if the `customer_branch` is already stripped of origin/branch_prefix and
    the full remote reference name.

    Args:
        repo (git.Repo): Repo GitPython object representing local git repository
        customer_branch (str): name of the customer branch
        branch_prefix (str): branch prefix example: `origin/{branch_prefix}...foo-branch-1.0.0`

    Returns:
        Optional[str]: Customer branch if found or None

    Raises:
        GitCommandError: git command failed
    """
    remote_customer_ref: Optional[str] = None
    remote_branch_prefix: str = "origin/" + branch_prefix
    try:
        branches: list[str] = repo.git.branch("-r").split("\n")
    except GitCommandError as e:
        LOGGER.error(
            "Error occurred while attempting to find all remote branches: %s", e
        )
        raise e
    LOGGER.info(
        f"Locating remote branches {pprint.pprint(branches)}, searching for {customer_branch}"
    )
    for ref in branches:
        if customer_branch == ref or customer_branch == ref.removeprefix(
            remote_branch_prefix
        ):
            remote_customer_ref = ref
            break
    if remote_customer_ref is None:
        LOGGER.error(f"Could not find {customer_branch} in list of remote branches")

    return remote_customer_ref


def guess_previous_customer_branch(
    sorted_non_semver_branches: list[Tuple[str, str, str]],
    sorted_semver_branches: list[Tuple[str, str, str]],
) -> Tuple[str, str, str]:
    """
    Checks to see which branch was the most recently used as the customer branch if provided
    does not exist in the repo. This requires that the branches are conformed to semantic versioning
    as X.Y.Z
    """
    LOGGER.info(
        "No previous customer branch provided or found. Currently guessing previous customer branch"
    )
    if not sorted_non_semver_branches and not sorted_semver_branches:
        LOGGER.error(f"No valid semver branches have been found in the repository.")
        raise NoCustomerBranchesFoundException()
    elif sorted_semver_branches and not sorted_non_semver_branches:
        return sorted_semver_branches[-1]
    elif sorted_non_semver_branches and not sorted_semver_branches:
        return sorted_non_semver_branches[-1]

    # compare the two forms of versioning X.Y to X.Y.Z
    major_minor_parsed_version: Union[LegacyVersion, Version] = parse_version(
        sorted_non_semver_branches[-1][1]
    )
    semver_parsed_version: Union[LegacyVersion, Version] = parse_version(
        sorted_semver_branches[-1][1]
    )
    if semver_parsed_version >= major_minor_parsed_version:
        return sorted_semver_branches[-1]
    else:
        return sorted_non_semver_branches[-1]


def create_integration_branch_from_customer_branch(
    repo: Repo, customer_branches: Tuple[str, str, str]
) -> str:
    """
    Create a local branch from the remote customer reference using git cmd line wrapper.

    Args:
        repo (git.Repo): GitPython repository
        customer_branch (str): name of customer_branch
        branch_prefix (str): prefix of of the customer branch usually a remote reference `origin/foo/bar`

    Returns:
        str: Name of the integration_branch newly created in the local git repository.

    Raises:
        GitCommandError: git command failed
    """
    try:
        remote_ref: str = customer_branches[0]
        local_ref: str = customer_branches[1]
        repo.git.fetch("--all")
        LOGGER.info(f"Checking out {local_ref} from remote {remote_ref}")
        repo.git.checkout("-B", local_ref, remote_ref)

        integration_branch: str = "integration-" + local_ref
        LOGGER.info(f"Creating {integration_branch} from local branch {local_ref}")
        repo.git.checkout("-B", integration_branch, local_ref)
    except GitCommandError as e:
        LOGGER.error(
            "Creating integration branch using customer_branch has failed: %s", e
        )
        raise e
    return integration_branch


def merge_pristine_into_customer_branch(
    repo: Repo, pristine_branch: str, customer_branch: str, branch_prefix: str
) -> None:
    """
    Uses git cli commands to merge the pristine_branch into the customer branch.
    This function assumes that no merge conflicts are present and must be handled
    before.

    Args:
        repo (Repo): _description_
        pristine_branch (str): _description_
        customer_branch (str): _description_
        branch_prefix (str): _description_

    Raises:
        GitCommandError: git command failed
    """
    try:
        repo.git.fetch("--all")
        pristine_remote_ref: str = "origin/" + branch_prefix + pristine_branch
        LOGGER.info(f"Checking out the pristine_branch from remote")
        repo.git.checkout("-B", pristine_branch, pristine_remote_ref)
        LOGGER.info(
            f"Successfully checked out branch {pristine_branch} from tracking {pristine_remote_ref}"
        )
        repo.git.checkout(customer_branch)
        repo.git.merge(pristine_branch)
        repo.git.push("--set-upstream", "origin", customer_branch, force=True)
    except GitCommandError as e:
        LOGGER.error(
            "Failed to merge pristine_branch into customer integration branch: %s", e
        )
        raise e
    return


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


def main() -> None:
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
    pristine_branch_prefix = "/".join([gitea_org, product_name]) + "/"
    repo_name = product_name + "-config-management".strip()

    session: Session = connect_to_gitea_api(
        gitea_url, gitea_user, gitea_password, product_name, product_version
    )

    # TODO: Remove local testing code
    local_test = TestCode()
    local_test.testing_create_gitea_org(gitea_org, gitea_url, session)
    local_test.testing_create_gitea_repository(
        repo_name, gitea_org, gitea_url, False, session
    )
    # create branches for testing purposes since this should be a bare repository
    local_test.testing_create_branches(  # pristine_branch here
        repo_name,
        gitea_org,
        gitea_url,
        session,
        pristine_branch_prefix + pristine_branch,
    )
    local_test.testing_create_branches(
        repo_name,
        gitea_org,
        gitea_url,
        session,
        customer_branch_prefix + "2.0.0",
    )
    local_test.testing_create_branches(
        repo_name,
        gitea_org,
        gitea_url,
        session,
        customer_branch_prefix + "2.0.0",
    )
    local_test.testing_create_branches(
        repo_name,
        gitea_org,
        gitea_url,
        session,
        customer_branch_prefix + "2.1.0",
    )
    local_test.testing_create_branches(
        repo_name,
        gitea_org,
        gitea_url,
        session,
        customer_branch_prefix + "1.1.0",
    )
    local_test.testing_create_branches(
        repo_name,
        gitea_org,
        gitea_url,
        session,
        customer_branch_prefix + "3.0.0",
    )

    ### Real Code ###
    git_repo = get_gitea_respository(repo_name, gitea_org, gitea_url, session)
    repo: Repo = clone_repo(
        gitea_org, gitea_user, gitea_password, gitea_base_url, product_name
    )
    # TODO: remove test code
    # local_test.testing_populate_pristine_branch(
    #     repo, pristine_branch_prefix, pristine_branch, product_name
    # )

    customer_branch_ref: Optional[str] = find_customer_branch(
        repo=repo, customer_branch=customer_branch, branch_prefix=customer_branch_prefix
    )
    if customer_branch_ref:
        merge_pristine_into_customer_branch(
            repo=repo,
            pristine_branch=pristine_branch,
            customer_branch=customer_branch,
            branch_prefix=customer_branch_prefix,
        )
    else:
        try:
            remote_ref_versions: list[Tuple[str, str, str]] = get_remote_ref_versions(
                repo=repo, branch_prefix=customer_branch_prefix
            )
            best_guess_customer_branch: Tuple[
                str, str, str
            ] = guess_previous_customer_branch(
                get_sorted_non_semver_branches(remote_ref_versions),
                get_sorted_semver_branches(remote_ref_versions),
            )
            integration_branch: str = create_integration_branch_from_customer_branch(
                repo=repo,
                customer_branches=best_guess_customer_branch,
            )
            merge_pristine_into_customer_branch(
                repo=repo,
                pristine_branch=pristine_branch,
                customer_branch=integration_branch,
                branch_prefix=customer_branch_prefix,
            )
        except Exception as e:
            LOGGER.error(
                f"One or more failures occurred during update_content for product {product_name}"
            )
            raise e


if __name__ == "__main__":
    main()
