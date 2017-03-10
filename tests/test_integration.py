# -*- coding: utf-8 -*-
"""
Tests for full integration with a Falcon app
"""

# Std lib
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)
import logging
from datetime import date
from uuid import uuid1

# Third party
import pytest
import simplejson as json
from falcon import API, status_codes, testing
from marshmallow import fields, Schema

# Local
from falcon_marshmallow import middleware as m


log = logging.getLogger(__name__)


class Philosopher(Schema):
    """Philosopher schema"""
    id = fields.String()
    name = fields.String()
    birth = fields.Date()
    death = fields.Date()
    schools = fields.List(fields.String())
    works = fields.List(fields.String())


class DataStore:
    """Simple key-value store for testing.

    The initialized store contains one item, whose key id is
    'first'.
    """

    def __init__(self):
        self.store = {
            'first': {
                'id': 'first',
                'name': 'Søren Kierkegaard',
                'birth': date(1813, 5, 5),
                'death': date(1855, 11, 11),
                'schools': ['existentialism'],
                'works': ['Fear and Trembling', 'Either/Or']
            }
        }

    def get(self, key):
        """Get an object from the store"""
        return self.store.get(key)

    def insert(self, obj):
        """Insert a new object into the store"""
        key = str(uuid1())
        obj['id'] = key
        self.store[key] = obj
        return obj

    def clear(self):
        """Clear the store of all data"""
        self.__init__()


@pytest.fixture()
def hydrated_client():
    """A Falcon API with an endpoint for testing Marshmallow"""
    data_store = DataStore()

    class PhilosopherResource:

        schema = Philosopher()

        def on_get(self, req, resp, phil_id):
            """Get a philosopher"""
            req.context['result'] = data_store.get(phil_id)

    class PhilosopherCollection:

        schema = Philosopher()

        def on_post(self, req, resp):
            req.context['result'] = data_store.insert(req.context['json'])

    app = API(middleware=[m.Marshmallow()])

    app.add_route('/philosophers', PhilosopherCollection())
    app.add_route('/philosophers/{phil_id}', PhilosopherResource())

    yield testing.TestClient(app)

    data_store.clear()


class TestMarshmallowMiddleware:
    """Test Marshmallow middleware"""

    def test_get(self, hydrated_client):
        # type: (testing.TestClient) -> None
        """Test getting the pre-populated philosopher"""
        resp = hydrated_client.simulate_get(
            '/philosophers/first'
        )  # type: testing.Result
        assert resp.status_code == 200
        parsed = resp.json
        assert parsed['id'] == 'first'
        assert parsed['name'] == 'Søren Kierkegaard'
        assert parsed['birth'] == '1813-05-05'  # proper serialization to ISO

    def test_post(self, hydrated_client):
        # type: (testing.TestClient) -> None
        """Test posting a new philosopher"""
        phil = {
            'name': 'Albert Camus',
            'birth': date(1913, 11, 7).isoformat(),
            'death': date(1960, 1, 4).isoformat(),
            'schools': ['existentialism', 'absurdism'],
            'works': ['The Stranger', 'The Myth of Sisyphus']
        }
        resp = hydrated_client.simulate_post(
            '/philosophers',
            body=json.dumps(phil).encode()
        )  # type: testing.Result
        assert resp.status_code == 200
        parsed = resp.json
        assert 'id' in parsed

        resp = hydrated_client.simulate_get(
            '/philosophers/%s' % parsed['id']
        )  # type: testing.Result
        assert resp.status_code == 200
        got = resp.json
        assert got['id'] == parsed['id']
        assert got['name'] == 'Albert Camus'
        assert got['birth'] == '1913-11-07'

    def test_post_unprocessable_entitty(self, hydrated_client):
        # type: (testing.TestClient) -> None
        """Test posting with a bad date"""
        phil = {
            'name': 'Albert Camus',
            'birth': 'a long time ago',
            'death': date(1960, 1, 4).isoformat(),
            'schools': ['existentialism', 'absurdism'],
            'works': ['The Stranger', 'The Myth of Sisyphus']
        }
        resp = hydrated_client.simulate_post(
            '/philosophers',
            body=json.dumps(phil).encode()
        )  # type: testing.Result
        assert resp.status == status_codes.HTTP_UNPROCESSABLE_ENTITY
        parsed = resp.json
        # Validate that our validator told us which field was invalid
        assert 'birth' in parsed['description']

    @pytest.mark.parametrize('body', [
        '{::'.encode(),  # invalid json bytes
        '{::',  # bad json unicode
        '{"foo": "bar"}'.encode() + b'\xe7'  # bad unicode
    ])
    def test_post_bad_requests(self, hydrated_client, body):
        # type: (testing.TestClient) -> None
        """Test posting with invalid JSON"""
        resp = hydrated_client.simulate_post(
            '/philosophers',
            body=body
        )  # type: testing.Result
        assert resp.status == status_codes.HTTP_BAD_REQUEST


