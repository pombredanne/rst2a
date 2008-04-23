#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rst2a.py: Convert reStructuredText documents to other things.
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

from copy import copy
from cStringIO import StringIO
from os import chdir, extsep, getcwdu, remove, rmdir
from os.path import isdir, isfile, splitext
from subprocess import check_call, CalledProcessError
from tempfile import mkstemp, mkdtemp
from urllib2 import urlopen
from urlparse import urlparse, uses_netloc

import Image
import tidy
from docutils.core import publish_doctree, publish_from_doctree
from docutils.nodes import document, image, figure, SparseNodeVisitor


DEFAULT_SETTINGS = {
    'input-encoding': 'utf-8',
    'output-encoding': 'utf-8',
    'footnote-references': 'superscript'
}


DEFAULT_HTML_OVERRIDES = {
    'no-generator': True,
    'no-datestamp': True,
    'no-source-link': True,
    'no-section-numbering': True
}


DEFAULT_LATEX_OVERRIDES = {
    'no-section-numbering': True,
    'documentoptions': '10pt,a4paper',
    'documentclass': 'article',
    'font-encoding': 'T1',
    'graphicx-option': 'pdftex'
}


DEFAULT_TIDY_XHTML_OPTIONS = {
    'add_xml_decl': True,
    'add_xml_space': True,
    'clean': True,
    'css_prefix': 'tidystyle',
    'enclose_block_text': True,
    'enclose_text': True,
    'fix_backslash': True,
    'fix_bad_comments': True,
    'indent_cdata': True,
    'logical_emphasis': True,
    'output_xhtml': True,
    'replace_color': True,
    'indent': 'auto',
    'indent_spaces': 4,
    'tab_size': 4,
    'vertical_space': True,
    'wrap': 79,
    'char_encoding': 'utf8',
    'tidy_mark': False
}


DEFAULT_TIDY_HTML_OPTIONS = {
    'clean': True,
    'css_prefix': 'tidystyle',
    'enclose_block_text': True,
    'enclose_text': True,
    'fix_backslash': True,
    'fix_bad_comments': True,
    'indent_cdata': True,
    'logical_emphasis': True,
    'output_html': True,
    'replace_color': True,
    'indent': 'auto',
    'indent_spaces': 4,
    'tab_size': 4,
    'uppercase_tags': True,
    'vertical_space': True,
    'wrap': 79,
    'char_encoding': 'utf8',
    'tidy_mark': False
}


class ReSTDocument (object):
    
    def __init__(self, doc_handle, settings=DEFAULT_SETTINGS):
        self.fp = doc_handle
        self.document_raw = self.fp.read().decode('utf8')
        self.document = publish_doctree(self.document_raw)
        self.default_settings = settings
        self.img_localizer = ImageLocalizer(self.document)
    
    def to_latex(self, stylesheet_path='', settings=DEFAULT_LATEX_OVERRIDES,
        *args, **kwargs):
        cleanup_stylesheet = False
        if not isfile(str(stylesheet_path)) or is_filelike(stylesheet_path):
            stylesheet_path = create_temp_file(stylesheet_path, suffix='.tex')
            cleanup_stylesheet = True
        conversion_settings = copy(self.default_settings)
        conversion_settings.update(settings)
        conversion_settings['stylesheet-path'] = stylesheet_path
        self.localize_images()
        latex_string = publish_from_doctree(self.document, writer_name='latex',
            settings_overrides=conversion_settings, *args, **kwargs)
        if cleanup_stylesheet:
            return latex_string, [stylesheet_path] + \
                list(set(self.img_localizer.values()))
        else:
            return latex_string, list(set(self.img_localizer.values()))
    
    def to_pdf(self, stylesheet_path='', settings=DEFAULT_LATEX_OVERRIDES,
        *args, **kwargs):
        cleanup_stylesheet = False
        latex_string, extra_files = self.to_latex(settings=settings,
            stylesheet_path=stylesheet_path, *args, **kwargs)
        if splitext(extra_files[0])[1] == '.tex':
            cleanup_stylesheet = True
        temp_pdf_dir = mkdtemp()
        temp_latex_filename = create_temp_file(latex_string, suffix='.tex',
            dir=temp_pdf_dir)
        pdflatex = lambda: call_pdflatex(temp_latex_filename, temp_pdf_dir)
        if pdflatex():
            if pdflatex():
                if pdflatex():
                    pdf_conversion_successful = True
                else:
                    pdf_conversion_successful = False
            else:
                pdf_conversion_successful = False
        else:
            pdf_conversion_successful = False
        self.cleanup_images()
        if cleanup_stylesheet:
            remove(extra_files[0])
        if pdf_conversion_successful:  
            pdf_prefix = splitext(temp_latex_filename)[0]
            pdf_filename = pdf_prefix + extsep + 'pdf'
            pdf_handle = open(pdf_filename)
            pdf_data = pdf_handle.read()
            pdf_handle.close()
            remove_dir(temp_pdf_dir)
            return pdf_data, []
        else:
            remove_dir(temp_pdf_dir)
            raise IOError('PDF conversion unsuccessful.')
    
    def to_html(self, stylesheet_url='', settings=DEFAULT_HTML_OVERRIDES,
        tidy_output=True, tidy_settings=DEFAULT_TIDY_HTML_OPTIONS,
        *args, **kwargs):
        conversion_settings = copy(self.default_settings)
        conversion_settings.update(settings)
        if is_url(stylesheet_url, net_loc=('http', 'ftp')):
            conversion_settings['stylesheet-path'] = stylesheet_url
        html_string = publish_from_doctree(self.document,
            writer_name='html4css1',
            settings_overrides=conversion_settings, *args, **kwargs)
        if tidy_output:
            html_string = str(tidy.parseString(html_string, **tidy_settings))
        return html_string, []
    
    def to_xhtml(self, stylesheet_url='', settings=DEFAULT_HTML_OVERRIDES,
    tidy_settings=DEFAULT_TIDY_XHTML_OPTIONS, *args, **kwargs):
        if 'tidy_output' in kwargs:
            del kwargs['tidy_output']
        html_string, discard = self.to_html(stylesheet_url, tidy_output=False,
            *args, **kwargs)
        return str(tidy.parseString(html_string, **tidy_settings)), []
    
    def localize_images(self, check_images=False):
        old_dir = getcwdu()
        chdir(self.img_localizer.temp_dir)
        self.document.walk(self.img_localizer)
        os.chdir(old_dir)
    
    def cleanup_images(self, delete_temp_dir=True):
        self.img_localizer.switch_mode()
        self.document.walk(self.img_localizer)
        self.img_localizer.switch_mode()
        if delete_temp_dir:
            try:
                rmdir(self.img_localizer.temp_dir)
            except OSError:
                pass


