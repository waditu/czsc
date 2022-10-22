# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import sphinx_rtd_theme
sys.path.insert(0, os.path.abspath('../../../czsc'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'czsc'
copyright = '2022, zengbin93'
author = 'zengbin93'
release = '0.8.30'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.graphviz',
    'sphinx_automodapi.automodapi',
    'recommonmark',
]

templates_path = ['_templates']
exclude_patterns = []

language = 'zh_CN'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'alabaster'

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'restructuredtext',
    '.md': 'markdown',
}

# 设置 graphviz_dot 路径
# graphviz_dot = 'dot'
graphviz_dot = r"C:\Program Files\Graphviz\bin\dot.exe"
# 设置 graphviz_dot_args 的参数，这里默认了默认字体
graphviz_dot_args = ['-Gfontname=Georgia',
                     '-Nfontname=Georgia',
                     '-Efontname=Georgia']
# 输出格式，默认png，这里用svg矢量图
graphviz_output_format = 'svg'
