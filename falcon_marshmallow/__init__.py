# -*- coding: utf-8 -*-
"""
Middleware to integrate Marshmallow with Falcon
"""

from ._version import __version__, __version_info__

from .middleware import EmptyRequestDropper, JSONEnforcer, Marshmallow
