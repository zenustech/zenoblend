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
            bpy.context.scene.zeno.executing = True
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
        bpy.context.scene.zeno.executing = False
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
        #self.layout.operator("node.zeno_stop", text="Stop Running Graph")  # deprecated
        self.layout.operator("node.zeno_reload", text="Reload Graph Nodes")


def update_node_tree_list(self, context):
    tree_index = bpy.context.scene.zeno.ui_list_selected_tree
    global tree_name_dict
    name = bpy.data.node_groups.get(tree_name_dict[tree_index])
    if name and context.space_data and name != context.space_data.edit_tree.name:
        context.space_data.path.start(name)


class ZenoSceneProperties(bpy.types.PropertyGroup):
    frame_start: bpy.props.IntProperty(name='Start', default=1)
    frame_end: bpy.props.IntProperty(name='End', default=1000)
    executing: bpy.props.BoolProperty(name='is_executing', default=False)
    ui_list_selected_tree: bpy.props.IntProperty(update=update_node_tree_list)
   


class ZenoNewIndex():
    new_index = -1

class ZENO_UL_TreePropertyList(bpy.types.UIList):
    """Show in node tree editor"""
    

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        tree = item
        row = layout.row(align=True)

        # tree name
        # if context.space_data.node_tree and context.space_data.node_tree.name == tree.name:
        row.prop(tree, "name", text="", emboss=False, icon='NONE')
        global tree_name_dict
        if index not in tree_name_dict:
            tree_name_dict[index] = tree.name
            ZenoNewIndex.new_index = index
        else:
            tree_name_dict[index] = tree.name
            ZenoNewIndex.new_index = -1

        # buttons
        row = row.row(align=True)
        row.alignment = 'RIGHT'
        row.ui_units_x = 3
        row.prop(tree, 'zeno_enabled', icon= f"RESTRICT_VIEW_{'OFF' if tree.zeno_enabled else 'ON'}", text='', emboss=False)
        row.prop(tree, 'zeno_realtime_update', icon='FILE_REFRESH', text='')
        row.prop(tree, 'zeno_cached', icon='PHYSICS', text='')

    def filter_items(self, context, data, prop_name):
        trees = getattr(data, prop_name)
        filter_name = self.filter_name
        filter_invert = self.use_filter_invert
        filter_tree_types = [tree.bl_idname == 'ZenoNodeTree' for tree in trees]
        filter_tree_names = [filter_name.lower() in tree.name.lower() for tree in trees]
        filter_tree_names = [not f for f in filter_tree_names] if filter_invert else filter_tree_names
        combine_filter = [f1 and f2 for f1, f2 in zip(filter_tree_types, filter_tree_names)]
        # next code is needed for hiding wrong tree types
        combine_filter = [not f for f in combine_filter] if filter_invert else combine_filter
        combine_filter = [self.bitflag_filter_item if f else 0 for f in combine_filter]
        return combine_filter, []


class ZenoScenePanel(bpy.types.Panel):
    '''Zeno scene options'''

    bl_label = 'Zeno Scene'
    bl_idname = 'SCENE_PT_zeno_scene'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Node Tree"
    bl_context = 'scene'
    bl_order = 2

    @classmethod
    def poll(cls, context):
        try:
            return context.space_data.node_tree.bl_idname == 'ZenoNodeTree'
        except:
            return False

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column()
        col.template_list("ZENO_UL_TreePropertyList", "", bpy.data, 'node_groups',
                          scene.zeno, "ui_list_selected_tree")
        if ZenoNewIndex.new_index >= 0:
            try:
                bpy.context.scene.zeno.ui_list_selected_tree = ZenoNewIndex.new_index
            except:
                pass
        row = layout.row(align=True)
        row.prop(scene.zeno, 'frame_start')
        row.prop(scene.zeno, 'frame_end')
        col = layout.column()
        tree_id = scene.zeno.ui_list_selected_tree
        if tree_id >= 0:
            tree = bpy.data.node_groups[tree_name_dict[tree_id]]           
            if tree.zeno_cached:
                cached_to_frame = tree.nextFrameId - 1 if getattr(tree, "nextFrameId", None) else ''
                col.label(text=f"Cached to frame: {cached_to_frame}")
        row = layout.row()
        row.operator('node.zeno_apply')
        if tree.zeno_cached and scene.frame_current != scene.zeno.frame_start: 
            row.enabled = False # gray out button
        elif tree.zeno_realtime_update:
            row.enabled = False
        

classes = (
    ZenoApplyOperator,
    ZenoStopOperator,
    ZenoReloadOperator,
    ZenoSceneProperties,
    ZENO_UL_TreePropertyList,
    ZenoScenePanel,
)

# callback for updating editing nodetree
def notification_handler(*args):
    # set fake user automatically
    [setattr(t, 'use_fake_user', True) for t in bpy.data.node_groups if t.bl_idname == 'ZenoNodeTree']
    for area in bpy.context.screen.areas:
        if area.type == 'NODE_EDITOR':
            for space in area.spaces:
                if hasattr(space, "edit_tree"):
                    tree = space.edit_tree
    print(f"Object: {tree.name}, Args: {args}")
    global tree_name_dict
    key = next((k for k in tree_name_dict if tree_name_dict[k] == tree.name), None)
    if key is not None:
        bpy.context.scene.zeno.ui_list_selected_tree = key



def subscribe_active_obj():
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.SpaceNodeEditor, 'node_tree'),
        owner=object(),
        args=("a", "b", "c"),
        notify=notification_handler,
        options={"PERSISTENT",}
    )
    if load_handler_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler_post)


@bpy.app.handlers.persistent
def load_handler_post(dummy):
    subscribe_active_obj()


if load_handler_post not in bpy.app.handlers.load_post:
    bpy.app.handlers.load_post.append(load_handler_post)

def register():
    global tree_name_dict
    tree_name_dict = dict()
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
                if len(input.links) == 1:
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
