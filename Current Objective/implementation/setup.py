#!/usr/bin/env python3

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lfs-wrapper",
    version="0.1.0",
    author="WARP System Development Team",
    description="A comprehensive wrapper system for LFS build scripts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where=".", exclude=["tests"]),
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
        "PyYAML>=6.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "pytest-mock>=3.10.0",
            "mypy>=1.0.0",
            "types-PyYAML>=6.0.0",
            "black>=22.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "lfs-wrapper=scripts.lfs_wrapper:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
    ],
)

