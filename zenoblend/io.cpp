#include <zeno/zeno.h>
#include "BlenderMesh.h"
#include <zeno/types/PrimitiveObject.h>
#include <zeno/types/NumericObject.h>
#include <zeno/types/StringObject.h>
#include <zeno/utils/safe_at.h>
#include <zeno/types/ListObject.h>

#include <ctime>

#include <iostream>
#include <spdlog/spdlog.h>

namespace {
using namespace zeno;

std::shared_ptr<zeno::PrimitiveObject> BlenderMeshToPrimitiveObject(
        const BlenderMesh* mesh,
        bool allow_quads,
        bool do_transform,
        bool has_edges,
        bool has_faces,
        bool has_vert_attr){
    auto prim = std::make_shared<zeno::PrimitiveObject>();
    prim->resize(mesh->vert.size());
    auto &pos = prim->add_attr<vec3f>("pos");
    // std::cout << "mesh_size : " << mesh->vert.size() << std::endl;
    if (do_transform) {
        auto m = mesh->matrix;
        #pragma omp parallel for
        for (int i = 0; i < mesh->vert.size(); i++) {
            auto p = mesh->vert[i];
            p = {
                m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2] + m[0][3],
                m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2] + m[1][3],
                m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2] + m[2][3],
            };
            pos[i] = p;
        }
    } else {
        for (int i = 0; i < mesh->vert.size(); i++) {
            pos[i] = mesh->vert[i];
        }
    }

    if (has_edges) {
        for (int i = 0; i < mesh->edge.size(); i++) {
            auto [src, dst] = mesh->edge[i];
            prim->lines.emplace_back(src, dst);
        }
    }

    if (has_faces) {
        for (int i = 0; i < mesh->poly.size(); i++) {
            auto [start, len] = mesh->poly[i];
            if (len < 3) continue;
            if (len == 4 && allow_quads) {
                prim->quads.emplace_back(
                        mesh->loop[start + 0],
                        mesh->loop[start + 1],
                        mesh->loop[start + 2],
                        mesh->loop[start + 3]);
                continue;
            }
            prim->tris.emplace_back(
                    mesh->loop[start + 0],
                    mesh->loop[start + 1],
                    mesh->loop[start + 2]);
            for (int j = 3; j < len; j++) {
                prim->tris.emplace_back(
                        mesh->loop[start + 0],
                        mesh->loop[start + j - 1],
                        mesh->loop[start + j]);
            }
        }
    }

    // input the vert attrs here
    if(has_vert_attr) {
        mesh->vert.foreach_attr([&] (auto const& key,auto const& attr) {
            // std::cout << "INPUT ATTR : " << key << std::endl;

            using T = std::decay_t<decltype(attr[0])>;
            auto &arr = prim->add_attr<T>(key);
            for(size_t i = 0;i < prim->size();++i)
                arr[i] = attr[i];
        });
    }

    return prim;    
}

struct BlenderInputText : INode {
    virtual void apply() override {
        auto text = get_input2<std::string>("text");
        set_output2("value", std::move(text));
    }
};

ZENDEFNODE(BlenderInputText, {
    {},
    {{"string", "value"}},
    {},
    {"blender"},
});

struct BlenderInputAxes : INode {
    virtual void complete() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");
        ud.input_names.insert(objid);
    }

    virtual void apply() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");
        auto object = safe_at(ud.inputs, objid, "blender input")();

        auto m = object->matrix;

        auto origin = std::make_shared<NumericObject>();
        origin->set(vec3f(m[0][3], m[1][3], m[2][3]));

        auto axisX = std::make_shared<NumericObject>();
        axisX->set(vec3f(m[0][0], m[1][0], m[2][0]));

        auto axisY = std::make_shared<NumericObject>();
        axisY->set(vec3f(m[0][1], m[1][1], m[2][1]));

        auto axisZ = std::make_shared<NumericObject>();
        axisZ->set(vec3f(m[0][2], m[1][2], m[2][2]));

        set_output("origin", std::move(origin));
        set_output("axisX", std::move(axisX));
        set_output("axisY", std::move(axisY));
        set_output("axisZ", std::move(axisZ));
    }
};

ZENDEFNODE(BlenderInputAxes, {
    {},
    {{"vec3f", "origin"}, {"vec3f", "axisX"}, {"vec3f", "axisY"}, {"vec3f", "axisZ"}},
    {},
    {"blender"},
});

