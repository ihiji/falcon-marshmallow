# -*- coding: utf-8 -*-
"""
Middleware class(es) for Falcon-Marshmallow
"""

# Std lib
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)
import logging
from typing import Container, Optional

# Third party
import simplejson as json
from falcon import Request, Response
from falcon.errors import (
    HTTPBadRequest,
    HTTPInternalServerError,
    HTTPNotAcceptable,
    HTTPUnprocessableEntity,
    HTTPUnsupportedMediaType,
)
from marshmallow import Schema


log = logging.getLogger(__name__)


JSON_CONTENT_REQUIRED_METHODS = ('POST', 'PUT', 'PATCH')


class JSONEnforcer:
    """Enforce that requests are JSON compatible"""

    def __init__(self, required_methods=JSON_CONTENT_REQUIRED_METHODS):
        # type: (Container) -> None
        """Initialize the middleware

        :param required_methods: a collection of HTTP methods for
            which "application/json" should be required as a
            Content-Type header
        """
        log.debug('JSONEnforcer.__init__(%s)', required_methods)
        self._methods = required_methods

    def process_request(self, req, resp):
        # type: (Request, Response) -> None
        """Ensure requests accept JSON or specify JSON as content type

        :param req: the passed request object
        :param resp: the passed repsonse object

        :raises HttpNotAcceptable: if the request does not specify
            "application/json" responses as acceptable
        :raises HttpUnsupportedContentType: if a request of a type
            specified by "required_methods" does not specify a
            content-type of "application/json"
        """
        log.debug('JSONEnforcer.process_request(%s, %s)', req, resp)
        if not req.client_accepts_json:
            raise HTTPNotAcceptable(
                description=(
                    'This server only supports responses encoded as JSON. '
                    'Please update your "Accept" header to include '
                    '"application/json".'
                )
            )

        if req.method in JSON_CONTENT_REQUIRED_METHODS:
            if (req.content_type is None or
                    'application/json' not in req.content_type):
                raise HTTPUnsupportedMediaType(
                    description=(
                        '%s requests must have "application/json" in their '
                        '"Content-Type" header.' % req.method
                    )
                )


class EmptyRequestDropper:
    """Check and drop empty requests"""

    def process_request(self, req, resp):
        # type: (Request, Response) -> None
        """Ensure that a request does not contain an empty body

        If a request has content length, but its body is empty,
        raise an HTTPBadRequest error.

        :param req: the passed request object
        :param resp: the passed response object

        :raises HTTPBadRequest: if the request has content length with
            an empty body
        """
        log.debug('EmptyRequestDropper.process_request(%s, %s)', req, resp)
        if req.content_length in (None, 0):
            return

        body = req.stream.read()
        if not body:
            raise HTTPBadRequest(
                description=(
                    'Empty response body. A valid JSON document is required.'
                )
            )


