from typing import List, Type, Union
from enum import IntEnum, auto
import bpy


class FCurveWrapper(bpy.types.PropertyGroup):
    class FCurveErrEnum(IntEnum):
        ID = auto()
        ANIMATION_DATA = auto()
        PATH = auto()
        DUPLICATE = auto()
    class WrapperErrEnum(IntEnum):
        ID = auto()
        PATH = auto()

    # bpy.types.Scene
    ID: bpy.props.PointerProperty(type=bpy.types.ID)

    # property that has fcurve
    data: bpy.props.FloatProperty()

    # path to FCurveWrapper.data from FCurveWrapper.ID
    path: bpy.props.StringProperty()

    # index number of FCurveWrapper.ID.animation_data.drivers
    anim_index: bpy.props.FloatProperty()
    
    def wrapper_path_observer(self) -> Union[tuple[False, WrapperErrEnum], tuple[True, str]]:
        if self.ID != self.id_data:
            return (False, FCurveWrapper.WrapperErrEnum.ID)
        if self.path != self.path_from_id("data"):
            return (False, FCurveWrapper.WrapperErrEnum.PATH)
        return (True, "")

    def wrapper_path_resolver(self) -> None:
        wres, wrsn = self.wrapper_path_observer()
        if not wres:
            if wrsn == FCurveWrapper.WrapperErrEnum.ID:
                self.ID = self.id_data
                _, wrsn = self.wrapper_path_observer()
            if wrsn == FCurveWrapper.WrapperErrEnum.PATH:
                fres, frsn = self.fcurve_path_observer(self.ID, self.path)
                if fres:
                    self.rerouting_fcurve(self.path, self.path_from_id("data"))
                self.path = self.path_from_id("data")

    def fcurve_path_observer(ID: bpy.types.ID, path: str) -> Union[tuple[False, FCurveErrEnum], tuple[True, int]]:
        if not hasattr(ID, "animation_data"):
            return (False, FCurveWrapper.FCurveErrEnum.ID)
        if not ID.animation_data:
            return (False, FCurveWrapper.FCurveErrEnum.ANIMATION_DATA)
        fixes = [i for i, f in enumerate(ID.animation_data.drivers) if f.data_path==path]
        if not fixes:
            return (False, FCurveWrapper.FCurveErrEnum.PATH)
        if len(fixes) > 1:
            return (False, FCurveWrapper.FCurveErrEnum.DUPLICATE)
        return (True, fixes[0])
    
    def fcurve_path_resolver(self) -> None:
        self.wrapper_path_resolver()
        fres, frsn = self.fcurve_path_observer(self.ID, self.path)
        if not fres:
            if frsn == FCurveWrapper.FCurveErrEnum.ID:
                raise Exception("invalid ID data-block")
            if frsn == FCurveWrapper.FCurveErrEnum.ANIMATION_DATA:
                self.ID.animation_data_create()
                frsn == FCurveWrapper.FCurveErrEnum.PATH
            if frsn == FCurveWrapper.FCurveErrEnum.PATH:
                self.add_driver("data")
                _, frsn = self.fcurve_path_observer(self.ID, self.path)
            if frsn == FCurveWrapper.FCurveErrEnum.DUPLICATE:
                raise Exception("duplicate fcurve data path")
        self.anim_index = frsn

    def add_driver(self, path: str) -> bpy.types.FCurve:
        try:
            f = self.driver_add(path)
            f.keyframe_points.add(2)
            f.modifiers.remove(f.modifiers[0])
            for i in range(2):
                p = f.keyframe_points[i]
                p.co = [float(i), float(i)]
                p.handle_left = [i-0.2, i-0.2]
                p.handle_right = [i+0.2, i+0.2]
            fd = f.driver
            fd.type = "SCRIPTED"
            fd.expression = "1.0"
            return f
        except Exception as e:
            print(e)
            self.remove_driver(path)
            raise Exception("couldn't add driver")
    
    def remove_driver(self, path: str):
        try:
            self.driver_remove(path)
        except Exception as e:
            print(e)

    def init(self):
        self.fcurve_path_resolver()
        return self

    def fcurve(self) -> bpy.types.FCurve:
        self.fcurve_path_resolver()
        return self.ID.animation_data.drivers[self.anim_index]
    
    def rerouting_fcurve(self, old_path: str, new_path: str) -> None:
        nres, nrsn = self.fcurve_path_observer(self.ID, new_path)
        if nres or nrsn != FCurveWrapper.FCurveErrEnum.PATH:
            raise Exception("new path is already exist")
        ores, orsn = self.fcurve_path_observer(self.ID, old_path)
        if not ores:
            raise Exception("old path is not found")
        f = self.ID.animation_data.drivers[orsn]
        f.data_path = new_path

