#!/usr/bin/env python

from distutils.core import setup

setup(
    name='thinkrf',
    version='0.1.0',
    author='ThinkRF Corporation',
    author_email='support@thinkrf.com',
    packages=['thinkrf'],
    url='https://github.com/thinkrf/python-thinkrf',
    license='LICENSE.txt',
    description='ThinkRF Python Device API',
    long_description=open('README.rst').read(),
)
