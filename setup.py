#!/usr/bin/env python

try:
    import setuptools
    def setup(**kwargs):
        setuptools.setup(zip_safe=False, **kwargs)
except ImportError:
    from distutils.core import setup

setup(
    name='thinkrf',
    version='0.2.1',
    author='ThinkRF Corporation',
    author_email='support@thinkrf.com',
    packages=['thinkrf'],
    url='https://github.com/thinkrf/python-thinkrf',
    license='BSD',
    description='ThinkRF Python Device API',
    long_description=open('README.rst').read(),
)
