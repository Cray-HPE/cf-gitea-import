from typing import Tuple

import mock
import pytest
import requests
import requests_mock
from git.exc import GitCommandError
from requests.adapters import HTTPAdapter
from requests.sessions import Session

from vcs_update import update_content


@pytest.fixture
def session():
    session: Session = Session()
    session.auth = ("user", "password")
    session.headers.update({"User-Agent": "cf-gitea-update product_name/1.0.0"})
    return session


@pytest.fixture
def mock_session():
    session = requests.Session()
    adapter = requests_mock.Adapter()
    session.mount("mock://", adapter)
    return session


def test_get_value_or_raise():
    data: dict = {"food": "tasty", 1: 2}
    food_value: str = update_content.get_value_or_raise(data=data, key="food")
    assert food_value == "tasty"

    # Check failure case
    with pytest.raises(update_content.RequiredParameterException):
        update_content.get_value_or_raise(data=data, key="bad_key")


class TestVCSUpdate:
    """
    class for common parameters during test cases.
    """

    gitea_url: str = "https://api-gw-service-nmn.local/vcs/api/v1"

    def test_connect_to_gitea_api(self, requests_mock):
        # Expected values
        user: str = "user"
        password: str = "password"
        product_name: str = "product_name"
        product_version: str = "1.0.80"

        requests_mock.get(self.gitea_url)

        good_session: requests.Session = update_content.connect_to_gitea_api(
            self.gitea_url, user, password, product_name, product_version
        )
        assert good_session.auth == (user, password)
        key, value = "User-Agent", "cf-gitea-update {}/{}".format(
            product_name, product_version
        )
        assert key in good_session.headers and value == good_session.headers[key]
        assert isinstance(good_session.adapters[self.gitea_url], HTTPAdapter)

    def test_create_gitea_org(self, requests_mock, session):
        org: str = "cray"
        session: requests.Session = session
        # what gitea should respond with
        org_response = {
            "username": "user",
            "description": "description",
            "name": "name",
            "id": 1,
        }

        # 200 ok test case
        requests_mock.post(self.gitea_url + "/orgs", json=org_response)

        assert (
            update_content.testing_create_gitea_org(
                org, self.gitea_url, session
            ).status_code
            == 200
        )

    def test_get_gitea_respository(self, requests_mock, session):
        mock_response = {
            "repo_name": "foo",
        }

        requests_mock.get(
            "https://api-gw-service-nmn.local/vcs/api/v1/repos/cray/foorepo",
            json=mock_response,
        )
        assert (
            update_content.get_gitea_respository(
                "foorepo", "cray", self.gitea_url, session
            )
            == mock_response
        )

        # non 200
        requests_mock.get(
            "https://api-gw-service-nmn.local/vcs/api/v1/repos/cray/foorepo",
            status_code=400,
        )
        with pytest.raises(requests.HTTPError):
            update_content.get_gitea_respository(
                "foorepo", "cray", self.gitea_url, session
            )

    # TODO: fix patches when this code is moved
    @mock.patch("vcs_update.update_content.Repo")
    def test_clone_repository(self, mock_repo):
        # Set the "bare" attribute of the Repo instance to be False
        bare_mock = mock.PropertyMock(return_value=False)
        type(mock_repo.clone_from.return_value).bare = bare_mock
        git_workdir = "/tmp"
        git_base_url: str = "http://localhost:3000"
        expected_clone_url: str = (
            "http://user:password@localhost:3000/cray/foo-product-config-management.git"
        )

        update_content.clone_repo(
            "cray", "user", "password", git_base_url, "foo-product"
        )
        mock_repo.clone_from.called_once_with(expected_clone_url, git_workdir)

        # Exception case
        mock_repo.clone_from.side_effect = GitCommandError(
            "Failed to clone git repository"
        )
        with pytest.raises(GitCommandError):
            update_content.clone_repo(
                "cray", "user", "password", git_base_url, "foo-product"
            )

    # def test_find_customer_branch(self, requests_mock, mock_session):
    #     org: str = "cray"
    #     repo_name: str = "repo-name"
    #     customer_branch: str = "foobranch"
    #     expected_url: str = "https://api-gw-service-nmn.local/vcs/api/v1/repos/cray/repo-name/branches/foobranch"

    #     # 200 case
    #     requests_mock.get(expected_url, status_code=200)
    #     assert (
    #         update_content.find_customer_branch(
    #             mock_session, self.gitea_url, org, repo_name, customer_branch
    #         )
    #         is True
    #     )

    #     # 404
    #     requests_mock.get(expected_url, status_code=404)
    #     assert (
    #         update_content.find_customer_branch(
    #             mock_session, self.gitea_url, org, repo_name, customer_branch
    #         )
    #         is False
    #     )

    #     # raise for status
    #     requests_mock.get(expected_url, status_code=404)
    #     assert (
    #         update_content.find_customer_branch(
    #             mock_session, self.gitea_url, org, repo_name, customer_branch
    #         )
    #         is False
    #     )

    @mock.patch("vcs_update.update_content.Repo")
    def test_find_customer_branch_success(self, mock_repo: mock.Mock):
        branches: str = (
            "origin/cray/cos-2.4.0\n"
            "origin/cray/cos-1.4.0\n"
            "origin/cray/cos-3.4.0\n"
            "origin/cray/cos-5.4.0"
        )

        customer_branch: str = "cos-2.4.0"
        branch_prefix: str = "cray/"
        branch_mock = mock.PropertyMock(return_value=branches)
        mock_repo.git.branch = branch_mock

        result = update_content.find_customer_branch(
            mock_repo, customer_branch, branch_prefix
        )
        assert result == "origin/cray/" + customer_branch

    @mock.patch("vcs_update.update_content.Repo")
    def test_find_customer_branch_failure(self, mock_repo: mock.Mock):
        branches: str = (
            "origin/cray/cos-2.4.0\n"
            "origin/cray/cos-1.4.0\n"
            "origin/cray/cos-3.4.0\n"
            "origin/cray/cos-5.4.0"
        )

        customer_branch: str = "cos-2.5.0"
        branch_prefix: str = "cray/"
        branch_mock = mock.PropertyMock(return_value=branches)
        mock_repo.git.branch = branch_mock

        result = update_content.find_customer_branch(
            mock_repo, customer_branch, branch_prefix
        )
        assert result is None

        # Test: empty branches returned
        empty_branches: str = ""
        branch_mock = mock.PropertyMock(return_value=empty_branches)
        mock_repo.git.branch = branch_mock
        empty_branches_result = update_content.find_customer_branch(
            mock_repo, customer_branch, branch_prefix
        )
        assert empty_branches_result is None

        # Test: exception on git command
        mock_repo.git.branch.side_effect = GitCommandError("git error")
        with pytest.raises(GitCommandError):
            update_content.find_customer_branch(
                mock_repo, customer_branch, branch_prefix
            )

    def test_guess_previous_customer_branch(self):
        sorted_non_semver_branches: list[Tuple[str, str]] = [
            ("origin/cray/cos-1.12-really-cool", "1.12"),
            ("origin/cray/cos-2.1-really-cool", "2.1"),
            ("origin/cray/cos-2.2-really-cool", "2.2"),
            ("origin/cray/cos-2.3-really-cool", "2.3"),
            ("origin/cray/cos-2.4-really-cool", "2.4"),
            ("origin/cray/cos-2.5-really-cool", "2.5"),
            ("origin/cray/cos-3.0-really-cool", "3.0"),
        ]

        sorted_semver_branches: list[Tuple[str, str]] = [
            ("origin/cray/cos-1.1-really-cool", "1.1"),
            ("origin/cray/cos-1.12-really-cool", "1.12"),
            ("origin/cray/cos-1.22-really-cool", "1.22"),
            ("origin/cray/cos-2.1-really-cool", "2.1.0"),
            ("origin/cray/cos-2.2.2-really-cool", "2.2.2"),
            ("origin/cray/cos-2.3.11-really-cool", "2.3.11"),
            ("origin/cray/cos-2.4.5-really-cool", "2.4.5"),
            ("origin/cray/cos-2.5.6-really-cool", "2.5.6"),
            ("origin/cray/cos-3.0.1-really-cool", "3.0.1"),
        ]

        # Test: empty lists couldnt find any branches that are of semver
        with pytest.raises(update_content.NoCustomerBranchesFoundException):
            update_content.guess_previous_customer_branch([], [])
        with pytest.raises(update_content.NoCustomerBranchesFoundException):
            update_content.guess_previous_customer_branch(None, None)

        # Test: only semvers were found
        expected_semver_tuple = ("origin/cray/cos-3.0.1-really-cool", "3.0.1")
        assert (
            update_content.guess_previous_customer_branch(
                sorted_non_semver_branches=[],
                sorted_semver_branches=sorted_semver_branches,
            )
            == expected_semver_tuple
        )

        # Test: only non-semver were found
        expected_non_semver_tuple = ("origin/cray/cos-3.0-really-cool", "3.0")
        assert (
            update_content.guess_previous_customer_branch(
                sorted_non_semver_branches=sorted_non_semver_branches,
                sorted_semver_branches=[],
            )
            == expected_non_semver_tuple
        )

        # Test: both types X.Y and X.Y.Z are found
        expected_version_tuple = ("origin/cray/cos-3.0.1-really-cool", "3.0.1")
        assert (
            update_content.guess_previous_customer_branch(
                sorted_non_semver_branches, sorted_semver_branches
            )
            == expected_version_tuple
        )

        # Test: case where X.Y has the latest version
        sorted_non_semver_branches = [("origin/cray/cos-3.0-really-cool", "3.0")]
        sorted_semver_branches = [("origin/cray/cos-2.0.99-really-cool", "2.0.99")]
        expected_version_tuple = ("origin/cray/cos-3.0-really-cool", "3.0")
        assert (
            update_content.guess_previous_customer_branch(
                sorted_non_semver_branches, sorted_non_semver_branches
            )
        ) == expected_version_tuple

    @mock.patch("vcs_update.update_content.Repo")
    def test_create_integration_branch_from_customer_branch(self, mock_repo: mock.Mock):
        customer_branch: str = "customer-branch-1.0.0"
        branch_prefix: str = "origin/cray/"
        expected_integration_branch: str = "integration-customer-branch-1.0.0"
        result = update_content.create_integration_branch_from_customer_branch(
            mock_repo, customer_branch, branch_prefix
        )
        assert result == expected_integration_branch

    @mock.patch("vcs_update.update_content.Repo")
    def test_create_integration_branch_from_customer_branch_failure(
        self, mock_repo: mock.Mock
    ):
        customer_branch: str = "customer-branch-1.0.0"
        branch_prefix: str = "origin/cray/"
        mock_repo.git.checkout.side_effect = GitCommandError("Checkout error")
        with pytest.raises(GitCommandError):
            update_content.create_integration_branch_from_customer_branch(
                mock_repo, customer_branch, branch_prefix
            )

    @mock.patch("vcs_update.update_content.Repo")
    def test_merge_pristine_into_customer_branch_failure(self, mock_repo: mock.Mock):
        mock_repo.git.merge.side_effect = GitCommandError("Merge error")
        with pytest.raises(GitCommandError) as e:
            update_content.merge_pristine_into_customer_branch(mock_repo, "", "", "")
