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
            # TODO test if this makes sensegraphSetInputMesh2
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

    edgeCount = len(mesh.edges)
    edgePtr = mesh.edges[0].as_pointer() if edgeCount else 0

    return vertPtr, vertCount, loopPtr, loopCount, polyPtr, polyCount, edgePtr, edgeCount


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

    edgeCount = core.meshGetEdgesCount(meshPtr)
    mesh.edges.add(edgeCount)
    assert edgeCount == len(mesh.edges), (edgeCount, len(mesh.edges))
    edgePtr = mesh.edges[0].as_pointer() if edgeCount else 0
    core.meshGetEdges(meshPtr, edgePtr, edgeCount)

    mesh.use_auto_smooth = core.meshGetUseAutoSmooth(meshPtr)

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
    print("reload")
    jsonStr = dump_scene()
    if sceneId is not None and lastJsonStr == jsonStr:
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

# if the input name is not an object's name, it might be a collection name
def graph_deal_input(graphPtr, inputName):
    if inputName not in bpy.data.objects:
        raise RuntimeError('No object named `{}` in scene'.format(inputName))
        # return lambda: None
    blenderObj = bpy.data.objects[inputName]
    matrix = tuple(map(tuple, blenderObj.matrix_world))

    # print("matrix_world:\n{}".format(matrix))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    prepareCallback = lambda: None

    # An Axis
    if blenderObj.type == 'EMPTY':
        core.graphSetInputAxis(graphPtr, inputName, matrix)
    # A Mesh
    elif blenderObj.type == 'MESH':
        preparedMesh, prepareCallback = _prepare_mesh(blenderObj, depsgraph)
        core.graphSetInputMesh2(graphPtr,inputName,matrix,blenderObj.data.as_pointer())
    else:
        raise RuntimeError('Unexpected input object type: {}'.format(blenderObj.type))

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
    # print("outMeshAttrs:")
    # for attrName, attrType in core.meshGetVertAttrNameType(outMeshPtr).items():
    #     print("attrName : {}",format(attrName))


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


def graph_deal_collection_input(graphPtr,_inputColName): # return a list a mesh callbacks
    colName = _inputColName[4:]
    if colName not in bpy.data.collections:
        raise RuntimeError('No collection named `{}` in scene'.format(colName))
    C = bpy.data.collections[colName]
    cbs = []
    for objName in C.all_objects.keys():
        if bpy.data.objects[objName].type == 'MESH':
            cbs.append(graph_deal_input(graphPtr,objName))
            core.graphUpdateCollectionDict(graphPtr,colName,objName)
    return cbs

# if the input is an armature, we should update the bone-binding relationship, and input the geo of the bones
def graph_deal_armature_input(graphPtr,_armature_name):
    armature_name = _armature_name[4:]
    if armature_name not in bpy.data.objects:
        raise RuntimeError('No Armature named {} in scene'.format(armature_name))
    A = bpy.data.objects[armature_name]
    if A.type != 'ARMATURE':
        raise RuntimeError('No Armature named {} in objects'.format(armature_name))
    cbs = []

#   the dynamic data of bones 
    poses = A.pose.bones
#   the static data of bones
    btree = A.data.bones

    # Make sure the binded bone geometries are loaded in
    bone2geo = {}
    for bone in btree.keys():
        bone2geo[bone] = "None"
    for obj in A.children:
        if obj.type == 'MESH':
            cbs.append(graph_deal_input(graphPtr,obj.name))
            bone2geo[obj.parent_bone] = obj.name

    print("bone2geo:\n{}".format(bone2geo))

    bone2idx = {}
    for i in range(len(btree.keys())):
        bone2idx[btree[i].name] = i
    # (parent_idx,bone_idname,bone_custom_shape_idname,loc_quat,loc_b)
    bone_tree = []
    print("PYTYON_INPUT:")
    for i in range(len(btree.keys())):
        bone = btree[i]
        bone_name_full = armature_name + '@' + bone.name
        parent_idx = -1 if bone.parent is None else bone2idx[bone.parent.name]
        bone_custom_shape_name = bone2geo[bone.name]
        pose = poses[bone.name]
        # safe the rotation mode
        ori_mode = pose.rotation_mode
        # Update the quaternion
        pose.rotation_mode = 'QUATERNION'
        # Store as tuple

        bone_tree.append(
            (   parent_idx
            ,   bone_name_full
            ,   bone_custom_shape_name
            # ,   tuple(bone.head_local) # the head local lies in the matrix_local, it is a general case
            ,   tuple(pose.rotation_quaternion)
            ,   tuple(pose.location)
            ,   tuple(map(tuple,bone.matrix_local))
            )
        )

        # print("{}-{}-{}-{}-{}-{}".format(parent_idx,bone_name_full,bone_custom_shape_name,bone.head_local,pose.rotation_quaternion,pose.location))
        pose.rotation_mode = ori_mode

    # do forward kinematics and write the resulted pose into core
    core.graphSetInputBoneStructure(graphPtr,armature_name,bone_tree)

    return cbs