class ImageLocalizer (SparseNodeVisitor):
    
    def __init__(self, document, check_images=False, local_mode=True):
        self.localized_images = {}
        self.check_images = check_images
        self.temp_dir = mkdtemp(prefix='img_')
        self.__local_mode = local_mode
        SparseNodeVisitor.__init__(self, document)
    
    def switch_mode(self):
        self.__local_mode = not self.__local_mode
    
    def visit_image(self, img_node):
        if self.__local_mode:
            if not isdir(self.temp_dir):
                self.temp_dir = mkdtemp(prefix='img_')
            img_url = img_node.attributes['uri']
            if not is_url(img_url, net_loc=('http', 'ftp')):
                return
            elif img_url in self.localized_images:
                img_node.attributes['uri'] = self.localized_images[img_url]
            remote_handle = urlopen(img_url)
            img_ext = splitext(img_url)[1].lower()
            assert img_ext in Image.EXTENSION.keys(), \
                'Weird image extension: "%s"' % (img_ext,)
            local_filename = mkstemp(dir=self.temp_dir, suffix=img_ext)
            if self.check_images:
                img_buffer = StringIO()
                stream_cp(remote_handle, img_buffer)
                img_data_handle.seek(0)
                img = Image.open(fp=img_buffer)
                img.save(local_filename)
            else:
                local_handle = open(local_filename, 'w')
                stream_cp(remote_handle, local_handle)
                local_handle.close()
            remote_handle.close()
            self.localized_images[img_url] = local_filename
        else:
            img_path = img_node.attributes['uri']
            img_url = reverse_lookup(self.localized_images, img_path)
            img_node.attributes['uri'] = img_url
            remove(img_path)
    
    def visit_figure(self, figure_node):
        return self.visit_image(figure_node)


def stream_cp(input_handle, output_handle, block_size=1024, block_count=None):
    block_size = int(block_size)
    if block_count is None:
        tmp_data = input_handle.read(block_size)
        while tmp_data:
            output_handle.write(tmp_data)
            tmp_data = input_handle.read(block_size)
    else:
        for i in xrange(int(block_count)):
            output_handle.write(input_handle.read(block_size))


def reverse_lookup(dictionary, value, cmp=cmp):
    for curr_key, curr_value in dictionary.items():
        if cmp(value, curr_value) == 0:
            return curr_key


def is_filelike(handle, mode=None):
    if mode is None:
        if hasattr(handle, mode):
            mode = handle.mode
        else:
            mode = 'rw'
    if 'r' in mode:
        for attr in ('read', 'readline', 'readlines', '__iter__'):
            if not hasattr(handle, attr):
                return False
    if 'w' in mode or 'a' in mode:
        for attr in ('write', 'writelines', 'close'):
            if not hasattr(handle, attr):
                return False
    return True


def create_temp_file(filein, *args, **kwargs):
    if isinstance(filein, basestring):
        temp_filename = mkstemp(*args, **kwargs)[1]
        temp_handle = open(temp_filename, 'w')
        temp_handle.write(filein)
        temp_handle.close()
        return temp_filename
    elif is_filelike(filein):
        temp_filename = mkstemp(*args, **kwargs)[1]
        temp_handle = open(temp_filename, 'w')
        stream_cp(filein, temp_handle)
        temp_handle.close()
        return temp_filename
    else:
        raise TypeError("""Temporary file creation needs a file-like object \
or string; %r received instead.""" % (filein,))


def call_pdflatex(latex_filename, pdf_dir):
    try:
        check_call(['pdflatex', '-halt-on-errors', latex_filename],
            cwd=pdf_dir)
    except CalledProcessError:
        return False
    return True


def remove_dir(dirname):
    for temp_dirname, sub_dirs, files in walk(dirname):
        if (not sub_dirs) and (not files):
            rmdir(temp_dirname)
        if files:
            for filename in files:
                remove(join(temp_dirname, filename))
        if sub_dirs:
            for sub_dir in sub_dirs:
                remove_dir(sub_dir)
        rmdir(temp_dirname)
    rmdir(dirname)


def is_url(url, net_loc=''):
    url_net_loc = urlparse(url)[0]
    if not net_loc:
        if url_net_loc in uses_netloc:
            return True
    elif hasattr(net_loc, '__iter__'):
        if url_net_loc in net_loc:
            return True
    elif isinstance(net_loc, basestring) and (url_net_loc == net_loc):
        return True
    return False
