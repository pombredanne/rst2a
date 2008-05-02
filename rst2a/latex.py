#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rst2a: Convert reStructuredText documents to other formats.
# rst2a.latex: Default options and functions used for converting doctrees to
#              LaTeX. Images may be localized, being stored in a temporary
#              directory if they are located at remote URLs. This functionality
#              uses the rst2a.images sub-module.
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

from os.path import isfile

from docutils.core import publish_from_doctree

from rst2a.common import is_filelike, create_temp_file

DEFAULT_LATEX_OVERRIDES = {
    'no-section-numbering': True,
    'documentoptions': '10pt,a4paper',
    'documentclass': 'article',
    'font-encoding': 'T1',
    'graphicx-option': 'pdftex'
}


def doctree_to_latex(doctree, img_localizer, stylesheet_url='',
    settings=DEFAULT_LATEX_OVERRIDES, *args, **kwargs):
    cleanup_stylesheet = False
    if not isfile(str(stylesheet_url)) or is_filelike(stylesheet_url):
        stylesheet_url = create_temp_file(stylesheet_url, suffix='.tex')
        cleanup_stylesheet = True
    conversion_settings = copy(settings)
    conversion_settings['stylesheet-path'] = stylesheet_url
    img_localizer.localize_images(doctree)
    latex_string = publish_from_doctree(doctree, writer_name='latex',
        settings_overrides=conversion_settings, *args, **kwargs)
    temp_files = sorted(list(set(img_localizer.values())))
    if cleanup_stylesheet:
        temp_files = [stylesheet_path] + temp_files
    return latex_string, temp_files
