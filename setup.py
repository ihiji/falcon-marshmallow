"""
setup module for falcon-marshmallow
"""

from os.path import dirname, join, realpath
from setuptools import setup, find_packages
from textwrap import dedent


NAME = 'falcon_marshmallow'
URL = 'https://www.github.com/ihiji/falcon-marshmallow'
AUTHOR = 'Matthew Planchard'
EMAIL = 'engineering@ihiji.com'


SHORT_DESC = 'Automatic Marshmallow (De)serialization in Falcon'

LONG_DESC = dedent(
    """
    Falcon-Marshmallow is a middleware library designed to assist
    developers who wish to easily incorporate automatic (de)serialization
    using Marshmallow schemas into their Falcon application. Once
    the middleware is in place, requests to any resources that have
    a ``schema`` attribute defined will automatically use that schema
    to parse the request body. In addition, responses for that resource
    will automatically use the defined schema to dump results.

    You may also specify method-specific schemas on a resource, e.g.
    ``patch_schema``, which will be used only when the request method
    matches the schema prefix.

    By default, this middleware will also automatically parse requests
    and responses to JSON even if they do not have any schema(s) defined.
    This can be easily disabled, if you would prefer to use your own JSON
    parsing middleware. This is done using ``simplejson`` by default,
    but you may specify any module or object you like that implements
    the public interface of the standard library ``json`` module.
    """
)

KEYWORDS = [
    'ihiji',
    'falcon',
    'marshmallow',
    'marshalling',
    'middleware',
    'serialization',
    'deserialization',
    'json',
    'wsgi',
]


PACKAGE_DEPENDENCIES = [
    'falcon',
    'marshmallow',
    'simplejson',
    'typing;python_version<"3.5"',
]

SETUP_DEPENDENCIES = [
    'pytest-runner',
]

TEST_DEPENDENCIES = [
    'pytest',
    'pytest-cov',
    'ipdb',
    'mock;python_version<"3.3"',
]

EXTRAS_DEPENDENCIES = {}


PACKAGE_EXCLUDE = ['*.tests', '*.tests.*']

# See https://pypi.python.org/pypi?%3Aaction=list_classifiers for all
# available setup classifiers
CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    # 'Development Status :: 4 - Beta',
    # 'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    # 'License :: Other/Proprietary License',
    'License :: OSI Approved :: MIT License',
    # 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Natural Language :: English',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: Implementation :: CPython',
    'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
]


__version__ = '0.0.0'

cwd = dirname(realpath(__file__))

with open(join(cwd, '%s/_version.py' % NAME)) as version_file:
    for line in version_file:
        # This will populate the __version__ and __version_info__ variables
        if line.startswith('__'):
            exec(line)

setup(
    name=NAME,
    version=__version__,
    description=SHORT_DESC,
    long_description=LONG_DESC,
    url=URL,
    author=AUTHOR,
    author_email=EMAIL,
    classifiers=CLASSIFIERS,
    keywords=KEYWORDS,
    packages=find_packages(exclude=PACKAGE_EXCLUDE),
    install_requires=PACKAGE_DEPENDENCIES,
    setup_requires=SETUP_DEPENDENCIES,
    tests_require=TEST_DEPENDENCIES,
    extras_require=EXTRAS_DEPENDENCIES,
)
