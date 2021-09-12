#include <zeno/zeno.h>
#include "BlenderMesh.h"
#include <zeno/types/PrimitiveObject.h>
#include <zeno/types/NumericObject.h>
#include <zeno/types/StringObject.h>
#include <zeno/utils/safe_at.h>

namespace {
using namespace zeno;



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


struct BlenderInputPrimitive : INode {
    virtual void complete() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");
        ud.input_names.insert(objid);
    }

    virtual void apply() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");
        auto object = safe_at(ud.inputs, objid, "blender input")();

        auto mesh = safe_dynamic_cast<BlenderMesh>(object);
        auto prim = std::make_shared<PrimitiveObject>();
        auto allow_quads = get_param<bool>("allow_quads");
        auto do_transform = get_param<bool>("do_transform");

        // todo: support **input** blender attributes
        prim->resize(mesh->vert.size());
        auto &pos = prim->add_attr<vec3f>("pos");
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
        set_output("prim", std::move(prim));
        set_output2("object", std::move(object));
    }
};

ZENDEFNODE(BlenderInputPrimitive, {
    {},
    {"prim"},
    {},
    {"blender"},
});


struct BlenderOutputPrimitive : INode {
    virtual void complete() override {
        if (get_param<bool>("active")) {
            graph->finalOutputNodes.insert(myname);
        }
    }

    virtual void apply() override {
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
                mesh->vert.attrs[key] = attr;  // deep copy
            });
        }

        mesh->is_smooth = get_param<bool>("is_smooth");
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

        ud.outputs[objid] = std::move(mesh);
    }
};

ZENDEFNODE(BlenderOutputPrimitive, {
    {"prim"},
    {"mesh"},
    {
    {"bool", "is_smooth", "0"},
    {"bool", "has_vert_color", "0"},
    {"bool", "has_vert_attr", "0"},
    {"bool", "has_face_attr", "0"},
    {"bool", "active", "1"},
    },
    {"blender"},
});

}
