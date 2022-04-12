import bpy
from bpy.types import NodeTree, Node, NodeSocket
from nodeitems_utils import NodeCategory, NodeItem
from nodeitems_utils import register_node_categories
from nodeitems_utils import unregister_node_categories
from bpy.utils import register_class, unregister_class
from . import scenario
from . import gpu_drawer
from . import tree_dumper


class ZenoNodeTree(NodeTree):
    '''Zeno node tree type'''
    bl_idname = 'ZenoNodeTree'
    bl_label = "Zeno Node Tree"
    bl_icon = 'NODETREE'

    def __init__(self):  # Declare attributes of ZenoNodeTree. No practical effect
        self.nextFrameId = None
        self.frameCache = {}
        self.batch = None
        self.draw_handler = None

    def enabled_callback(self, context):
        if self.zeno_enabled:  # if the state is switched from false to true
            scenario.reload_scene()
            scenario.frame_update_callback()
        else:
            gpu_drawer.clear_draw_handler(self)
            scenario.reload_scene()

    def realtime_update_callback(self, context):
        if self.zeno_realtime_update:  # if the state is switched from false to true
            scenario.reload_scene()
            scenario.frame_update_callback()

    def cached_callback(self, context):
        if self.zeno_cached:  # if the state is switched from false to true
            scenario.frame_update_callback()
        else:
            self.frameCache = {}
            self.nextFrameId = None

    zeno_enabled: bpy.props.BoolProperty(name="Enabled", default=True, description='Enable Graph', update=enabled_callback)
    zeno_realtime_update: bpy.props.BoolProperty(name="Realtime Update", default=True, description='Realtime Update', update=realtime_update_callback)
    zeno_cached: bpy.props.BoolProperty(name="Cached", default=False, description='Cache frames', update=cached_callback)
    

class ZenoNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ZenoNodeTree'


class ZenoTreeNode:
    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'ZenoNodeTree'



class ZenoNodeSocket(NodeSocket):
    '''Zeno node socket type'''
    bl_idname = 'ZenoNodeSocket'
    bl_label = "Zeno Node Socket"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 1.0)


class ZenoNodeSocket_Dummy(NodeSocket):
    '''Zeno node dummy socket type'''
    bl_idname = 'ZenoNodeSocket_Dummy'
    bl_label = "Zeno Node Socket Dummy"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (0.4, 0.4, 0.4, 1.0)


enum_types_cache = {}

def get_enum_socket_type(type):
    from hashlib import md5
    type_id = 'ZenoNodeSocket_Enum_' + md5(str(type).encode()).hexdigest()
    if type_id in enum_types_cache:
        return type_id

    enums = type.split()[1:]
    items = []
    for key in enums:
        items.append((key, key, key))

    class Def(NodeSocket):
        '''Zeno node enum socket type'''
        bl_label = "Zeno Node Socket Enum (" + ', '.join(enums) + ")"

        default_value: bpy.props.EnumProperty(
            name="Enum value",
            description="Enum imported from ZDK",
            items=items,
            default=enums[0],
        )

        # Optional function for drawing the socket input value
        def draw(self, context, layout, node, text):
            if self.is_output or self.is_linked:
                layout.label(text=text)
            else:
                layout.prop(self, "default_value", text=text)

        # Socket color
        def draw_color(self, context, node):
            return (0.375, 0.75, 1.0, 1.0)

    Def.__name__ = type_id

    register_class(Def)
    enum_types_cache[type_id] = Def
    return type_id


def eval_type(type):
    if type.startswith('enum '):
        return get_enum_socket_type(type)
    type_lut = {
        'int': 'NodeSocketInt',
        'bool': 'NodeSocketBool',
        'float': 'NodeSocketFloat',
        'NumericObject': 'NodeSocketFloat',
        'vec3f': 'NodeSocketVector',
        'color3f': 'NodeSocketColor',
        'string': 'NodeSocketString',
        'readpath': 'NodeSocketString',
        'writepath': 'NodeSocketString',
        'multiline_string': 'NodeSocketString',
    }
    return type_lut.get(type, 'ZenoNodeSocket')


