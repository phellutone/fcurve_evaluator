
# Copyright (c) 2021 phellutone
# Released under the MIT license
# https://opensource.org/licenses/mit-license


bl_info = {
    "name": "fcurve evaluator",
    "author": "phellutone",
    "version": (1, 1),
    "blender": (2, 93, 0),
    "location": "View3D > Sidebar > Tool Tab",
    "description": "property interpolation with fcurve",
    "support": "COMMUNITY",
    "tracker_url": "https://github.com/phellutone/fcurve_evaluator/issues",
    "category": "Object"
}


if "bpy" in locals():
    import imp
    imp.reload(FCurveWrapper)
    imp.reload(re)
else:
    from .fcurve_wrapper import FCurveWrapper
    import re

import bpy



class FCurveEvaluator(bpy.types.PropertyGroup):
    target: bpy.props.PointerProperty(type=FCurveWrapper)
    value: bpy.props.PointerProperty(type=FCurveWrapper)
    controller: bpy.props.FloatProperty(
        max=1.0,
        min=0.0
    )

    def update_bool(self, context):
        tf = self.target.fcurve()
        vf = self.value.fcurve()
        if tf and vf:
            tf.mute = not self.mute
            vf.mute = not self.mute
    mute: bpy.props.BoolProperty(
        default=True,
        update=update_bool
    )

    index: bpy.props.IntProperty()

    def update_name(self, context):
        self.target.name = self.name 
    name: bpy.props.StringProperty(
        update=update_name
    )

    def init(self):
        tf = self.target.fcurve()
        tf.select = True

        vf = self.value.fcurve()
        vf.select = False
        vf.hide = True
        vd = vf.driver

        if re.search('evaluate\(.+,.+,.+\)', vd.expression):
            for v in vd.variables:
                vd.variables.remove(v)

        id = vd.variables.new()
        id.name ="id"
        id.targets[0].id_type = 'SCENE'
        id.targets[0].id = self.target.ID
        id.targets[0].data_path = "original"

        anim_index = vd.variables.new()
        anim_index.name = "anim_index"
        anim_index.targets[0].id_type = 'SCENE'
        anim_index.targets[0].id = self.target.ID
        anim_index.targets[0].data_path = self.target.path_from_id("anim_index")

        controller = vd.variables.new()
        controller.name = "controller"
        controller.targets[0].id_type = 'SCENE'
        controller.targets[0].id = self.id_data
        controller.targets[0].data_path = self.path_from_id("controller")

        vd.expression = "evaluate(id, anim_index, controller)"

    def delete(self):
        self.target.remove_driver("data")
        self.value.remove_driver("data")

class FCurveEvaluator_OT_add(bpy.types.Operator):
    bl_idname = "fcurve_evaluator.add"
    bl_label = "add"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        fcurve_evaluator = scene.fcurve_evaluator
        if not "evaluate" in bpy.app.driver_namespace:
            bpy.app.driver_namespace["evaluate"] = lambda scene, anim_index, var: scene.animation_data.drivers[anim_index].evaluate(var)
        block = fcurve_evaluator.add()

        block.init()
        block.index = len(fcurve_evaluator)-1
        block.name = "Curve "+str(block.index+1)
        scene.active_fcurve_evaluator_index = block.index

        return {'FINISHED'}

class FCurveEvaluator_OT_remove(bpy.types.Operator):
    bl_idname = "fcurve_evaluator.remove"
    bl_label = "remove"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        fcurve_evaluator = scene.fcurve_evaluator
        index = scene.active_fcurve_evaluator_index
        if index < 0 or not fcurve_evaluator:
            return {'CANCELLED'}

        block = fcurve_evaluator[index]
        block.delete()
        fcurve_evaluator.remove(index)

        for b in fcurve_evaluator:
            if b.index < index:
                continue
            b.index = b.index-1
            b.init()
        
        scene.active_fcurve_evaluator_index = min(max(0, index-1), len(fcurve_evaluator)-1)
        
        return {'FINISHED'}

class FCurveEvaluator_UL_evaluator(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        block = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(block, "name", icon="ANIM", text="", emboss=False)
            row.prop(block, "mute", icon="CHECKBOX_HLT" if block.mute else "CHECKBOX_DEHLT", text="", emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = "CENTER"
            layout.label(text="", icon=icon)

class OBJECT_PT_FCurveEvaluator(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_idname = "VIEW3D_PT_fcurve_evaluator"
    bl_label = "FCurve Evaluator"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        scene = context.scene
        fcurve_evaluator = scene.fcurve_evaluator
        index = scene.active_fcurve_evaluator_index
        layout = self.layout
        
        row = layout.row()
        
        rows = 3
        if fcurve_evaluator:
            rows = 5
        row.template_list("FCurveEvaluator_UL_evaluator", "", scene, "fcurve_evaluator", scene, "active_fcurve_evaluator_index", rows=rows)
        
        col = row.column(align=True)
        col.operator("fcurve_evaluator.add", icon="ADD", text="")
        col.operator("fcurve_evaluator.remove", icon="REMOVE", text="")
        
        if fcurve_evaluator:
            block = fcurve_evaluator[index]
            
            fcurve = block.target.fcurve()
            if fcurve:
                if fcurve.data_path != block.target.path:
                    fcurve = None
            if fcurve:
                sub = layout.column()
                sub.label(text="data ("+block.target.name+")", icon="DOT")
                
                row = sub.row()
                row.prop(block, "controller", text="controller")
                row.operator("screen.drivers_editor_show", text="Show FCurve Editor")
                row.prop(block.value, "data", text="output")
            else:
                sub = layout.column()
                sub.label(text="recovoer index to access fcurve")

classes = (
    FCurveWrapper,
    FCurveEvaluator,
    FCurveEvaluator_OT_add,
    FCurveEvaluator_OT_remove,
    FCurveEvaluator_UL_evaluator,
    OBJECT_PT_FCurveEvaluator
)

def update_index(self, context):
    scene = self
    fcurve_evaluator = scene.fcurve_evaluator
    index = scene.active_fcurve_evaluator_index
    if index < 0 or not fcurve_evaluator:
        return
    for b in fcurve_evaluator:
        f = b.target.fcurve()
        if f:
            f.hide = not b.index == index
            f.select = b.index == index

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.fcurve_evaluator = bpy.props.CollectionProperty(type=FCurveEvaluator)
    bpy.types.Scene.active_fcurve_evaluator_index = bpy.props.IntProperty(update=update_index)
        
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.fcurve_evaluator
    del bpy.types.Scene.active_fcurve_evaluator_index

if __name__ == "__main__":
    register()
