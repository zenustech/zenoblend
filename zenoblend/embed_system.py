import bpy

from . import zenoblend_pybind11_module as core


def mesh_get_vertices(mesh):
    verts = [0. for i in range(len(mesh.vertices) * 3)]
    mesh.vertices.foreach_get('co', verts)
    return verts


def mesh_set_vertices(mesh, verts):
    n = len(mesh.vertices) * 3
    while len(verts) < n:
        verts.append(0.)
    while len(verts) > n:
        verts.pop()
    mesh.vertices.foreach_set('co', verts)
    mesh.update()


def demo():
    mesh = bpy.context.object.data
    verts = mesh_get_vertices(mesh)
    verts = core.getDemoVertices()
    print('setting', verts)
    mesh_set_vertices(mesh, verts)


def register():
    print('register')
    demo()


def unregister():
    pass
