#!/usr/bin/blender -P

import os, sys

repo_path = os.path.dirname(os.path.abspath(__file__))

if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

print('====== restart ======')
if 'zenoblend' in sys.modules:
    sys.modules['zenoblend'].unregister()

    del sys.modules['zenoblend']
    for key in list(sys.modules.keys()):
        if key.startswith('zeno'):
            del sys.modules[key]

__import__('zenoblend').register()
