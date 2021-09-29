# all code below is contributed by @hooyuser:

import bpy
import time
import gpu
from gpu_extras.batch import batch_for_shader

from .dll import core
from .polywire_shaders import vertex_shader, fragment_shader, geometry_shader, preprocessor
from .scenario import get_enabled_trees

shader = None

def draw_graph(graph_name, graphPtr):
    nodetree = bpy.data.node_groups[graph_name]
    line_pos = core.graphGetDrawLineVertexBuffer(graphPtr)
    line_color = core.graphGetDrawLineColorBuffer(graphPtr)
    line_indices = core.graphGetDrawLineIndexBuffer(graphPtr)
   
    if line_pos:
        global shader
        if shader is None:
            shader = gpu.types.GPUShader(vertex_shader, fragment_shader, geocode=geometry_shader, defines=preprocessor)
        
        nodetree.batch = batch_for_shader(shader, 'LINES', {"pos": line_pos, 'color': line_color}, indices=line_indices)
        if getattr(nodetree, 'draw_handler', None):
            bpy.types.SpaceView3D.draw_handler_remove(nodetree.draw_handler, 'WINDOW')
        nodetree.draw_handler = bpy.types.SpaceView3D.draw_handler_add(gen_draw_handler(nodetree.batch), (), 'WINDOW', 'POST_VIEW')
        tag_redraw_all_3dviews()
    elif getattr(nodetree, 'draw_handler', None):
        clear_draw_handler(nodetree)

    
def gen_draw_handler(batch):
    def draw_handler():
        shader.bind()
        matrix = bpy.context.region_data.perspective_matrix
        shader.uniform_float("ModelViewProjectionMatrix", matrix)
        shader.uniform_float("lineWidth", 1.2)
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for r in area.regions:
                    if r.type == 'WINDOW':
                        shader.uniform_float("viewportSize", (r.width, r.height)) 
                        break
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.depth_mask_set(True)
        gpu.state.blend_set("ALPHA")
        batch.draw(shader)
        gpu.state.depth_mask_set(False)
    return draw_handler

def tag_redraw_all_3dviews():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        region.tag_redraw()


def clear_draw_handler(nodetree):
    if getattr(nodetree, 'draw_handler', None):
        bpy.types.SpaceView3D.draw_handler_remove(nodetree.draw_handler, 'WINDOW')
        nodetree.draw_handler = None
        tag_redraw_all_3dviews()

@bpy.app.handlers.persistent
def clear_draw_handlers(*unused):
    for tree in get_enabled_trees():
        if hasattr(tree, 'draw_handler'):
            clear_draw_handler(tree)


def register():
    if clear_draw_handler not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(clear_draw_handlers)


def unregister():
    if clear_draw_handler in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(clear_draw_handlers)
