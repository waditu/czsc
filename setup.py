# coding: utf-8
import czsc
from os import path
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(path.join(here, "requirements.txt"), encoding="utf-8") as f:
    install_requires = f.read().strip().split("\n")

extensions = [
    Extension("czsc", ["czsc/*.py"]),
]


setup(
    name="czsc",
    version=czsc.__version__,
    author=czsc.__author__,
    author_email=czsc.__email__,
    keywords=["缠论", "技术分析", "A股", "期货", "缠中说禅"],
    description="缠中说禅技术分析工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="Apache Software License",
    url="https://github.com/waditu/czsc",
    packages=find_packages(exclude=["test", "images", "docs", "examples", "hist"]),
    include_package_data=True,
    ext_modules=cythonize(extensions),
    install_requires=install_requires,
    package_data={"": ["utils/china_calendar.feather", "utils/minutes_split.feather"]},
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    entry_points={
        "console_scripts": [
            "czsc = czsc.cmd:czsc",
        ],
    },
)

# 打包 pyd：python setup.py build_ext --inplace
