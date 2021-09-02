import bpy
import time
from . import scenario


class ZenoApplyOperator(bpy.types.Operator):
    """Apply the Zeno graph"""
    bl_idname = "node.zeno_apply"
    bl_label = "Apply"

    @classmethod
    def poll(cls, context):
        return getattr(context.space_data, 'tree_type', 'ZenoNodeTree') == 'ZenoNodeTree'

    def execute(self, context):
        data = dump_scene()
        t0 = time.time()
        scenario.load_scene(data)
        if not scenario.frame_update_callback():
            self.report({'ERROR'}, 'No node tree specified! Please check the Zeno Scene panel.')
        else:
            dt = time.time() - t0
            self.report({'INFO'}, 'Node tree applied in {:.04f}s'.format(dt))
        return {'FINISHED'}


class ZenoStopOperator(bpy.types.Operator):
    """Stop the running Zeno graph"""
    bl_idname = "node.zeno_stop"
    bl_label = "Stop"

    @classmethod
    def poll(cls, context):
        return getattr(context.space_data, 'tree_type', 'ZenoNodeTree') == 'ZenoNodeTree'

    def execute(self, context):
        if scenario.delete_scene():
            self.report({'INFO'}, 'Node tree stopped')
        else:
            self.report({'WARNING'}, 'Node tree already stopped!')
        return {'FINISHED'}


class ZenoReloadOperator(bpy.types.Operator):
    """Reload Zeno graphs"""
    bl_idname = "node.zeno_reload"
    bl_label = "Reload"

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ZenoNodeTree'

    def execute(self, context):
        from .node_system import init_node_subgraphs, deinit_node_subgraphs
        deinit_node_subgraphs()
        init_node_subgraphs()
        reinit_subgraph_sockets()
        self.report({'INFO'}, 'Node tree reloaded')
        return {'FINISHED'}


def draw_menu(self, context):
    if context.area.ui_type == 'ZenoNodeTree':
        self.layout.separator()
        self.layout.operator("node.zeno_apply", text="Apply Graph")
        self.layout.operator("node.zeno_stop", text="Stop Running Graph")
        self.layout.operator("node.zeno_reload", text="Reload Graph Nodes")


class ZenoSceneProperties(bpy.types.PropertyGroup):
    node_tree_static: bpy.props.StringProperty(name='Static')
    node_tree_framed: bpy.props.StringProperty(name='Framed')
    frame_start: bpy.props.IntProperty(name='Start', default=1)
    frame_end: bpy.props.IntProperty(name='End', default=1000)


class ZenoScenePanel(bpy.types.Panel):
    '''Zeno scene options'''

    bl_label = 'Zeno Scene'
    bl_idname = 'SCENE_PT_zeno_scene'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        row.prop(scene.zeno, 'frame_start')
        row.prop(scene.zeno, 'frame_end')
        col = layout.column()
        col.prop_search(scene.zeno, 'node_tree_static', bpy.data, 'node_groups')
        col.prop_search(scene.zeno, 'node_tree_framed', bpy.data, 'node_groups')
        row = layout.row()
        row.operator('node.zeno_apply')
        row.operator('node.zeno_stop')


