import bpy
# from itertools import zip_longest

bl_info = {
    "name": "property interpolation",
    "author": "phellutone",
    "version": (0, 1),
    "blender": (2, 82, 0),
    "location": "View3D > Sidebar > Tool Tab",
    "description": "property interpolation with fcurve",
    "warning": "work in progress",
    "support": "TESTING",
    "category": "Object"
}

def path_disassembly(id, path):
    tmp = ""
    res = []
    sid = -1
    for i, s in enumerate(path):
        if sid != -1 and sid != i:
            continue
        sid = -1
        if s == "[":
            res.append(tmp)
            idx = path.find("]", i)
            tmp = path[i+1:idx].replace('"', "")
            sid = idx+1
        elif s == ".":
            res.append(tmp)
            tmp = ""
        else:
            tmp += s
    res.append(tmp)
    
    rna = id
    pres = [rna]
    for i, p in enumerate(res):
        if str.isdigit(p):
            rna = rna[int(p)]
            res[i] = '['+p+']'
        else:
            if hasattr(rna, p):
                rna = getattr(rna, p)
            elif p in rna.keys():
                rna = rna.get(p)
                res[i] = '["'+p+'"]'
        pres.append(rna)
    res.append(None)
    return (tuple(pres), tuple(res))

def path_observer(id, path):
    rna = None
    value = None
    anim_index = 0
    
    try:
        if not isinstance(id, bpy.types.ID):
            raise Exception("invalid id data")
        value = id.path_resolve(path)
        rna = path_disassembly(id, path)
        if value != rna[0][-1]:
            raise Exception("invalid rna path")
        
        p = None
        if hasattr(rna[0][-2], "bl_rna"):
            p = rna[0][-2].bl_rna.properties
            if rna[1][-2] in p.keys():
                p = p.get(rna[1][-2])
                anim_index = -2
        elif len(rna[0]) < 3:
            pass
        elif hasattr(rna[0][-3], "bl_rna"):
            p = rna[0][-3].bl_rna.properties
            if rna[1][-3] in p.keys():
                p = p.get(rna[1][-3])
                anim_index = -3
        
        if anim_index and isinstance(p, bpy.types.Property):
            if not p.is_animatable:
                anim_index = 0
    except Exception as e:
        return {"rna": None, "value": None, "anim_index": 0}
    return {"rna": rna, "value": value, "anim_index": anim_index}

def fcurve_index_observer(id, path, idx=None):
    if not hasattr(id, "animation_data"):
        return (False, "ID")
    if not id.animation_data:
        return (False, "ANIMATION_DATA")
    fix = [i for i, f in enumerate(id.animation_data.drivers) if f.data_path==path]
    if not fix:
        return (False, "FCURVE")
    if idx is None:
        return (True, fix[0])
    if fix[0] != idx:
        return (False, "INDEX")
    return (True, "")

def fcurve_add(id, path):
    f = id.driver_add(path)
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




class fprop(bpy.types.PropertyGroup):
    def update_bool(self, context):
        block = self
        fcurve = self.fcurve()
        if fcurve:
            fcurve.mute = not self.mute
    
    name: bpy.props.StringProperty()
    id: bpy.props.PointerProperty(type=bpy.types.ID)
    path: bpy.props.StringProperty()
    data: bpy.props.FloatProperty()
    index: bpy.props.IntProperty()
    anim_index: bpy.props.IntProperty()
    mute: bpy.props.BoolProperty(
        default=True,
        update=update_bool
    )
    
    def fcurve(self):
        if not hasattr(self.id, "animation_data"):
            return None
        anim_data = self.id.animation_data
        if not anim_data.drivers:
            return None
        fcurves = anim_data.drivers
        if self.anim_index >= len(fcurves):
            return None
        return fcurves[self.anim_index]
    
    def add_driver(self):
        state = path_observer(self.id, self.path)
        if not state["anim_index"]:
            return
        try:
            fcurve_add(self, "data").hide = True
            fix = fcurve_index_observer(self.id, self.path)
            if fix[0]:
                self.anim_index = fix[1]
            else:
                self.remove_driver()
        except Exception as e:
            print(e)
            self.remove_driver()
    
    def remove_driver(self):
        try:
            self.driver_remove("data")
        except Exception as e:
            print(e)
    
    def refresh(self):
        self.path = self.path_from_id("data")
        self.index = int(self.path_from_id()[-2])
    
    def rerouting_index(self):
        fix = fcurve_index_observer(self.id, self.path, self.anim_index)
        if fix[0]:
            return True
        elif fix[1] == "INDEX":
            fix = fcurve_index_observer(self.id, self.path)
            if fix[0]:
                self.anim_index = fix[1]
            return fix[0]
        else:
            return False
        
    def rerouting_path(self, path):
        fix = fcurve_index_observer(self.id, self.path)
        if fix[0]:
            self.id.animation_data.drivers[fix[1]].data_path = path
            self.path = path
        return fix[0]