def eval_category_icon(type):
    type_lut = {
        'blender': 'BLENDER',
        'openvdb': 'FILE_VOLUME',
        'primitive': 'PARTICLES',
        'trimesh': 'MESH_MONKEY',
        'subgraph': 'SYSTEM',
        'portal': 'RNA',
        'control': 'SCRIPT',
        'bullet': 'RIGID_BODY',
        'Rigid': 'RIGID_BODY',
        'FLIPSolver': 'MATFLUID',
        'FLIP': 'MATFLUID',
        'cloth': 'MATCLOTH',
        'string': 'FILE_FOLDER',
        'cgmesh': 'MESH_DATA',
        'numeric': 'PLUS',
        'literal': 'DOT',
        'zenofx': 'PHYSICS',
        'EasyGL': 'IMAGE',
    }
    return type_lut.get(type, 'NODETREE')


def eval_defl(socket, defl, type):
    if not defl: return
    defl_list = defl.split(' ')
    defl = defl_list[0]
    minval = defl[1] if len(defl_list) > 1 else None
    maxval = defl[2] if len(defl_list) > 2 else None
    try:
        if type == 'NodeSocketInt':
            socket.default_value = int(defl)
        elif type == 'NodeSocketFloat':
            socket.default_value = float(defl)
        elif type == 'NodeSocketVector':
            x, y, z = defl.split(',')
            socket.default_value = (float(x), float(y), float(z))
        elif type == 'NodeSocketString':
            socket.default_value = str(defl)
        elif type == 'NodeSocketBool':
            socket.default_value = bool(int(defl))
        elif type.startswith('ZenoNodeSocket_Enum_'):
            socket.default_value = str(defl)
    except ValueError:
        pass


def def_node_class(name, inputs, outputs, category):
    def prepare_socket_types():
        for type, name, defl in inputs + outputs:
            if type.startswith('enum '):
                get_enum_socket_type(type)
    prepare_socket_types()

    class Def(Node, ZenoTreeNode):
        bl_label = name
        bl_icon = eval_category_icon(category)
        zeno_type = name
        zeno_category = category

        def init(self, context):
            self.init_sockets(inputs, outputs)

        def reinit(self):
            self.reinit_sockets(inputs, outputs)

        def init_sockets(self, inputs, outputs):
            for type, name, defl in inputs:
                type = eval_type(type)
                socket = self.inputs.new(type, name)
                eval_defl(socket, defl, type)

            for type, name, defl in outputs:
                type = eval_type(type)
                self.outputs.new(type, name)

            self.inputs.new('ZenoNodeSocket_Dummy', 'SRC')
            self.outputs.new('ZenoNodeSocket_Dummy', 'DST')

        def reinit_sockets(self, inputs, outputs):
            links = []
            defls = {}
            for name, socket in self.inputs.items():
                if hasattr(socket, 'default_value'):
                    value = socket.default_value
                    if type(value).__name__ in ['bpy_prop_array', 'Vector']:
                        value = tuple(value)
                    defls[name] = type(socket), value
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

            self.init_sockets(inputs, outputs)

            for name, socket in self.inputs.items():
                if hasattr(socket, 'default_value'):
                    if name in defls and type(socket) is defls[name][0]:
                        socket.default_value = defls[name][1]

            node_tree = self.id_data
            for from_node, from_socket, to_node, to_socket in links:
                if from_socket not in from_node.outputs:
                    continue
                if to_socket not in to_node.inputs:
                    continue
                from_socket = from_node.outputs[from_socket]
                to_socket = to_node.inputs[to_socket]
                node_tree.links.new(from_socket, to_socket)

        def update(self):  # rewrite update function
            if self.id_data.zeno_realtime_update:
                print('updating by node edit')             
                scenario.frame_update_callback()

    Def.__doc__ = 'Zeno node from ZDK: ' + name
    Def.__name__ = 'ZenoNode_' + name
    return Def


