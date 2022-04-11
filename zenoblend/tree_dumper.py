import bpy


def dump_tree(tree):
    assert tree.bl_idname == 'ZenoNodeTree', tree
    for node_name, node in tree.nodes.items():
        if not hasattr(node, 'zeno_type'): continue
        node_type = node.zeno_type
        yield ('addNode', node_type, node_name)

        # thank @hooyuser for contribute!
        print('node_name = {}'.format(node_name))
        if hasattr(node, 'bpy_data_inputs'):
            for input_name, data_type in node.bpy_data_inputs.items():

                data_blocks = getattr(bpy.data, data_type)
                data_block_name = getattr(node, input_name)

                if hasattr(node,'selected_input_obj'):
                    print("selected_input_obj : {}".format(bpy.context.selected_objects[0].name))
                    data_block_name = bpy.context.selected_objects[0].name

                # print("{} -> {} -> {}".format(input_name,data_type,data_block_name))
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
    'collections': lambda data: data.name,
    'armatures': lambda data: data.name,
}
