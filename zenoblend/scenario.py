import bpy

from .dll import core


def meshFromBlender(mesh):
    vertCount = len(mesh.vertices)
    vertPtr = mesh.vertices[0].as_pointer() if vertCount else 0

    loopCount = len(mesh.loops)
    loopPtr = mesh.loops[0].as_pointer() if loopCount else 0

    polyCount = len(mesh.polygons)
    polyPtr = mesh.polygons[0].as_pointer() if polyCount else 0

    return vertPtr, vertCount, loopPtr, loopCount, polyPtr, polyCount


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


sceneId = None
lastFrameId = None


def load_scene(jsonStr):
    global sceneId
    delete_scene()
    sceneId = core.createScene()
    core.sceneLoadFromJson(sceneId, jsonStr)


def delete_scene():
    global sceneId
    global lastFrameId
    lastFrameId = None
    if sceneId is not None:
        core.deleteScene(sceneId)
    sceneId = None


def execute_scene():
    core.sceneSwitchToGraph(sceneId, 'NodeTree')
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    inputNames = core.graphGetEndpointNames(graphPtr)
    for inputName in inputNames:
        if inputName not in bpy.data.objects:
            raise RuntimeError('No object named `{}` in scene'.format(inputName))
        else:
            blenderObj = bpy.data.objects[inputName]
            blenderMesh = blenderObj.data
        matrix = tuple(map(tuple, blenderObj.matrix_world))
        meshData = meshFromBlender(blenderMesh)
        core.graphSetEndpointMesh(graphPtr, inputName, matrix, *meshData)

    core.graphApply(graphPtr)

    outputNames = core.graphGetEndpointSetNames(graphPtr)
    for outputName in outputNames:
        outMeshPtr = core.graphGetEndpointSetMesh(graphPtr, outputName)
        matrix = core.meshGetMatrix(outMeshPtr)
        if outputName not in bpy.data.objects:
            blenderMesh = bpy.data.meshes.new(outputName)
            blenderObj = bpy.data.objects.new(outputName, blenderMesh)
            bpy.context.collection.objects.link(blenderObj)
        else:
            blenderObj = bpy.data.objects[outputName]
            blenderMesh = blenderObj.data
        if any(map(any, matrix)):
            blenderObj.matrix_world = matrix
        meshToBlender(outMeshPtr, blenderMesh)


def update_scene():
    if sceneId is None:
        return
    global lastFrameId
    currFrameId = bpy.context.scene.frame_current
    if lastFrameId is None or currFrameId == lastFrameId + 1:
        print('executing frame:', currFrameId)
        execute_scene()
        lastFrameId = currFrameId


@bpy.app.handlers.persistent
def frame_update_callback(*unused):
    update_scene()


def register():
    if frame_update_callback not in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.append(frame_update_callback)


def unregister():
    delete_scene()
    if frame_update_callback in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(frame_update_callback)
