#!/usr/bin/python

#
# grizz
# static website generator
# Kevin Gessner, 2010-01-24
#

import os
import re

path_re = r'(?P<path>[-a-zA-Z0-9_./]+)'

class InvalidLineError(Exception):
    def __init__(self, expected, line):
        self.expected = expected
        self.line = line
    def __str__(self):
        return 'Invalid line: expecting %s, got "%s"' % (self.expected, self.line)

def manifest_to_files(manifest):
    """converts a manifest into a list of file objects, one per file in the manifest.

    manifest should be an iterable of lines (e.g. a file handle, list of strings, etc.)
    """
    ret = []
    file = {}
    for line in manifest:
        line = line.strip()
        if (not line) and file:
            ret.append(file)
            file = {}
        elif not 'path' in file:
            m = re.match(path_re + ':(\s+\((?P<name>\w+)\))?', line)
            if not m: raise InvalidLineError('path', line)
            file['path'] = m.group('path').lstrip('/')
            if m.group('name'):
                file['name'] = m.group('name')
        elif not 'template' in file:
            m = re.match(path_re, line)
            if not m: raise InvalidLineError('template', line)
            file['template'] = m.group('path').lstrip('/')
        else:
            if not 'content' in file:
                file['content'] = {}
            m = re.match(r'(?P<name>\w+): ' + path_re, line)
            if not m: raise InvalidLineError('content', line)
            if m.group('name') in file['content']:
                raise Exception('found extra definition of %s content in %s' % (m.group('name'), file['path']))
            file['content'][m.group('name')] = m.group('path').lstrip('/')
    if file:
        ret.append(file)
    return ret

def render_file(file, files, root_path):
    """renders file into a list of strings, based on the given files"""
    ret = []
    with open(os.path.join(root_path, file['template']), 'r') as template:
        for line in template:
            m = re.search(r'{(?P<name>\w+)}', line)
            if m:
                if not ('content' in file and m.group('name') in file['content']):
                    print('''warning: found content %s in template %s, but there's no associated file''' % (m.group('name'), file['template']))
                else:
                    span = m.span()
                    with open(os.path.join(root_path, file['content'][m.group('name')])) as content:
                        content_lines = content.readlines()
                        if len(content_lines) == 1:
                            ret.append(line[:span[0]] + content_lines[0].rstrip('\n') + line[span[1]:])
                        else:
                            i = 0
                            for content_line in content_lines:
                                if i == 0:
                                    ret.append(line[:span[0]] + content_line)
                                elif i == len(content_lines) - 1:
                                    ret.append(content_line.rstrip('\n') + line[span[1]:])
                                else:
                                    ret.append(content_line)
                                i += 1
            else:
                ret.append(line)
    return ret
    
