# coding: utf-8
from setuptools import setup, find_packages
import czsc

setup(
    name="czsc",
    version=czsc.__version__,
    author=czsc.__author__,
    author_email=czsc.__email__,
    keywords=["缠论", "技术分析", "A股", "期货"],
    description="缠中说禅技术分析工具",
    long_description="缠中说禅技术分析工具，源自 http://blog.sina.com.cn/chzhshch",
    license="MIT",

    url="https://github.com/zengbin93/czsc",
    packages=find_packages(exclude=['test', 'images', 'docs']),
    include_package_data=True,
    install_requires=["pandas", "pyecharts", "mplfinance", "tushare", "matplotlib"],

    classifiers=[
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
        ]
)
