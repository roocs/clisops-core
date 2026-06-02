"""Common utilities for CLISOPS-core."""

import functools
import sys
import warnings
from collections.abc import Callable
from types import FunctionType, ModuleType

import xarray as xr
from loguru import logger
from packaging.version import Version


# Try importing xesmf and set to None if not found at correct version
# If set to None, the `require_module` decorator will throw an exception
XESMF_MINIMUM_VERSION = "0.8.10"
try:
    import xesmf as xe

    if Version(xe.__version__) < Version(XESMF_MINIMUM_VERSION):
        msg = f"xESMF >= {XESMF_MINIMUM_VERSION} is required to use the regridding operations."
        warnings.warn(msg, stacklevel=2)
        raise ValueError(msg)
except (ModuleNotFoundError, ValueError):
    xe = None

# FIXME: Remove this when xarray addresses https://github.com/pydata/xarray/issues/7794
XARRAY_INCOMPATIBLE_VERSION = "2023.3.0"
XARRAY_COMPATIBLE_VERSION = "2025.6.0"
XARRAY_WARNING_MESSAGE = (
    f"xarray versions between {XARRAY_INCOMPATIBLE_VERSION} and {XARRAY_COMPATIBLE_VERSION} "
    f"are not supported for regridding operations with cf-time indexed arrays. "
    f"Please use xarray version >= {XARRAY_COMPATIBLE_VERSION}. "
    "For more information, see: https://github.com/pydata/xarray/issues/7794."
)


def _logging_examples() -> None:
    """Testing module."""
    logger.trace("0")
    logger.debug("1")
    logger.info("2")
    logger.success("2.5")
    logger.warning("3")
    logger.error("4")
    logger.critical("5")


def enable_logging() -> list[int]:
    """
    Enable logging for CLISOPS.

    Returns
    -------
    list[int]
        List of enabled log levels, e.g., [10, 20, 30, 40, 50].
    """
    logger.enable("clisops")

    config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS Z UTC}</>"
                " <red>|</> <lvl>{level}</> <red>|</> <cyan>{name}:{function}:{line}</>"
                " <red>|</> <lvl>{message}</>",
                "level": "INFO",
            },
            {
                "sink": sys.stderr,
                "format": "<red>{time:YYYY-MM-DD HH:mm:ss.SSS Z UTC} | {level} | {name}:{function}:{line} | {message}</>",
                "level": "WARNING",
            },
        ]
    }
    return logger.configure(**config)


def require_module(
    func: FunctionType,
    module: ModuleType,
    module_name: str,
    min_version: str | None = None,
    unsupported_version_range: list | tuple[str, str] | None = None,
    max_supported_version: str | None = None,
    max_supported_warning: str | None = None,
) -> Callable:
    """
    Ensure that module is installed before function/method is called, decorator.

    Parameters
    ----------
    func : FunctionType
        The function to be decorated.
    module : ModuleType
        The module to check for availability.
    module_name : str
        The name of the module to check.
    min_version : str, optional
        The minimum version of the module required. Defaults to "0.0.0".
    unsupported_version_range : list of str or tuple of str, optional
        A list with two elements, with the elements marking a range of unsupported versions,
        with the first element being the first unsupported and the second element being
        the first supported version.
        If provided, a warning will be issued if the module version falls within this range:
        version_0 <= module_version < version_1
        Defaults to None, meaning no unsupported version range check is performed.
    max_supported_version : str, optional
        The maximum supported version of the module.
        If provided, a warning will be issued if the module version exceeds this.
        Defaults to None, meaning no maximum version check is performed.
    max_supported_warning : str, optional
        The warning message to display if the module version exceeds the maximum supported version.

    Returns
    -------
    FunctionType
        The decorated function that checks for the module's availability and version before execution.
    """

    @functools.wraps(func)
    def wrapper_func(*args, **kwargs):  # numpydoc ignore=GL08
        exception_msg = f"Package {module_name} >= {min_version} is required to use {func}."
        if Version(module.__version__) < Version(min_version):
            raise ImportError(exception_msg)

        if max_supported_version is not None:
            if Version(module.__version__) > Version(max_supported_version):
                if max_supported_warning is not None:
                    warnings.warn(max_supported_warning, stacklevel=2)
                else:
                    warnings.warn(
                        f"Package {module_name} version {module.__version__} is greater than the suggested version {max_supported_version}.",
                        stacklevel=2,
                    )

        if unsupported_version_range is not None:
            if not isinstance(unsupported_version_range, list | tuple) or not len(unsupported_version_range) == 2:
                raise ValueError(
                    "The unsupported_version_range argument must be a list or tuple with two elements of type str, "
                    "with the elements being the minimum and maximum versions of an unsupported version range."
                )
            if Version(module.__version__) >= Version(unsupported_version_range[0]) and Version(module.__version__) < Version(
                unsupported_version_range[1]
            ):
                warnings.warn(max_supported_warning, stacklevel=2)

        return func(*args, **kwargs)

    return wrapper_func


# Check if xESMF module is imported - decorator, used below
require_xesmf = functools.partial(require_module, module=xe, module_name="xESMF", min_version=XESMF_MINIMUM_VERSION)

# Check if xarray version is compatible - decorator, used below
require_xarray = functools.partial(
    require_module,
    module=xr,
    module_name="xarray",
    unsupported_version_range=[XARRAY_INCOMPATIBLE_VERSION, XARRAY_COMPATIBLE_VERSION],
    max_supported_warning=XARRAY_WARNING_MESSAGE,
)
