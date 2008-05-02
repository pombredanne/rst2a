#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rst2a: Convert reStructuredText documents to other formats.
# rst2a.pdf: Default options and functions for creating PDF files from docutils
#            document trees. A significant number of temporary files are
#            created and then removed in this process, and the pdflatex command
#            must be installed on the system.
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

from tempfile import mkdtemp
import os
import subprocess

from rst2a import latex, common

def pdflatex_installed():
    try:
        subprocess.check_call(['pdflatex', '-version'])
    except subprocess.CalledProcessError:
        return False
    return True

def call_pdflatex(latex_filename, pdf_dir=getcwdu()):
    try:
        subprocess.check_call(['pdflatex', '-halt-on-errors', latex_filename],
            cwd=pdf_dir)
    except subprocess.CalledProcessError, exc_instance:
        return False, exc_instance.returncode
    return True, 0

def call_pdflatex_repeat(n, latex_filename, pdf_dir=getcwdu()):
    if n == 0:
        return 0
    success, return_code = call_pdflatex(latex_filename, pdf_dir=pdf_dir)
    if not success:
        return return_code
    return call_pdflatex_repeat(n - 1, latex_filename, pdf_dir=pdf_dir)

def doctree_to_pdf(doctree, img_localizer, stylesheet_url='',
    settings=latex.DEFAULT_LATEX_OVERRIDES, *args, **kwargs):
    if not pdflatex_installed():
        raise EnvironmentError((127, 'pdflatex not installed.'))
    cleanup_stylesheet = False
    latex_string, extra_files = latex.doctree_to_latex(doctree, img_localizer,
        settings=settings, stylesheet_url=stylesheet_url, *args, **kwargs)
    if os.path.splitext(extra_files[0])[1] == '.tex':
        cleanup_stylesheet = True
    temp_pdf_dir = mkdtemp()
    temp_latex_filename = common.create_temp_file(latex_string, suffix='.tex',
        dir=temp_pdf_dir)
    err = call_pdflatex_repeat(3, temp_latex_filename, pdf_dir=temp_pdf_dir)
    if err == 0:
        pdf_conversion_successful = True
    else:
        pdf_conversion_successful = False
    img_localizer.cleanup_images(doctree)
    if cleanup_stylesheet:
        os.remove(extra_files[0])
    if pdf_conversion_successful:
        pdf_prefix = os.path.splitext(temp_latex_filename)[0]
        pdf_filename = pdf_prefix + os.extsep + 'pdf'
        pdf_handle = open(pdf_filename)
        pdf_data = pdf_handle.read()
        pdf_handle.close()
        common.remove_dir(temp_pdf_dir)
        return pdf_data
    else:
        common.remove_dir(temp_pdf_dir)
        raise EnvironmentError((err, 'PDF conversion unsuccessful.'))
