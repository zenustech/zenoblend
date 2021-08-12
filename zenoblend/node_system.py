import bpy
from bpy.types import NodeTree, Node, NodeSocket


class ZenoNodeTree(NodeTree):
    '''Zeno node tree type'''
    bl_idname = 'ZenoNodeTree'
    bl_label = "Zeno Node Tree"
    bl_icon = 'NODETREE'


class ZenoNodeSocket(NodeSocket):
    '''Zeno node socket type'''
    bl_idname = 'ZenoNodeSocket'
    bl_label = "Zeno Node Socket"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 1.0)


class ZenoTreeNode:
    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'ZenoTreeType'


# Derived from the Node base type.
class ZenoNode_TransformPrimitive(Node, ZenoTreeNode):
    '''Zeno node from ZDK: TransformPrimitive'''
    bl_idname = 'ZenoNode_TransformPrimitive'
    bl_label = "TransformPrimitive"
    bl_icon = 'NODETREE'

    my_string_prop: bpy.props.StringProperty()
    my_float_prop: bpy.props.FloatProperty(default=3.1415926)

    def init(self, context):
        self.inputs.new('ZenoNodeSocket', "Hello")
        self.inputs.new('NodeSocketFloat', "World")
        self.inputs.new('NodeSocketVector', "!")

        self.outputs.new('NodeSocketColor', "How")
        self.outputs.new('NodeSocketColor', "are")
        self.outputs.new('NodeSocketFloat', "you")

    def draw_buttons(self, context, layout):
        layout.label(text="(Imported From ZDK)")

    def draw_label(self):
        return self.bl_label


import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem


class ZenoNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ZenoTreeType'


node_categories = [
    # identifier, label, items list
    ZenoNodeCategory('PRIMITIVE', "primitive", items=[
        NodeItem("ZenoNode_TransformPrimitive"),
    ]),
]

classes = (
    ZenoNodeTree,
    ZenoNodeSocket,
    ZenoNode_TransformPrimitive,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    nodeitems_utils.register_node_categories('ZENO_NODES', node_categories)


def unregister():
    nodeitems_utils.unregister_node_categories('ZENO_NODES')

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


if __name__ == "__main__":
    register()

