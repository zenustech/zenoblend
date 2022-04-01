#pragma once

#include <zeno/core/IObject.h>
#include <zeno/types/AttrVector.h>
#include <zeno/utils/vec.h>
#include <array>
#include <vector>

namespace zeno {

// PolyMesh structure can also serve as Armature
struct PolyMesh {
    struct Polygon {
        int start = 0, len = 0;

        inline Polygon() = default;
        inline Polygon(int start, int len)
            : start(start), len(len) {}
    };

    struct Edge {
        int src = 0, dst = 0;

        inline Edge() = default;
        inline Edge(int src, int dst)
            : src(src), dst(dst) {}
    };

    AttrVector<vec3f> vert;
    AttrVector<Edge> edge;
    AttrVector<Polygon> poly;
    AttrVector<int> loop;
};

struct BlenderAxis : IObjectClone<BlenderAxis> {
    std::array<std::array<float, 4>, 4> matrix;// global affine matrix
};

// struct BlenderBone : IObjectClone<BlenderBone,BlenderAxis> {
//     // std::array<std::array<float, 4>, 4> matrix;// global affine matrix
//     // extra properties for forward kinematics
//     std::array<float,4> loc_quat;              // local quaternion
//     std::array<float,3> loc_b;                 // local translation

//     std::string parent;
// };

struct BlenderMesh : IObjectClone<BlenderMesh, BlenderAxis>, PolyMesh {
    bool is_smooth = false;
    bool use_auto_smooth = false;
};

// we need a collection structure here

struct BlenderBone : IObjectClone<BlenderBone,BlenderAxis> {
    int parent_idx;
    std::string bone_idname;
    std::string bone_custom_shape_idname;
    std::array<float,4> quat;
    std::array<float,3> b;
};

// struct BlenderBoneTreeNode {}

struct BlenderData {
    std::set<std::string> input_names;// might include collection names
    std::map<std::string, std::function<std::shared_ptr<BlenderAxis>()>> inputs; // the map from object idname to object
    std::map<std::string, std::shared_ptr<BlenderAxis>> outputs;

    std::map<std::string, std::set<std::string>> collections;// the map from collection name to all the descend objects' idnames
    std::map<std::string, std::set<std::string>> armature2bones;
    std::map<std::string, std::set<std::string>> bone2geos;

    std::map<std::string,std::vector<BlenderBone>> armature2btree;

    std::vector<std::vector<float>> line_vertices;
    std::vector<std::vector<int>> line_indices;
    std::vector<std::vector<float>> line_colors;
};

}
