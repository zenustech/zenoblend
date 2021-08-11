import bpy

from . import zenoblend_pybind11_module as core


def demo():
    mesh = bpy.context.object.data
    core.testMesh(mesh.as_pointer())


def register():
    print('=== register ===')
    demo()


def unregister():
    pass
