import bpy
import time

from .dll import core

# https://github.com/LuxCoreRender/BlendLuxCore/blob/b1ad8e6041bb088e6e4fc53457421b36139d89e7/export/mesh_converter.py
def _prepare_mesh(obj, depsgraph, no_modifiers=False):
    """
    Create a temporary mesh from an object.
    The mesh is guaranteed to be removed when the calling block ends.
    Can return None if no mesh could be created from the object (e.g. for empties)
    Use it like this:
    with mesh_converter.convert(obj, depsgraph) as mesh:
        if mesh:
            print(mesh.name)
            ...
    """

    if no_modifiers:
        return obj.data, lambda: None

    mesh = None
    object_eval = None

    object_eval = obj.evaluated_get(depsgraph)
    if object_eval:
        mesh = object_eval.to_mesh()

        if mesh:
            # TODO test if this makes sense
            # If negative scaling, we have to invert the normals
            # if not mesh.has_custom_normals and object_eval.matrix_world.determinant() < 0.0:
            #     # Does not handle custom normals
            #     mesh.flip_normals()

            mesh.calc_loop_triangles()
            if not mesh.loop_triangles:
                object_eval.to_mesh_clear()
                mesh = None

        if mesh:
            if mesh.use_auto_smooth:
                if not mesh.has_custom_normals:
                    mesh.calc_normals()
                mesh.split_faces()

            mesh.calc_loop_triangles()

            if mesh.has_custom_normals:
                mesh.calc_normals_split()

    if not mesh:
        return obj.data, lambda: None

    def callback():
        if object_eval and mesh:
            object_eval.to_mesh_clear()

    return mesh, callback


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
nextFrameId = None


def load_scene(jsonStr):
    global sceneId
    delete_scene()
    sceneId = core.createScene()
    core.sceneLoadFromJson(sceneId, jsonStr)


def delete_scene():
    global sceneId
    global nextFrameId
    nextFrameId = None
    if sceneId is not None:
        core.deleteScene(sceneId)
    sceneId = None
    frameCache.clear()


def execute_scene(graph_name, is_framed):
    if is_framed:
        currFrameId = bpy.context.scene.frame_current
        currFrameCache = frameCache.setdefault(currFrameId, {})

    depsgraph = bpy.context.evaluated_depsgraph_get()

    core.sceneSwitchToGraph(sceneId, graph_name)
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    prepareCallbacks = []
    inputNames = core.graphGetEndpointNames(graphPtr)
    for inputName in inputNames:
        if inputName not in bpy.data.objects:
            raise RuntimeError('No object named `{}` in scene'.format(inputName))
        else:
            blenderObj = bpy.data.objects[inputName]
            blenderMesh = blenderObj.data
        matrix = tuple(map(tuple, blenderObj.matrix_world))
        preparedMesh, prepareCallback = _prepare_mesh(blenderObj, depsgraph)
        prepareCallbacks.append(prepareCallback)
        meshData = meshFromBlender(preparedMesh)
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
            if is_framed:
                # todo: only need to copy the material actually:
                blenderMesh = blenderObj.data.copy()
                blenderObj.data = blenderMesh
            else:
                blenderMesh = blenderObj.data
        if any(map(any, matrix)):
            blenderObj.matrix_world = matrix
        if is_framed:
            currFrameCache[blenderObj.name] = blenderMesh.name
        meshToBlender(outMeshPtr, blenderMesh)

    for cb in prepareCallbacks:
        cb()


frameCache = {}


def update_frame():
    global nextFrameId
    currFrameId = bpy.context.scene.frame_current
    if nextFrameId is None:
        nextFrameId = bpy.context.scene.frame_start
    if currFrameId > bpy.context.scene.frame_end:
        return
    if currFrameId == nextFrameId:
        print(time.strftime('%H:%M:%S'), 'executing frame:', currFrameId)
        execute_scene('NodeTreeFramed', is_framed=True)
        nextFrameId = currFrameId + 1

    if currFrameId not in frameCache:
        return
    for objName, meshName in frameCache[currFrameId].items():
        if objName not in bpy.data.objects:
            continue
        if meshName not in bpy.data.meshes:
            continue
        blenderObj = bpy.data.objects[objName]
        blenderMesh = bpy.data.meshes[meshName]
        if blenderObj.data is not blenderMesh:
            blenderObj.data = blenderMesh


def update_scene():
    currFrameId = bpy.context.scene.frame_current
    print(time.strftime('%H:%M:%S'), 'updating scene:', currFrameId)
    execute_scene('NodeTree', is_framed=False)


@bpy.app.handlers.persistent
def frame_update_callback(*unused):
    if sceneId is None:
        return

    global nowUpdating
    try:
        nowUpdating = True
        update_scene()
        update_frame()
    finally:
        nowUpdating = False


nowUpdating = False


@bpy.app.handlers.persistent
def scene_update_callback(*unused):
    if sceneId is None:
        return

    global nowUpdating
    if not nowUpdating:
        try:
            nowUpdating = True
            update_scene()
        finally:
            nowUpdating = False


def register():
    if frame_update_callback not in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.append(frame_update_callback)
    if scene_update_callback not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(scene_update_callback)


def unregister():
    delete_scene()
    if frame_update_callback in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(frame_update_callback)
    if scene_update_callback in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(scene_update_callback)
