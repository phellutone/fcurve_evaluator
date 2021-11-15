import bpy

class FcurveWrapper(bpy.types.PropertyGroup):
    id: bpy.props.PointerProperty(type=bpy.types.ID)
    path: bpy.props.StringProperty()
    anim_index: bpy.props.FloaatProperty()
    
    def fcurve_path_observer(id: bpy.types.ID, path: str):
        if not hasattr(id, "animation_data"):
            return (False, "ID")
        if not id.animation_data:
            return (False, "ANIMATION_DATA")
        fixes = [i for i, f in enumerate(id.animation_data.drivers) if f.data_path==path]
        if not fixes:
            return (False, "PATH")
        if len(fixes) > 1:
            return (False, "DUPLICATE")
        return (True, fixes[0])

    def fcurve(self):
        res, fix = self.fcurve_path_observer(self.id, self.path)
        if not res:
            print(fix)
            return None
        
        fcurve = self.id.animation_data.drivers
        if self.anim_index >= len(fcurve):
            print()

        if fcurve[self.anim_index] != fcurve[fix]:
            print()
    
    def rerouting_fcurve(self, path: str):
        res, fix = self.fcurve_path_observer(self.id, self.path)
        if not fix == "PATH":
            print("path is not already exist")
            return

