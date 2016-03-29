#!/usr/bin/env python

import setuptools

from erlastic import __version__ as version

setuptools.setup(
    name = 'basho-erlastic',
    version = version,
    description = 'Erlastic',
    author = 'Samuel Stauffer, Basho Technologies',
    author_email = 'clients@basho.com',
    url = 'http://github.com/basho/python-erlastic',
    packages = ['erlastic'],
    install_requires=['six'],
    test_suite='tests',
    classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
