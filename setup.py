#!/usr/bin/env python

try:
    import setuptools
    def setup(**kwargs):
        setuptools.setup(zip_safe=False, **kwargs)
except ImportError:
    from distutils.core import setup

setup(
    name='pyrf',
    version='0.2.3',
    author='ThinkRF Corporation',
    author_email='support@thinkrf.com',
    packages=['pyrf'],
    url='https://github.com/pyrf/pyrf',
    license='BSD',
    description='API for RF receivers including ThinkRF WSA4000',
    long_description=open('README.rst').read(),
)