classes = (
    ZenoApplyOperator,
    ZenoStopOperator,
    ZenoReloadOperator,
    ZenoSceneProperties,
    ZenoScenePanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.zeno = bpy.props.PointerProperty(name='zeno', type=ZenoSceneProperties)
    bpy.types.NODE_MT_context_menu.append(draw_menu)


def unregister():
    bpy.types.NODE_MT_context_menu.remove(draw_menu)
    del bpy.types.Scene.zeno
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


def reinit_subgraph_sockets():
    for tree_name, tree in bpy.data.node_groups.items():
        if tree.bl_idname != 'ZenoNodeTree': continue
        for node_name, node in tree.nodes.items():
            if not hasattr(node, 'zeno_type'): continue
            node.reinit()


'''
def load_from_zsg(prog):
    graphs = prog['graph']
    for key, val in graphs.items():
        if key in bpy.data.node_groups:
            del bpy.data.node_groups[key]
        tree = bpy.data.node_groups.new(key, 'ZenoNodeTree')
        nodes = val['nodes']

        nodesLut = {}
        for ident, data in nodes.items():
            if 'special' in data: continue
            type = data['name']
            if type in graphs:
                type = 'Subgraph'
            try:
                node = tree.nodes.new('ZenoNode_' + type)
            except RuntimeError:
                print('nodetype RuntimeError:', type)
                continue
            node.location.x, node.location.y = data['uipos']
            nodesLut[ident] = node
            if type == 'Subgraph':
                node.inputs['name:'].default_value = data['name']
            node.init(None)

        for ident, data in nodes.items():
            if 'special' in data: continue
            for key, connection in data['inputs'].items():
                try:
                    srcNode, srcSock, deflVal = connection
                except ValueError:
                    print('connection ValueError:', ident, key, connection)
                    continue
                if deflVal is not None:
                    node.inputs[key].default_value = deflVal
                if srcNode is None:
                    continue
                if key not in node.inputs:
                    node.inputs.new('ZenoNodeSocket', key)
                if srcNode not in nodesLut:
                    print('nodesLut KeyError:', ident, srcNode)
                    continue
                srcNode = nodesLut[srcNode]
                if srcSock not in srcNode.outputs:
                    srcNode.outputs.new('ZenoNodeSocket', srcSock)
                tree.links.new(node.inputs[key], srcNode.outputs[srcSock])

            for key, value in data['params'].items():
                key = key + ':'
                if key not in node.inputs:
                    print('params KeyError:', ident, key)
                    continue
                node.inputs[key].default_value = value

#bpy.load_zsg = lambda path: load_from_zsg(__import__('json').load(open(path)))
'''


def find_tree_sub_category(tree):
    assert tree.bl_idname == 'ZenoNodeTree', tree
    if 'SubCategory' in tree.nodes:
        node = tree.nodes['SubCategory']
        if node.zeno_type == 'SubCategory':
            return node.inputs['name:'].default_value
    for node_name, node in tree.nodes.items():
        if not hasattr(node, 'zeno_type'): continue
        if node.zeno_type == 'SubCategory':
            return node.inputs['name:'].default_value
    return 'uncategorized'


def find_tree_sub_io_names(tree):
    assert tree.bl_idname == 'ZenoNodeTree', tree
    inputs = []
    outputs = []
    for node_name, node in tree.nodes.items():
        if not hasattr(node, 'zeno_type'): continue
        if node.zeno_type == 'SubInput':
            type = node.inputs['type:'].default_value
            name = node.inputs['name:'].default_value
            defl = node.inputs['defl:'].default_value
            inputs.append((type, name, defl))
        elif node.zeno_type == 'SubOutput':
            type = node.inputs['type:'].default_value
            name = node.inputs['name:'].default_value
            defl = node.inputs['defl:'].default_value
            outputs.append((type, name, defl))
    return inputs, outputs


eval_bpy_data = {
    # possibly support more bpy datablocks, like objects, images, textures
    'texts': lambda data: data.as_string(),
    'objects': lambda data: data.name,
}

def dump_tree(tree):
    assert tree.bl_idname == 'ZenoNodeTree', tree
    for node_name, node in tree.nodes.items():
        if not hasattr(node, 'zeno_type'): continue
        node_type = node.zeno_type
        yield ('addNode', node_type, node_name)

        # thank @hooyuser for contribute!
        if hasattr(node, 'bpy_data_inputs'):
            for input_name, data_type in node.bpy_data_inputs.items():
                data_blocks = getattr(bpy.data, data_type)
                data_block_name = getattr(node, input_name)
                if data_block_name not in data_blocks:
                    print('WARNING: object named `{}` not exist!')
                    continue
                data = data_blocks[data_block_name]
                value = eval_bpy_data[data_type](data)
                yield ('setNodeInput', node_name, input_name, value)

        for input_name, input in node.inputs.items():
            if input.is_linked:
                assert len(input.links) == 1
                link = input.links[0]
                src_node_name = link.from_node.name
                src_socket_name = link.from_socket.name
                yield ('bindNodeInput', node_name, input_name,
                        src_node_name, src_socket_name)
            elif hasattr(input, 'default_value'):
                value = input.default_value
                if type(value).__name__ in ['bpy_prop_array', 'Vector']:
                    value = tuple(value)
                yield ('setNodeInput', node_name, input_name, value)

        if node.zeno_type == 'Subgraph':
            yield ('setNodeInput', node_name, 'name:', node.graph_name)
        yield ('completeNode', node_name)


def dump_all_trees():
    yield ('clearAllState',)
    for name, tree in bpy.data.node_groups.items():
        if tree.bl_idname != 'ZenoNodeTree': continue
        yield ('switchGraph', name)
        yield from dump_tree(tree)


def dump_scene():
    import json
    data = list(dump_all_trees())
    data = json.dumps(data)
    return data
