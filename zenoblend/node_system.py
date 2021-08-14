import bpy
from bpy.types import NodeTree, Node, NodeSocket
from nodeitems_utils import NodeCategory, NodeItem


class ZenoNodeTree(NodeTree):
    '''Zeno node tree type'''
    bl_idname = 'ZenoNodeTree'
    bl_label = "Zeno Node Tree"
    bl_icon = 'NODETREE'

    def draw_buttons(self, *args):
        print('!!!', args)

    def draw(self, *args):
        print('???', args)


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
node_descriptors = []


def add_node_class(name, inputs, outputs, category, update=None):
    type_lut = {
        'int': 'NodeSocketInt',
        'float': 'NodeSocketFloat',
        'vec3f': 'NodeSocketVector',
        'color3f': 'NodeSocketColor',
        'string': 'NodeSocketString',
        'readpath': 'NodeSocketString',
        'writepath': 'NodeSocketString',
        'multiline_string': 'NodeSocketString',
    }

    def eval_type(type):
        return type_lut.get(type, 'ZenoNodeSocket')

    def eval_defl(defl, type):
        try:
            if type == 'int':
                return int(defl)
            elif type == 'float':
                return float(defl)
            elif type == 'string':
                return str(defl)
        except ValueError:
            return None

    class Def(Node, ZenoTreeNode):
        bl_idname = 'ZenoNode_' + name
        bl_label = name
        bl_icon = 'NODETREE'
        zeno_type = name

        def init(self, context):
            for type, name, defl in inputs:
                socket = self.inputs.new(eval_type(type), name)
                if defl:
                    defl = eval_defl(defl, type)
                    if defl is not None:
                        socket.default_value = defl

            for type, name, defl in outputs:
                type = eval_type(type)
                self.outputs.new(eval_type(type), name)

        def reinit(self):
            links = []
            for name, socket in self.inputs.items():
                for link in socket.links:
                    links.append((
                        link.from_node, link.from_socket.name,
                        link.to_node, link.to_socket.name,
                        ))
                self.inputs.remove(socket)
            for name, socket in self.outputs.items():
                for link in socket.links:
                    links.append((
                        link.from_node, link.from_socket.name,
                        link.to_node, link.to_socket.name,
                        ))
                self.outputs.remove(socket)

            for type, name, defl in inputs:
                socket = self.inputs.new(eval_type(type), name)
                if defl:
                    defl = eval_defl(defl, type)
                    if defl is not None:
                        socket.default_value = defl

            for type, name, defl in outputs:
                type = eval_type(type)
                self.outputs.new(eval_type(type), name)

            node_tree = self.id_data
            for from_node, from_socket, to_node, to_socket in links:
                if from_socket not in from_node.outputs:
                    continue
                if to_socket not in to_node.inputs:
                    continue
                from_socket = from_node.outputs[from_socket]
                to_socket = to_node.inputs[to_socket]
                node_tree.links.new(from_socket, to_socket)

    Def.__doc__ = 'Zeno node from ZDK: ' + name
    Def.__name__ = 'ZenoNode_' + name
    node_classes.append(Def)
    node_pre_categories.setdefault(category, []).append(Def.__name__)
    return Def


def get_descriptors():
    node_descriptors.clear()
    from .dll import core
    descs = core.dumpDescriptors()
    for desc in descs.splitlines():
        if not desc.startswith('DESC@'):
            continue
        _, title, rest = desc.split('@', 2)
        assert rest[0] == '{' and rest[-1] == '}', rest
        inputs, outputs, params, category = rest[1:-1].split('}{')
        inputs = inputs.split('%') if inputs else []
        outputs = outputs.split('%') if outputs else []
        params = params.split('%') if params else []
        inputs = [x.split('@') for x in inputs]
        outputs = [x.split('@') for x in outputs]
        params = [x.split('@') for x in params]
        inputs += [(x, y + ':', z.split(' ')[0]) for x, y, z in params]
        node_descriptors.append((title, inputs, outputs, category))


def init_node_classes():
    get_descriptors()

    node_classes.clear()
    node_pre_categories.clear()

    for title, inputs, outputs, category in node_descriptors:
        add_node_class(title, inputs, outputs, category)

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

