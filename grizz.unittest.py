import unittest
from grizz import *
import os
import difflib

class GrizzRenderTest(unittest.TestCase):
    def setUp(self):
        self.manifest = './test/manifest'
        self.root_path = os.path.dirname(self.manifest)
        self.out_path = './test/out/'
        self.cmp_path = './test/cmp/'

        def file_provider(path):
            with open(os.path.join(self.root_path, path), 'r') as f:
                return f.readlines()
        self.file_provider = file_provider
    
        self.errors = []
        self.error_handler = self.errors.append

    def testrender(self):
        with open(self.manifest) as f:
            files = manifest_to_files(f)
        for f in files:
            with open(os.path.join(self.cmp_path, f['path'].lstrip('/')), 'r') as cmp:
                diff = difflib.unified_diff(cmp.readlines(), render_file(f, files, self.file_provider, self.error_handler))
                diff = [l for l in diff]
                self.assertTrue(len(diff) == 0, 'difference in %s:\n%s' % (f['path'], '\n'.join(diff)))
    
class GrizzTemplateReplaceTest(unittest.TestCase):
    def setUp(self):
        def file_provider(path):
            try:
                return {'notext.tpl': 'foo\nbar', 'nested.tpl': 'line\n{/notext.tpl}\nand more stuff\nandmore', 'double-nested.tpl': '<p>{/nested.tpl}</p>', 'error.tpl': 'foo {/nosuch.tpl}'}[path].splitlines(True)
            except:
                raise NoSuchFileError(path)
        self.file_provider = file_provider
        
        self.errors = []
        self.error_handler = self.errors.append

    def test_non_replacement(self):
        lines = self.file_provider('notext.tpl')
        post_lines = replace_template_tags(lines, self.file_provider)
        self.assertEqual(lines, post_lines)
        self.assertEqual(self.errors, [])

    def test_replacement(self):
        lines = self.file_provider('nested.tpl')
        correct_lines = ['line\n', 'foo\n', 'bar\n', 'and more stuff\n', 'andmore']
        post_lines = replace_template_tags(lines, self.file_provider)
        self.assertEqual(correct_lines, post_lines)
        self.assertEqual(self.errors, [])
    
    def test_double_replacement(self):
        lines = self.file_provider('double-nested.tpl')
        correct_lines = ['<p>line\n', 'foo\n', 'bar\n', 'and more stuff\n', 'andmore</p>']
        post_lines = replace_template_tags(lines, self.file_provider)
        self.assertEqual(correct_lines, post_lines)
        self.assertEqual(self.errors, [])

    def test_error_replacement(self):
        lines = self.file_provider('error.tpl')
        self.assertRaises(NoSuchFileError, replace_template_tags, lines, self.file_provider)

class GrizzTextReplaceTest(unittest.TestCase):
    def setUp(self):
        def file_provider(path):
            try:
                return {'notext.tpl': 'foo\nbar', 'text.tpl': 'line\n{text}\nand more stuff\nandmore', 'two-text.tpl': '<p>{text}</p>\n<span>{text_two}</span>', 'one.txt': 'some text', 'two.txt': 'two\nlines'}[path].splitlines(True)
            except:
                raise NoSuchFileError(path)
        self.file_provider = file_provider
        
        self.errors = []
        self.error_handler = self.errors.append

    def test_non_replacement(self):
        lines = self.file_provider('notext.tpl')
        post_lines = replace_text_tags(lines, None, self.file_provider, self.error_handler)
        self.assertEqual(lines, post_lines)
        self.assertEqual(self.errors, [])

    def test_replacement(self):
        lines = self.file_provider('text.tpl')
        correct_lines = ['line\n', 'some text\n', 'and more stuff\n', 'andmore']
        post_lines = replace_text_tags(lines, {'content': {'text': 'one.txt'} }, self.file_provider, self.error_handler)
        self.assertEqual(correct_lines, post_lines)
        self.assertEqual(self.errors, [])
    
    def test_double_replacement(self):
        lines = self.file_provider('two-text.tpl')
        correct_lines = ['<p>some text</p>\n', '<span>two\n', 'lines</span>']
        post_lines = replace_text_tags(lines, {'content': {'text': 'one.txt', 'text_two': 'two.txt'} }, self.file_provider, self.error_handler)
        self.assertEqual(correct_lines, post_lines)
        self.assertEqual(self.errors, [])

    def test_error_replacement(self):
        lines = self.file_provider('text.tpl')
        correct_lines = ['line\n', '{text}\n', 'and more stuff\n', 'andmore']
        post_lines = replace_text_tags(lines, {'path': 'error-test'}, self.file_provider, self.error_handler)
        self.assertEqual(correct_lines, post_lines)
        self.assertEqual(len(self.errors), 1)
    
    def test_error_replacement_2(self):
        lines = self.file_provider('text.tpl')
        self.assertRaises(NoSuchFileError, replace_text_tags, lines, {'path': 'error-test', 'content': {'text': 'nosuchfile'}}, self.file_provider, self.error_handler)

if __name__ == '__main__':
    unittest.main()