class FPROP_OT_add(bpy.types.Operator):
    bl_idname = "fprop.add"
    bl_label = "add"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        fprop = scene.fprop
        block = fprop.add()
        
        block.name = "Curve "+str(len(fprop))
        block.id = scene
        block.path = block.path_from_id("data")
        block.index = int(block.path_from_id()[-2])
        block.add_driver()
        scene.active_fprop_index = len(fprop)-1
        
        return {'FINISHED'}

class FPROP_OT_remove(bpy.types.Operator):
    bl_idname = "fprop.remove"
    bl_label = "remove"
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        fprop = scene.fprop
        index = scene.active_fprop_index
        if index < 0 or not fprop:
            return {'CANCELLED'}
        
        block = fprop[index]
        
        block.remove_driver()
        
        for block in fprop:
            if block.index < index:
                continue
            block.index = block.index-1
            block.rerouting_path("fprop["+str(block.index)+"].data")
            block.rerouting_index()
        
        fprop.remove(index)
        scene.active_fprop_index = min(max(0, index-1), len(fprop)-1)
        
        return {'FINISHED'}



class FPROP_UL_fprop(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        block = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(block, "name", icon="ANIM", text="", emboss=False)
            row.prop(block, "mute", icon="CHECKBOX_HLT" if block.mute else "CHECKBOX_DEHLT", text="", emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = "CENTER"
            layout.label(text="", icon=icon)

class OBJECT_PT_fprop(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_idname = "VIEW3D_PT_fprop"
    bl_label = "Property Interpolation"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        scene = context.scene
        fprop = scene.fprop
        index = scene.active_fprop_index
        layout = self.layout
        
        row = layout.row()
        
        rows = 3
        if fprop:
            rows = 5
        row.template_list("FPROP_UL_fprop", "", scene, "fprop", scene, "active_fprop_index", rows=rows)
        
        col = row.column(align=True)
        col.operator("fprop.add", icon="ADD", text="")
        col.operator("fprop.remove", icon="REMOVE", text="")
        
        if fprop:
            block = fprop[index]
            
            fcurve = block.fcurve()
            if fcurve:
                if fcurve.data_path != block.path:
                    fcurve = None
            if fcurve:
                sub = layout.column()
                sub.label(text="data ("+block.name+")", icon="DOT")
                
                col = sub.column()
                col.enabled = False
                col.prop(fcurve, "data_path", text="", icon="RNA")
                col.prop(block, "anim_index", text="Fcurve Index")
                
                sub.label(text="Display Color:")
                
                row = sub.row(align=True)
                row.prop(fcurve, "color_mode", text="")
                rsb = row.row(align=True)
                rsb.enabled = fcurve.color_mode == "CUSTOM"
                rsb.prop(fcurve, "color", text="")
                
                sub.label(text="Auto Handle Smoothing:")
                sub.prop(fcurve, "auto_smoothing", text="")
            else:
                sub = layout.column()
                sub.label(text="recovoer index to access fcurve")
                block.rerouting_index()
                
                
                

classes = (
    fprop,
    FPROP_OT_add,
    FPROP_OT_remove,
    FPROP_UL_fprop,
    OBJECT_PT_fprop,
)

def update_index(self, context):
    scene = self
    fprop = scene.fprop
    index = scene.active_fprop_index
    if index < 0 or not fprop:
        return
    
    for block in fprop:
        fcurve = block.fcurve()
        if fcurve:
            block.fcurve().hide = not block.index == index
            block.fcurve().select = block.index == index

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.fprop = bpy.props.CollectionProperty(type=fprop)
    bpy.types.Scene.active_fprop_index = bpy.props.IntProperty(update=update_index)
    
    bpy.app.driver_namespace["evaluate"] = lambda scene, anim_index, var: scene.animation_data.drivers[anim_index].evaluate(var)
        
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
