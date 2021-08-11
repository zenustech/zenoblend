#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;

#include <blender/DNA_mesh_types.h>
#include <blender/DNA_meshdata_types.h>

#include <zeno/zeno.h>
#include <zeno/types/PrimitiveObject.h>

static std::map<int, std::unique_ptr<zeno::Scene>> scenes;

PYBIND11_MODULE(zenoblend_pybind11_module, m) {

    m.def("createScene", []
            (
            ) -> int
    {
        static int topid = 0;
        auto id = topid++;
        scenes[id] = zeno::createScene();
        return id;
    });

    m.def("sceneGetCurrentGraph", []
            ( int sceneId
            ) -> uintptr_t
    {
        auto const &scene = scenes.at(sceneId);
        zeno::Graph *graph = &scene->getGraph();
        return reinterpret_cast<uintptr_t>(graph);
    });

    m.def("sceneLoadCommandList", []
            ( int sceneId
            , const char *jsonStr
            ) -> void
    {
        auto const &scene = scenes.at(sceneId);
        scene->loadScene(jsonStr);
    });

    m.def("graphCreateInputPrimitive", []
            ( uintptr_t graphPtr
            , std::string const &inputName
            ) -> uintptr_t
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto prim = std::make_shared<zeno::PrimitiveObject>();
        auto primPtr = reinterpret_cast<uintptr_t>(prim.get());
        graph->setGraphInput(inputName, std::move(prim));
        return primPtr;
    });

    m.def("graphApply", []
            ( uintptr_t graphPtr
            ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        graph->applyGraph();
    });

    m.def("graphGetOutputPrimitive", []
            ( uintptr_t graphPtr
            , std::string const &outputName
            ) -> uintptr_t
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto prim = graph->getGraphOutput(outputName);
        auto primPtr = reinterpret_cast<uintptr_t>(prim.get());
        return primPtr;
    });

    m.def("primitiveSetVertices", []
            ( uintptr_t primPtr
            , uintptr_t vertPtr
            , size_t vertCount
            ) -> void
    {
        auto prim = reinterpret_cast<zeno::PrimitiveObject *>(primPtr);
        prim->resize(vertCount);
        auto vert = reinterpret_cast<MVert const *>(vertPtr);
        auto &pos = prim->add_attr<zeno::vec3f>("pos");
        for (int i = 0; i < vertCount; i++) {
            pos[i] = {vert[i].co[0], vert[i].co[1], vert[i].co[2]};
        }
    });

    m.def("primitiveGetVerticesCount", []
            ( uintptr_t primPtr
            ) -> size_t
    {
        auto prim = reinterpret_cast<zeno::PrimitiveObject *>(primPtr);
        return prim->size();
    });

    m.def("primitiveGetVertices", []
            ( uintptr_t primPtr
            , uintptr_t vertPtr
            , size_t vertCount
            ) -> void
    {
        auto prim = reinterpret_cast<zeno::PrimitiveObject *>(primPtr);
        auto vert = reinterpret_cast<MVert const *>(vertPtr);
        auto &pos = prim->add_attr<zeno::vec3f>("pos");
        for (int i = 0; i < vertCount; i++) {
            pos[i] = {vert[i].co[0], vert[i].co[1], vert[i].co[2]};
        }
    });

}
