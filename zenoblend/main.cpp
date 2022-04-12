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

#include <Eigen/Core>
#include <Eigen/Geometry>
#include <Eigen/StdVector>

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
// It seems that, in blender3.1 the armature's bone's quaternion and location switch y-z axis
    m.def("graphSetInputBoneStructure",[] 
        (   uintptr_t graphPtr
        ,   std::string armature_name
        ,   std::vector<std::tuple<
                            int,                                    // parent idx
                            std::string,                            // bone_name_full
                            std::string,                            // custom_shape_idname
                            // std::array<float,3>,                 // the location of head lies in the local matrix
                            std::array<float,4>,                    // loc_quat
                            std::array<float,3>,                    // loc_trans
                            std::array<std::array<float,4>,4>       // local_matrix
                            >> loc_btree
        )-> void
    {
        auto graph = reinterpret_cast<zeno::Graph *>(graphPtr);
        auto &ud = graph->getUserData().get<zeno::BlenderData>("blender_data");

        if(ud.armature2btree.find(armature_name) == ud.armature2btree.end())
            ud.armature2btree.insert(std::make_pair(armature_name,std::vector<zeno::BlenderBone>()));

        auto& global_tree = ud.armature2btree[armature_name];
        global_tree.resize(loc_btree.size());

        // before applying the forward kinematric algorithm,
        // we need to map the local quaterion and translation on local basis into the ones on the global basis.
        // do forward kinematics
        // reference code : https://github.com/libigl/libigl/blob/36e8435a2f724e83e14f79d128102d06b514a4f4/include/igl/forward_kinematics.cpp 
        // the btree vector is ordered using DFS, we can do forward kinematic using dynamic programming directly in a propagating forward fasion

        for(int i = 0;i < global_tree.size();++i){
            const auto& loc_cnode = loc_btree[i];
            auto& global_cnode = global_tree[i];

            const auto& p = std::get<0>(loc_cnode);
            const auto& b_idname = std::get<1>(loc_cnode);
            const auto& geo_idname = std::get<2>(loc_cnode);
            const auto& dQ_ = std::get<3>(loc_cnode);
            const auto& dT_ = std::get<4>(loc_cnode);
            const auto& dM_ = std::get<5>(loc_cnode);

            global_cnode.parent_idx = p;
            if(p >= i){
                throw std::runtime_error("THE INPUT BTREE VECTOR IS NOT A DFS TRANSVERSE");
            }
            global_cnode.bone_idname = b_idname;
            global_cnode.bone_custom_shape_idname = geo_idname;

            // first we need to switch the dQ and dT into global basis
            auto dQ = Eigen::Quaterniond();
            dQ.w() = dQ_[0];
            dQ.x() = dM_[0][0] * dQ_[1] + dM_[0][1] * dQ_[2] + dM_[0][2] * dQ_[3];
            dQ.y() = dM_[1][0] * dQ_[1] + dM_[1][1] * dQ_[2] + dM_[1][2] * dQ_[3];
            dQ.z() = dM_[2][0] * dQ_[1] + dM_[2][1] * dQ_[2] + dM_[2][2] * dQ_[3];
            auto dT = Eigen::Vector3d();
            dT <<   dM_[0][0] * dT_[0] + dM_[0][1] * dT_[1] + dM_[0][2] * dT_[2], \
                    dM_[1][0] * dT_[0] + dM_[1][1] * dT_[1] + dM_[1][2] * dT_[2], \
                    dM_[2][0] * dT_[0] + dM_[2][1] * dT_[1] + dM_[2][2] * dT_[2];

            Eigen::Vector3d r;      // head location in the global basis
            r << dM_[0][3],dM_[1][3],dM_[2][3];

            auto vQ = Eigen::Quaterniond();
            auto vT = Eigen::Vector3d();
            if(global_cnode.parent_idx == -1){          // if the bone is a root bone
                vQ = dQ;
                vT = r - dQ * r + dT;
            }else{
                const auto& global_pnode = global_tree[global_cnode.parent_idx];
                auto vQp = Eigen::Quaterniond();
                vQp.w() = global_pnode.quat[0];
                vQp.x() = global_pnode.quat[1];
                vQp.y() = global_pnode.quat[2];
                vQp.z() = global_pnode.quat[3]; 

                Eigen::Vector3d vTp;
                vTp << global_pnode.b[0],global_pnode.b[1],global_pnode.b[2];
                vQ = vQp * dQ;
                vT = vTp - vQ * r + vQp * (r + dT);
            }

            global_cnode.quat = {vQ.w(),vQ.x(),vQ.y(),vQ.z()};
            global_cnode.b = {vT[0],vT[1],vT[2]};
        }  
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
            , std::array<std::array<float, 4>, 4> matrix_basis
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
            zeno_mesh->matrix_basis = matrix_basis;
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
        // std::cout << "graphGetOutMesh" << std::endl;
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
