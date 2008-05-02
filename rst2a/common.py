#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rst2a: Convert reStructuredText documents to other formats.
# rst2a.common: Several functions and definitions which are used in one or more
#               of the other rst2a component modules.
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

import tempfile
import os

VALID_NETLOCS = ('ftp', 'http', 'https', 'shttp', 'sftp')

def remove_dir(dirname):
    for temp_dirname, sub_dirs, files in os.walk(dirname):
        if (not sub_dirs) and (not files):
            os.rmdir(temp_dirname)
        if files:
            for filename in files:
                os.remove(join(temp_dirname, filename))
        if sub_dirs:
            for sub_dir in sub_dirs:
                remove_dir(sub_dir)
        os.rmdir(temp_dirname)
    os.rmdir(dirname)


def is_url(url, net_loc=''):
    url_net_loc = urlparse(url)[0]
    if not net_loc:
        if url_net_loc in VALID_NETLOCS:
            return True
    elif hasattr(net_loc, '__iter__'):
        if url_net_loc in net_loc:
            return True
    elif isinstance(net_loc, basestring) and (url_net_loc == net_loc):
        return True
    return False


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
    raise ValueError('Value %r not found in dictionary' % (value,))


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
    temp_filename = tempfile.mkstemp(*args, **kwargs)[1]
    temp_handle = open(temp_filename, 'w')
    if isinstance(filein, basestring):
        temp_handle.write(filein)
    elif is_filelike(filein):
        stream_cp(filein, temp_handle)
    else:
        temp_handle.close()
        remove(temp_filename)
        raise TypeError("""Temporary file creation needs a file-like object \
or string; %r received instead.""" % (filein,))
    temp_handle.close()
    return temp_filename