// input a list of objects in the same collection
struct BlenderInputCollection : INode {
    virtual void complete() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto colid = get_input2<std::string>("colid");
        // the input idname of collection might very likely cooincide with the name of one input object
        // further decorate the collection name with a prefix
        std::string pcolid = "@BC_";
        pcolid.append(colid);
        ud.input_names.insert(pcolid);

    }

    virtual void apply() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto colid = get_input2<std::string>("colid");
        auto primlist = std::make_shared<zeno::ListObject>();
        for(const auto& objName : ud.collections[colid]){
            auto object = safe_at(ud.inputs, objName, "blender collection input")();
            auto mesh = safe_dynamic_cast<BlenderMesh>(object);
            auto prim = BlenderMeshToPrimitiveObject(mesh.get(),
                get_param<bool>("allow_quads"),
                get_param<bool>("do_transform"),
                get_param<bool>("has_edges"),
                get_param<bool>("has_faces"),
                get_param<bool>("has_vert_attr"));

            primlist->arr.push_back(std::move(prim));

        }

        set_output("primlist",std::move(primlist));
    }
};


ZENDEFNODE(BlenderInputCollection, {
    {},
    {"primlist"},
    {
    {"bool", "allow_quads", "0"},
    {"bool", "do_transform", "1"},
    {"bool", "has_edges", "0"},
    {"bool", "has_faces", "1"},
    {"bool", "has_vert_attr","1"}
    },
    {"blender"},
});

// input the name of the armature, and return the binding geo
// the armature is also a kind of blender object, there is no naming conflict among objects
// Currently we only support single bone_geo binding to a specific bone
struct BlenderInputArmature : INode {
    virtual void complete() override {
        auto& ud = graph->getUserData().get<BlenderData>("blender_data");
        auto armid = get_input2<std::string>("armid");
        std::string parmid = "@BA_";
        parmid.append(armid);
        ud.input_names.insert(parmid);
    }

