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
        lines = template.readlines()
        try:
            lines = replace_template_tags(lines, root_path)
        except IOError: # included file not found
            print('''error: referenced template in %s not found; see following error''' % file['template'])
            raise
        
        try:
            lines = replace_text_tags(lines, file, root_path)
        except IOError: # included file not found
            print('''error: referenced content file in %s not found; see following error''' % file['path'])
            raise
        except KeyError as e: # content tag not found in manifest
            print('''warning: content tag %s found in %s, but no replacement file is specified''' % (e, file['path']))

        for line in lines:
            m = re.search(r'{\@(?P<name>\w+)}', line)
            if m:
                span = m.span()
                try:
                    url = [file['path'] for file in files if 'name' in file and file['name'] == m.group('name')][0]
                    line = line[:span[0]] + url + line[span[1]:]
                except IndexError:
                    print('''warning: referenced URL %s in %s not found''' % (m.group('name'), file['path']))
            ret.append(line)
    return ret

def replace_template_tags(lines, root_path):
    """replaces all {/path/to/template} tags with the text of the template, with the same replacement performed on the template. paths are relative to root_path, even if prefixed with /."""
    ret = []
    for line in lines:
        m = re.search(r'{/' + path_re + '}', line)
        if m:
            span = m.span()
            template_path = m.group('path').lstrip('/')
            with open(os.path.join(root_path, template_path)) as template:
                template_lines = replace_template_tags(template.readlines(), root_path)
                template_lines[0] = line[:span[0]] + template_lines[0]
                template_lines[-1] = template_lines[-1].rstrip('\n') + line[span[1]:]
                ret += template_lines
        else:            
            ret.append(line)
    return ret

def replace_text_tags(lines, file, root_path):
    """replaces all {name} tags with the associated text, given the information in file."""
    ret = []
    for line in lines:
        m = re.search(r'{(?P<name>\w+)}', line)
        if m:
            span = m.span()
            with open(os.path.join(root_path, file['content'][m.group('name')])) as content:
                content_lines = content.readlines()
                content_lines[0] = line[:span[0]] + content_lines[0]
                content_lines[-1] = content_lines[-1].rstrip('\n') + line[span[1]:]
                ret += content_lines
        else:
            ret.append(line)
    return ret

def render_from_manifest(manifest_path):
    with open(manifest_path) as manifest:
        files = manifest_to_files(manifest)
    for f in files:
        print '%s:' % f['path']
        for line in render_file(f, files, os.path.dirname(manifest_path)):
            print line,

