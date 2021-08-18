#!/usr/bin/env python3

import os
import sys
import time
import shutil
import subprocess

if sys.platform == 'win32':
    os_name = 'windows'
elif sys.platform == 'linux':
    os_name = 'linux'
else:
    raise AssertionError('not supported platform: {}'.format(sys.platform))

version = int(time.strftime('%Y')), int(time.strftime('%m')), int(time.strftime('%d'))
version = '{}.{}.{}'.format(*version)

print('==> building release for version={} os_name={}'.format(version, os_name))
subprocess.check_call([sys.executable, 'build.py'])

if os_name == 'linux':
    print('==> copying linux shared libraries')
    subprocess.check_call([sys.executable, 'scripts/linux_dist.py'])

print('==> creating packaging directory')
if not os.path.exists('dist'):
    os.mkdir('dist')

shutil.copytree('zenoblend', 'dist/zenoblend')

print('==> appending version informations')
with open('dist/zenoblend/__init__.py', 'r') as f:
    content = f.read()

content = content.replace("'version': (0, 0, 0)",
        "'version': ({}, {}, {})".format(*version.split('.')))

with open('dist/zenoblend/__init__.py', 'w') as f:
    f.write(content)

zipname = 'dist/zenoblend-{}-{}'.format(os_name, version)
print('==> creating zip archive at {}'.format(zipname))
shutil.make_archive(zipname, 'zip', 'zenoblend', verbose=1)
print('==> done with zip archive {}.zip'.format(zipname))
