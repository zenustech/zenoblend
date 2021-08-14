'''
Zeno Node System Blender Intergration

Copyright (c) archibate <1931127624@qq.com> (2021- ). All Rights Reserved.
'''


bl_info = {
        'name': 'Zeno-Blend',
        'description': 'Blender intergration of the Zeno node system',
        'author': 'archibate <1931127624@qq.com>',
        'version': (0, 0, 1),
        'blender': (2, 83, 0),
        'location': 'Zeno Node Tree',
        'support': 'COMMUNITY',
        'wiki_url': 'https://github.com/zenustech/zeno/wiki',
        'tracker_url': 'https://github.com/zenustech/zeno/issues',
        'category': 'Physics',
}


from . import (
    scenario,
    node_system,
    execute_operator,
)

modules = (
    scenario,
    node_system,
    execute_operator,
)


def register():
    for mod in modules:
        mod.register()


def unregister():
    for mod in reversed(modules):
        mod.unregister()
