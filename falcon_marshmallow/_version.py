# -*- coding: utf-8 -*-
"""
version.py module

The version set here will be automatically incorporated into setup.py
and also set as the __version__ attribute for the package.

"dev", "rc", and other verison tags should be added using the
``setup.py egg_info`` command when creating distributions.
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

__version_info__ = (0, 1, 0)
__version__ = '.'.join([str(ver) for ver in __version_info__])
