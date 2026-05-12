import pytest

from clisops_core.utils import testing
from clisops_core.utils.testing import stratus as _stratus


@pytest.fixture(scope="session", autouse=True)
def threadsafe_data_dir(tmp_path_factory):
    return tmp_path_factory.getbasetemp().joinpath("data")


@pytest.fixture(scope="session")
def nimbus(threadsafe_data_dir, worker_id):
    return _stratus(
        repo=testing.XCLIM_TEST_DATA_REPO_URL,
        branch=testing.XCLIM_TEST_DATA_VERSION,
        cache_dir=(testing.XCLIM_TEST_DATA_CACHE_DIR if worker_id == "master" else threadsafe_data_dir),
    )


@pytest.fixture(scope="session", autouse=True)
def load_test_data(worker_id, nimbus):
    """
    Load the test data repository.

    This fixture ensures that the required test data repository
    has been cloned to the cache directory within the home directory.
    """
    repositories = {
        "nimbus": {
            "worker_cache_dir": nimbus.path,
            "repo": testing.XCLIM_TEST_DATA_REPO_URL,
            "branch": testing.XCLIM_TEST_DATA_VERSION,
            "cache_dir": testing.XCLIM_TEST_DATA_CACHE_DIR,
        },
    }

    for repo in repositories.values():
        testing.gather_testing_data(worker_id=worker_id, **repo)
