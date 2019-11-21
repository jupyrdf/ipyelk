#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function
from glob import glob
from os.path import join as pjoin


from setupbase import (
    create_cmdclass, install_npm, ensure_targets,
    find_packages, combine_commands, ensure_python,
    get_version, HERE
)

from setuptools import setup


# The name of the project
name = 'elk'

# Ensure a valid python version
ensure_python('>=3.3')

# Get our version
version = get_version(pjoin(name, '_version.py'))

setup_args = dict(
    name            = name,
    description     = 'ELK widget for Jupyter',
    version         = version,
    scripts         = glob(pjoin('scripts', '*')),
    packages        = ["elk"],
    author          = 'Dane Freeman',
    author_email    = 'dane.freeman@gtri.gatech.edu',
    url             = 'https://github.gatech.edu/dfreeman6/elk-widget',
    license         = 'BSD',
    platforms       = "Linux, Mac OS X, Windows",
    keywords        = ['Jupyter', 'Widgets', 'IPython'],
    classifiers     = [
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Jupyter',
    ],
    include_package_data = True,
    install_requires = [
        'ipywidgets>=7.5.0',
    ],
    extras_require = {
        'test': [
            'pytest',
            'pytest-cov',
            'nbval',
        ],
    },
    entry_points = {
    },
)

if __name__ == '__main__':
    setup(**setup_args)
