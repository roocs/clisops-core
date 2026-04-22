import numpy as np


def to_isoformat(tm):
    """
    Return an ISO 8601 string from a time object (of different types).

    Parameters
    ----------
    tm : datetime.datetime or datetime.date or numpy.datetime64 or similar
        A time object that can be converted to an ISO 8601 string.

    Returns
    -------
    str
        An ISO 8601 formatted string representing the time.
    """
    if isinstance(tm, np.datetime64):
        return str(tm).split(".")[0]
    else:
        return tm.isoformat()