def execute_scene(graph_name, is_framed):
    t0 = time.time()


    core.sceneSwitchToGraph(sceneId, graph_name)
    graphPtr = core.sceneGetCurrentGraph(sceneId)
    core.graphClearDrawBuffer(graphPtr)

    # print('T1 spent', '{:.4f}s'.format(time.time() - t0))

    t0 = time.time()

    prepareCallbacks = []
    inputNames = core.graphGetInputNames(graphPtr) # might include collection names
    print('graph inputs:', inputNames)
    for inputName in inputNames:
        if inputName.startswith('@BC_'): # collection name
            print("BC!!!")
            prepareCallbacks.extend(graph_deal_collection_input(graphPtr, inputName))
        elif inputName.startswith('@BA_'): # armature name
            print("BA!!!")
            prepareCallbacks.extend(graph_deal_armature_input(graphPtr,inputName))
        else: # input name indicating a mesh name
            prepareCallbacks.append(graph_deal_input(graphPtr, inputName))

    # print('T2 spent', '{:.4f}s'.format(time.time() - t0))

    t0 = time.time()

    core.graphApply(graphPtr)


    # print('T3 spent', '{:.4f}s'.format(time.time() - t0))

    t0 = time.time()

    outputNames = core.graphGetOutputNames(graphPtr)
    # print('graph outputs:', outputNames)
    for outputName in outputNames:
        graph_deal_output(graph_name, graphPtr, outputName, is_framed)

    for cb in prepareCallbacks:
        cb()

    # print('T4 spent', '{:.4f}s'.format(time.time() - t0))

    t0 = time.time()

    from .gpu_drawer import draw_graph
    draw_graph(graph_name, graphPtr)

    # print('T5 spent', '{:.4f}s'.format(time.time() - t0))


def get_dependencies(graph_name):
    core.sceneSwitchToGraph(sceneId, graph_name)
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    inputNames = core.graphGetInputNames(graphPtr)
    return inputNames

def update_frame(graph_name):
    tree = bpy.data.node_groups[graph_name]
    currFrameId = bpy.context.scene.frame_current
    if tree.nextFrameId is None:
        tree.nextFrameId = bpy.context.scene.zeno.frame_start
    if currFrameId > bpy.context.scene.zeno.frame_end:
        return
    if currFrameId == tree.nextFrameId:
        print(time.strftime('[%H:%M:%S]'), 'update_frame at', currFrameId)
        t0 = time.time()
        execute_scene(graph_name, is_framed=True)
        print('update_frame spent', '{:.4f}s'.format(time.time() - t0))
        tree.nextFrameId = currFrameId + 1

    if currFrameId not in tree.frameCache:
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
    print("get_called")
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
                _our_deps = get_dependencies(static_tree)
                our_deps = set()
                for dep in _our_deps:
                    if dep.startswith('@BA_'):
                        our_deps.add(dep[4:])
                    if dep.startswith('@BC_'):
                        colname = dep[4:]
                        for obj in bpy.data.collections[colname].all_objects:
                            our_deps.add(obj.name)
                print("deps:{}".format(our_deps))

                needs_update = False
                for update in depsgraph.updates:
                    object = update.id
                    print("update_id: {}".format(object))
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
                    print("STILL")
                    return

                global nowUpdating
                if not nowUpdating:
                    try:
                        nowUpdating = True
                        #static_tree, framed_tree = get_tree_names()
                        if static_tree:
                            print("update_scene")
                            update_scene(static_tree)
                    finally:
                        nowUpdating = False

#@bpy.app.handlers.persistent
#def load_post_callback(dummy):
    #bpy.ops.node.zeno_apply()


def register():
    if frame_update_callback not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(frame_update_callback)
    if scene_update_callback not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(scene_update_callback)
    #if load_post_callback not in bpy.app.handlers.load_post:
        #bpy.app.handlers.load_post.append(load_post_callback)


def unregister():
    delete_scene()
    if frame_update_callback in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(frame_update_callback)
    if scene_update_callback in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(scene_update_callback)
    #if load_post_callback in bpy.app.handlers.load_post:
        #bpy.app.handlers.load_post.remove(load_post_callback)