class Marshmallow:
    """Attempt to deserialize objects with any available schemas"""
    
    def __init__(self, req_key='json', resp_key='result', force_json=True,
                 json_module=json):
        # type: (str, str, bool, type(json)) -> None
        """Instantiate the middleware object
        
        :param req_key: (default ``'json'``) the key on the
            ``req.context`` object where the parsed request body
            will be stored
        :param resp_key: (default ``'result'``) the key on the
            ``req.context`` object where the response parser will
            look to find data to serialize into the response body
        :param force_json: (default ``True``) whether requests
            and responses for resources *without* any defined
            Marshmallow schemas should be parsed as json anyway.
        :param json_module: (default ``simplejson``) the json module to
            use for  (de)serialization if no schema is available on a
            resource and ``force_json`` is ``True`` - if you would like
            to use an alternative serializer to the stdlib ``json``
            module for your Marshmallow schemas, you will have to
            specify using a schema metaclass, as defined in the
            `Marshmallow documentation`_

            .. _marshmallow documentation: http://marshmallow.readthedocs.io/
                en/latest/api_reference.html#marshmallow.Schema.Meta

        """
        log.debug(
            'Marshmallow.__init__(%s, %s, %s, %s)',
            req_key, resp_key, force_json, json_module
        )
        self._req_key = req_key
        self._resp_key = resp_key
        self._force_json = force_json
        self._json = json_module

    @staticmethod
    def _get_method_schema(resource, method):
        # type: (object, str) -> Optional[Schema]
        """Return a method-specific schema or None

        If the provided resource has defined a method-specific schema
        that matches the passed method, e.g. 'get_schema' for a 'GET'
        request or 'post_schema" for a 'POST' request, return that
        schema.

        Return ``None`` if no matching schema exists

        :param resource: the resource object passed to
            ``process_response`` or ``process_resource``
        :param method: the (case-insensitive) HTTP method used
            for the request, e.g. 'GET' or 'POST'
        """
        log.debug('Marshmallow._get_method_schema(%s, %s)', resource, method)
        sch_name = '%s_schema' % method.lower()
        return getattr(resource, sch_name, None)

    @classmethod
    def _get_schema(cls, resource, method):
        # type: (object, str) -> Optional[Schema]
        """Return a method-specific schema, a generic schema, or None

        If the provided resource has defined a method-specific schema
        that matches the passed method, e.g. 'get_schema' for a 'GET'
        request or 'post_schema" for a 'POST' request, return that
        schema.

        Otherwise, if the provided resource has defined a generic
        schema under ``resource.schema``, return that schema.

        Return ``None`` if neither of the above is found

        :param resource: the resource object passed to
            ``process_response`` or ``process_resource``
        :param method: the (case-insensitive) HTTP method used
            for the request, e.g. 'GET' or 'POST'
        """
        log.debug('Marshmallow._get_schema(%s, %s)', resource, method)
        method_schema = cls._get_method_schema(resource, method)
        if method_schema is not None:
            return method_schema
        return getattr(resource, 'schema', None)

    def process_resource(self, req, resp, resource, params):
        # type: (Request, Response, object, dict) -> None
        """Deserialize request body with any resource-specific schemas

        Store deserialized data on the ``req.context`` object
        under the ``req_key`` provided to the class constructor
        or on the ``json`` key if none was provided.

        If a Marshmallow schema is defined on the passed ``resource``,
        use it to deserialize the request body.

        If no schema is defined and the class was instantiated with
        ``force_json=True``, request data will be deserialized with
        any ``json_module`` passed to the class constructor or
        ``simplejson`` by default.

        :param falcon.Request req: the request object
        :param falcon.Response resp: the response object
        :param object resource: the resource object
        :param dict params: any parameters parsed from the url

        :rtype: None
        :raises falcon.HTTPBadRequest: if the data cannot be
            deserialized or decoded
        """
        log.debug(
            'Marshmallow.process_resource(%s, %s, %s, %s)',
            req, resp, resource, params
        )
        if req.content_length in (None, 0):
            return

        sch = self._get_schema(resource, req.method)

        if sch is not None:
            if not isinstance(sch, Schema):
                raise TypeError(
                    'The schema and <method>_schema properties of a resource '
                    'must be instantiated Marshmallow schemas.'
                )

            try:
                body = req.stream.read().decode('utf-8')
                parsed = self._json.loads(body)
            except UnicodeDecodeError:
                raise HTTPBadRequest('Body was not encoded as UTF-8')
            except self._json.JSONDecodeError:
                raise HTTPBadRequest('Request must be valid JSON')

            data, errors = sch.load(parsed)

            if errors:
                raise HTTPUnprocessableEntity(
                    description=self._json.dumps(errors)
                )

            req.context[self._req_key] = data

        elif self._force_json:

            body = req.stream.read()
            try:
                req.context[self._req_key] = self._json.loads(
                    body.decode('utf-8')
                )
            except (ValueError, UnicodeDecodeError):
                raise HTTPBadRequest(
                    description=(
                        'Could not decode the request body, either because '
                        'it was not valid JSON or because it was not encoded '
                        'as UTF-8.'
                    )
                )

    def process_response(self, req, resp, resource, req_succeeded):
        # type: (Request, Response, object, bool) -> None
        """Serialize the result and dump it in ``resp.body``

        Look in the ``req.context`` for the ``req_key`` provided to
        the constructor of this function, or ``result`` if not
        provided. If not found, return.

        If a Marshmallow schema is defined for the given ``resource``,
        use it to serialize the result.

        If no schema is defined and the class was instantiated with
        ``force_json=True``, request data will be serialized with
        any ``json_module`` passed to the class constructor or
        ``simplejson`` by default.

        :param falcon.Request req: the request object
        :param falcon.Response resp: the response object
        :param object resource: the resource object
        :param bool req_succeeded: whether the request was successful

        :raises falcon.HTTPInternalServerError: if the data found
            in the ``req.context`` object cannot be serialized
        """
        log.debug(
            'Marshmallow.process_response(%s, %s, %s, %s)',
            req, resp, resource, req_succeeded
        )
        if self._resp_key not in req.context:
            return

        sch = self._get_schema(resource, req.method)

        if sch is not None:
            if not isinstance(sch, Schema):
                raise TypeError(
                    'The schema and <method>_schema properties of a resource '
                    'must be instantiated Marshmallow schemas.'
                )

            data, errors = sch.dumps(req.context[self._resp_key])

            if errors:
                raise HTTPInternalServerError(
                    title='Could not serialize response',
                    description=json.dumps(errors)
                )

            resp.body = data

        elif self._force_json:
            try:
                resp.body = self._json.dumps(req.context[self._resp_key])
            except TypeError:
                raise HTTPInternalServerError(
                    title='Could not serialize response',
                    description=(
                        'The server attempted to serialize an object that '
                        'cannot be serialized. This is likely a server-side '
                        'bug.'
                    )
                )
