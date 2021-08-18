#!/usr/bin/env python3

import subprocess
import tempfile
import shutil
import sys
import os


with tempfile.TemporaryDirectory() as tmpdir:
    #tmpdir = '/tmp/a.dir'
    subprocess.check_call([sys.executable,
        'scripts/linux_link.py', 'zenoblend/bin', tmpdir])
    for fname in os.listdir(tmpdir):
        dstpath = os.path.join(tmpdir, fname)
        print('patching', dstpath)
        subprocess.check_call(['patchelf', '--set-rpath', '${ORIGIN}', dstpath])
    shutil.rmtree('zenoblend/bin', ignore_errors=True)
    shutil.copytree(tmpdir, 'zenoblend/bin')
