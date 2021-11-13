import bpy

class FcurveWrapper(bpy.types.PropertyGroup):
    id: bpy.props.PointerProperty(type=bpy.types.ID)
    path: bpy.props.StringProperty()
    anim_index: bpy.props.FloaatProperty()
    
    def fcurve_index_observer(self):
        if not hasattr(self.id, "animation_data"):
            return (False, "ID")
        if not self.id.animation_data:
            return (False, "ANIMATION_DATA")
        fix = [i for i, f in enumerate(self.id.animation_data.drivers) if f.data_path==self.path]
        if not fix:
            return (False, "FCURVE")
        return (True, fix[0])

    def fcurve(self):
        res, fix = self.fcurve_index_observer()
