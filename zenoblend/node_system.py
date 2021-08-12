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
        return ntree.bl_idname == 'ZenoNodeTree'


node_classes = []

type_lut = {
    'int': 'NodeSocketInt',
    'float': 'NodeSocketFloat',
    'vec3f': 'NodeSocketVector',
}

def make_node_class(name, inputs, outputs):
    class Def(Node, ZenoTreeNode):
        '''Zeno node from ZDK: ''' + name
        bl_idname = 'ZenoNode_' + name
        bl_label = name
        bl_icon = 'NODETREE'

        def init(self, context):
            for type, name in inputs:
                type = type_lut.get(type, 'ZenoNodeSocket')
                self.inputs.new(type, name)

            for type, name in outputs:
                type = type_lut.get(type, 'ZenoNodeSocket')
                self.outputs.new(type, name)

    Def.__name__ = 'ZenoNode_' + name
    node_classes.append(Def)
    return Def

make_node_class('TransformPrimitive',
        [('int', 'inner'), ('float', 'second')],
        [('float', 'outer')],
)


import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem


class ZenoNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ZenoNodeTree'


node_categories = [
    # identifier, label, items list
    ZenoNodeCategory('PRIMITIVE', "primitive", items=[
        NodeItem("ZenoNode_TransformPrimitive"),
    ]),
]

classes = (
    ZenoNodeTree,
    ZenoNodeSocket,
)


def register():
    from bpy.utils import register_class
    for cls in node_classes:
        register_class(cls)
    for cls in classes:
        register_class(cls)

    nodeitems_utils.register_node_categories('ZENO_NODES', node_categories)


def unregister():
    nodeitems_utils.unregister_node_categories('ZENO_NODES')

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    for cls in reversed(node_classes):
        unregister_class(cls)


if __name__ == "__main__":
    register()

