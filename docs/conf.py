# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.append("../")

# -- Project information -----------------------------------------------------

project = 'SpDB'
copyright = '2020, 于治 YUZhi@ipp.ac.cn '
author = '于治 (yuzhi@ipp.ac.cn)'

# The full version, including alpha/beta/rc tags
release = '0.0.1'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinx.ext.napoleon",
              "sphinx.ext.imgmath",
              "sphinx.ext.graphviz",
              #   "sphinx.ext.autodoc",
              "sphinx.ext.todo",
              "sphinx.ext.imgconverter",
              "sphinx.ext.graphviz",
              "sphinx.ext.autosectionlabel",
              # "sphinxcontrib.bibtex",
              # 'sphinxcontrib.plantuml',
              # "recommonmark",
              # "docxsphinx"
              ]

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'zh'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
# html_theme = 'alabaster'


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# imgmath_latex = 'xelatex'
imgmath_latex_preamble = r'''
\usepackage{wasysym}
'''
latex_engine = 'xelatex'
latex_elements = {
    'fontpkg': r'''
\setmainfont[Mapping=tex-text]{Noto Serif CJK SC}
\setsansfont[Mapping=tex-text]{Noto Sans Mono CJK SC}
\setmonofont{Noto Sans Mono CJK SC}
''',
    'preamble': r'''
\usepackage[titles]{tocloft}
\cftsetpnumwidth {1.25cm}\cftsetrmarg{1.5cm}
\setlength{\cftchapnumwidth}{0.75cm}
\setlength{\cftsecindent}{\cftchapnumwidth}
\setlength{\cftsecnumwidth}{1.25cm}
\usepackage{polyglossia}
\setdefaultlanguage[variant=american]{english}
\usepackage{wasysym}
\usepackage{esint}
\usepackage{etoolbox}
\patchcmd{\thebibliography}{\section*{\refname}}{}{}{}
''',
    'fncychap': r'\usepackage[Bjornstrup]{fncychap}',
    'printindex': r'\footnotesize\raggedright\printindex',
}
latex_show_urls = 'footnote'

autodoc_member_order = 'bysource'  # "groupwise"

todo_include_todos = True

image_converter_args = ['-verbose']

plantuml_output_format='png'