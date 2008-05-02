#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rst2a: Convert reStructuredText documents to other formats.
# Copyright (C) 2008  Zachary Voase
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Convert reStructuredText documents to other formats.

The main rst2a module (``__init__.py``) defines a dictionary of default
settings and a ``ReSTDocument`` class which serves as an abstraction for reST
conversions to other formats.

The ``docutils`` module is imported here, and used excessively, therefore it is
required that it is installed on the Python import path - if it is not, then
rst2a will not work. Period.

``DEFAULT_SETTINGS`` simply tells docutils that the input and output encodings
for documents are in utf-8, and that footnote references should be output in
superscript (a personal preference of the author). This may be modified at
run-time by applications which import ``rst2a``.

For more information on the ``ReSTDocument`` class, see its individual
documentation.
"""

from copy import copy
from os import chdir, extsep, getcwdu, remove, rmdir
from os.path import isdir, isfile, splitext

from docutils.core import publish_doctree, publish_from_doctree
from docutils.nodes import document, image, figure, SparseNodeVisitor

from rst2a import common, html, images, latex, pdf

__all__ = ['common', 'html', 'images', 'latex', 'pdf']


DEFAULT_SETTINGS = {
    'input-encoding': 'utf-8',
    'output-encoding': 'utf-8',
    'footnote-references': 'superscript'
}


class ReSTDocument (object):
    
    def __init__(self, doc_handle, settings=DEFAULT_SETTINGS):
        self.fp = doc_handle
        # Make sure document is read in utf-8. This will avoid any surprises
        # down the line, when converting the document.
        self.document_raw = self.fp.read().decode('utf8')
        # ``self.document`` holds a document tree instance.
        self.document = publish_doctree(self.document_raw)
        # Hold some settings within the ``ReSTDocument`` instance.
        self.default_settings = settings
        # Initialize an image localizer, just in case the user wishes to
        # convert to LaTeX and have images localized, or convert to PDF, for
        # which it is necessary to localize images.
        self.img_localizer = images.ImageLocalizer(self.document)
        # Just remove XHTML and PDF conversion capabilities if they are not
        # supported by the system.
        if html.tidy is None:
            del self.to_xhtml
        if not pdf.pdflatex_installed():
            del self.to_pdf
    
    def to_latex(self, stylesheet_url='',
        settings=latex.DEFAULT_LATEX_OVERRIDES, *args, **kwargs):
        # Create a set of conversion settings based on those given and the
        # default settings held in the ``ReSTDocument`` instance.
        conversion_settings = copy(self.default_settings)
        conversion_settings.update(settings)
        # Wrap the ``latex.doctree_to_latex`` function.
        return latex.doctree_to_latex(self.document, self.img_localizer,
            stylesheet_url=stylesheet_url, settings=conversion_settings)
        
    def to_html(self, stylesheet_url='', settings=html.DEFAULT_HTML_OVERRIDES,
        tidy_output=True, tidy_settings=html.DEFAULT_TIDY_HTML_OPTIONS,
        *args, **kwargs):
        conversion_settings = copy(self.default_settings)
        conversion_settings.update(settings)
        # Wrap the ``html.doctree_to_html`` function.
        return html.doctree_to_html(self.document,
        stylesheet_url=stylesheet_url, settings=settings,
        tidy_output=tidy_output, tidy_settings=tidy_settings, *args, **kwargs)
    
    def to_xhtml(self, stylesheet_url='', settings=html.DEFAULT_HTML_OVERRIDES,
        tidy_settings=html.DEFAULT_TIDY_XHTML_OPTIONS, *args, **kwargs):
        if 'tidy_output' in kwargs:
            del kwargs['tidy_output']
        conversion_settings = copy(self.default_settings)
        conversion_settings.update(settings)
        return html.doctree_to_xhtml(self.document,
        stylesheet_url=stylesheet_url, settings=settings,
        tidy_settings=tidy_settings, *args, **kwargs)
    
    def to_pdf(self, stylesheet_url='', settings=latex.DEFAULT_LATEX_OVERRIDES,
        *args, **kwargs):
        conversion_settings = copy(self.default_settings)
        conversion_settings.update(settings)
        return pdf.doctree_to_pdf(self.document, self.img_localizer,
            stylesheet_url=stylesheet_url, settings=settings, *args, **kwargs)
    
    def cleanup_images(self):
        self.img_localizer.switch_mode()
        self.document.walk(self.img_localizer)
        self.img_localizer.switch_mode()
