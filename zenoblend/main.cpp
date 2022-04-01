#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>
namespace py = pybind11;

#include <blender/makesdna/DNA_mesh_types.h>
#include <blender/makesdna/DNA_meshdata_types.h>
#include <blender/makesdna/DNA_customdata_types.h>
#include <blender/blenlib/BLI_float3.hh>

#include <zeno/zeno.h>
#include "BlenderMesh.h"

PYBIND11_MAKE_OPAQUE(std::vector<float>);
PYBIND11_MAKE_OPAQUE(std::vector<std::vector<float>>);

static std::map<int, std::unique_ptr<zeno::Scene>> scenes;

void updateKey2SetMap(std::map<std::string, std::set<std::string>>& smap,
    const std::string& key,const std::string& elm) {
        if(smap.find(key) == smap.end())
            smap.insert(std::make_pair(key,std::set<std::string>()));
        smap[key].insert(elm);
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
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        return ud.input_names;
    });

    m.def("graphGetOutputNames", []
            ( uintptr_t graphPtr
            ) -> std::set<std::string>
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        std::set<std::string> keys;
        for (auto const &[key, val]: ud.outputs) {
            keys.insert(key);
        }
        return keys;
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
            , std::string objName
            , std::array<std::array<float, 4>, 4> matrix
            ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");

        ud.inputs[objName] = [=] () -> std::shared_ptr<zeno::BlenderAxis> {
            auto axis = std::make_shared<zeno::BlenderAxis>();
            axis->matrix = matrix;
            return axis;
        };
    });

    m.def("graphSetInputBoneStructure",[] 
        (   uintptr_t graphPtr
        ,   std::string ArmatureName
        ,   std::vector<std::pair<std::string,int>> parent_pairs
        )   -> void
        {

        }
    
    );

    m.def("graphSetInputBone",[] 
            (   uintptr_t graphPtr
            ,   std::string boneName
            ,   std::array<std::array<float, 4>, 4> matrix
            ,   std::array<float,4> loc_quat
            ,   std::array<float,3> loc_trans
            ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");

        ud.inputs[boneName] = [=] () -> std::shared_ptr<zeno::BlenderAxis> {
            auto bone = std::make_shared<zeno::BlenderBone>();
            bone->matrix = matrix;
            bone->loc_quat = loc_quat;
            bone->loc_b = loc_trans;
            return bone;
        };
    });

    m.def("graphSetInputMesh", []
            ( uintptr_t graphPtr
            , std::string objName
            , std::array<std::array<float, 4>, 4> matrix
            , uintptr_t vertPtr
            , size_t vertCount
            , uintptr_t loopPtr
            , size_t loopCount
            , uintptr_t polyPtr
            , size_t polyCount
            , uintptr_t edgePtr
            , size_t edgeCount
            ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");

        ud.inputs[objName] = [=] () -> std::shared_ptr<zeno::BlenderAxis> {
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
            mesh->edge.resize(edgeCount);
            auto edge = reinterpret_cast<MEdge const *>(edgePtr);
            for (int i = 0; i < edgeCount; i++) {
                mesh->edge[i] = {edge[i].v1, edge[i].v2};
            }
            return mesh;
        };
    });

    m.def("graphUpdateCollectionDict",[]
            ( uintptr_t graphPtr
            , std::string collection_name
            , std::string objName
            ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        if(ud.inputs.find(objName) == ud.inputs.end())
            throw std::runtime_error("INVALID OBJNAME UPDATE COLLECTION DICT");
        updateKey2SetMap(ud.collections,collection_name,objName);
    });

    m.def("graphUpdateArmature2BonesDict",[]
            ( uintptr_t graphPtr
            , std::string armature_name
            , std::string bone_name
            )
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto& ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        // std::cout << "Update Armature: " << armature_name << "\t" << bone_name << std::endl;
        updateKey2SetMap(ud.armature2bones,armature_name,bone_name);
    });

    m.def("graphUpdateBone2GeosDict",[]
            ( uintptr_t graphPtr
            , std::string bone_name
            , std::string geo_name
            )
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto& ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        if(ud.inputs.find(geo_name) == ud.inputs.end())
            throw std::runtime_error("INVALID OBJNAME UPDATE Bone2Geos DICT");
        // std::cout << "Update Bone Key : " << bone_name << "\t" << geo_name << std::endl;
        updateKey2SetMap(ud.bone2geos,bone_name,geo_name);
        
    });


    m.def("graphSetInputMesh2",[]
            ( uintptr_t graphPtr
            , std::string objName
            , std::array<std::array<float, 4>, 4> matrix
            , uintptr_t meshPtr
            ) ->void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");

        ud.inputs[objName] = [=] () -> std::shared_ptr<zeno::BlenderAxis> {
            auto zeno_mesh = std::make_shared<zeno::BlenderMesh>();
            auto blender_mesh = reinterpret_cast<Mesh const *>(meshPtr);
            auto vdata = blender_mesh->vdata;

            zeno_mesh->matrix = matrix;
            zeno_mesh->vert.resize(blender_mesh->totvert);

            for(size_t idx = 0;idx < vdata.totlayer;++idx){
                auto layer = vdata.layers[idx];
                int type = layer.type;                  // seem to be deprecated
                int offset = layer.offset;
                int uid = layer.uid;
                auto name = layer.name;
                auto active = layer.active;

                if(type == CustomDataType::CD_MVERT)
                    continue;
                if(type == CustomDataType::CD_PROP_FLOAT){
                    auto& attr = zeno_mesh->vert.add_attr<float>(name);
                    for(size_t i = 0;i < blender_mesh->totvert;++i)
                        attr[i] = ((float*)layer.data)[i];
                }else if(type == CustomDataType::CD_PROP_FLOAT3){
                    auto& attr = zeno_mesh->vert.add_attr<zeno::vec3f>(name);
                    for(size_t i = 0;i < blender_mesh->totvert;++i){
                        const auto& data = ((blender::float3*)layer.data)[i];
                        attr[i] = zeno::vec3f(data.x,data.y,data.z);
                    }
                }
            }

            auto blender_vert = blender_mesh->mvert;
            for (int i = 0; i < blender_mesh->totvert; i++) {
                zeno_mesh->vert[i] = {blender_vert[i].co[0], blender_vert[i].co[1], blender_vert[i].co[2]};
            }

            zeno_mesh->loop.resize(blender_mesh->totloop);
            auto blender_loop = blender_mesh->mloop;
            for (int i = 0; i < blender_mesh->totloop; i++) {
                zeno_mesh->loop[i] = blender_loop[i].v;
            }

            zeno_mesh->poly.resize(blender_mesh->totpoly);
            auto blender_poly = blender_mesh->mpoly;
            for (int i = 0; i < blender_mesh->totpoly; i++) {
                zeno_mesh->poly[i] = {blender_poly[i].loopstart, blender_poly[i].totloop};
            }

            zeno_mesh->edge.resize(blender_mesh->totedge);
            auto blender_edge = blender_mesh->medge;
            for (int i = 0; i < blender_mesh->totedge; i++) {
                zeno_mesh->edge[i] = {blender_edge[i].v1, blender_edge[i].v2};
            }

            return zeno_mesh;
        };
    });

    // todo: support input/output volume too
    m.def("graphGetOutputMesh", []
            ( uintptr_t graphPtr
            , std::string const &objName
            ) -> uintptr_t
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");

        auto const &mesh = ud.outputs.at(objName);
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

    m.def("meshGetVertAttrNameType", []
        ( uintptr_t meshPtr
        ) -> std::map<std::string, size_t>
    {
        std::map<std::string, size_t> attrNameType;
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        for (auto const& [key, value] : mesh->vert.attrs) {
            attrNameType.emplace(key, value.index());
        }
        return attrNameType;
    });

    m.def("meshGetVertAttr", []
        ( uintptr_t meshPtr
        , std::string attrName
        , uintptr_t vertAttrPtr
        , size_t vertCount
        ) -> void
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        
        for (int i = 0; i < vertCount; i++) {
            auto attr = mesh->vert.attrs.at(attrName);
            size_t attrIndex = attr.index();
            if (attrIndex == 0) {
                auto vertAttr = reinterpret_cast<blender::float3 *>(vertAttrPtr);
                auto attrFloat3 = std::get<0>(attr)[i];
                vertAttr[i].x = attrFloat3[0];
                vertAttr[i].y = attrFloat3[1];
                vertAttr[i].z = attrFloat3[2];
            } else if (attrIndex == 1) {
                auto vertAttr = reinterpret_cast<MFloatProperty *>(vertAttrPtr);
                vertAttr[i].f = std::get<1>(attr)[i];
            }
        }
    });

    m.def("meshGetPolyAttrNameType", []
        ( uintptr_t meshPtr
        ) -> std::map<std::string, size_t>
    {
        std::map<std::string, size_t> attrNameType;
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        for (auto const& [key, value] : mesh->poly.attrs) {
            attrNameType.emplace(key, value.index());
        }
        return attrNameType;
    });

    m.def("meshGetPolyAttr", []
        ( uintptr_t meshPtr
        , std::string attrName
        , uintptr_t polyAttrPtr
        , size_t polyCount
        ) -> void
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        
        for (int i = 0; i < polyCount; i++) {
            auto attr = mesh->poly.attrs.at(attrName);
            size_t attrIndex = attr.index();
            if (attrIndex == 0) {
                auto polyAttr = reinterpret_cast<blender::float3 *>(polyAttrPtr);
                auto attrFloat3 = std::get<0>(attr)[i];
                polyAttr[i].x = attrFloat3[0];
                polyAttr[i].y = attrFloat3[1];
                polyAttr[i].z = attrFloat3[2];
            } else if (attrIndex == 1) {
                auto polyAttr = reinterpret_cast<MFloatProperty *>(polyAttrPtr);
                polyAttr[i].f = std::get<1>(attr)[i];
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
            poly[i].loopstart = mesh->poly[i].start;
            poly[i].totloop = mesh->poly[i].len;
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

    m.def("meshGetEdgesCount", []
        ( uintptr_t meshPtr
        ) -> size_t
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        return mesh->edge.size();
    });

    m.def("meshGetEdges", []
            ( uintptr_t meshPtr
            , uintptr_t edgePtr
            , size_t edgeCount
            ) -> void
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        auto edge = reinterpret_cast<MEdge *>(edgePtr);
        for (int i = 0; i < edgeCount; i++) {
            edge[i].v1 = mesh->edge[i].src;
            edge[i].v2 = mesh->edge[i].dst;
        }
    });


    m.def("meshGetLoopAttrNameType", []
        ( uintptr_t meshPtr
        ) -> std::map<std::string, size_t>
    {
        std::map<std::string, size_t> attrNameType;
        auto mesh = reinterpret_cast<zeno::BlenderMesh *>(meshPtr);
        for (auto const& [key, value] : mesh->loop.attrs) {
            attrNameType.emplace(key, value.index());
        }
        return attrNameType;
    });

    m.def("meshGetLoopColor", []
        ( uintptr_t meshPtr
        , std::string const &attrName
        , uintptr_t loopColorPtr
        , size_t loopCount
        ) -> void
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh*>(meshPtr);

        auto const &attr = mesh->loop.attrs.at(attrName);
        auto attrIndex = attr.index();
        auto loopColor = reinterpret_cast<MLoopCol *>(loopColorPtr);
        const double gamma = 1.0 / 2.2;
        if (attrIndex == 0) {
            #pragma omp parallel for
            for (int i = 0; i < loopCount; i++) {
                auto color = std::get<0>(attr)[i];
                loopColor[i].r = static_cast<unsigned char>(zeno::clamp(zeno::pow(color[0], gamma) * 255.0, 0.0, 255.0));
                loopColor[i].g = static_cast<unsigned char>(zeno::clamp(zeno::pow(color[1], gamma) * 255.0, 0.0, 255.0));
                loopColor[i].b = static_cast<unsigned char>(zeno::clamp(zeno::pow(color[2], gamma) * 255.0, 0.0, 255.0));
                loopColor[i].a = 255; // todo: support vec4f attributes in future
            }
        } else if (attrIndex == 1) {
            #pragma omp parallel for
            for (int i = 0; i < loopCount; i++) {
                auto color = std::get<1>(attr)[i];
                auto graylevel = static_cast<unsigned char>(zeno::clamp(zeno::pow(color, gamma) * 255.0, 0.0, 255.0));
                loopColor[i].r = graylevel;
                loopColor[i].g = graylevel;
                loopColor[i].b = graylevel;
                loopColor[i].a = 255;
            }
        }
    });

    m.def("meshGetUseAutoSmooth", []
        ( uintptr_t meshPtr
        ) -> bool
    {
        auto mesh = reinterpret_cast<zeno::BlenderMesh*>(meshPtr);
        return mesh->use_auto_smooth;
    });

    py::bind_vector<std::vector<float>>(m, "FloatVec3");
    py::bind_vector<std::vector<std::vector<float>>>(m, "FloatVec3Array");
    py::bind_vector<std::vector<int>>(m, "IntVec2");
    py::bind_vector<std::vector<std::vector<int>>>(m, "IntVec2Array");

    m.def("graphGetDrawLineVertexBuffer", []
        (uintptr_t graphPtr
        ) -> std::vector<std::vector<float>>
    {
        auto graph = reinterpret_cast<zeno::Graph*>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        return ud.line_vertices;
    });

    m.def("graphGetDrawLineColorBuffer", []
        (uintptr_t graphPtr
        ) -> std::vector<std::vector<float>>
    {
        auto graph = reinterpret_cast<zeno::Graph*>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        return ud.line_colors;
    });

    m.def("graphGetDrawLineIndexBuffer", []
        (uintptr_t graphPtr
        ) -> std::vector<std::vector<int>>
    {
        auto graph = reinterpret_cast<zeno::Graph*>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        return ud.line_indices;
    });

    m.def("graphClearDrawBuffer", []
        (uintptr_t graphPtr
        ) -> void
    {
        auto graph = reinterpret_cast<zeno::Graph*>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");
        ud.line_vertices.clear();
        ud.line_colors.clear();
        ud.line_indices.clear();
    });

    py::register_exception_translator([](std::exception_ptr p) {
        try {
            //printf("[pybind11 exception translator called]\n");
            if (p)
                std::rethrow_exception(p);
        } catch (zeno::BaseException const &e) {
            PyErr_SetString(PyExc_RuntimeError, e.what());
        }
    });
}
