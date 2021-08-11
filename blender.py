# run this in blender scripting module to debug zenoblend
# the path below should be modified to fit your location:
repo_path = '/home/bate/Codes/zeno-blender'

import sys

if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

if 'zenoblend' in sys.modules:
    sys.modules['zenoblend'].unregister()

    del sys.modules['zenoblend']
    for key in list(sys.modules.keys()):
        if key.startswith('zeno'):
            del sys.modules[key]

__import__('zenoblend').register()