class ZenoNode_Subgraph(def_node_class('Subgraph', [], [], 'subgraph')):
    '''Zeno specialized Subgraph node'''
    bl_icon = 'COMMUNITY'

    graph_name: bpy.props.StringProperty()

    def init(self, context):
        self.zeno_inputs, self.zeno_outputs = [], []

    def draw_label(self):
        return self.graph_name

    def draw_buttons(self, context, layout):
        row = layout.row()
        row.operator("node.zeno_reload", text="Load")
        #row.operator("node.zeno_goto", text="Goto")  # todo: impl jump to subgraph..

    def reinit(self):
        tree = bpy.data.node_groups[self.graph_name]
        from .tree_dumper import find_tree_sub_io_names
        self.zeno_inputs, self.zeno_outputs = find_tree_sub_io_names(tree)

        self.reinit_sockets(self.zeno_inputs, self.zeno_outputs)


class ZenoNode_FinalOutput(def_node_class('FinalOutput', [], [], 'subgraph')):
    '''Zeno specialized FinalOutput node'''

    def draw_buttons(self, context, layout):
        row = layout.row()
        row.operator("node.zeno_start", text="Start")
        row.operator("node.zeno_stop", text="Stop")


class ZenoNode_BlenderInputText:
    '''Zeno specialized mixin BlenderInputText node'''
    text: bpy.props.StringProperty()

    bpy_data_inputs = {'text': 'texts'}  # parameter name 'text' is temporarily hardcoded, possibly get processed automatically

    def draw_buttons(self, context, layout):
        layout.prop_search(self, 'text', bpy.data, 'texts', text='', icon='TEXT')

class ZenoNode_BlenderInputAxes:
    '''Zeno specialized mixin BlenderInputAxes node'''
    objid: bpy.props.StringProperty()

    bpy_data_inputs = {'objid': 'objects'}

    def draw_buttons(self, context, layout):
        layout.prop_search(self, 'objid', bpy.data, 'objects', text='', icon='OBJECT_DATA')

class ZenoNode_BlenderSelectedPrimtive:
    '''Zeno specicalized mixin BlenderSelected Node'''
    objid: bpy.props.StringProperty()

    bpy_data_inputs = {'objid': 'objects'}

    selected_input_obj = True
    selected_input_collection = False

    # def draw_buttons(self, context, layout):
        # layout.prop_search(self, 'objid', bpy.data, 'objects', text='', icon='OBJECT_DATA')
        # objid = context.selected_objects[0].name

class ZenoNode_BlenderInputPrimitive:
    '''Zeno specialized mixin BlenderInputPrimitive node'''
    objid: bpy.props.StringProperty()

    bpy_data_inputs = {'objid': 'objects'}

    def draw_buttons(self, context, layout):
        layout.prop_search(self, 'objid', bpy.data, 'objects', text='', icon='OBJECT_DATA')


class ZenoNode_BlenderInputCollection:
    '''Zeno specialized mixin BlenderInputCollection node'''
    colid: bpy.props.StringProperty()

    bpy_data_inputs = {'colid' : 'collections'}

    def draw_buttons(self,context,layout):
        layout.prop_search(self,'colid',bpy.data,'collections',text='',icon='COLLECTION_NEW')

class ZenoNode_BlenderInputArmature:
    '''Zeno specialized mixin BlenderInputArmature node'''
    armid: bpy.props.StringProperty()

    bpy_data_inputs = {'armid' : 'armatures'}
    def draw_buttons(self,context,layout):
        layout.prop_search(self,'armid',bpy.data,'armatures',text='',icon='ARMATURE_DATA')

