falcon-marshmallow
==================

Marshmallow serialization/deserialization middleware for Falcon

=============   ==================================================
Maintained By   `Ihiji, Inc.`_
Author          `Matthew Planchard`_
License         `MIT`_
Contributors    `Your Name Here!`_
=============   ==================================================

.. _Ihiji, Inc.: https://github.com/ihiji
.. _Matthew Planchard: https://github.com/mplanchard
.. _MIT: https://github.com/ihiji/falcon-marshmallow/blob/master/LICENSE
.. _Your Name Here!: Contributing_

Usage
-----

The primary middleware provided by this package is called ``Marshmallow``. To
use it, simply add it to your Falcon app instantiation::

    from falcon import API
    from falcon_marshmallow import Marshmallow

    app = API(
        middleware=[
            Marshmallow(),
        ]
    )

The Marshmallow middleware looks for schemas defined on your resources, and,
if it finds an applicable schema, uses it to serialize incoming requests
and deserialize outgoing responses. Schema attributes should either be
named ``schema`` or ``<method>_schema``, where ``<method>`` is an HTTP method. If
both an appropriate method schema and a general schema are defined, the
method schema takes precedence.

Marshmallow assumes JSON serialization and uses the standard library's
``json`` module, but if you specify a different serialization module in a
schema's Meta class, that will be seamlessly integrated into this library's
(de)serialization.

By default, if no schema is found, the Marshmallow middleware will still
attempt to (de)serialize data using the ``simplejson`` module. This can be
disabled when instantiating the middleware by setting ``force_json`` to
``False``.

Two extra middleware classes are provided for convenience:

* ``JSONEnforcer`` raises an ``HTTPNotAcceptable`` error if the client request
  indicates that it will does not accept JSON and ensures that the Content-Type
  of requests is "application/json" for specified HTTP methods (default PUT,
  POST, PATCH).
* ``EmptyRequestDropper`` returns an ``HTTPBadRequest`` if a request has
  a non-zero Content-Length header with an empty body


Examples
++++++++


Standard ReST Resource
~~~~~~~~~~~~~~~~~~~~~~

Let's look at a standard ReST resource corresponding to a Philosopher
resource in our chosen data store::

    from datetime import date
    from random import randint

    from marshmallow import fields, Schema
    from falcon import API
    from falcon_marshmallow import Marshmallow
    from wsgiref import simple_server


    class MyDataStore:
        """Whatever DB driver you like"""

        def get(self, table, phil_id):
            print('I got item with id %s from %s' % (phil_id, table))
            return {
                'id': phil_id,
                'name': 'Albert Camus',
                'birth': date(1913, 11, 7),
                'death': date(1960, 1, 4),
                'schools': ['existentialism', 'absurdism'],
                'works': ['The Stranger', 'The Myth of Sissyphus']
            }

        def insert(self, table, obj):
            print('I inserted %s into %s' % (obj, table))
            return {
                'id': randint(1, 100),
                'name': 'Søren Kierkegaard',
                'birth': date(1813, 5, 5),
                'death': date(1855, 11, 11),
                'schools': ['existentialism'],
                'works': ['Fear and Trembling', 'Either/Or']
            }


    class Philosopher(Schema):
        """Philosopher schema"""
        id = fields.Integer()
        name = fields.String()
        birth = fields.Date()
        death = fields.Date()
        schools = fields.List(fields.String())
        works = fields.List(fields.String())


    class PhilosopherResource:

        schema = Philosopher()

        def on_get(self, req, resp, phil_id):
            """req['result'] will be automatically serialized

            The key in which results are stored can be customized when
            the middleware is instantiated.
            """
            req.context['result'] = MyDataStore().get('philosophers', phil_id)


    class PhilosopherCollection:

        schema = Philosopher()

        def on_post(self, req, resp):
            """req['json'] contains our deserialized data

            The key in which deserialized data can be stored can be
            customized when the middleware is instantiated.
            """
            inserted = MyDataStore().insert('philosophers', req.context['json'])
            req.context['result'] = inserted


    app = API(middleware=[Marshmallow()])

    app.add_route('/v1/philosophers', PhilosopherCollection())
    app.add_route('/v1/philosophers/{phil_id}', PhilosopherResource())


    if __name__ == '__main__':
        svr = simple_server.make_server('127.0.0.1', 8080, app)
        svr.serve_forever()

Done! 

When parsing a request body, if it cannot be decoded or its JSON 
is malformed, an HTTPBadRequest error will be raised. If the 
deserialization of the request body fails due to schema validation errors,
an HTTPUnprocessableEntity error will be raised.

We can test our new server easily enough using the ``requests`` library::

    >>> import requests

    # - GET some philosopher - #

    >>> resp = requests.get('http://127.0.0.1:8080/v1/philosophers/12')

    >>> resp.text
    '{"birth": "1913-11-07", "id": 12, "death": "1960-01-04", "works": ["The Stranger", "The Myth of Sissyphus"], "schools": ["existentialism", "absurdism"], "name": "Albert Camus"}'

    >>> resp.json()
    {'birth': '1913-11-07',
     'death': '1960-01-04',
     'id': 12,
     'name': 'Albert Camus',
     'schools': ['existentialism', 'absurdism'],
     'works': ['The Stranger', 'The Myth of Sissyphus']}

    # - POST a new philosopher - #

    >>> post_data = resp.json()

    >>> import json

    >>> presp = requests.post('http://127.0.0.1:8080/v1/philosophers', data=json.dumps(post_data))

    >>> presp.json()
    {'birth': '1813-05-05',
     'death': '1855-11-11',
     'id': 100,
     'name': 'Søren Kierkegaard',
     'schools': ['existentialism'],
     'works': ['Fear and Trembling', 'Either/Or']}


    # - Try to POST bad data - #

    >>> post_data['birth'] = 'not a date'

    >>> presp = requests.post('http://127.0.0.1:8080/v1/philosophers', data=json.dumps(post_data))

    >>> presp
    <Response [422]>

    >>> presp.json()
    {'description': '{"birth": ["Not a valid date."]}',
     'title': '422 Unprocessable Entity'}

Customization
+++++++++++++

Customization is effected by keyword arguments to the middleware constructor.
The constructor takes the following arguments:

* ``req_key`` (default ``json``) - the key on the request's ``context``
  dict on which to store parsed request data
* ``resp_key`` (default ``result``) - the key on the request's ``context``
  dict in which data to be serialized for a response should be stored
* ``force_json`` (default ``True``) - attempt to (de)serialize request
  and response bodies to/from JSON even if no schema is defined for a resource
* ``json_module`` (default ``simplejson``) - the module to use for
  (de)serialization; must implement the public interface of the ``json``
  standard library module

Contributing
------------

Contributions are welcome. Please feel free to raise Issues, submit PRs,
fix documentation typos, etc. If opening a PR, please be sure to run
tests, and ensure that your additions are compatible with Python 2.7, 3.4,
and above.

Testing
+++++++

To test against Python 2.7, 3.4, and 3.6, you will need to ``pip install tox``
for your system or active Python if you do not already have it installed,
and then run::

  tox

To test against your active Python environment::

  python setup.py test --addopts "--cov=falcon_marshmallow"
