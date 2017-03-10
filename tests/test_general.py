# -*- coding: utf-8 -*-
"""
Test some broad, structural things.
"""

# Std lib
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

# Local
import falcon_marshmallow
from falcon_marshmallow import _version as version


class TestVersion:
    """Test that the _version module is behaving normally"""

    def test_version_info_exists(self):
        """Test that ``__version_info__`` exists and is a tuple"""
        assert isinstance(version.__version_info__, tuple)

    def test_version_parsing(self):
        """Test that ``__version__`` is parsed correctly"""
        split_ver = version.__version__.split('.')
        assert len(split_ver) == 3
        for v in split_ver:
            # Ensure these can be cast to ints without raising errors
            int(v)


class TestPublicInterface:
    """Ensure the public interface does not change"""

    def test_root(self):
        """Ensure the root of the public interface stays consistent"""
        expected_attrs = (
            '__version__',
            '__version_info__',
            'Marshmallow',
            'middleware'
        )
        for attr in expected_attrs:
            assert hasattr(falcon_marshmallow, attr)
