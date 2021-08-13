import bpy


class ZenoApplyOperator(bpy.types.Operator):
    """Apply the Zeno graph"""
    bl_idname = "node.zeno_apply"
    bl_label = "Apply"

    @classmethod
    def poll(cls, context):
        return 'NodeTree' in bpy.data.node_groups

    def execute(self, context):
        import json
        from . import scenario
        data = list(dump_graph(bpy.data.node_groups['NodeTree']))
        data = json.dumps(data)
        scenario.load_scene(data)
        scenario.update_scene()
        return {'FINISHED'}


def draw_menu(self, context):
    if context.area.ui_type == 'ZenoNodeTree':
        self.layout.separator()
        self.layout.operator("node.zeno_apply", text="Apply Zeno Graph")


def register():
    bpy.utils.register_class(ZenoApplyOperator)
    bpy.types.NODE_MT_context_menu.append(draw_menu)


def unregister():
    bpy.types.NODE_MT_context_menu.remove(draw_menu)
    bpy.utils.unregister_class(ZenoApplyOperator)


def dump_graph(tree):
    yield ('clearAllState',)
    yield ('switchGraph', 'main')
    for node_name, node in tree.nodes.items():
        node_type = node.zeno_type
        yield ('addNode', node_type, node_name)
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
                yield ('setNodeInput', node_name, input_name, value)
        yield ('completeNode', node_name)
