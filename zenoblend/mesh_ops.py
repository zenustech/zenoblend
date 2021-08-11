import bpy

from . import zenoblend_pybind11_module as core


def primitiveFromMesh(primPtr, mesh):
    vertCount = len(mesh.vertices)
    vertPtr = mesh.vertices[0].as_pointer()
    core.primitiveSetVertices(primPtr, vertPtr, vertCount)

def primitiveToMesh(primPtr, mesh):
    vertConnt = core.primitiveGetVerticesCount()
    if vertCount > len(mesh.vertices):
        mesh.vertices.add(vertCount - len(mesh.vertices))
    vertCount = len(mesh.vertices)
    vertPtr = mesh.vertices[0].as_pointer()
    core.primitiveGetVertices(primPtr, vertPtr, vertCount)

def demo():
    sceneId = core.createScene()
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    inPrimPtr = core.graphCreateInputPrimitive(graphPtr, 'inputPrim')
    primitiveFromMesh(inPrimPtr, bpy.context.object.data)

    core.graphApply(graphPtr)
    outPrimPtr = core.graphGetOutputPrimitive(graphPtr, 'outputPrim')
    primitiveToMesh(outPrimPtr, bpy.context.object.data)

    bpy.context.object.data.update()


def register():
    print('=== register ===')
    demo()


def unregister():
    pass
