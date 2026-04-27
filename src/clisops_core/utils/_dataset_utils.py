"""Dataset utilities."""

import warnings

import cftime
import dask.array as da
import numpy as np
import xarray as xr


__all__ = ["get_coord_by_type", "get_coord_type", "get_main_variable", "is_latitude", "is_level", "is_longitude", "is_realization", "is_time"]


known_coord_types = ["time", "level", "latitude", "longitude", "realization"]


def get_main_variable(ds, exclude_common_coords=True):
    """
    Find the main variable of an xarray Dataset.

    Parameters
    ----------
    ds : xarray.Dataset
        The xarray Dataset to search for the main variable.
    exclude_common_coords : bool
        If True, common coordinates (time, level, latitude, longitude, bounds) are excluded from the search for the
        main variable. Default is True.

    Returns
    -------
    str
        The name of the main variable in the dataset, e.g. 'tas'.
    """
    if isinstance(ds, xr.Dataset):
        variables = list(ds.variables.items())
        data_dims = [data.dims for var_id, data in variables]
    else:
        variables = []
        data_dims = []
    flat_dims = [dim for sublist in data_dims for dim in sublist]

    results = {}
    common_coords = [
        "bnd",
        "bound",
        "lat",
        "lon",
        "time",
        "level",
        "realization_index",
        "realization",
    ]

    for var_id, _data in variables:
        if var_id in flat_dims:
            continue
        if exclude_common_coords is True and any(coord in var_id for coord in common_coords):
            continue
        else:
            results.update({var_id: len(ds[var_id].shape)})
    result = max(results, key=results.get)

    if result is None:
        raise Exception("Could not determine main variable")
    else:
        return result


def get_coord_type(coord: xr.DataArray | xr.Dataset) -> str | None:
    """
    Get the coordinate type.

    Parameters
    ----------
    coord : xarray.DataArray or xarray.Dataset
        Coordinate of xarray dataset, e.g. coord = ds.coords[coord_id].

    Returns
    -------
    str, optional
        The type of coordinate as a string. Either 'longitude', 'latitude', 'time', 'level', 'realization' or None.
    """
    if is_longitude(coord):
        return "longitude"
    elif is_latitude(coord):
        return "latitude"
    elif is_level(coord):
        return "level"
    elif is_time(coord):
        return "time"
    elif is_realization(coord):
        return "realization"

    return None


def get_coord_by_type(
    ds: xr.DataArray | xr.Dataset,
    coord_type: str,
    ignore_aux_coords: bool = True,
    return_further_matches: bool = False,
    warn_if_no_main_variable: bool = True,
):
    """
    Return the name of the coordinate that matches the given type.

    Parameters
    ----------
    ds : xarray.Dataset or xarray.DataArray
        Dataset/DataArray to search for coordinate.
    coord_type : str
        Type of coordinate, e.g. 'time', 'level', 'latitude', 'longitude', 'realization'.
    ignore_aux_coords : bool
        Whether to ignore auxiliary coordinates. Default is True.
    return_further_matches : bool
        Whether to return further matches. Default is False.
    warn_if_no_main_variable : bool
        Whether to warn if no main variable can be identified. Default is True.

    Returns
    -------
    str
        Name of the coordinate that matches the given type.
    str or list of str
        If return_further_matches is True, apart from the matching coordinate,
        a list with further potential matches is returned.

    Raises
    ------
    ValueError
        If the coordinate type is not known.
    """
    # List for all potential matches
    coords = []

    # If coord_type is not in known_coord_types then raise an error
    if coord_type not in known_coord_types:
        raise ValueError(f"Coordinate type not known: {coord_type}")

    # Get main variable ... if possible
    try:
        main_var = get_main_variable(ds)
    except ValueError:
        if warn_if_no_main_variable:
            msg = f"No main variable found for dataset '{ds}'."
            warnings.warn(msg, stacklevel=2)
        main_var = None

    # Loop through all (potential) coordinates to find all possible matches
    if isinstance(ds, xr.DataArray):
        coord_vars = list(ds.coords)
    elif isinstance(ds, xr.Dataset):
        # Not all coordinate variables are always classified as such
        coord_vars = list(ds.coords) + list(ds.data_vars)
        # make sure we skip the main variable!
        if main_var is not None:
            coord_vars.remove(main_var)
    else:
        raise TypeError("Not an xarray.Dataset or xarray.DataArray.")
    for coord_id in coord_vars:
        # If ignore_aux_coords is True, then ignore coords that are not dimensions
        if ignore_aux_coords and coord_id not in ds.dims:
            continue

        coord = ds[coord_id]

        if get_coord_type(coord) == coord_type:
            coords.append(coord_id)

    # Return None if no match
    if len(coords) == 0:
        msg = f"No coordinate variable found for type '{coord_type}'."
        warnings.warn(msg, stacklevel=2)
        return None
    elif len(coords) == 1:
        if return_further_matches:
            return coords[0], []
        else:
            return coords[0]
    # If more than one match is found, a selection has to be made
    else:
        msg = f"More than one coordinate variable found for type '{coord_type}'. Selecting the best fit."
        warnings.warn(msg, stacklevel=2)
        # Sort in terms of number of dimensions
        coords = sorted(coords, key=lambda x: len(ds[x].dims), reverse=True)

        if main_var is not None:
            # Get dimensions and singleton coords of the main variable
            main_var_dims = list(ds[main_var].dims)

            # Select coordinate with most dims (matching with main variable dims)
            for coord_id in coords:
                if coord_id in ds.coords:
                    if all([dim in main_var_dims for dim in ds.coords[coord_id].dims]):
                        if return_further_matches:
                            return coord_id, [x for x in coords if x != coord_id]
                        else:
                            return coord_id
        # If the decision-making fails, pass the first match
        if return_further_matches:
            return coords[0], coords[1:]
        else:
            return coords[0]


