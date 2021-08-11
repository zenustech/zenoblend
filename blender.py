# run this in blender scripting module to debug zenoblend
# the path below should be modified to fit your location:
repo_path = '/home/bate/Codes/zeno-blender'

import os
import sys

if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

zeno_path = os.path.join(repo_path, 'external', 'zeno')
if zeno_path not in sys.path:
    sys.path.insert(0, zeno_path)

if 'zenoblend' in sys.modules:
    sys.modules['zenoblend'].unregister()

    del sys.modules['zenoblend']
    keys = list(sys.modules.keys())
    for key in keys:
        if key.startswith('zen'):
            del sys.modules[key]

__import__('zenoblend').register()
