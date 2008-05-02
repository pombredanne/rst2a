#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rst2a: Convert reStructuredText documents to other formats.
# rst2a.html: Default options and functions which are used to convert a doctree
#             to (X)HTML. XHTML conversion requires utidylib, a Python wrapper
#             for TidyLib.
#
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

from docutils.core import publish_from_doctree
try:
    import tidy
except ImportError:
    tidy = None

from rst2a.common import is_url

DEFAULT_HTML_OVERRIDES = {
    'no-generator': True,
    'no-datestamp': True,
    'no-source-link': True,
    'no-section-numbering': True
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

def doctree_to_html(doctree, stylesheet_url='',
    settings=DEFAULT_HTML_OVERRIDES, tidy_output=True,
    tidy_settings=DEFAULT_TIDY_HTML_OPTIONS, *args, **kwargs):
    conversion_settings = copy(settings)
    if tidy is None:
        tidy_output = False
    if is_url(stylesheet_url, net_loc=('http', 'ftp')):
        conversion_settings['stylesheet-path'] = stylesheet_url
    html_string = publish_from_doctree(doctree, writer_name='html4css1',
        settings_overrides=conversion_settings, *args, **kwargs)
    if tidy_output:
        html_string = str(tidy.parseString(html_string, **tidy_settings))
    return html_string

def doctree_to_xhtml(doctree, stylesheet_url='',
    settings=DEFAULT_HTML_OVERRIDES, tidy_settings=DEFAULT_TIDY_XHTML_OPTIONS,
    *args, **kwargs):
    if tidy is None:
        raise ImportError('utidylib must be present to convert to XHTML.')
    if 'tidy_output' in kwargs:
        del kwargs['tidy_output']
    html_string = doctree_to_html(doctree, stylesheet_url, tidy_output=False,
        *args, **kwargs)
    return str(tidy.parseString(html_string, **tidy_settings))
