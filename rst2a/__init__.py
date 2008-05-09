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
    
    """
    Hold a reST document and associated objects.
    
    The ``ReSTDocument`` class is a class for holding, and carrying out
    procedures on, a reStructuredText document. An instance has several useful
    attributes:
        
        ``fp``
            The ``fp`` attribute holds a reference to the file handle used to
            initialize the ``ReSTDocument`` instance. By default, the document
            is read, decoded and parsed upon initialization, but it is useful
            to hold the file handle in the case of having to close the file
            after initialization, or to get information about an instance.
        
        ``document_raw``
            This attribute holds a utf-8 string of the document, read from the
            current position of the document's file handle (as passed upon
            initialization). This is useful for viewing the original document,
            and/or saving it to another file.
        
        ``document``
            This attribute holds the docutils-parsed document tree of the reST
            document. The class for this is ``docutils.nodes.document``, and
            holding it allows for transformations and modifications to be made
            to the document tree before writing.
        
        ``default_settings``
            This holds a dictionary of default settings, passed to any writer
            when someone tries to write the document out to another format. It
            may be passed in the ``settings`` keyword argument during
            initialization, but by default takes the value of the
            ``DEFAULT_SETTINGS`` dictionary found within this namespace.
        
        ``img_localizer``
            Holds an image localizer instance specific to this document's
            doctree; see the documentation in ``rst2a.images`` for more
            information on ``ImageLocalizer`` instances.
    """
    
    def __init__(self, doc_handle, settings=DEFAULT_SETTINGS):
        """
        Initialize a ``ReSTDocument`` instance, with a file and some settings.
        
        The initialization method for the ``ReSTDocument`` class will
        initialize an instance with a document, as read from the first
        positional argument, and with a set of conversion settings given by the
        ``settings`` keyword argument. By default, this will take the value of
        the ``DEFAULT_SETTINGS`` dictionary, located within this namespace.
        
        This method will read the data from ``doc_handle`` by calling its
        ``read`` method with no arguments, and then call the returned string's
        ``decode`` method with 'utf-8' as the argument. On most file-like
        classes in the Python stdlib (e.g. files, URL connections, StringIOs),
        the former will return a ``str`` and the latter will produce a
        ``unicode`` instance. For a third-party class to work, just make sure
        its ``read`` method returns a string.
        
        The read document will then be processed using
        ``docutils.core.publish_doctree``. Ensure that documents are valid reST
        inputs - failure to do so will probably produce an error upon
        initialization of the ``ReSTDocument`` instance.
        
        An ``ImageLocalizer`` instance is wrapped around the produced doctree;
        this eases the strain of LaTeX and PDF conversion greatly.
        
        If the Python installation from which this is run does not have the
        ``pdflatex`` command available (this includes most win32 systems), then
        PDF support will be removed from the resulting ``ReSTDocument``
        instance. If the ``tidy`` module is not available, then XHTML
        conversion will likewise be removed.
        """
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
        """
        Convert a document tree to LaTeX format, returning a string and a list.
        
        The ``to_latex`` method will return a string containing the produced
        LaTeX file and a list containing the locations of temporary files
        created during the LaTeX conversion. The LaTeX string returned will
        most likely be a ``unicode``, and the list of files will be (possibly)
        a .tex file (the stylesheet) followed by several image files.
        
        The LaTeX stylesheet is passed in the ``stylesheet_url`` keyword. The
        way of dealing with the stylesheet is quite complex, so here's a
        summary of the possibile configurations:
            
            1)  You pass a string which *is* the stylesheet, equivalent to the
                results of an ``open('filename').read()``. In this case, a .tex
                file *will* be included in the list of temporary files.
            
            2)  You pass a filename *pointing to* the stylesheet, equivalent to
                the last example's ``'filename'``. This would *not* create a
                .tex file in the temporary file list.
            
            3)  You pass a file-like object which *contains* the stylesheet,
                which is the same as passing ``open('filename')``. As with
                example 1, a .tex file *will* be included in the returned list
                of temporary files.
        
        The ``settings`` keyword argument specifies a particular dictionary of
        docutils writer settings to be passed to the LaTeX writer. They will
        augment the ``ReSTDocument`` instance's ``default_settings`` attribute,
        but keywords specified in ``settings`` will override any conflicts in
        the instance-specific settings. This defaults to the
        ``DEFAULT_LATEX_OVERRIDES`` dictionary, in the ``rst2a.latex`` module.
        
        Any additional positional or keyword arguments will be passed to the
        ``rst2a.latex.doctree_to_latex`` function.
        """
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
