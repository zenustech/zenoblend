import bpy


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


def demo():
    mesh = bpy.context.object.data
    verts = mesh_get_vertices(mesh)
    for i in range(len(verts)):
        verts[i] += 0.1
    mesh_set_vertices(mesh, verts)


def register():
    demo()


def unregister():
    pass