    zeno::vec4f rotation2Quat(const std::array<std::array<float,4>,4>& m){
            auto m00 = m[0][0];
            auto m01 = m[0][1];
            auto m02 = m[0][2];
            auto m10 = m[1][0];
            auto m11 = m[1][1];
            auto m12 = m[1][2];
            auto m20 = m[2][0];
            auto m21 = m[2][1];
            auto m22 = m[2][2];

            auto qd = zeno::vec4f(0);
// https://www.euclideanspace.com/maths/geometry/rotations/conversions/matrixToQuaternion/
// this algorithm can bring in discontinueties
            auto tr = m00 + m11 + m22;
            if(tr > 0) {
                auto s = sqrt(tr + 1) * 2;
                qd[0] =  s / 4;             // w
                qd[1] = (m21 - m12) / s;    // x
                qd[2] = (m02 - m20) / s;    // y
                qd[3] = (m10 - m01) / s;    // z
            } else if((m00 > m11) && (m00 > m22)) {
                auto s = sqrt(1 + m11 - m00 - m22) * 2;
                qd[0] = (m21 - m12) / s;
                qd[1] = s / 4;
                qd[2] = (m01 + m10) / s;
                qd[3] = (m02 + m20) / s;
            } else if(m11 > m22) {
                auto s = sqrt(1.0 + m11 - m00 - m22) * 2;
                qd[0] = (m02 - m20) / s;
                qd[1] = (m01 + m10) / s;
                qd[2] = s / 4;
                qd[3] = (m12 + m21) / s;
            } else{
                auto s = sqrt(1 + m22 - m00 - m11) * 2;
                qd[0] = (m10 - m01) / s;
                qd[1] = (m02 + m20) / s;
                qd[2] = (m12 + m21) / s;
                qd[3] = s / 4;
            }

            return qd;
    }

// Output the 
// the Qs and Ts should be computed using forward kinematic
// Deriv Qs and Ts from Affine Transformation matrices can bring in discontinueties
    virtual void apply() override {
        // std::cout << "BlenderInputArmature Get Called" << std::endl;

        auto start = clock();

        auto& ud = graph->getUserData().get<BlenderData>("blender_data");
        auto armid = get_input2<std::string>("armid");
        auto output_geos = get_param<bool>("output_geos");
        auto allow_quads = get_param<bool>("allow_quads");

        const auto& bones = ud.armature2bones[armid];

        auto Qs = std::make_shared<zeno::ListObject>();
        auto Ts = std::make_shared<zeno::ListObject>();
        auto As = std::make_shared<zeno::ListObject>();
        auto Geos = std::make_shared<zeno::ListObject>();

        // forward kinematic here
        

        for(const auto& bone : bones){
            const auto bone_data = safe_at(ud.inputs, bone, "blender input")();

            auto m = bone_data->matrix;
            auto A = std::make_shared<std::array<std::array<float,4>,4>>();
            *A = m;

            auto q = std::make_shared<zeno::NumericObject>();
            auto b = std::make_shared<zeno::NumericObject>();

            auto qd = rotation2Quat(m);

            q->set(zeno::vec4f(qd[1],qd[2],qd[3],qd[0]));
            b->set(zeno::vec3f(m[0][3], m[1][3], m[2][3]));

            Qs->arr.push_back(q);
            Ts->arr.push_back(b);
            As->arr.push_back(A);


        }

        if(output_geos){
            for(const auto& bone : bones){
                for(const auto& geo_name : ud.bone2geos[bone]){
                    if(ud.inputs.find(geo_name) == ud.inputs.end())
                        throw std::runtime_error("NO SPECIFIED GEO DETECTED IN INPUTS");

                    // std::cout << "OUTPUT GEO NAME : " << geo_name << std::endl;
                    auto object = safe_at(ud.inputs, geo_name, "blender collection input")();
                    auto mesh = safe_dynamic_cast<BlenderMesh>(object);
                    // std::cout << geo_name << "'s matrix : " << std::endl;
                    // for(size_t i = 0;i < 4;++i){
                    //     for(size_t j = 0;j < 4;++j)
                    //         std::cout << mesh->matrix[i][j] << "\t";
                    //     std::cout << std::endl;
                    // } 

                    bool do_transform = get_param<bool>("do_transform");
                    bool allow_quads = get_param<bool>("allow_quads");
                    auto prim = BlenderMeshToPrimitiveObject(mesh.get(),
                        allow_quads,
                        do_transform,
                        true,
                        true,
                        true);  

                    // std::cout << "OUT_BONE_GEO : " << geo_name << std::endl;
                    Geos->arr.push_back(std::move(prim));                  
                }
            }
        }



        // std::cout << "Finish BlenderInputArmature" << std::endl;

        auto end = clock();
        fmt::print("{}-{}", 1, 1.0);
        std::cout << "TIME_ELAPSE : " << ((float)(end - start)) / CLOCKS_PER_SEC << std::endl;

        set_output("Ts",std::move(Ts));
        set_output("Qs",std::move(Qs));
        set_output("As",std::move(As));
        set_output("geos",std::move(Geos));
    }
};
ZENDEFNODE(BlenderInputArmature, {
    {"armid"},
    {"Ts","Qs","As","geos"},
    {
        {"bool", "output_geos","1"},
        {"bool", "allow_quads", "1"}, // only work for the outputFeos tag is turned on 
        {"bool", "do_transform", "1"},
    // {"bool", "has_faces", "1"},should have faces
    },
    {"blender"},
});


struct BlenderInputPrimitive : INode {
    virtual void complete() override {
        // Push the input name into the graph input list before the graph is activated
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");
        ud.input_names.insert(objid);
    }

    virtual void apply() override {
        // std::cout << "BlenderInputPrimitive Apply" << std::endl;
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");

        for(const auto& key : ud.input_names){
            std::cout << "NAME : " << key << std::endl;
        }
        std::cout << "FINISH OUTPUT INPUTS" << std::endl;
        auto object = safe_at(ud.inputs, objid, "blender input")();
        // std::cout << "PASS HERE" << std::endl;

        auto mesh = safe_dynamic_cast<BlenderMesh>(object);
        auto prim = BlenderMeshToPrimitiveObject(mesh.get(),
            get_param<bool>("allow_quads"),
            get_param<bool>("do_transform"),
            get_param<bool>("has_edges"),
            get_param<bool>("has_faces"),
            get_param<bool>("has_vert_attr"));

        set_output("prim", std::move(prim));
        set_output2("object", std::move(object));
    }
};

ZENDEFNODE(BlenderInputPrimitive, {
    {},
    {"prim"},
    {
    {"bool", "allow_quads", "0"},
    {"bool", "do_transform", "1"},
    {"bool", "has_edges", "0"},
    {"bool", "has_faces", "1"},
    {"bool", "has_vert_attr","1"}
    },
    {"blender"},
});


