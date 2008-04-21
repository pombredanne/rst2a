#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rst2pdf.py: Convert reStructuredText documents to PDF files.
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
rst2pdf: Convert reStructuredText documents to PDF files.

The ``rst2pdf`` module exports several classes and functions which aid in the
process of converting reStructuredText to PDF. The classes defined are:

    ``ReSTConversion``
        An abstract representation of a reST to PDF conversion.
    
    ``ImageLocalizer``
        Walk down a ``docutils`` document tree, localizing all images found.

More information on these classes may be found in their respective docstrings.

The functions defined here are:

    ``localize_images``
        Localize images in a doctree, returning the new doctree and local \
images.

More information on these functions may be found in their docstrings.

The global variables defined here are:

    ``DOCUMENT_CLASSES``
        The list of possible document classes for PDF creation.
    
    ``LATEX_OVERRIDES``
        A dictionary of settings for reST-to-LaTeX conversion.
    
    ``option_parser``
        An instance of ``optparse.OptionParser``, for command-line usage.
"""

from cStringIO import StringIO
from copy import copy
import tempfile
import urllib2
import os
import optparse
import sys

from docutils.core import publish_doctree, publish_from_doctree
from docutils.nodes import image, figure, SparseNodeVisitor
import ImageFile

# The document classes used by rst2a.
DOCUMENT_CLASSES = (
    'article',
    'book',
    'report',
    'scrarticle',
    'scrbook',
    'scrreport'
)

# The most common set of LaTeX conversion settings.
LATEX_OVERRIDES = {
    'input-encoding': 'utf-8',
    'output-encoding': 'utf-8',
    'documentoptions': '10pt,a4paper',
    'no-section-numbering': True,
    'font-encoding': 'T1'
}

class ReSTConversion(object):
    """
    An abstract representation of a reST to PDF conversion.
    
    The ``ReSTConversion`` class holds a reST document and LaTeX stylesheet
    in memory, and defines several methods and attributes which are useful
    in the conversion of a reST document to a PDF file.
    
    The methods defined are:
        
        ``__init__``
            Construct a ``ReSTConversion`` instance from a reST document.
        
        ``to_latex``
            Convert a reST document to LaTeX, returning a string.
        
        ``to_pdf``
            Convert a reST document to PDF, returning the PDF file's path.
    
    Several attributes are also defined for a ``ReSTConversion`` instance:
        
        ``document``
            A unicode string representing the document.
        
        ``stylesheet``
            A unicode string representing the stylesheet.
        
        ``settings``
            A dictionary with all the settings for the LaTeX conversion.
    """
    def __init__(self, document, stylesheet, document_class='article',
        **kwargs):
        """
        Construct a ``ReSTConversion`` instance from a reST document.
        
        This method accepts a document (as a string), a stylesheet (as a 
        string), a document class and several keyword arguments, and creates
        a ``ReSTConversion`` instance with them. The keyword arguments are
        placed into the ``settings`` attribute, whereas the document and
        stylesheet get packed into the ``document`` and ``stylesheet``
        attributes respectively.
        """
        self.document = unicode(document)
        self.stylesheet = unicode(stylesheet)
        self.settings = {}
        # If invalid document class, just use the default. Trying to be as
        # quiet here as possible: this is being used in production.
        if document_class in DOCUMENT_CLASSES:
            self.settings['documentclass'] = document_class
        else:
            self.settings['documentclass'] = 'article'
        # If ``documentoptions`` is specified, then use the union of the new
        # and old settings. If a complete override is required, then
        # modification of an instance's ``settings`` attribute is required.
        self.settings.update(kwargs)
    
    def to_latex(self, settings_extra={}, *args, **kwargs):
        """
        Convert a reST document to LaTeX, returning a string.
        
        The ``to_latex`` method converts a reST document to LaTeX, returning
        the LaTeX document as a string and a list of the localized images.
        Additional settings are accepted in a dictionary, via the
        ``settings_extra`` keyword argument, and any additional arguments and
        keyword arguments will get passed to
        ``docutils.core.publish_from_doctree``.
        """
        # Localize all images, in order to fix the problem with PDF creation.
        doc_tree, images = localize_images(publish_doctree(self.document))
        # Put the stylesheet into a temporary file, in order to be able to use
        # it from the LaTeX writer.
        fd, stylesheet_filename = tempfile.mkstemp('.tex')
        stylesheet_file = open(stylesheet_filename,'w')
        stylesheet_file.write(self.stylesheet)
        stylesheet_file.close()
        # Copy the settings, so that the whole instance's settings are not
        # modified.
        settings = copy(self.settings)
        # Add a 'stylesheet-path' option to the settings.
        settings['stylesheet-path'] = stylesheet_filename
        # If any extra settings were specified, merge them.
        settings.update(settings_extra)
        # Return straight from ``publish_from_doctree``. The extra step of
        # converting to a doctree and then to LaTeX is to allow the
        # localization of images, for PDF output purposes.
        string_out = publish_from_doctree(doc_tree,
            settings_overrides=self.settings, writer_name='latex',
            *args, **kwargs)
        return string_out, images, stylesheet_filename
    
    def to_pdf(self, *args, **kwargs):
        """
        Convert a reST document to PDF, returning the PDF file's path.
        
        The ``to_pdf`` method converts the reST document to LaTeX via the
        ``to_latex`` method, and then calls ``pdflatex`` on the created file
        to create a PDF file. It returns a string of the path on the filesystem
        to the created PDF file, and removes any temporary files made in the
        process.
        """
        # Standard call to ``to_latex``.
        latex_doc, images, stylesheet_filename = self.to_latex(*args, **kwargs)
        # Make a temporary file for the LaTeX document.
        fd, latex_filename = tempfile.mkstemp('.tex')
        latex_file = open(latex_filename, 'w')
        latex_file.write(latex_doc)
        latex_file.close()
        # Run ``pdflatex`` on this 3 times. This is necessary to clean up the
        # resulting PDF file.
        err = os.system('pdflatex -halt-on-error %s' % (latex_filename,))
        i = 0
        while (i < 2) and (err == 0):
            err = os.system('pdflatex -halt-on-error %s' % (latex_filename,))
            i += 1
        # Get the name of the PDF file which has been created. It should be
        # the name of the LaTeX file, with a '.pdf' extension instead.
        pdf_filename = os.path.dirname(latex_filename) + os.path.sep + \
            os.extsep.join(os.path.basename(latex_filename).split(
                os.extsep)[:-1] + ['pdf'])
        # Get rid of all temporary LaTeX docs, stylesheets and images
        # downloaded and created during conversion.
        for temp_filename in [latex_filename, stylesheet_filename] + images:
            os.remove(temp_filename)
        # Return the name of the PDF file.
        return pdf_filename

class ImageLocalizer(SparseNodeVisitor):
    """
    Walk down a ``docutils`` document tree, localizing all images found.
    
    ``ImageLocalizer`` is a subclass of ``docutils.nodes.SparseNodeVisitor``.
    It overrides two methods of its superclass:
        
        ``visit_image``
            Localize an image, modifying the node.
        
        ``visit_figure``
            Localize a figure, modifying the node.
    
    An ``ImageLocalizer`` instance also has an ``image_files`` attribute, which
    contains the locations of all localized images. This is used by the PDF
    conversion to clean up after the PDF file has been created.
    """
    
    image_files = []
    
    def visit_image(self, node):
        """
        Visit an image node, and localize its specified image.
        
        The ``visit_image`` method extracts the image URL from a
        reStructuredText doctree node, downloads it to a temporary file on the
        filesystem, and modifies the node to point to the localized image file.

        It also appends the path of the newly localized image to the
        ``image_files`` attribute of the ``ImageLocalizer`` instance.
        """
        # Get the old image URL.
        old_url = node.attributes['uri']
        # Extract the image extension (which will determine the format).
        img_fmt = old_url.split(os.extsep)[-1]
        # Make a temporary file, to be the new, local image file.
        fd, temp_filename = tempfile.mkstemp('.' + img_fmt)
        # Initialize a parser instance, to process the downloaded image
        # and make sure it is completely valid.
        img_parser = ImageFile.Parser()
        # Open up a connection to the image URL.
        img_handle = urllib2.urlopen(old_url)
        # Start off the ``data`` attribute, and keep feeding it into the
        # parser until nothing is left.
        temp_img_data = img_handle.read(1024)
        while temp_img_data:
            img_parser.feed(temp_img_data)
            temp_img_data = img_handle.read(1024)
        # Close the parser, returning an image file.
        img = img_parser.close()
        # Close the remote image connection.
        img_handle.close()
        # Save the image to the temporary, local filename.
        img.save(temp_filename)
        # Modify the node so that it points to the new image file.
        node.attributes['uri'] = temp_filename
        self.image_files.append(temp_filename)
    
    def visit_figure(self, node):
        """
        Visit a figure node, and localize its specified image.
        
        The ``visit_figure`` method simply calls ``ImageLocalizer.visit_image``
        on the given node, as the logic behind localization of both types of
        node is the same.
        """
        return self.visit_image(node)

def localize_images(doctree):
    """
    Localize images in a doctree, returning the new doctree and local images.
    
    ``localize_images`` is a wrapper around the use of the ``ImageLocalizer``
    doctree-walking class. It calls the doctree's ``walk`` method, with an
    ``ImageLocalizer`` instance as an argument, and returns the modified
    doctree, along with a list of local image files as returned by the image
    localizer.
    """
    visitor = ImageLocalizer(doctree)
    doctree.walk(visitor)
    return doctree, visitor.image_files


# Begin command-line option parsing definitions.


option_parser = optparse.OptionParser(
    usage='Usage: %prog [options] filein.rst fileout.pdf',
    version='%prog v0.1',
    description='''%prog is a script to convert reStructuredText input to PDF \
output. It works by taking reST input, converting it to LaTeX using docutils, \
localizing images included in the reST file, and then converting it to PDF \
using pdflatex. Several temporary files are created and then deleted during \
PDF creation, so it is necessary to be able to write to the temporary \
directory on your filesystem, as returned by Python's tempfile module.'''
)

option_parser.add_option('-c', '--class',
    dest='class_',
    metavar='CLASS',
    help='''Use document class CLASS.
One of:
    * article
    * book
    * report
    * scrarticle
    * scrbook
    * screport''')

option_parser.add_option('-s', '--stylesheet',
    dest='stylesheet',
    metavar='STYLESHEET',
    default=None,
    help='''Use stylesheet STYLESHEET. Should have an extension 'tex'.''')

option_parser.add_option('-f', '--file',
    dest='filename',
    metavar='FILE',
    default=None,
    help='''Use reStructuredText document FILE. If no file specified through \
this option, and no additional arguments given to this program, then stdin \
will be used as the file input.''')

option_parser.add_option('--safe',
    dest='safe',
    action='store_true',
    default=False,
    help='''Switch on safe mode. Disables embedding of arbitrary files and \
TeX statements. Recommended.''')

option_parser.add_option('-d', '--documentoptions',
    dest='documentoptions',
    default='10pt,a4paper',
    metavar='OPTIONS',
    help='''Comma-separated document options list. There should be no spaces \
between the different options.
See http://docutils.sf.net/docs/user/latex.html for more information.''')

option_parser.add_option('-o', '--output',
    dest='output',
    metavar='PDF_FILE',
    default=None,
    help='''Write PDF output to file PDF_FILE. By default, if no file is \
specified through this option, and no additional arguments given to this \
program, then output will be written to stdout.''')

# End option parsing definitions.

if __name__ == '__main__':
    # Begin actual option parsing.
    options, args = option_parser.parse_args()
    # Begin I/O file option parsing.
    if options.filename and options.output:
        infile = open(options.filename)
        outfile = open(options.output, 'w')
    elif options.filename and not options.output:
        if len(args) > 0:
            outfile = open(args[0], 'w')
        else:
            outfile = sys.stdout
        infile = open(options.filename)
    elif options.output and not options.filename:
        if len(args) > 0:
            infile = open(args[0])
        else:
            infile = sys.stdin
        outfile = open(options.output, 'w')
    elif not options.filename and not options.filename:
        if len(args) == 2:
            infile, outfile = open(args[0]), open(args[1], 'w')
        elif len(args) == 1:
            infile, outfile = open(args[0]), sys.stdout
        elif len(args) == 0:
            infile, outfile = sys.stdin, sys.stdout
    # End I/O file option parsing.
    # Begin stylesheet file option parsing.
    if options.stylesheet:
        stylesheet_file = open(options.stylesheet)
    else:
        option_parser.error('No stylesheet specified.')
    # End stylesheet file option parsing.
    # Begin general option parsing.
    doc_class = options.class_
    LATEX_OVERRIDES['documentoptions'] = options.documentoptions
    if options.safe:
        LATEX_OVERRIDES['file-insertion-enabled'] = False
        LATEX_OVERRIDES['raw-enabled'] = False
    else:
        LATEX_OVERRIDES['file-insertion-enabled'] = True
        LATEX_OVERRIDES['raw-enabled'] = True
    conversion = ReSTConversion(infile.read(), stylesheet_file.read(),
        document_class=doc_class, **LATEX_OVERRIDES)
    infile.close()
    stylesheet_file.close()
    pdf_filename = conversion.to_pdf()
    pdf_file = open(pdf_filename)
    data = pdf_file.read(1024)
    while data:
        outfile.write(data)
        data = pdf_file.read(1024)
    outfile.close()
    pdf_file.close()
