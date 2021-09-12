#if 0
#include <zeno/zeno.h>
#include "BlenderMesh.h"
#include <zeno/types/PrimitiveObject.h>
#include <zeno/types/NumericObject.h>

namespace {
using namespace zeno;


struct GetBlenderObjectAxes : INode {
    virtual void apply() override {
        auto object = get_input<BlenderAxis>("object");
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

ZENDEFNODE(GetBlenderObjectAxes, {
    {"object"},
    {{"vec3f", "origin"}, {"vec3f", "axisX"}, {"vec3f", "axisY"}, {"vec3f", "axisZ"}},
    {},
    {"blender"},
});


struct BMeshToPrimitive : INode {
    virtual void apply() override {
        auto mesh = get_input<BlenderMesh>("mesh");
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
    }
};

ZENDEFNODE(BMeshToPrimitive, {
    {"mesh"},
    {"prim"},
    {{"bool", "allow_quads", "0"}, {"bool", "do_transform", "1"}},
    {"blender"},
});


struct PrimitiveToBMesh : INode {
    virtual void apply() override {
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

        set_output("mesh", std::move(mesh));
    }
};

ZENDEFNODE(PrimitiveToBMesh, {
    {"prim"},
    {"mesh"},
    {
    {"bool", "is_smooth", "0"},
    {"bool", "has_vert_color", "0"},
    {"bool", "has_vert_attr", "0"},
    {"bool", "has_face_attr", "0"},
    },
    {"blender"},
});


struct ConvertTo_BlenderMesh_PrimitiveObject : BMeshToPrimitive {
    virtual void apply() override {
        BMeshToPrimitive::apply();
        get_input<PrimitiveObject>("prim")->move_assign(std::move(smart_any_cast<std::shared_ptr<IObject>>(outputs.at("prim"))).get());
    }
};

ZENO_DEFOVERLOADNODE(ConvertTo, _BlenderMesh_PrimitiveObject, typeid(BlenderMesh).name(), typeid(PrimitiveObject).name())({
        {"mesh", "prim"},
        {},
        {},
        {"blender"},
});


struct ConvertTo_PrimitiveObject_BlenderMesh : PrimitiveToBMesh {
    virtual void apply() override {
        PrimitiveToBMesh::apply();
        get_input<BlenderMesh>("mesh")->move_assign(std::move(smart_any_cast<std::shared_ptr<IObject>>(outputs.at("mesh"))).get());
    }
};

ZENO_DEFOVERLOADNODE(ConvertTo, _PrimitiveObject_BlenderMesh, typeid(PrimitiveObject).name(), typeid(BlenderMesh).name())({
        {"prim", "mesh"},
        {},
        {},
        {"blender"},
});


/*
static void decompose_matrix(const Matrix4x4 &m, Vector3f *T,
                                  Quaternion *Rquat, Matrix4x4 *S) {
    // 获取平移T
    T->x = m.m[0][3];
    T->y = m.m[1][3];
    T->z = m.m[2][3];

    // 获取除去平移的新矩阵M
    Matrix4x4 M = m;
    for (int i = 0; i < 3; ++i) M.m[i][3] = M.m[3][i] = 0.f;
    M.m[3][3] = 1.f;

    // 从M分离出R
    Float norm;
    int count = 0;
    Matrix4x4 R = M;
    do {
        // 计算Mi+1
        Matrix4x4 Rnext;
        Matrix4x4 Rit = Inverse(Transpose(R));
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j)
                Rnext.m[i][j] = 0.5f * (R.m[i][j] + Rit.m[i][j]);

        // 计算Mi和Mi+1之间的差
        norm = 0;
        for (int i = 0; i < 3; ++i) {
            Float n = std::abs(R.m[i][0] - Rnext.m[i][0]) +
                      std::abs(R.m[i][1] - Rnext.m[i][1]) +
                      std::abs(R.m[i][2] - Rnext.m[i][2]);
            norm = std::max(norm, n);
        }
        R = Rnext;
    } while (++count < 100 && norm > .0001);//当迭代次数超过上限，或者连续项之间的差足够小，则退出循环
    // 获取旋转矩阵的四元数形式
    *Rquat = Quaternion(R);

    // 计算缩放矩阵S
    *S = Matrix4x4::Mul(Inverse(R), M);
}

struct BAxisExtract : INode {
    virtual void apply() override {
        auto axis = get_input<BlenderAxis>("axis");
        auto translation = std::make_shared<NumericObject>();
        auto quaternion = std::make_shared<NumericObject>();
        auto scaling = std::make_shared<NumericObject>();
        trans->matrix = mesh->matrix;

        set_output("trans", std::move(trans));
    }
};

ZENDEFNODE(BAxisExtract, {
    {"mesh"},
    {"trans"},
    {},
    {"blender"},
});*/


}
#endif
