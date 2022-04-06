import bpy
from bpy.types import Menu
from bpy.types import Operator
from bpy_extras import object_utils

from bpy.props import (
        FloatProperty,
        IntProperty,
        BoolProperty,
        StringProperty,
        FloatVectorProperty
        )


class ImportMsh(Operator,object_utils.AddObjectHelper):
    bl_idname = "import_scene.msh_import"
    bl_label = "Mesh-Gmsh MSH (*.msh)"

    bl_option = {'REGISTER', 'UNDO', 'PRESET'}

    name : StringProperty(name = "Name",
                    description = "Name")

    def draw(self,context):
        layout = self.layout
        box = layout.box()
        box.prop(self,'name')

    @classmethod
    def poll(cls,context):
        return context.scene is not None
    
    def execute(self,context):
        print("IMPORT MESH")
    
    def invoke(self,context,event):
        self.execute(context)

        return {'FINISHED'}



def extra_import_func(self,context):
    layout = self.layout
    layout.operator_context = "INVOKE_REGION_WIN"

    layout.separator()
    oper = layout.operator("import_scene.msh_import")

classes = [
    ImportMsh,
]

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(extra_import_func)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(extra_import_func)

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)