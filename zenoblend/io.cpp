#include <zeno/zeno.h>
#include "BlenderMesh.h"
#include <zeno/types/PrimitiveObject.h>
#include <zeno/types/NumericObject.h>
#include <zeno/types/StringObject.h>
#include <zeno/utils/safe_at.h>

namespace {
using namespace zeno;



struct BlenderText : INode {
    virtual void apply() override {
        auto text = get_input2<std::string>("text");
        set_output2("value", std::move(text));
    }
};

ZENDEFNODE(BlenderText, {
    {{"string", "text", "DontUseThisNodeDirectly"}},
    {{"string", "value"}},
    {},
    {"blender"},
});


struct BlenderInput : INode {
    virtual void complete() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");
        ud.input_names.insert(objid);
    }

    virtual void apply() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");
        auto object = safe_at(ud.inputs, objid, "blender input")();
        set_output2("object", std::move(object));
    }
};

ZENDEFNODE(BlenderInput, {
    {{"string", "objid", "DontUseThisNodeDirectly"}},
    {{"BlenderAxis", "object"}},
    {},
    {"blender"},
});


struct BlenderOutput : INode {
    virtual void complete() override {
        if (get_param<bool>("active")) {
            graph->finalOutputNodes.insert(myname);
        }
    }

    virtual void apply() override {
        auto &ud = graph->getUserData().get<BlenderData>("blender_data");
        auto objid = get_input2<std::string>("objid");
        auto object = get_input<BlenderMesh>("object");
        ud.outputs[objid] = std::move(object);
    }
};

ZENDEFNODE(BlenderOutput, {
    {{"string", "objid", "DontUseThisNodeDirectly"}, {"BlenderMesh", "object"}},
    {},
    {{"bool", "active", "1"}},
    {"blender"},
});

}