class TestExtraMiddleware:
    """Test the enforcement of convenience middleware"""

    @pytest.mark.parametrize('endpoint, accepts, required, endpoint_exists', [
        ('/foo', True, True, False),
        ('/foo', False, True, False)
    ])
    def test_accepts_json_required(self, endpoint, accepts, required,
                                   endpoint_exists):
        # type: (str, bool, bool, bool) -> None
        """Test that application/json is required in the accepts header

        Note ``required`` is always true at the moment, because the
        middleware applies to all requests with no exceptions. If
        that changes, add parameters above.

        The endpoint here does not really matter, because
        ``process_request`` middleware, which handles enforcement
        of the accept header, is processed before routing. However,
        the ``endpoint_exists`` option is provided in case it is
        necessary in the future to ensure this is called against
        a real endpoint.
        """
        client = testing.TestClient(API(middleware=[m.JSONEnforcer()]))

        if accepts:
            heads = {'Accept': str('application/json')}
        else:
            heads = {'Accept': str('mimetype/xml')}

        res = client.simulate_get(
            endpoint, headers=heads
        )  # type: testing.Result

        if required:
            if accepts:
                if endpoint_exists:
                    assert bool(
                        200 <= res.status_code < 300 or
                        res.status_code == status_codes.HTTP_METHOD_NOT_ALLOWED
                    )
                else:
                    assert res.status == status_codes.HTTP_NOT_FOUND
            else:
                assert res.status == status_codes.HTTP_NOT_ACCEPTABLE
        else:
            # Not currently needed or implemented
            pass

    @pytest.mark.parametrize(
        'endpoint, method, ct_is_json, endpoint_exists, required', [
            ('/foo', 'GET', False, False, True),
            ('/foo', 'GET', True, False, True),
            ('/foo', 'DELETE', False, False, True),
            ('/foo', 'DELETE', True, False, True),
            ('/foo', 'POST', False, False, True),
            ('/foo', 'POST', True, False, True),
            ('/foo', 'PATCH', False, False, True),
            ('/foo', 'PATCH', True, False, True),
            ('/foo', 'PUT', False, False, True),
            ('/foo', 'PUT', True, False, True),
        ]
    )
    def test_content_type_json_required(self, endpoint, method,
                                        endpoint_exists, ct_is_json, required):
        # type: (str, str, bool, bool, bool) -> None
        """Test HTTP methods that should reuquire content-type json

        Note ``required`` is always true at the moment, because the
        middleware applies to all requests with no exceptions. If
        that changes, add parameters above.

        The endpoint here does not really matter, because
        ``process_request`` middleware, which handles enforcement
        of the accept header, is processed before routing. However,
        the ``endpoint_exists`` option is provided in case it is
        necessary in the future to ensure this is called against
        a real endpoint.
        """
        client = testing.TestClient(API(middleware=[m.JSONEnforcer()]))

        if ct_is_json:
            heads = {'Content-Type': str('application/json')}
        else:
            heads = {}

        res = client.simulate_request(
            method=str(method), path=endpoint, headers=heads
        )  # type: testing.Result

        meth_not_allowed = status_codes.HTTP_METHOD_NOT_ALLOWED
        if required:
            if method in m.JSON_CONTENT_REQUIRED_METHODS:
                # Ensure that non-json content type is denied
                if ct_is_json:
                    if endpoint_exists:
                        assert bool(
                            200 <= res.status_code < 300 or
                            res.status_code == meth_not_allowed
                        )
                    else:
                        assert res.status == status_codes.HTTP_NOT_FOUND
                else:
                    exp_code = status_codes.HTTP_UNSUPPORTED_MEDIA_TYPE
                    assert res.status == exp_code
            else:
                # We shouldn't deny for non-json content type
                if endpoint_exists:
                    assert bool(
                        200 <= res.status_code < 300 or
                        res.status_code == meth_not_allowed
                    )
                else:
                    assert res.status == status_codes.HTTP_NOT_FOUND
        else:
            # No endpoints for which this is applicable exist at the moment
            pass

    @pytest.mark.parametrize(
        'empty_body, endpoint, endpoint_exists', [
            (False, '/foo', False),
            (True, '/foo', False),
        ]
    )
    def test_empty_requests_dropped(self, empty_body, endpoint,
                                    endpoint_exists):
        # type: (bool, str, bool) -> None
        """Test that empty requests are dropped before routing

        Note that content_length is None if not explicitly set,
        so HEAD, GET, etc. requests are fine.
        """
        client = testing.TestClient(API(middleware=[m.EmptyRequestDropper()]))

        # We have to forge the content-length header, because if it is
        # made automatically for our empty body, we won't get to the check
        # of the body contents.
        heads = {'Content-Length': str('20')} if empty_body else None
        body = '' if empty_body else None

        res = client.simulate_get(
            endpoint, body=body, headers=heads
        )  # type: testing.Result

        if empty_body:
            assert res.status == status_codes.HTTP_BAD_REQUEST
        else:
            if endpoint_exists:
                assert bool(
                    200 <= res.status_code < 300 or
                    res.status_code == status_codes.HTTP_METHOD_NOT_ALLOWED
                )
            else:
                assert res.status == status_codes.HTTP_NOT_FOUND
