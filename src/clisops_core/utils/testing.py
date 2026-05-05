"""Testing support"""

import importlib.resources as ilr
import os
from pathlib import Path
from shutil import copytree
from sys import platform
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlretrieve

import pooch
from filelock import FileLock
from loguru import logger


try:
    default_xclim_test_data_cache = pooch.os_cache("xclim-testdata")
except (AttributeError, TypeError):
    default_xclim_test_data_cache = None


XCLIM_TEST_DATA_REPO_URL = os.getenv(
    "XCLIM_TEST_DATA_REPO_URL",
    "https://raw.githubusercontent.com/Ouranosinc/xclim-testdata",
)
default_xclim_test_data_version = "v2024.8.23"
XCLIM_TEST_DATA_VERSION = os.getenv("XCLIM_TEST_DATA_VERSION", default_xclim_test_data_version)
XCLIM_TEST_DATA_CACHE_DIR = os.getenv("XCLIM_TEST_DATA_CACHE_DIR", default_xclim_test_data_cache)


class ContextLogger:
    """
    Helper function for safe logging management in pytests.

    This class manages the loguru logger context, enabling and disabling logging
    for a specific package during the test execution. It also handles the case
    where pytest's caplog fixture is used, allowing for log capturing without
    interfering with the logger's configuration.

    Parameters
    ----------
    caplog : CaplogFixture, optional
        The pytest caplog fixture, if provided, to capture logs during tests.
    """

    def __init__(self, caplog=False):
        """Initialize the ContextLogger."""
        from loguru import logger

        self.logger = logger
        self.using_caplog = False
        if caplog:
            self.using_caplog = True

    def __enter__(self, package_name: str = "clisops"):
        """If test is supplying caplog, pytest will manage setup."""
        self.logger.enable(package_name)
        self._package = package_name
        return self.logger

    def __exit__(self, *args, **kwargs):
        """If test is supplying caplog, pytest will manage teardown."""
        self.logger.disable(self._package)
        if not self.using_caplog:
            try:
                self.logger.remove()
            except ValueError:  # noqa: S110
                pass


def load_registry(branch: str, repo: str) -> dict[str, str]:
    """
    Load the registry file for the test data.

    Parameters
    ----------
    branch : str
        The branch of the repository to use for the registry.
    repo : str
        The URL of the repository to use for the registry.

    Returns
    -------
    dict
        Dictionary of filenames and hashes.
    """
    if repo == XCLIM_TEST_DATA_REPO_URL:
        project = "xclim-testdata"
        default_testdata_version = XCLIM_TEST_DATA_VERSION
        default_testdata_repo_url = XCLIM_TEST_DATA_REPO_URL
    else:
        raise ValueError(
            f"Repository URL {repo} not recognized. "
            f"Please set {XCLIM_TEST_DATA_REPO_URL}"
        )

    remote_registry = audit_url(f"{repo}{branch}/data/{project}_registry.txt")
    if branch != default_testdata_version:
        custom_registry_folder = Path(str(ilr.files("clisops_core").joinpath(f"utils/registries/{branch}")))
        custom_registry_folder.mkdir(parents=True, exist_ok=True)
        registry_file = custom_registry_folder.joinpath(f"{project}_registry.txt")
        urlretrieve(remote_registry, registry_file)  # noqa: S310
    elif repo != default_testdata_repo_url:
        registry_file = Path(str(ilr.files("clisops_core").joinpath(f"utils/{project}_registry.txt")))
        urlretrieve(remote_registry, registry_file)  # noqa: S310

    registry_file = Path(str(ilr.files("clisops_core").joinpath(f"utils/{project}_registry.txt")))
    if not registry_file.exists():
        raise FileNotFoundError(f"Registry file not found: {registry_file}")

    # Load the registry file
    with registry_file.open() as f:
        registry = {line.split()[0]: line.split()[1] for line in f}
    return registry


def stratus(
    repo: str,
    branch: str,
    cache_dir: str | Path,
    data_updates: bool = True,
):
    """
    Pooch registry instance for xclim test data.

    Parameters
    ----------
    repo : str
        URL of the repository to use when fetching testing datasets.
    branch : str
        Branch of repository to use when fetching testing datasets.
    cache_dir : str or Path
        The path to the directory where the data files are stored.
    data_updates : bool
        If True, allow updates to the data files. Default is True.

    Returns
    -------
    pooch.Pooch
        The Pooch instance for accessing the testing data.

    Examples
    --------
    Using the registry to download a file:

    .. code-block:: python

        import xarray as xr
        from clisops.utils.testing import stratus

        s = stratus(data_dir=..., repo=..., branch=...)
        example_file = s.fetch("example.nc")
        data = xr.open_dataset(example_file)
    """
    if pooch is None:
        raise ImportError(
            "The `pooch` package is required to fetch the remote testing data. "
            "You can install it with `pip install pooch` or `pip install roocs-utils[dev]`."
        )

    if repo.endswith("xclim-testdata"):
        _version = XCLIM_TEST_DATA_VERSION
        _default_version = default_xclim_test_data_version
    else:
        raise ValueError(
            f"Repository URL {repo} not recognized. "
            f"Please set {XCLIM_TEST_DATA_REPO_URL}"
        )

    remote = audit_url(f"{repo}/{branch}/data")
    return pooch.create(
        path=cache_dir,
        base_url=remote,
        version=_default_version,
        version_dev=_version,
        allow_updates=data_updates,
        registry=load_registry(branch=branch, repo=repo),
    )


