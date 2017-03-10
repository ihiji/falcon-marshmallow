# -*- coding: utf-8 -*-
"""
Tests for falcon_marshmallow.middleware
"""

# Std lib
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

try:
    from unittest import mock
except ImportError:
    import mock

from typing import Optional

# Third party
import pytest
from falcon import errors
from marshmallow import fields, Schema

# Local
from falcon_marshmallow import middleware as mid


class TestMarshmallow:
    """Test Marshmallow middleware"""

    mw = mid.Marshmallow()

    class FooSchema(Schema):
        """Convert foo to bar for testing purposes"""
        bar = fields.String(load_from='foo', dump_to='foo')
        int = fields.Integer()

    def test_instantiation(self):
        """Test instantiating the class"""
        mid.Marshmallow()

    @pytest.mark.parametrize('method, attr_name, has_sch', [
        ('GET', 'get_schema', True),
        ('get', 'get_schema', True),
        ('get', 'schema', False),
        ('get', 'put_schema', False),
        ('POST', 'post_schema', True),
        ('post', 'post_schema', True),
        ('POST', 'schema', False),
        ('POST', 'get_schema', False),
        ('PATCH', 'patch_schema', True),
        ('patch', 'patch_schema', True),
        ('PUT', 'put_schema', True),
        ('put', 'put_schema', True),
        ('DELETE', 'delete_schema', True),
        ('delete', 'delete_schema', True),
    ])
    def test_get_method_schema(self, method, attr_name, has_sch):
        # type: (str, str, bool) -> None
        """Test getting a method-specific schema from a resource"""

        class TestResource:
            """Quick test object"""
            def __init__(self):
                setattr(self, attr_name, 'foo')

        tr = TestResource()

        sch = mid.Marshmallow._get_method_schema(tr, method)

        if has_sch:
            assert sch == 'foo'

        else:
            assert sch is None

    @pytest.mark.parametrize('method, attrs, exp_value', [
        ('GET', (('get_schema', 'foo'), ('schema', 'bar')), 'foo'),
        (
            'GET',
            (('get_schema', 'foo'), ('schema', 'bar'), ('post_schema', 'baz')),
            'foo'
        ),
        ('GET', (('post_schema', 'foo'), ('schema', 'bar')), 'bar'),
        ('GET', (('schema', 'bar'), ), 'bar'),
        ('GET', (), None),
    ])
    def test_get_schema(self, method, attrs, exp_value):
        # type: (str, tuple, str) -> None
        """Test getting a general or method-specific schema"""

        class TestResource:
            """Quick test object"""
            def __init__(self):
                for attr_name, value in attrs:
                    setattr(self, attr_name, value)

        tr = TestResource()

        val = mid.Marshmallow()._get_schema(tr, method)

        if exp_value is None:
            assert val is None
        else:
            assert val == exp_value

    @pytest.mark.parametrize(
        'stream, schema, schema_err, bad_sch, bad_uni, force_json, json_err, '
        'exp_ret', [
            (  # Good schema
                '{"foo": "test"}',
                True,
                False,
                False,
                False,
                False,
                False,
                {'bar': 'test'}
            ),
            (  # Schema errors on load
                '{"foo": "test", "int": "test"}',
                True,
                True,
                False,
                False,
                False,
                False,
                {'bar': 'test'}
            ),
            (  # Good schema, bad unicode in body
                '{"foo": "test"}',
                True,
                False,
                False,
                True,
                False,
                False,
                {'bar': 'test'}
            ),
            (  # Bad schema
                '{"foo": "test"}',
                True,
                False,
                True,
                False,
                False,
                False,
                {'bar': 'test'}
            ),
            (  # No schema, no force json (no change to req.context)
                '{"foo": "test"}',
                False,
                False,
                False,
                False,
                False,
                False,
                {'bar': 'test'}
            ),
            (  # No schema, force json
                '{"foo": "test"}',
                False,
                False,
                False,
                False,
                True,
                False,
                {'foo': 'test'}
            ),
            (  # No schema, force json, bad json
                '{"foo": }',
                False,
                False,
                False,
                False,
                True,
                True,
                {'foo': 'test'}
            ),
            (  # No schema, force json, good json, bad unicode
                '{"foo": "test"}',
                False,
                False,
                False,
                True,
                True,
                False,
                {'foo': 'test'}
            ),
        ]
    )
    def test_process_resource(self, stream, schema, schema_err, bad_sch,
                              bad_uni, force_json, json_err, exp_ret):
        # type: (str, bool, bool, bool, bool, bool, bool, dict) -> None
        """Test processing a resource

        :param stream: the return of req.stream.read()
        :param schema: whether a schema should be returned (TestSchema)
        :param schema_err: whether a schema error is expected
        :param bad_sch: pass an uninstantiated or non-schema object
        :param bad_uni: whether bad unicode is expected
        :param force_json: whether to try json if no schema is found
        :param json_err: whether a JSON error is expected
        :param exp_ret: expected return if no errors are raised
        """
        mw = mid.Marshmallow()

        mw._force_json = force_json
        if schema:
            if bad_sch:
                mw._get_schema = lambda *x, **y: self.FooSchema
            else:
                mw._get_schema = lambda *x, **y: self.FooSchema()
        else:
            mw._get_schema = lambda *x, **y: None

        req = mock.Mock(method='GET')
        if not bad_uni:
            req.stream.read.return_value = stream.encode()
        else:
            req.stream.read.return_value = stream.encode() + b'\xe7'
        req.context = {}

        if schema_err:
            with pytest.raises(errors.HTTPUnprocessableEntity):
                # noinspection PyTypeChecker
                mw.process_resource(req, 'foo', 'foo', 'foo')
            return
        if bad_uni:
            with pytest.raises(errors.HTTPBadRequest):
                # noinspection PyTypeChecker
                mw.process_resource(req, 'foo', 'foo', 'foo')
            return
        if bad_sch:
            with pytest.raises(TypeError):
                # noinspection PyTypeChecker
                mw.process_resource(req, 'foo', 'foo', 'foo')
            return
        if json_err:
            with pytest.raises(errors.HTTPBadRequest):
                # noinspection PyTypeChecker
                mw.process_resource(req, 'foo', 'foo', 'foo')
            return

        # noinspection PyTypeChecker
        mw.process_resource(req, 'foo', 'foo', 'foo')
        if schema or force_json:
            assert req.context[mw._req_key] == exp_ret
        else:
            assert mw._req_key not in req.context

    @pytest.mark.parametrize(
        'res, schema, sch_err, bad_sch, force_json, json_err, exp_ret', [
            (  # Good result, good schema
                {'bar': 'test'},
                True,
                False,
                False,
                False,
                False,
                '{"foo": "test"}'
            ),
            (  # Schema error on loading result
                {'bar': 'test', 'int': 'foo'},
                True,
                True,
                False,
                False,
                False,
                '{"foo": "test"}'
            ),
            (  # Bad schema instance (not an instance)
                {'bar': 'test'},
                True,
                False,
                True,
                False,
                False,
                '{"foo": "test"}'
            ),
            (  # Good result, no schema, force json
                {'bar': 'test'},
                False,
                False,
                False,
                True,
                False,
                '{"bar": "test"}'
            ),
            (  # Unserializable response, no schema, force json
                set('foo'),
                False,
                False,
                False,
                True,
                True,
                '{"bar": "test"}'
            ),
            (  # No schema, no force json
                {'bar': 'test'},
                False,
                False,
                False,
                False,
                False,
                '{"foo": "test"}'
            ),
            (  # No result
                None,
                True,
                False,
                False,
                False,
                False,
                '{"foo": "test"}'
            ),
        ]
    )
    def test_process_response(self, res, schema, sch_err, bad_sch, force_json,
                              json_err, exp_ret):
        """Test process_response

        :param res: the value to put in the result key on req.context
        :param schema: whether a schema should be available
        :param sch_err: whether an error is expected dumping the data
        :param bad_sch: pass an uninstantiated or non-schema object
        :param force_json: whether force_json is true
        :param json_err: whether an error is expected dumping the data
        :param exp_ret: expected return if no errors are raised
        """
        mw = mid.Marshmallow()

        mw._force_json = force_json
        if schema:
            if bad_sch:
                mw._get_schema = lambda *x, **y: self.FooSchema
            else:
                mw._get_schema = lambda *x, **y: self.FooSchema()
        else:
            mw._get_schema = lambda *x, **y: None

        req = mock.Mock(method='GET')
        if res is None:
            req.context = {}
        else:
            req.context = {mw._resp_key: res}

        resp = mock.Mock()

        if bad_sch:
            with pytest.raises(TypeError):
                # noinspection PyTypeChecker
                mw.process_response(req, resp, 'foo', 'foo')
            return
        if sch_err:
            with pytest.raises(errors.HTTPInternalServerError):
                # noinspection PyTypeChecker
                mw.process_response(req, resp, 'foo', 'foo')
            return
        if json_err:
            with pytest.raises(errors.HTTPInternalServerError):
                # noinspection PyTypeChecker
                mw.process_response(req, resp, 'foo', 'foo')
            return

        # noinspection PyTypeChecker
        mw.process_response(req, resp, 'foo', 'foo')
        if res is None or (not schema and not force_json):
            # "body" has not been written, and is thus a mock object still
            assert isinstance(resp.body, mock.Mock)
        else:
            assert resp.body == exp_ret


