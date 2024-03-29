#!/usr/bin/python

#
# grizz
# static website generator
# Kevin Gessner, 2010-01-24
#

import os
import re
import markdown
import sys
import time
import traceback

path_re = r'(?P<path>[-a-zA-Z0-9_./]+)'
name_re = r'(?P<name>[\w-]+)'
info_re = r'^(?P<name>[^:]+):\s*(?P<contents>.+)\n$'

NOW_TIME = int(time.time())

class InvalidLineError(Exception):
    def __init__(self, expected, line):
        self.expected = expected
        self.line = line
    def __str__(self):
        return 'Invalid line: expecting %s, got "%s"' % (self.expected, self.line)

class NoSuchFileError(Exception):
    def __init__(self, path):
        self.path = path
    def __str__(self):
        return self.path

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
            m = re.match(path_re + ':(\s+\(' + name_re + '\))?', line)
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
            m = re.match(r'' + name_re + ': ' + path_re, line)
            if not m: raise InvalidLineError('content', line)
            if m.group('name') in file['content']:
                raise Exception('found extra definition of %s content in %s' % (m.group('name'), file['path']))
            file['content'][m.group('name')] = m.group('path').lstrip('/')
    if file:
        ret.append(file)
    return ret

def render_file(file, files, file_provider, error_handler):
    """renders file into a list of strings, based on the given files"""
    ret = []
    lines = file_provider(file['template'])
    try:
        lines = replace_template_tags(lines, file_provider)
    except NoSuchFileError as e: # included file not found
        error_handler('''error: referenced template %s in %s not found''' % (e, file['template']))
    
    try:
        lines = replace_text_tags(lines, file, file_provider, error_handler)
    except NoSuchFileError as e: # included file not found
        error_handler('''error: referenced content file %s in /%s not found''' % (e, file['path']))
        raise

    for line in lines:
        m = re.search(r'{\@' + name_re + '}', line)
        if m:
            span = m.span()
            try:
                url = [f['path'] for f in files if 'name' in f and f['name'] == m.group('name')][0]
                line = line[:span[0]] + url + line[span[1]:]
            except IndexError:
                error_handler('''warning: referenced URL %s in /%s not found''' % (m.group('name'), file['path']))
        ret.append(line)
    return ret

def process_replacement_lines(prefix, suffix, lines):
    """returns a list with contents of lines, with the first line prefixed with prefix, the last line suffixed with suffix, and all lines prefixed with the leading whitespace of prefix"""
    if not lines: return []
    m = re.match(r'^(?P<ws>\s*)(?P<text>.*)$', prefix)
    ws_prefix = m.group('ws')
    prefix = m.group('text')
    lines[0] = prefix + lines[0]
    lines[-1] = lines[-1].rstrip('\n') + suffix
    return [ws_prefix + line for line in lines]

def replace_template_tags(lines, file_provider):
    """replaces all {/path/to/template} tags with the text of the template, with the same replacement performed on the template. paths are relative to root_path, even if prefixed with /."""
    ret = []
    for line in lines:
        m = re.search(r'{/' + path_re + '}', line)
        if m:
            span = m.span()
            template_path = m.group('path').lstrip('/')
            template_lines = file_provider(template_path)
            template_lines = replace_template_tags(template_lines, file_provider)
            ret += process_replacement_lines(line[:span[0]], line[span[1]:], template_lines)
        else:
            ret.append(line)
    return ret

def extract_info(lines):
    ret = {}
    for line in lines:
        m = re.match(info_re, line)
        if not m: break
        ret[m.group('name')] = m.group('contents')
    return ret

def replace_text_tags(lines, file, file_provider, error_handler):
    """replaces all {name} tags with the associated text, given the information in file."""
    ret = []
    info = {}
    for line in lines:
        m = re.search(r'{' + name_re + '}', line)
        if not m: continue
        try:
            filename = file['content'][m.group('name')]
        except KeyError as e: # content tag not found in manifest; error next time
            continue
        for k, v in list(extract_info(file_provider(filename)).items()):
            if k not in info:
                info[k] = v

    for i, line in enumerate(lines):
        m = re.search(r'{' + name_re + '}', line)
        if m:
            span = m.span()
            if re.search(r'{' + name_re + '}', line[span[1]:]):
                # TODO fix this bug for real
                error_handler('''warning: multiple replacements found on line %d of /%s, but only the first will be replaced''' % (i, file['path']))
            name = m.group('name')
            if name == '_now':
                content_lines = [str(NOW_TIME)]
            else:
                try:
                    filename = file['content'][name]
                    content_lines = file_provider(filename)
                    got_info = False
                    while re.match(info_re, content_lines[0]):
                        content_lines = content_lines[1:]
                        got_info = True
                    if got_info:
                        content_lines = content_lines[1:]
                    if filename.endswith('.markdown'):
                        content_lines = markdown.markdown(''.join(content_lines)).splitlines(True)
                except KeyError as e: # content tag not found in manifest
                    try:
                        content_lines = [info[name]]
                    except KeyError as e: # no info found either
                        error_handler('''warning: content tag %s found in /%s, but no replacement file or named info is specified''' % (e, file['path']))
                        ret.append(line)
                        continue
            ret += process_replacement_lines(line[:span[0]], line[span[1]:], content_lines)
        else:
            ret.append(line)
    return ret

def render_from_manifest(manifest_path):
    """renders the site defined in the manifest at manifest_path to files"""
    root_path = os.path.dirname(manifest_path)
    out_path = os.path.join(root_path, 'out')
    if not os.access(out_path, os.F_OK):
        os.mkdir(out_path)

    def file_provider(path):
        try:
            with open(os.path.join(root_path, path)) as f:
                return f.readlines();
        except IOError as e:
            raise NoSuchFileError(e.filename)
    def error_handler(s):
        print(s)

    with open(manifest_path) as manifest:
        files = manifest_to_files(manifest)
    for f in files:
        try:
            lines = render_file(f, files, file_provider, error_handler)
        except Exception as e:
            print('%s: %s\n%s' % (f, e, traceback.format_exc()))
            return False
        out_file_path = os.path.join(out_path, f['path'])
        if out_file_path.endswith('/'):
            out_file_path += 'index.html'
        if not os.access(os.path.dirname(out_file_path), os.F_OK):
            os.makedirs(os.path.dirname(out_file_path))
        with open(out_file_path, 'w') as out_file:
            out_file.writelines(lines)
    return True

def serve(out_path):
    """starts a webserver at localhost:8080 serving the contents of the rendered site"""
    from http.server import HTTPServer
    from http.server import SimpleHTTPRequestHandler

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            tpath = SimpleHTTPRequestHandler.translate_path(self, out_path + path)
            return tpath

    try:
        server = HTTPServer(('', 8080), Handler)
        print('started server at localhost:8080 (ctrl-c to quit)...')
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()