def populate_testing_data(
    repo: str,
    branch: str,
    cache_dir: Path,
):
    """
    Populate the local cache with the testing data.

    Parameters
    ----------
    repo : str, optional
        URL of the repository to use when fetching testing datasets.
    branch : str, optional
        Branch of repository to use when fetching testing datasets.
    cache_dir : Path
        The path to the local cache. Defaults to the location set by the platformdirs library.
        The testing data will be downloaded to this local cache.
    """
    # Create the Pooch instance
    n = stratus(cache_dir=cache_dir, repo=repo, branch=branch)

    # Download the files
    errored_files = []
    for file in load_registry(branch=branch, repo=repo):
        try:
            n.fetch(file)
        except HTTPError:
            msg = f"File `{file}` not accessible in remote repository."
            logger.error(msg)
            errored_files.append(file)
        else:
            logger.info("Files were downloaded successfully.")

    if errored_files:
        logger.error(
            "The following files were unable to be downloaded: %s",
            errored_files,
        )


def gather_testing_data(
    worker_cache_dir: str | os.PathLike[str] | Path,
    worker_id: str,
    branch: str,
    repo: str,
    cache_dir: str | os.PathLike[str] | Path,
):
    """
    Gather testing data across workers.

    Parameters
    ----------
    worker_cache_dir : str or Path
        The path to the worker's cache directory where the testing data will be copied.
    worker_id : str
        The ID of the worker. If 'master', the testing data will be populated.
    branch : str
        The branch of the repository to use when fetching testing datasets.
    repo : str
        The URL of the repository to use when fetching testing datasets.
    cache_dir : str or Path
        The path to the local cache where the testing data is stored.

    Raises
    ------
    ValueError
        If the repository URL is not recognised.
    FileNotFoundError
        If the testing data is not found and UNIX-style file-locking is not supported on Windows.
    """
    cache_dir = Path(cache_dir)
    if repo.endswith("xclim-testdata"):
        version = default_xclim_test_data_version
    else:
        raise ValueError(
            f"Repository URL {repo} not recognized. "
            f"Please set {XCLIM_TEST_DATA_REPO_URL}"
        )

    if worker_id == "master":
        populate_testing_data(branch=branch, repo=repo, cache_dir=cache_dir)
    else:
        if platform == "win32":
            if not cache_dir.joinpath(branch).exists():
                raise FileNotFoundError(
                    "Testing data not found and UNIX-style file-locking is not supported on Windows. "
                    "Consider running `populate_testing_data()` to download testing data beforehand."
                )
        else:
            cache_dir.mkdir(exist_ok=True, parents=True)
            lockfile = cache_dir.joinpath(".lock")
            test_data_being_written = FileLock(lockfile)
            with test_data_being_written:
                # This flag prevents multiple calls from re-attempting to download testing data in the same pytest run
                populate_testing_data(branch=branch, repo=repo, cache_dir=cache_dir)
                cache_dir.joinpath(".data_written").touch()
            with test_data_being_written.acquire():
                if lockfile.exists():
                    lockfile.unlink()
        copytree(cache_dir.joinpath(version), worker_cache_dir)


def audit_url(url: str, context: str | None = None) -> str:
    """
    Check if the URL is well-formed.

    Parameters
    ----------
    url : str
        The URL to check.
    context : str, optional
        Context for the error message, if the URL is not well-formed.

    Returns
    -------
    str
        The original URL if it is well-formed and uses secure HTTP (https).

    Raises
    ------
    URLError
        If the URL is not well-formed.
    """
    msg = ""
    result = urlparse(url)
    if result.scheme == "http":
        msg = f"{context if context else ''} URL is not using secure HTTP: '{url}'".strip()
    if not all([result.scheme, result.netloc]):
        msg = f"{context if context else ''} URL is not well-formed: '{url}'".strip()

    if msg:
        logger.error(msg)
        raise URLError(msg)
    return url
