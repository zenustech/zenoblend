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

    for attrName, attrType in core.meshGetVertAttrNameType(meshPtr).items():
        attrType = ['FLOAT_VECTOR', 'FLOAT'][attrType]
        if attrName not in mesh.attributes:
            mesh.attributes.new(name=attrName, type=attrType, domain='POINT')
        elif mesh.attributes[attrName].data_type != attrType or mesh.attributes[attrName].domain != 'POINT':
            mesh.attributes.remove(mesh.attributes[attrName])
            mesh.attributes.new(name=attrName, type=attrType, domain='POINT')
        print('adding POINT attribute', attrName, 'with type', attrType)

        if vertCount:
            vertAttrPtr = mesh.attributes[attrName].data[0].as_pointer()
            core.meshGetVertAttr(meshPtr, attrName, vertAttrPtr, vertCount)

    loopCount = core.meshGetLoopsCount(meshPtr)
    mesh.loops.add(loopCount)
    assert loopCount == len(mesh.loops), (loopCount, len(mesh.loops))
    loopPtr = mesh.loops[0].as_pointer() if loopCount else 0
    core.meshGetLoops(meshPtr, loopPtr, loopCount)

    # loop attributes are considered to be vertex color now...
    for attrName, attrType in core.meshGetLoopAttrNameType(meshPtr).items():
        bl_attr_name = 'Zeno_'+attrName
        if bl_attr_name not in mesh.vertex_colors:
            mesh.vertex_colors.new(name=bl_attr_name)
        loopColorPtr = mesh.vertex_colors[bl_attr_name].data[0].as_pointer() if loopCount else 0
        core.meshGetLoopColor(meshPtr, attrName, loopColorPtr, loopCount)

    polyCount = core.meshGetPolygonsCount(meshPtr)
    mesh.polygons.add(polyCount)
    assert polyCount == len(mesh.polygons), (polyCount, len(mesh.polygons))
    polyPtr = mesh.polygons[0].as_pointer() if polyCount else 0
    core.meshGetPolygons(meshPtr, polyPtr, polyCount)

    for attrName, attrType in core.meshGetPolyAttrNameType(meshPtr).items():
        attrType = ['FLOAT_VECTOR', 'FLOAT'][attrType]
        if attrName not in mesh.attributes:
            mesh.attributes.new(name=attrName, type=attrType, domain='FACE')
        elif mesh.attributes[attrName].data_type != attrType or mesh.attributes[attrName].domain != 'FACE':
            mesh.attributes.remove(mesh.attributes[attrName])
            mesh.attributes.new(name=attrName, type=attrType, domain='FACE')
        print('adding FACE attribute', attrName, 'with type', attrType)

        if polyCount:
            polyAttrPtr = mesh.attributes[attrName].data[0].as_pointer()
            core.meshGetPolyAttr(meshPtr, attrName, polyAttrPtr, polyCount)

    mesh.update()


sceneId = None
lastJsonStr = None


def load_scene(jsonStr):
    print(time.strftime('[%H:%M:%S]'), 'load_scene')
    global sceneId
    global lastJsonStr
    delete_scene()
    lastJsonStr = jsonStr
    sceneId = core.createScene()
    core.sceneLoadFromJson(sceneId, jsonStr)


def reload_scene():  # todo: have an option to turn off this
    global sceneId
    global lastJsonStr
    from .tree_dumper import dump_scene
    jsonStr = dump_scene()
    if lastJsonStr == jsonStr:
        return False
    print(time.strftime('[%H:%M:%S]'), 'reload_scene')
    t0 = time.time()
    load_scene(jsonStr)
    print('reload_scene spent', '{:.4f}s'.format(time.time() - t0))
    return True


def delete_scene():
    hadScene = False
    global sceneId   
    print(time.strftime('[%H:%M:%S]'), 'delete_scene')   
    if sceneId is not None:
        core.deleteScene(sceneId)
        hadScene = True
    sceneId = None
    
    for nodetree in get_enabled_trees():
        nodetree.nextFrameId = None
        if not hasattr(nodetree, "frameCache"):
            nodetree.frameCache = {}
        nodetree.frameCache.clear()
    return hadScene


def graph_deal_input(graphPtr, inputName):
    if inputName not in bpy.data.objects:
        raise RuntimeError('No object named `{}` in scene'.format(inputName))
    blenderObj = bpy.data.objects[inputName]
    matrix = tuple(map(tuple, blenderObj.matrix_world))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    prepareCallback = lambda: None
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


def graph_deal_output(graph_name, graphPtr, outputName, is_framed):
    if outputName not in bpy.data.objects:
        print('WARNING: object `{}` not exist, creating now'.format(outputName))
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
        tree = bpy.data.node_groups[graph_name]
        if not hasattr(tree, "frameCache"):
            tree.frameCache = {}
        currFrameCache = tree.frameCache.setdefault(currFrameId, {})
        currFrameCache[blenderObj.name] = blenderMesh.name

    meshToBlender(outMeshPtr, blenderMesh)


