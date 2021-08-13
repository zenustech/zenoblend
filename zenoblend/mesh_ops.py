import bpy

from .dll import core


def meshFromBlender(meshPtr, mesh):
    vertCount = len(mesh.vertices)
    vertPtr = mesh.vertices[0].as_pointer() if vertCount else 0
    core.meshSetVertices(meshPtr, vertPtr, vertCount)

    loopCount = len(mesh.loops)
    loopPtr = mesh.loops[0].as_pointer() if loopCount else 0
    core.meshSetLoops(meshPtr, loopPtr, loopCount)

    polyCount = len(mesh.polygons)
    polyPtr = mesh.polygons[0].as_pointer() if polyCount else 0
    core.meshSetPolygons(meshPtr, polyPtr, polyCount)


def meshToBlender(meshPtr, mesh):
    mesh.clear_geometry()

    vertCount = core.meshGetVerticesCount(meshPtr)
    mesh.vertices.add(vertCount)
    assert vertCount == len(mesh.vertices), (vertCount, len(mesh.vertices))
    vertPtr = mesh.vertices[0].as_pointer() if vertCount else 0
    core.meshGetVertices(meshPtr, vertPtr, vertCount)

    loopCount = core.meshGetLoopsCount(meshPtr)
    mesh.loops.add(loopCount)
    assert loopCount == len(mesh.loops), (loopCount, len(mesh.loops))
    loopPtr = mesh.loops[0].as_pointer() if loopCount else 0
    core.meshGetLoops(meshPtr, loopPtr, loopCount)

    polyCount = core.meshGetPolygonsCount(meshPtr)
    mesh.polygons.add(polyCount)
    assert polyCount == len(mesh.polygons), (polyCount, len(mesh.polygons))
    polyPtr = mesh.polygons[0].as_pointer() if polyCount else 0
    core.meshGetPolygons(meshPtr, polyPtr, polyCount)

    mesh.update()


def execute_graph(jsonStr):
    sceneId = core.createScene()
    core.sceneLoadFromJson(sceneId, jsonStr)

    core.sceneSwitchToGraph(sceneId, 'main')
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    inputNames = core.graphGetInputNames()
    outputNames = core.graphGetOutputNames()

    for inputName in inputNames:
        inMeshPtr = core.graphCreateInputMesh(graphPtr, inputName)
        if inputName not in bpy.data.objects:
            raise RuntimeError('No object named `{}` in scene'.format(inputName))
        else:
            blenderObj = bpy.data.objects[inputName]
        meshFromBlender(inMeshPtr, blenderMesh)

    core.graphApply(graphPtr)

    for outputName in outputNames:
        outMeshPtr = core.graphGetOutputMesh(graphPtr, outputName)
        if outputName not in bpy.data.objects:
            blenderMesh = bpy.data.meshes.new(outputname)
            blenderObj = bpy.data.objects.new(outputName, blenderMesh)
        else:
            blenderObj = bpy.data.objects[outputName]
        meshToBlender(outMeshPtr, blenderMesh)

    core.deleteScene(sceneId)


def register():
    pass


def unregister():
    pass