class FCurveEvaluator(bpy.types.PropertyGroup):
    target: FCurveWrapper#bpy.props.PointerProperty(type=FCurveWrapper)
    value: FCurveWrapper#bpy.props.PointerProperty(type=FCurveWrapper)
    controller: bpy.props.FloatProperty()

    def update_bool(self, context):
        f = self.target.fcurve()
        if f:
            f.mute = not self.mute
    mute: bpy.props.BoolProperty(
        default=True,
        update=update_bool
    )

    index: bpy.props.IntProperty()

    def init(self):
        tf = self.target.fcurve().mute
        tf.mute = True

        vf = self.value.fcurve().mute
        vf.mute = True
        vd = vf.driver

        id = vf.variables.new()
        id.name ="id"
        id.targets[0].id = self.target.ID
        id.targets[0].data_path = "original"

        anim_index = vf.variables.new()
        anim_index.name = "anim_index"
        anim_index.targets[0].id = self.target.ID
        anim_index.targets[0].data_path = self.target.path_from_id("anim_index")

        controller = vf.variables.new()
        controller.name = "controller"
        controller.targets[0].id = self.id_data
        controller.targets[0].data_path = self.path_from_id("controller")

        vd.expression = "evaluate(id, anim_index, controller)"

    def delete(self):
        self.target.remove_driver("data")
        self.value.remove_driver("data")
        self.init()

class FCurveEvaluator_OT_add(bpy.types.Operator):
    bl_idname = "fcurve_evaluator.add"
    bl_label = "add"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene: bpy.types.Scene = context.scene
        fcurve_evaluator: List[FCurveEvaluator] = scene.fcurve_evaluator
        block: FCurveEvaluator = fcurve_evaluator.add()

        block.init()
        scene.active_fcurve_evaluator_index = len(fcurve_evaluator)-1

        return {'FINISHED'}

class FCurveEvaluator_OT_remove(bpy.types.Operator):
    bl_idname = "fcurve_evaluator.remove"
    bl_label = "remove"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        fcurve_evaluator: List[FCurveEvaluator] = scene.fcurve_evaluator
        index: int = scene.active_fcurve_evaluator_index
        if index < 0 or not fcurve_evaluator:
            return {'CANCELLED'}

        block: FCurveEvaluator = fcurve_evaluator[index]
        block.delete()
        block.remove(index)
        scene.active_fcurve_evaluator_index = min(max(0, index-1), len(fcurve_evaluator)-1)

        for b in fcurve_evaluator:
            if b.index < index:
                continue
            b.index = b.index-1
            b.init()
        
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
    bl_label = "Property Interpolation"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        scene = context.scene
        fcurve_evaluator: List[FCurveEvaluator] = scene.fprop
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
            block = fcurve_evaluator[index].target
            
            fcurve = block.fcurve()
            if fcurve:
                if fcurve.data_path != block.path:
                    fcurve = None
            if fcurve:
                sub = layout.column()
                sub.label(text="data ("+block.name+")", icon="DOT")
                
                col = sub.column()
                col.use_property_split = True
                col.use_property_decorate = False
                col.operator("screen.drivers_editor_show", text="Show FCurve Editor")
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
    fcurve_evaluator: List[FCurveEvaluator] = scene.fcurve_evaluator
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
    
    bpy.app.driver_namespace["evaluate"] = lambda scene, anim_index, var: scene.animation_data.drivers[anim_index].evaluate(var)
        
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
