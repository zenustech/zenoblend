import bpy

from . import zenoblend_pybind11_module as core


def demo():
    mesh = bpy.context.object.data
    vertCount = len(mesh.vertices)
    vertPtr = mesh.vertices[0].as_pointer()
    core.primitiveSetVertices(primPtr, vertPtr, vertCount)


def register():
    print('=== register ===')
    demo()


def unregister():
    pass