def execute_scene(graph_name, is_framed):
    core.sceneSwitchToGraph(sceneId, graph_name)
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    core.graphClearDrawBuffer(graphPtr)

    prepareCallbacks = []
    inputNames = core.graphGetInputNames(graphPtr)
    print('graph inputs:', inputNames)
    for inputName in inputNames:
        cb = graph_deal_input(graphPtr, inputName)
        prepareCallbacks.append(cb)

    core.graphApply(graphPtr)

    outputNames = core.graphGetOutputNames(graphPtr)
    print('graph outputs:', outputNames)
    for outputName in outputNames:
        graph_deal_output(graph_name, graphPtr, outputName, is_framed)

    for cb in prepareCallbacks:
        cb()

    from .gpu_drawer import draw_graph
    draw_graph(graph_name, graphPtr)


def get_dependencies(graph_name):
    core.sceneSwitchToGraph(sceneId, graph_name)
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    inputNames = core.graphGetInputNames(graphPtr)
    return inputNames

def update_frame(graph_name):
    tree = bpy.data.node_groups[graph_name]
    currFrameId = bpy.context.scene.frame_current
    if getattr(tree, "nextFrameId", None) is None:
        tree.nextFrameId = bpy.context.scene.zeno.frame_start
    if currFrameId > bpy.context.scene.zeno.frame_end:
        return
    if currFrameId == tree.nextFrameId:
        print(time.strftime('[%H:%M:%S]'), 'update_frame at', currFrameId)
        t0 = time.time()
        execute_scene(graph_name, is_framed=True)
        print('update_frame spent', '{:.4f}s'.format(time.time() - t0))
        tree.nextFrameId = currFrameId + 1

    
    if currFrameId not in getattr(tree, "frameCache", {}):
        return
    for objName, meshName in tree.frameCache[currFrameId].items():
        if objName not in bpy.data.objects:
            continue
        if meshName not in bpy.data.meshes:
            continue
        blenderObj = bpy.data.objects[objName]
        blenderMesh = bpy.data.meshes[meshName]
        if blenderObj.data is not blenderMesh:
            blenderObj.data = blenderMesh


def update_scene(graph_name):
    currFrameId = bpy.context.scene.frame_current
    print(time.strftime('[%H:%M:%S]'), 'update_scene')
    t0 = time.time()
    execute_scene(graph_name, is_framed=False)
    print('update_scene spent', '{:.4f}s'.format(time.time() - t0))


def get_enabled_trees():
    return [t for t in bpy.data.node_groups if t.bl_idname == 'ZenoNodeTree' and t.zeno_enabled]


@bpy.app.handlers.persistent
def frame_update_callback(*unused):
    if sceneId is None:
        return

    global nowUpdating
    try:
        nowUpdating = True

        # static_tree, framed_tree = get_tree_names()
        #if not static_tree and not framed_tree:
        #    return False
        reload_scene()
        for tree in get_enabled_trees():
            if tree.zeno_cached:
                update_frame(tree.name)
            else:
                update_scene(tree.name)
        
        # if framed_tree:
        #     update_frame(framed_tree)
        # if static_tree:
        #     update_scene(static_tree)
        return True
    finally:
        nowUpdating = False


nowUpdating = False


@bpy.app.handlers.persistent
def scene_update_callback(scene, depsgraph):
    if sceneId is None:
        return

    scene_reloaded = False

    for tree in get_enabled_trees():
        if tree.zeno_realtime_update:
            if tree.zeno_cached:
                reload_scene()
                update_frame(tree.name)
               
            else:
                static_tree = tree.name
                our_deps = get_dependencies(static_tree)

                needs_update = False
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
                    if scene_reloaded or reload_scene():
                        print(time.strftime('[%H:%M:%S]'), 'update cause node graph')
                        needs_update = True
                        scene_reloaded = True  # avoid reloading scene more than one time

                if not needs_update:
                    return

                global nowUpdating
                if not nowUpdating:
                    try:
                        nowUpdating = True
                        #static_tree, framed_tree = get_tree_names()
                        if static_tree:
                            update_scene(static_tree)
                    finally:
                        nowUpdating = False

@bpy.app.handlers.persistent
def load_post_callback(dummy):
    for tree in bpy.data.node_groups:
        if tree.bl_idname == 'ZenoNodeTree': 
            tree.zeno_realtime_update = False


def register():
    if frame_update_callback not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(frame_update_callback)
    if scene_update_callback not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(scene_update_callback)
    if load_post_callback not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_callback)


def unregister():
    delete_scene()
    if frame_update_callback in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(frame_update_callback)
    if scene_update_callback in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(scene_update_callback)
    if load_post_callback in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_callback)