def is_latitude(coord: xr.DataArray | xr.Dataset) -> bool:
    """
    Determine if a coordinate is latitude.

    Parameters
    ----------
    coord : xarray.DataArray or xarray.Dataset
        Coordinate of xarray dataset, e.g. coord = ds.coords[coord_id].

    Returns
    -------
    bool
        True if the coordinate is latitude, otherwise False.
    """
    if "latitude" in coord.cf.coordinates and coord.name in coord.cf.coordinates["latitude"]:
        return True

    if "latitude" in coord.cf.standard_names and coord.name in coord.cf.standard_names["latitude"]:
        return True

    if hasattr(coord, "standard_name") and coord.standard_name == "latitude":
        return True

    if hasattr(coord, "long_name") and coord.long_name == "latitude":
        return True

    return False


def is_longitude(coord: xr.DataArray | xr.Dataset) -> bool:
    """
    Determine if a coordinate is longitude.

    Parameters
    ----------
    coord : xarray.DataArray or xarray.Dataset
        Coordinate of xarray dataset, e.g. coord = ds.coords[coord_id].

    Returns
    -------
    bool
        True if the coordinate is longitude, otherwise False.
    """
    if "longitude" in coord.cf.coordinates and coord.name in coord.cf.coordinates["longitude"]:
        return True

    if "longitude" in coord.cf.standard_names and coord.name in coord.cf.standard_names["longitude"]:
        return True

    if hasattr(coord, "standard_name") and coord.standard_name == "longitude":
        return True

    if hasattr(coord, "long_name") and coord.long_name == "longitude":
        return True

    return False


def is_level(coord: xr.DataArray | xr.Dataset) -> bool:
    """
    Determine if a coordinate is level.

    Parameters
    ----------
    coord : xarray.DataArray or xarray.Dataset
        Coordinate of xarray dataset, e.g. coord = ds.coords[coord_id].

    Returns
    -------
    bool
        True if the coordinate is level, otherwise False.
    """
    if "vertical" in coord.cf.coordinates and coord.name in coord.cf.coordinates["vertical"]:
        return True

    if hasattr(coord, "positive"):
        if coord.attrs.get("positive", None) in ["up", "down"]:
            return True

    if hasattr(coord, "axis"):
        if coord.attrs.get("axis", None) == "Z":
            return True

    return False


def _is_time(coord: xr.DataArray | xr.Dataset) -> bool:
    """
    Check if a coordinate uses cftime datetime objects.

    Handles Dask-backed arrays for lazy evaluation.

    Parameters
    ----------
    coord : xarray.DataArray or xarray.Dataset
        Coordinate of xarray dataset, e.g. coord = ds.coords[coord_id].

    Returns
    -------
    bool
        True if the coordinate is time, otherwise False.
    """
    if coord.size == 0:
        return False  # Empty array

    if isinstance(coord.dtype.type(), cftime.datetime):
        return True

    # Safely get the first element without loading the entire array
    first_value = coord.isel({dim: 0 for dim in coord.dims}).values

    # Compute only if it's a Dask array
    if isinstance(first_value, da.Array):
        first_value = first_value.compute()

    return isinstance(first_value.item(0), cftime.datetime)


def is_time(coord: xr.DataArray | xr.Dataset) -> bool:
    """
    Determine if a coordinate is time.

    Parameters
    ----------
    coord : xarray.DataArray or xarray.Dataset
        Coordinate of xarray dataset, e.g. coord = ds.coords[coord_id].

    Returns
    -------
    bool
        True if the coordinate is time, otherwise False.
    """
    if coord.ndim >= 2:
        # skip variables with more than two dimensions: lat_bnds, lon_bnds, time_bnds, t, ...
        return False

    if "time" in coord.cf.coordinates and coord.name in coord.cf.coordinates["time"]:
        return True

    if "time" in coord.cf.standard_names and coord.name in coord.cf.standard_names["time"]:
        return True

    if np.issubdtype(coord.dtype, np.datetime64):
        return True

    if hasattr(coord, "axis"):
        if coord.axis == "T":
            return True

    return _is_time(coord)


def is_realization(coord: xr.DataArray | xr.Dataset) -> bool:
    """
    Determine if a coordinate is realisation.

    Parameters
    ----------
    coord : xarray.DataArray or xarray.Dataset
        Coordinate of xarray dataset, e.g. coord = ds.coords[coord_id].

    Returns
    -------
    bool
        True if the coordinate is realization, otherwise False.
    """
    if "realization" in coord.cf.standard_names and coord.name in coord.cf.standard_names["realization"]:
        return True

    if coord.attrs.get("standard_name", None) == "realization":
        return True

    return False
