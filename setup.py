# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import re
from pathlib import Path

import setuptools

HERE = Path(__file__).parent
name = "ipyelk"
src = "py_src"

setup_args = dict(
    name=name,
    description="ELK widget for Jupyter",
    version=re.findall(
        r'''__version__ = "([^"]+)"''',
        (HERE / src / name / "_version.py").read_text(encoding="utf-8"),
    )[0],
    packages=setuptools.find_packages(src),
    package_dir={name: f'{src}/{name}'},
    author="Dane Freeman",
    author_email="dane.freeman@gtri.gatech.edu",
    url="https://github.edu/dfreeman06/ipyelk",
    license="BSD-3-Clause",
    platforms="Linux, Mac OS X, Windows",
    keywords=["Jupyter", "Widgets", "IPython", "ElkJS"],
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Framework :: Jupyter",
    ],
    python_requires=">=3.7",
    include_package_data=True,
    install_requires=["ipywidgets>=7.5.0", "networkx"],
)

if __name__ == "__main__":
    setuptools.setup(**setup_args)
