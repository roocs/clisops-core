from collections.abc import ByteString

import xarray as xr


def _fix_str_encoding(s: str | ByteString, encoding: str = "utf-8") -> str:
    """
    Helper function to fix string encoding of surrogates.

    Parameters
    ----------
    s : str or byte
        The string to be fixed. If the input is not of type str or bytes,
        it is returned as is.
    encoding : str
        The encoding to be used. Default is "utf-8".

    Returns
    -------
    str
        The fixed string.
    """
    if isinstance(s, bytes):
        # Decode directly from bytes, potentially replacing undecodable sequences
        try:
            decoded = s.decode(encoding, errors="surrogateescape")
        except UnicodeDecodeError:
            decoded = s.decode(encoding, errors="replace")
        return decoded
    elif isinstance(s, str):
        try:
            # If this works, no surrogates present:
            s.encode(encoding)
            return s
        except UnicodeEncodeError:
            # Handle surrogate escapes
            b = s.encode(encoding, "surrogateescape")
            return b.decode(encoding, errors="replace")


def fix_netcdf_attrs_encoding(ds: xr.Dataset, encoding: str = "utf-8") -> xr.Dataset:
    """
    Fix strings that contain invalid chars in Dataset attrs to be safe for NetCDF writing.

    Parameters
    ----------
    ds : xarray.Dataset
        The dataset with attrs to be fixed.
    encoding : str
        The encoding to be used. Default is "utf-8".

    Returns
    -------
    xarray.Dataset
        The dataset with fixed attrs.
    """
    # Work on a shallow copy so original ds is untouched
    ds = ds.copy()

    # Fix global attributes
    for k, v in list(ds.attrs.items()):
        fixed_v = _fix_str_encoding(v, encoding)
        if fixed_v is not v:
            ds.attrs[k] = fixed_v

    # Fix variable attributes
    for var in ds.variables:
        for k, v in list(ds[var].attrs.items()):
            fixed_v = _fix_str_encoding(v, encoding)
            if fixed_v is not v:
                ds[var].attrs[k] = fixed_v

    return ds


# class FileLock:
#     """
#     Create and release a lockfile.

#     Adapted from https://github.com/cedadev/cmip6-object-store/cmip6_zarr/file_lock.py

#     Parameters
#     ----------
#     fpath : str
#         The file path for the lock file to be created.
#     """

#     def __init__(self, fpath):
#         """Initialize Lock for 'fpath'."""
#         self._fpath = fpath
#         dr = os.path.dirname(fpath)
#         if dr and not os.path.isdir(dr):
#             os.makedirs(dr)

#         self.state = "UNLOCKED"

#     def acquire(self, timeout: int = 10):
#         """
#         Create actual lockfile, raise error if already exists beyond 'timeout'.

#         Parameters
#         ----------
#         timeout : int
#             Maximum time in seconds to wait for the lockfile to be created.
#             Default is 10 seconds.

#         Raises
#         ------
#         Exception
#             If the lockfile cannot be created within the specified timeout.
#         """
#         start = dt.now()
#         deadline = start + td(seconds=timeout)

#         while dt.now() < deadline:
#             if not os.path.isfile(self._fpath):
#                 Path(self._fpath).touch()
#                 break

#             time.sleep(3)
#         else:
#             raise Exception(f"Could not obtain file lock on {self._fpath}")

#         self.state = "LOCKED"

#     def release(self):
#         """Release lock, i.e. delete lockfile."""
#         if os.path.isfile(self._fpath):
#             try:
#                 os.remove(self._fpath)
#             except FileNotFoundError:
#                 logger.info("Lock file already removed.")
#                 pass

#         self.state = "UNLOCKED"


# def create_lock(fname: str | Path) -> FileLock | None:
#     """
#     Check whether lockfile already exists and else creates lockfile.

#     Parameters
#     ----------
#     fname : str
#         Path of the lockfile to be created.

#     Returns
#     -------
#     FileLock or None
#         Returns a FileLock object if the lockfile is created successfully,
#         or None if the lockfile already exists.
#     """
#     lock_obj = FileLock(fname)
#     try:
#         lock_obj.acquire(timeout=10)
#         locked = False
#     except Exception as exc:
#         if str(exc) == f"Could not obtain file lock on {fname}":
#             locked = True
#         else:
#             raise Exception(exc)
#     if locked:
#         return None
#     else:
#         return lock_obj
