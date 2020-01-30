# coding: utf-8
from setuptools import setup, find_packages
import chan

setup(
    name="chan",
    version=chan.__version__,
    author=chan.__author__,
    author_email=chan.__email__,
    keywords=("缠论", "技术分析"),
    description="缠论技术分析工具",
    long_description="缠论技术分析工具",
    license="MIT",

    url="https://github.com/zengbin93/chan",
    packages=find_packages(exclude=['test', 'images', 'docs']),
    include_package_data=True,
    install_requires=["pandas"],

    classifiers=[
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
        ]
)
