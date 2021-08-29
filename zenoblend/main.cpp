#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>
namespace py = pybind11;

#include <blender/DNA_mesh_types.h>
#include <blender/DNA_meshdata_types.h>

#include <zeno/zeno.h>
#include <zeno/types/BlenderMesh.h>

PYBIND11_MAKE_OPAQUE(std::map<std::string, size_t>);

static std::map<int, std::unique_ptr<zeno::Scene>> scenes;

namespace Blender {  // blender-master/source/blender/blenlib/BLI_float3.hh
    struct float3 {
        float x, y, z;
    };
}

PYBIND11_MODULE(pylib_zenoblend, m) {

    m.def("dumpDescriptors", []
            (
            ) -> std::string
    {
        return zeno::dumpDescriptors();
    });

    m.def("createScene", []
            (
            ) -> int
    {
        static int topid = 0;
        auto id = topid++;
        scenes[id] = zeno::createScene();
        return id;
    });

    m.def("deleteScene", []
            ( int sceneId
            ) -> void
    {
        scenes.erase(sceneId);
    });

    m.def("sceneSwitchToGraph", []
            ( int sceneId
            , std::string const &graphName
            ) -> void
    {
        auto const &scene = scenes.at(sceneId);
        scene->switchGraph(graphName);
    });

    m.def("sceneGetCurrentGraph", []
            ( int sceneId
            ) -> uintptr_t
    {
        auto const &scene = scenes.at(sceneId);
        zeno::Graph *graph = &scene->getGraph();
        return reinterpret_cast<uintptr_t>(graph);
    });

    m.def("sceneLoadFromJson", []
            ( int sceneId
            , const char *jsonStr
            ) -> void
    {
        auto const &scene = scenes.at(sceneId);
        scene->loadScene(jsonStr);
    });

    m.def("graphGetInputNames", []
            ( uintptr_t graphPtr
            ) -> std::set<std::string>
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        return graph->getGraphInputNames();
    });

    m.def("graphGetOutputNames", []
            ( uintptr_t graphPtr
            ) -> std::set<std::string>
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        return graph->getGraphOutputNames();
    });

    m.def("graphApply", []
            ( uintptr_t graphPtr
            ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        graph->applyGraph();
    });

    m.def("graphSetInputAxis", []
            ( uintptr_t graphPtr
            , std::string endpName
            , std::array<std::array<float, 4>, 4> matrix
            ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        graph->setGraphInputPromise(endpName, [=] () -> zeno::zany {
            auto axis = std::make_shared<zeno::BlenderAxis>();
            axis->matrix = matrix;
            return axis;
        });
    });

    m.def("graphSetInputMesh", []
            ( uintptr_t graphPtr
            , std::string endpName
            , std::array<std::array<float, 4>, 4> matrix
            , uintptr_t vertPtr
            , size_t vertCount
            , uintptr_t loopPtr
            , size_t loopCount
            , uintptr_t polyPtr
            , size_t polyCount
            ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        graph->setGraphInputPromise(endpName, [=] () -> zeno::zany {
            auto mesh = std::make_shared<zeno::BlenderMesh>();
            mesh->matrix = matrix;
            mesh->vert.resize(vertCount);
            auto vert = reinterpret_cast<MVert const *>(vertPtr);
            for (int i = 0; i < vertCount; i++) {
                mesh->vert[i] = {vert[i].co[0], vert[i].co[1], vert[i].co[2]};
            }
            mesh->loop.resize(loopCount);
            auto loop = reinterpret_cast<MLoop const *>(loopPtr);
            for (int i = 0; i < loopCount; i++) {
                mesh->loop[i] = loop[i].v;
            }
            mesh->poly.resize(polyCount);
            auto poly = reinterpret_cast<MPoly const *>(polyPtr);
            for (int i = 0; i < polyCount; i++) {
                mesh->poly[i] = {poly[i].loopstart, poly[i].totloop};
            }
            return mesh;
        });
    });
    // todo: support input/output volume too

    m.def("graphGetOutputMesh", []
            ( uintptr_t graphPtr
            , std::string const &endpName
            ) -> uintptr_t
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto meshAny = graph->getGraphOutput2(endpName);
        auto mesh = zeno::smart_any_cast<std::shared_ptr<zeno::BlenderMesh>>(meshAny);
        auto meshPtr = reinterpret_cast<uintptr_t>(mesh.get());
        return meshPtr;
    });

    m.def("meshGetMatrix", []
            ( uintptr_t meshPtr
            ) -> std::array<std::array<float, 4>, 4>
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        return mesh->matrix;
    });

    m.def("meshGetVerticesCount", []
            ( uintptr_t meshPtr
            ) -> size_t
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        return mesh->vert.size();
    });

    m.def("meshGetVertices", []
            ( uintptr_t meshPtr
            , uintptr_t vertPtr
            , size_t vertCount
            ) -> void
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        auto vert = reinterpret_cast<MVert *>(vertPtr);
        for (int i = 0; i < vertCount; i++) {
            vert[i].co[0] = mesh->vert[i][0];
            vert[i].co[1] = mesh->vert[i][1];
            vert[i].co[2] = mesh->vert[i][2];
        }
    });

    py::bind_map<std::map<std::string, size_t>>(m, "MapAttrNameType");

    m.def("getAttrNameType", []
    (uintptr_t meshPtr) -> std::map<std::string, size_t>
    {
        std::map<std::string, size_t> attrNameType;
        auto mesh = reinterpret_cast<zeno::BlenderMesh*>(meshPtr);
        for (auto const& [key, value] : mesh->attrs) {
            if (key != "pos") {
                attrNameType.emplace(key, value.index());
            }
        }
        return attrNameType;
    });

    m.def("meshGetVertAttr", []
        (uintptr_t meshPtr
        , std::string attrName
        , uintptr_t vertAttrPtr
        , size_t vertCount
        ) -> void
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh*>(meshPtr);
        
        for (int i = 0; i < vertCount; i++) {
            auto attr = mesh->attrs.at(attrName);
            size_t attrIndex = attr.index();
            if (attrIndex == 0) {
                auto vertAttr = reinterpret_cast<Blender::float3*>(vertAttrPtr);
                auto attrFloat3 = std::get<0>(attr)[i];
                vertAttr[i].x = attrFloat3[0];
                vertAttr[i].y = attrFloat3[1];
                vertAttr[i].z = attrFloat3[2];
            }
            else if (attrIndex == 1) {
                auto vertAttr = reinterpret_cast<MFloatProperty*>(vertAttrPtr);
                vertAttr[i].f = std::get<1>(attr)[i];
            }
        }
    });

    m.def("meshGetPolygonsCount", []
            ( uintptr_t meshPtr
            ) -> size_t
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        return mesh->poly.size();
    });

    m.def("meshGetPolygons", []
            ( uintptr_t meshPtr
            , uintptr_t polyPtr
            , size_t polyCount
            ) -> void
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        auto poly = reinterpret_cast<MPoly *>(polyPtr);
        for (int i = 0; i < polyCount; i++) {
            std::tie(poly[i].loopstart, poly[i].totloop) = mesh->poly[i];
            if (mesh->is_smooth)
                poly[i].flag |= ME_SMOOTH;
        }
    });

    m.def("meshGetLoopsCount", []
            ( uintptr_t meshPtr
            ) -> size_t
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        return mesh->loop.size();
    });

    m.def("meshGetLoops", []
            ( uintptr_t meshPtr
            , uintptr_t loopPtr
            , size_t loopCount
            ) -> void
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        auto loop = reinterpret_cast<MLoop *>(loopPtr);
        for (int i = 0; i < loopCount; i++) {
            loop[i].v = mesh->loop[i];
            loop[i].e = 0;
        }
    });

}