struct BlenderOutputPrimitive : INode {
    virtual void complete() override {
        if (get_param<bool>("active")) {
            graph->finalOutputNodes.insert(myname);
        }
    }

    virtual void apply() override {
        // std::cout << "BlenderOutputPrimitive" << std::endl;

        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");

        auto prim = get_input<PrimitiveObject>("prim");
        auto mesh = std::make_shared<BlenderMesh>();
        // todo: support exporting transform matrix (for empty axis) too?

        mesh->vert.resize(prim->size());
        auto &pos = prim->attr<vec3f>("pos");
        for (int i = 0; i < prim->size(); i++) {
            mesh->vert[i] = pos[i];
        }
        if (get_param<bool>("has_vert_attr")) {
            prim->verts.foreach_attr([&] (auto const &key, auto const &attr) {
                std::cout << "PRIM_ATTR : " << key << std::endl;
                mesh->vert.attrs[key] = attr;  // deep copy
            });
            // if(prim->attrs.find())
        }

        mesh->is_smooth = get_param<bool>("is_smooth");
        mesh->use_auto_smooth = get_param<bool>("use_auto_smooth");

        if (get_param<bool>("has_faces")) {
            mesh->poly.resize(prim->tris.size() + prim->quads.size());
            mesh->loop.resize(3 * prim->tris.size() + 4 * prim->quads.size());
            #pragma omp parallel for
            for (int i = 0; i < prim->tris.size(); i++) {
                auto e = prim->tris[i];
                mesh->loop[i*3 + 0] = e[0];
                mesh->loop[i*3 + 1] = e[1];
                mesh->loop[i*3 + 2] = e[2];
                mesh->poly[i] = {i*3, 3};
            }
            if (get_param<bool>("has_face_attr")) {
                prim->tris.foreach_attr([&] (auto const &key, auto const &attr) {
                    using T = std::decay_t<decltype(attr[0])>;
                    auto &arr = mesh->poly.add_attr<T>(key);
                    for (int i = 0; i < prim->tris.size(); i++) {
                        arr[i] = attr[i];
                    }
                });
            }

            int base_loop = prim->tris.size() * 3;
            int base_poly = prim->tris.size();
            #pragma omp parallel for
            for (int i = 0; i < prim->quads.size(); i++) {
                auto e = prim->quads[i];
                mesh->loop[base_loop + i*4 + 0] = e[0];
                mesh->loop[base_loop + i*4 + 1] = e[1];
                mesh->loop[base_loop + i*4 + 2] = e[2];
                mesh->loop[base_loop + i*4 + 3] = e[3];
                mesh->poly[base_poly + i] = {base_loop + i*4, 4};
            }
            if (get_param<bool>("has_face_attr")) {
                prim->quads.foreach_attr([&] (auto const &key, auto const &attr) {
                    using T = std::decay_t<decltype(attr[0])>;
                    auto &arr = mesh->poly.add_attr<T>(key);
                    for (int i = 0; i < prim->tris.size(); i++) {
                        arr[base_poly + i] = attr[i];
                    }
                });
            }
        }

        if (get_param<bool>("has_vert_color")) {
            prim->verts.foreach_attr([&] (auto const &key, auto const &attr) {
                using T = std::decay_t<decltype(attr[0])>;
                auto &arr = mesh->loop.add_attr<T>(key);
                #pragma omp parallel for
                for (int i = 0; i < mesh->loop.size(); i++) {
                    arr[i] = attr[mesh->loop[i]];
                }
            });
        }

        if (get_param<bool>("has_edges")) {
            mesh->edge.resize(prim->lines.size());
            #pragma omp parallel for
            for (int i = 0; i < prim->lines.size(); i++) {
                auto e = prim->lines[i];
                mesh->edge[i] = {e[0], e[1]};
            }
        }

        ud.outputs[objid] = std::move(mesh);
    }
};

ZENDEFNODE(BlenderOutputPrimitive, {
    {"prim"},
    {"mesh"},
    {
    {"bool", "is_smooth", "0"},
    {"bool", "use_auto_smooth", "0"},
    {"bool", "has_vert_color", "0"},
    {"bool", "has_vert_attr", "1"},
    {"bool", "has_face_attr", "0"},
    {"bool", "has_edges", "0"},
    {"bool", "has_faces", "1"},
    {"bool", "active", "1"},
    },
    {"blender"},
});

}
