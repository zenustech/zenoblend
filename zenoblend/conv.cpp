#include <zeno/zeno.h>
#include "BlenderMesh.h"
#include <zeno/types/PrimitiveObject.h>
#include <zeno/types/NumericObject.h>

namespace {


struct GetBlenderObjectAxes : zeno::INode {
    virtual void apply() override {
        auto object = get_input<zeno::BlenderAxis>("object");
        auto m = object->matrix;

        auto origin = std::make_shared<zeno::NumericObject>();
        origin->set(zeno::vec3f(m[0][3], m[1][3], m[2][3]));

        auto axisX = std::make_shared<zeno::NumericObject>();
        axisX->set(zeno::vec3f(m[0][0], m[1][0], m[2][0]));

        auto axisY = std::make_shared<zeno::NumericObject>();
        axisY->set(zeno::vec3f(m[0][1], m[1][1], m[2][1]));

        auto axisZ = std::make_shared<zeno::NumericObject>();
        axisZ->set(zeno::vec3f(m[0][2], m[1][2], m[2][2]));

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


struct BMeshToPrimitive : zeno::INode {
    virtual void apply() override {
        auto mesh = get_input<zeno::BlenderMesh>("mesh");
        auto prim = std::make_shared<zeno::PrimitiveObject>();
        auto allow_quads = get_param<bool>("allow_quads");
        auto do_transform = get_param<bool>("do_transform");

        // todo: support **input** blender attributes
        prim->resize(mesh->vert.size());
        auto &pos = prim->add_attr<zeno::vec3f>("pos");
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


struct PrimitiveToBMesh : zeno::INode {
    virtual void apply() override {
        auto prim = get_input<zeno::PrimitiveObject>("prim");
        auto mesh = std::make_shared<zeno::BlenderMesh>();
        // todo: support exporting transform matrix (for empty axis) too?

        mesh->vert.resize(prim->size());
        auto &pos = prim->attr<zeno::vec3f>("pos");
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

struct LineViewer : zeno::INode {
    virtual void complete() override {
        if (get_param<bool>("display")) {
            graph->finalOutputNodes.insert(myname);
        }
    }

    virtual void apply() override {
        if (!has_input("prim") || !get_param<bool>("display")) {
            return;
        }
        auto prim = get_input<zeno::PrimitiveObject>("prim");
        
        auto verts = prim->verts;
        const size_t vertSize = verts.size();
        auto &vertexBuffer = graph->getUserData().get<zeno::LineViewerVertexBufferType>("line_vertex_buffer");
        auto &colorBuffer = graph->getUserData().get<zeno::LineViewerColorBufferType>("line_color_buffer");
        auto buffersize = vertexBuffer.size();
        vertexBuffer.reserve(buffersize + vertSize);
        colorBuffer.reserve(buffersize + vertSize);
        auto &vertexPos = verts.values;
        auto &color = verts.attr<zinc::vec3f>("clr");
        for (int i = 0; i < vertSize; i++) {
            vertexBuffer.emplace_back(std::vector<float>(vertexPos[i].begin(), vertexPos[i].end()));
            colorBuffer.emplace_back(std::vector<float>(color[i].begin(), color[i].end()));
        }
     
        auto &indexBuffer = graph->getUserData().get<zeno::LineViewerIndexBufferType>("line_index_buffer");
        auto &lines = prim->lines.values;
        const size_t lineSize = lines.size();
        indexBuffer.reserve(indexBuffer.size() + lineSize);
        for (int i = 0; i < lineSize; i++) {
            std::vector<int> line { lines[i][0] + static_cast<int>(buffersize), lines[i][1] + static_cast<int>(buffersize) };
            indexBuffer.emplace_back(std::move(line));
        }
    }
};

ZENDEFNODE(LineViewer, {
    {"prim"},
    {},
    {{"bool", "display", "1"}},
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

struct BAxisExtract : zeno::INode {
    virtual void apply() override {
        auto axis = get_input<zeno::BlenderAxis>("axis");
        auto translation = std::make_shared<zeno::NumericObject>();
        auto quaternion = std::make_shared<zeno::NumericObject>();
        auto scaling = std::make_shared<zeno::NumericObject>();
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
