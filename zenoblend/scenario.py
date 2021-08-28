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
lastJsonStr = None


def load_scene(jsonStr):
    global sceneId
    global lastJsonStr
    delete_scene()
    lastJsonStr = jsonStr
    sceneId = core.createScene()
    core.sceneLoadFromJson(sceneId, jsonStr)


def reload_scene():  # todo: have an option to turn off this
    global sceneId
    global lastJsonStr
    from .execute_operator import dump_scene
    jsonStr = dump_scene()
    if lastJsonStr == jsonStr:
        return False
    print(time.strftime('[%H:%M:%S]'), 'reload_scene')
    t0 = time.time()
    load_scene(jsonStr)
    print('reload_scene spent', '{:.4f}s'.format(time.time() - t0))
    return True


def delete_scene():
    global sceneId
    global nextFrameId
    print(time.strftime('[%H:%M:%S]'), 'delete_scene')
    nextFrameId = None
    if sceneId is not None:
        core.deleteScene(sceneId)
    sceneId = None
    frameCache.clear()


def graph_deal_input(graphPtr, inputName):
    if inputName not in bpy.data.objects:
        raise RuntimeError('No object named `{}` in scene'.format(inputName))
    blenderObj = bpy.data.objects[inputName]
    matrix = tuple(map(tuple, blenderObj.matrix_world))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    prepareCallback = lambda: NOne
    blenderMesh = blenderObj.data

    if blenderMesh is None:
        core.graphSetInputAxis(graphPtr, inputName, matrix)

    elif isinstance(blenderMesh, bpy.types.Mesh):
        preparedMesh, prepareCallback = _prepare_mesh(blenderObj, depsgraph)
        meshData = meshFromBlender(preparedMesh)
        core.graphSetInputMesh(graphPtr, inputName, matrix, *meshData)

    else:
        raise RuntimeError('Unexpected input object type: {}'.format(blenderMesh))

    return prepareCallback


def graph_deal_output(graphPtr, outputName, is_framed):
    if outputName not in bpy.data.objects:
        print('WARNING: object {} not exist, creating now'.format(outputName))
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

    outMeshPtr = core.graphGetOutputMesh(graphPtr, outputName)
    matrix = core.meshGetMatrix(outMeshPtr)
    if any(map(any, matrix)):
        blenderObj.matrix_world = matrix

    if is_framed:
        currFrameId = bpy.context.scene.frame_current
        currFrameCache = frameCache.setdefault(currFrameId, {})
        currFrameCache[blenderObj.name] = blenderMesh.name

    meshToBlender(outMeshPtr, blenderMesh)


def execute_scene(graph_name, is_framed):
    core.sceneSwitchToGraph(sceneId, graph_name)
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    prepareCallbacks = []
    inputNames = core.graphGetInputNames(graphPtr)
    for inputName in inputNames:
        cb = graph_deal_input(graphPtr, inputName)
        prepareCallbacks.append(cb)

    core.graphApply(graphPtr)

    outputNames = core.graphGetOutputNames(graphPtr)
    for outputName in outputNames:
        graph_deal_output(graphPtr, outputName, is_framed)

    for cb in prepareCallbacks:
        cb()


def get_dependencies(graph_name):
    core.sceneSwitchToGraph(sceneId, graph_name)
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    inputNames = core.graphGetInputNames(graphPtr)
    return inputNames


frameCache = {}


def update_frame():
    global nextFrameId
    currFrameId = bpy.context.scene.frame_current
    if nextFrameId is None:
        nextFrameId = bpy.context.scene.frame_start
    if currFrameId > bpy.context.scene.frame_end:
        return
    if currFrameId == nextFrameId:
        print(time.strftime('[%H:%M:%S]'), 'update_frame at', currFrameId)
        t0 = time.time()
        execute_scene('NodeTreeFramed', is_framed=True)
        print('update_frame spent', '{:.4f}s'.format(time.time() - t0))
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
    print(time.strftime('[%H:%M:%S]'), 'update_scene')
    t0 = time.time()
    execute_scene('NodeTree', is_framed=False)
    print('update_scene spent', '{:.4f}s'.format(time.time() - t0))


@bpy.app.handlers.persistent
def frame_update_callback(scene=None, *unused):
    if sceneId is None:
        return

    global nowUpdating
    try:
        nowUpdating = True
        reload_scene()
        update_scene()
        update_frame()
    finally:
        nowUpdating = False


nowUpdating = False


@bpy.app.handlers.persistent
def scene_update_callback(scene, depsgraph):
    if sceneId is None:
        return

    needs_update = False

    our_deps = get_dependencies('NodeTree')
    for update in depsgraph.updates:
        object = update.id
        if isinstance(object, bpy.types.Mesh):
            object = object.id_data
        if not isinstance(object, bpy.types.Object):
            continue
        if object.name in our_deps:
            print(time.strftime('[%H:%M:%S]'), 'update cause:', object.name)
            needs_update = True
            break
    else:

        if reload_scene():
            print(time.strftime('[%H:%M:%S]'), 'update cause node graph')
            needs_update = True

    if not needs_update:
        return

    global nowUpdating
    if not nowUpdating:
        try:
            nowUpdating = True
            update_scene()
        finally:
            nowUpdating = False


def register():
    if frame_update_callback not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(frame_update_callback)
    if scene_update_callback not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(scene_update_callback)


def unregister():
    delete_scene()
    if frame_update_callback in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(frame_update_callback)
    if scene_update_callback in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(scene_update_callback)
