import bpy

from . import zenoblend_pybind11_module as core


jsonStr = '''[["clearAllState"], ["switchGraph", "main"], ["addNode", "SubInput", "d6fbed98-SubInput"], ["setNodeParam", "d6fbed98-SubInput", "type", ""], ["setNodeParam", "d6fbed98-SubInput", "name", "inputPrim"], ["setNodeParam", "d6fbed98-SubInput", "defl", ""], ["completeNode", "d6fbed98-SubInput"], ["addNode", "SubOutput", "6c4b28d4-SubOutput"], ["bindNodeInput", "6c4b28d4-SubOutput", "port", "60a8466a-TransformPrimitive", "outPrim"], ["setNodeParam", "6c4b28d4-SubOutput", "type", ""], ["setNodeParam", "6c4b28d4-SubOutput", "name", "outputPrim"], ["setNodeParam", "6c4b28d4-SubOutput", "defl", ""], ["completeNode", "6c4b28d4-SubOutput"], ["addNode", "TransformPrimitive", "60a8466a-TransformPrimitive"], ["bindNodeInput", "60a8466a-TransformPrimitive", "prim", "d99d0064-IfElse", "result"], ["bindNodeInput", "60a8466a-TransformPrimitive", "eulerXYZ", "172b2029-NumericVec3", "vec3"], ["setNodeOption", "60a8466a-TransformPrimitive", "VIEW"], ["completeNode", "60a8466a-TransformPrimitive"], ["addNode", "Make3DGridPrimitive", "0e3f294b-Make3DGridPrimitive"], ["bindNodeInput", "0e3f294b-Make3DGridPrimitive", "nx", "67716fa9-NumericInt", "value"], ["setNodeParam", "0e3f294b-Make3DGridPrimitive", "isCentered", 0], ["completeNode", "0e3f294b-Make3DGridPrimitive"], ["addNode", "NumericInt", "67716fa9-NumericInt"], ["setNodeParam", "67716fa9-NumericInt", "value", 4], ["completeNode", "67716fa9-NumericInt"], ["addNode", "IfElse", "d99d0064-IfElse"], ["bindNodeInput", "d99d0064-IfElse", "true", "d6fbed98-SubInput", "port"], ["bindNodeInput", "d99d0064-IfElse", "false", "0e3f294b-Make3DGridPrimitive", "prim"], ["bindNodeInput", "d99d0064-IfElse", "cond", "d6fbed98-SubInput", "hasValue"], ["completeNode", "d99d0064-IfElse"], ["addNode", "NumericVec3", "172b2029-NumericVec3"], ["setNodeParam", "172b2029-NumericVec3", "x", 1.0], ["setNodeParam", "172b2029-NumericVec3", "y", 0.0], ["setNodeParam", "172b2029-NumericVec3", "z", 0.0], ["completeNode", "172b2029-NumericVec3"]]'''


def meshFromBlender(meshPtr, mesh):
    vertCount = len(mesh.vertices)
    vertPtr = mesh.vertices[0].as_pointer() if vertCount else 0
    core.meshSetVertices(meshPtr, vertPtr, vertCount)

    polyCount = len(mesh.polygons)
    polyPtr = mesh.polygons[0].as_pointer() if polyCount else 0
    core.meshSetPolygons(meshPtr, polyPtr, polyCount)

    loopCount = len(mesh.loops)
    loopPtr = mesh.loops[0].as_pointer() if loopCount else 0
    core.meshSetLoops(meshPtr, loopPtr, loopCount)

def meshToBlender(meshPtr, mesh):
    mesh.clear_geometries()

    vertCount = core.meshGetVerticesCount(meshPtr)
    mesh.vertices.add(vertCount)
    assert vertCount == len(mesh.vertices), (vertCount, len(mesh.vertices))
    vertPtr = mesh.vertices[0].as_pointer() if vertCount else 0
    core.meshGetVertices(meshPtr, vertPtr, vertCount)

    polyCount = core.meshGetPolygonsCount(meshPtr)
    mesh.polygons.add(polyCount)
    assert polyCount == len(mesh.polygons), (polyCount, len(mesh.polygons))
    polyPtr = mesh.polygons[0].as_pointer() if polyCount else 0
    core.meshGetPolygons(meshPtr, polyPtr, polyCount)

    loopCount = core.meshGetLoopsCount(meshPtr)
    mesh.loops.add(loopCount)
    assert loopCount == len(mesh.loops), (loopCount, len(mesh.loops))
    loopPtr = mesh.loops[0].as_pointer() if loopCount else 0
    core.meshGetLoops(meshPtr, loopPtr, loopCount)

    mesh.update()

def demo():
    sceneId = core.createScene()
    core.sceneLoadFromJson(sceneId, jsonStr)
    core.sceneSwitchToGraph(sceneId, 'main')
    graphPtr = core.sceneGetCurrentGraph(sceneId)

    inPrimPtr = core.graphCreateInputPrimitive(graphPtr, 'inputPrim')
    meshFromBlender(inPrimPtr, bpy.context.object.data)

    core.graphApply(graphPtr)

    outPrimPtr = core.graphGetOutputPrimitive(graphPtr, 'outputPrim')
    meshToBlender(outPrimPtr, bpy.context.object.data)


def register():
    print('=== register ===')
    demo()


def unregister():
    pass