class ZenoNode_BlenderOutputPrimitive:
    '''Zeno specialized mixin BlenderOutputPrimitive node'''
    objid: bpy.props.StringProperty()

    bpy_data_inputs = {'objid': 'objects'}

    def draw_buttons(self, context, layout):
        layout.prop_search(self, 'objid', bpy.data, 'objects', text='', icon='OBJECT_DATA')


#class ZenoNode_BlenderLineViewer(def_node_class('BlenderLineViewer', [('PrimitiveObject', 'prim', ''), ('bool', 'display:', '1')], [], 'blender')):
#    '''Zeno specialized BlenderLineViewer node'''




def get_descriptors():
    node_descriptors = []
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
        inputs = [(x, y, z) for x, y, z in inputs if y != 'SRC']
        outputs = [(x, y, z) for x, y, z in outputs if y != 'DST']
        node_descriptors.append((title, inputs, outputs, category))
    return node_descriptors



node_classes = []
node_pre_categories = {}


def descriptor_to_class(desc):
    title, inputs, outputs, category = desc
    Def = globals().get('ZenoNode_' + title, None)
    if Def is None:  # non-specialized
        return def_node_class(title, inputs, outputs, category)

    elif not hasattr(Def, 'zeno_type'):  # mixin-specialized
        OldDef = def_node_class(title, inputs, outputs, category)
        class NewDef(OldDef, Def):
            pass
        NewDef.__name__ = OldDef.__name__
        return NewDef

    else:  # fully-specialized
        return Def


def init_node_classes():
    node_descriptors = get_descriptors()

    node_classes.clear()
    node_pre_categories.clear()

    for desc in node_descriptors:
        Def = descriptor_to_class(desc)
        node_classes.append(Def)
        if desc[0] == 'Subgraph': continue
        node_pre_categories.setdefault(Def.zeno_category, []).append(Def.__name__)

    node_categories = []
    for name, node_names in node_pre_categories.items():
        items = [NodeItem(n) for n in node_names]
        node_categories.append(ZenoNodeCategory(name, name, items=items))

    register_node_categories('ZENO_NODES', node_categories)


def deinit_node_classes():
    unregister_node_categories('ZENO_NODES')


def init_node_subgraphs():
    if getattr(init_node_subgraphs, 'initialized', False):
        return
    init_node_subgraphs.initialized = True

    def make_node_item(graph_name):
        return NodeItem("ZenoNode_Subgraph", label=graph_name,
            settings={"graph_name": repr(graph_name)})

    node_pre_subgraph_categories = {}
    for tree_name, tree in bpy.data.node_groups.items():
        from .tree_dumper import find_tree_sub_category
        category = find_tree_sub_category(tree)
        node_pre_subgraph_categories.setdefault(category, []).append(tree_name)

    node_subgraph_categories = []
    for name, node_names in node_pre_subgraph_categories.items():
        items = [make_node_item(n) for n in node_names]
        node_subgraph_categories.append(ZenoNodeCategory(name, name, items=items))

    register_node_categories('ZENO_SUBGRAPH_NODES', node_subgraph_categories)


def deinit_node_subgraphs():
    if not getattr(init_node_subgraphs, 'initialized', False):
        return
    init_node_subgraphs.initialized = False

    unregister_node_categories('ZENO_SUBGRAPH_NODES')


def register_node_class(Def):
    node_classes.append(Def)
    node_pre_categories.setdefault(Def.zeno_category, []).append(Def.__name__)
    return Def



classes = (
    ZenoNodeTree,
    ZenoNodeSocket,
    ZenoNodeSocket_Dummy,
)


def register():
    init_node_classes()

    for cls in node_classes:
        register_class(cls)
    for cls in classes:
        register_class(cls)

    #init_node_subgraphs()


def unregister():
    try: deinit_node_subgraphs()
    except: pass

    for cls in enum_types_cache.values():
        unregister_class(cls)
    enum_types_cache.clear()

    for cls in reversed(classes):
        unregister_class(cls)
    for cls in reversed(node_classes):
        unregister_class(cls)

    deinit_node_classes()


if __name__ == "__main__":
    register()

