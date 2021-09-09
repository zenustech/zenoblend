import bpy
import time
import gpu
from gpu_extras.batch import batch_for_shader

from .dll import core
from .polywire_shaders import vertex_shader, fragment_shader, geometry_shader, preprocessor


handler = None
shader = None
batch = None


def after_execute():
    line_pos = core.graphGetLineVertexBuffer(graphPtr)
    line_color = core.graphGetLineColorBuffer(graphPtr)
    line_indices = core.graphGetLineIndexBuffer(graphPtr)
   
    global handler
    if line_pos:
        global batch
        global shader
        if shader is None:
            shader = gpu.types.GPUShader(vertex_shader, fragment_shader, geocode=geometry_shader, defines=preprocessor)
        batch = batch_for_shader(shader, 'LINES', {"pos": line_pos, 'color': line_color}, indices=line_indices)
        if handler:
            bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
        handler = bpy.types.SpaceView3D.draw_handler_add(draw_handler, (), 'WINDOW', 'POST_VIEW')
        tag_redraw_all_3dviews()
    elif handler:
        clear_draw_handler()

    
def draw_handler():
    global shader
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


def tag_redraw_all_3dviews():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        region.tag_redraw()


@bpy.app.handlers.persistent
def clear_draw_handler(*unused):
    global handler
    if handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
        handler = None
        tag_redraw_all_3dviews()


def register():
    if clear_draw_handler not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(clear_draw_handler)


def unregister():
    if clear_draw_handler in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(clear_draw_handler)
