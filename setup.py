#!/usr/bin/env python
import os

try:
    import setuptools
    def setup(**kwargs):
        setuptools.setup(zip_safe=False, **kwargs)
except ImportError:
    from distutils.core import setup

extras = {}
try:
    import py2exe
    extras.update({
        'windows':['rtsa-gui.py'],
        })
except ImportError:
    pass

exec(open(os.path.join("pyrf","version.py")).read())
release = __version__

setup(
    name='pyrf',
    version=release,
    author='ThinkRF Corporation',
    author_email='support@thinkrf.com',
    packages=['pyrf', 'pyrf.devices', 'pyrf.connectors'],
    url='https://github.com/pyrf/pyrf',
    license='BSD',
    description='API for RF receivers including ThinkRF RTSA platforms',
    long_description=open('README.rst').read(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Hardware",
        ],
    test_suite='pyrf.tests',
    entry_points={
        'gui_scripts': [
            "rtsa-gui = pyrf.gui.spectrum_analyzer:main",
            ],
        },
    **extras
    )