class TestJSONEnforcer:
    """Test enforcement of JSON requests"""

    enforcer = mid.JSONEnforcer()

    @pytest.mark.parametrize('accepts', [True, False])
    def test_client_accept(self, accepts):
        # type: (bool) -> None
        """Test asserting that the client accepts JSON"""
        req = mock.Mock()
        req.client_accepts_json = accepts
        req.method = 'GET'

        if not accepts:
            with pytest.raises(errors.HTTPNotAcceptable):
                # noinspection PyTypeChecker
                self.enforcer.process_request(req, 'foo')
        else:
            # noinspection PyTypeChecker
            self.enforcer.process_request(req, 'foo')

    @pytest.mark.parametrize('method, content_type, raises', [
        ('GET', None, False),
        ('GET', 'application/json', False),
        ('GET', 'mimetype/xml', False),
        ('POST', None, True),
        ('POST', 'application/json', False),
        ('POST', 'mimetype/xml', True),
        ('PATCH', None, True),
        ('PATCH', 'application/json', False),
        ('PATCH', 'mimetype/xml', True),
        ('PUT', None, True),
        ('PUT', 'application/json', False),
        ('PUT', 'mimetype/xml', True),
        ('DELETE', None, False),
        ('DELETE', 'application/json', False),
        ('DELETE', 'mimetype/xml', False),
    ])
    def test_method_content_type(self, method, content_type, raises):
        # type: (str, Optional[str], bool) -> None
        """Test checking of content-type for certain methods"""
        req = mock.Mock(client_accepts_json=True)
        req.method = method
        req.content_type = content_type

        if raises:
            with pytest.raises(errors.HTTPUnsupportedMediaType):
                # noinspection PyTypeChecker
                self.enforcer.process_request(req, 'foo')
        else:
            # noinspection PyTypeChecker
            self.enforcer.process_request(req, 'foo')


class TestEmptyRequestDropper:
    """Tests for the empty request dropper"""

    dropper = mid.EmptyRequestDropper()

    @pytest.mark.parametrize('content_length', [None, 0])
    def test_ignore_when_no_content_length(self, content_length):
        # type: (Optional[int]) -> None
        """Test that we drop out with no content_length"""
        req = mock.Mock(content_length=content_length, )

        # noinspection PyTypeChecker
        self.dropper.process_request(req, 'foo')

        # Assert we didn't go past the first return
        req.stream.read.assert_not_called()

    @pytest.mark.parametrize('read', ['foo', ''])
    def test_raise_on_empty_body(self, read):
        # type: (str) -> None
        """Test that we raise if we get an empty body"""
        req = mock.Mock(content_length=10)
        req.stream.read.return_value = read

        if not read:
            with pytest.raises(errors.HTTPBadRequest):
                # noinspection PyTypeChecker
                self.dropper.process_request(req, 'foo')
        else:
            # noinspection PyTypeChecker
            self.dropper.process_request(req, 'foo')
