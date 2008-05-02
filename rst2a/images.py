#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rst2a: Convert reStructuredText documents to other formats.
# rst2a.images: Provide a docutils node visitor to localize images within a
#               document tree. This involves downloading external URLs to
#               temporary files on the local filesystem, and changing the
#               references within the doctree to point to the temporary file.
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

from cStringIO import StringIO
from os.path import isdir, isfile, splitext
from tempfile import mkdtemp, mkstemp
from urllib2 import urlopen

import docutils.nodes
try:
    import Image
except ImportError:
    Image = None

from rst2a.common import is_url, stream_cp, reverse_lookup


class ImageURLError(Exception):
    pass


class ImageLocalizer (docutils.nodes.SparseNodeVisitor):
    
    def __init__(self, document, check_images=False, local_mode=True):
        self.localized_images = {}
        self.check_images = check_images
        self.temp_dir = mkdtemp(prefix='img_')
        self.__local_mode = local_mode
        docutils.nodes.SparseNodeVisitor.__init__(self, document)
    
    def switch_mode(self):
        self.__local_mode = not self.__local_mode
    
    def localize_image(self, img_url, local_filename=None):
        if local_filename is None:
            local_filename = mkstemp(dir=self.temp_dir, suffix=img_ext)[1]
        remote_handle = urlopen(img_url)
        img_ext = splitext(img_url)[1].lower()
        assert img_ext in ('.png', '.jpg', '.gif'), \
            'Weird image extension: "%s"' % (img_ext,)
        if self.check_images and Image is not None:
            img_buffer = StringIO()
            stream_cp(remote_handle, img_buffer)
            img_buffer.seek(0)
            img = Image.open(fp=img_buffer)
            img.save(local_filename)
        else:
            local_handle = open(local_filename, 'w')
            stream_cp(remote_handle, local_handle)
            local_handle.close()
        remote_handle.close()
        return local_filename
    
    def visit_image(self, img_node):
        if self.__local_mode:
            if not isdir(self.temp_dir):
                self.temp_dir = mkdtemp(prefix='img_')
            img_url = img_node.attributes['uri']
            if isfile(img_url):
                return
            if not is_url(img_url):
                raise ImageURLError('Invalid image URL: "%s"' % (img_url,))
            elif img_url in self.localized_images:
                local_filename = self.localized_images[img_url]
                if not isfile(temp_local_filename):
                    self.localize_image(img_url, local_filename=local_filename)
                img_node.attributes['uri'] = local_filename
                return
            else:
                self.localized_images[img_url] = self.localize_image
        else:
            img_path = img_node.attributes['uri']
            if not isfile(img_path) and not is_url(img_path):
                raise ImageURLError('Invalid image URL: "%s"' % (img_path,))
            if is_url(img_path):
                return
            elif isfile(img_path):
                try:
                    img_url = reverse_lookup(self.localized_images, img_path)
                except ValueError:
                    return
                else:
                    img_node.attributes['uri'] = img_url
                    os.remove(img_path)
    
    def visit_figure(self, figure_node):
        return self.visit_image(figure_node)
    
    def localize_images(self, doctree):
        old_dir = getcwdu()
        chdir(self.temp_dir)
        doctree.walk(self)
        os.chdir(old_dir)
    
    def cleanup_images(self, doctree, delete_temp_dir=True):
        self.switch_mode()
        doctree.walk(self)
        self.switch_mode()
        if delete_temp_dir:
            try:
                os.rmdir(self.temp_dir)
            except OSError:
                pass
