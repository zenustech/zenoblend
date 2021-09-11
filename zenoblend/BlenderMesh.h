#pragma once

#include <zeno/core/IObject.h>
#include <zeno/types/AttrVector.h>
#include <zeno/utils/vec.h>
#include <array>
#include <vector>

namespace zeno {

struct PolyMesh {
    struct Polygon {
        int start = 0, len = 0;

        inline Polygon() = default;
        inline Polygon(int start, int len)
            : start(start), len(len) {}
    };

    AttrVector<vec3f> vert;
    AttrVector<Polygon> poly;
    AttrVector<int> loop;
};

struct BlenderAxis : IObjectClone<BlenderAxis> {
    std::array<std::array<float, 4>, 4> matrix;
};

struct BlenderMesh : IObjectClone<BlenderMesh, BlenderAxis>, PolyMesh {
    bool is_smooth = false;
};

struct BlenderData {
    std::set<std::string> input_names;
    std::map<std::string, std::function<std::shared_ptr<BlenderAxis>()>> inputs;
    std::map<std::string, std::shared_ptr<BlenderAxis>> outputs;

    std::vector<std::vector<float>> line_vertices;
    std::vector<std::vector<int>> line_indices;
    std::vector<std::vector<float>> line_colors;
};

}
