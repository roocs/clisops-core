"""A Python package for performing core subsetting and spatial operations in clisops."""

###################################################################################
# BSD 3-Clause License
#
# Copyright (c) 2026, Trevor James Smith
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.
###################################################################################

import warnings

from loguru import logger

from clisops_core._version import __version__ as __version__
from clisops_core.subset import (
    create_mask,
    subset_bbox,
    subset_gridpoint,
    subset_level,
    subset_level_by_values,
    subset_shape,
    subset_time,
    subset_time_by_components,
    subset_time_by_values,
)


def showwarning(message, *args, **kwargs):  # numpydoc ignore=PR01
    """Inject warnings from `warnings.warn` into `loguru`."""
    logger.warning(message)
    showwarning_(message, *args, **kwargs)


showwarning_ = warnings.showwarning
warnings.showwarning = showwarning

# Disable logging for clisops_core and remove the logger that is instantiated on import
logger.disable("clisops_core")
logger.remove()
