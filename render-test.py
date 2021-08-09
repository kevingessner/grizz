#!/usr/bin/python

import difflib
import os.path
from grizz import *

manifest = './test/manifest'
root_path = os.path.dirname(manifest)
out_path = './test/out/'
cmp_path = './test/cmp/'

with open(manifest) as f:
    files = manifest_to_files(f)
for f in files:
    print(('checking %s...' % f['path']))
    with open(os.path.join(cmp_path, f['path'].lstrip('/')), 'r') as cmp:
        for line in difflib.unified_diff(cmp.readlines(), render_file(f, files, root_path)):
            print(line, end=' ')
        print('\n')
