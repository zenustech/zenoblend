#include <zeno/zeno.h>
#include "BlenderMesh.h"
#include <zeno/types/PrimitiveObject.h>
#include <zeno/types/NumericObject.h>

namespace {
using namespace zeno;


struct BlenderLineViewer : INode {
    virtual void complete() override {
        if (get_param<bool>("display")) {
            graph->finalOutputNodes.insert(myname);
        }
    }

    virtual void apply() override {
        if (!has_input("prim") || !get_param<bool>("display")) {
            return;
        }
        auto prim = get_input<PrimitiveObject>("prim");
        
        auto verts = prim->verts;
        const size_t vertSize = verts.size();
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto &vertexBuffer = ud.line_vertices;
        auto &colorBuffer = ud.line_colors;
        auto buffersize = vertexBuffer.size();
        vertexBuffer.reserve(buffersize + vertSize);
        colorBuffer.reserve(buffersize + vertSize);
        auto &vertexPos = verts.values;
        auto &color = verts.attr<vec3f>("clr");
        for (int i = 0; i < vertSize; i++) {
            vertexBuffer.emplace_back(std::vector<float>(vertexPos[i].begin(), vertexPos[i].end()));
            colorBuffer.emplace_back(std::vector<float>(color[i].begin(), color[i].end()));
        }
     
        auto &indexBuffer = ud.line_indices;
        auto &lines = prim->lines.values;
        const size_t lineSize = lines.size();
        indexBuffer.reserve(indexBuffer.size() + lineSize);
        for (int i = 0; i < lineSize; i++) {
            std::vector<int> line { lines[i][0] + static_cast<int>(buffersize), lines[i][1] + static_cast<int>(buffersize) };
            indexBuffer.emplace_back(std::move(line));
        }
    }
};

ZENDEFNODE(BlenderLineViewer, {
    {"prim"},
    {},
    {{"bool", "display", "1"}},
    {"blender"},
    });


}
