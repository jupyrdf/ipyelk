# Copyright (c) Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import re
from pathlib import Path

import setuptools

HERE = Path(__file__).parent


setup_args = dict(
    name="elk",
    description="ELK widget for Jupyter",
    version=re.findall(
        r'''__version__ = "([^"]+)"''', (HERE / "elk" / "_version.py").read_text()
    )[0],
    packages=setuptools.find_packages(),
    author="Dane Freeman",
    author_email="dane.freeman@gtri.gatech.edu",
    url="https://github.gatech.edu/dfreeman6/elk-widget",
    license="BSD-3-Clause",
    platforms="Linux, Mac OS X, Windows",
    keywords=["Jupyter", "Widgets", "IPython"],
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Framework :: Jupyter",
    ],
    include_package_data=True,
    install_requires=["ipywidgets>=7.5.0", "networkx",],
    extras_require={"test": ["pytest", "pytest-cov", "nbval",],},
)

if __name__ == "__main__":
    setuptools.setup(**setup_args)
