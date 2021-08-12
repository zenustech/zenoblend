from bpy.types import NodeTree, Node, NodeSocket
from nodeitems_utils import NodeCategory, NodeItem


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
node_pre_categories = {}
node_categories = []


def add_node_class(name, inputs, outputs, category):
    type_lut = {
        'int': 'NodeSocketInt',
        'float': 'NodeSocketFloat',
        'vec3f': 'NodeSocketVector',
    }

    class Def(Node, ZenoTreeNode):
        '''Zeno node from ZDK: ''' + name
        bl_idname = 'ZenoNode_' + name
        bl_label = name
        bl_icon = 'NODETREE'

        def init(self, context):
            for type, name, defl in inputs:
                type = type_lut.get(type, 'ZenoNodeSocket')
                socket = self.inputs.new(type, name)
                if defl:
                    socket.default_value = eval(defl)

            for type, name, defl in outputs:
                type = type_lut.get(type, 'ZenoNodeSocket')
                socket = self.outputs.new(type, name)

    Def.__name__ = 'ZenoNode_' + name
    node_classes.append(Def)
    node_pre_categories.setdefault(category, []).append(Def.__name__)
    return Def


def init_node_classes():
    node_classes.clear()
    node_pre_categories.clear()

    add_node_class('TransformPrimitive',
            [('int', 'inner', '42'), ('float', 'second', '3.142')],
            [('float', 'outer', '')],
            'primitive')

    init_node_categories()


def init_node_categories():
    node_categories.clear()
    for name, node_names in node_pre_categories.items():
        items = [NodeItem(n) for n in node_names]
        node_categories.append(ZenoNodeCategory(name, name, items=items))


class ZenoNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ZenoNodeTree'



classes = (
    ZenoNodeTree,
    ZenoNodeSocket,
)


def register():
    init_node_classes()

    from bpy.utils import register_class
    for cls in node_classes:
        register_class(cls)
    for cls in classes:
        register_class(cls)

    from nodeitems_utils import register_node_categories
    register_node_categories('ZENO_NODES', node_categories)


def unregister():
    from nodeitems_utils import unregister_node_categories
    unregister_node_categories('ZENO_NODES')

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    for cls in reversed(node_classes):
        unregister_class(cls)


if __name__ == "__main__":
    register()

