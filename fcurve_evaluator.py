from typing import Type, Union
from enum import IntEnum, auto
import bpy


class FCurveWrapper(bpy.types.PropertyGroup):
    class FCurveWrapperErrEnum(IntEnum):
        ID = 0
        ANIMATION_DATA = 1
        PATH = 2
        DUPLICATE = 3

    # bpy.types.Scene
    ID: bpy.props.PointerProperty(type=bpy.types.ID)

    # property that has fcurve
    data: bpy.props.FloatProperty()

    # path to FCurveWrapper.data from FCurveWrapper.ID
    path: bpy.props.StringProperty()

    # index number of FCurveWrapper.ID.animation_data.drivers
    anim_index: bpy.props.FloaatProperty()
    
    def fcurve_path_observer(ID: bpy.types.ID, path: str):
        if not hasattr(ID, "animation_data"):
            return (False, FCurveWrapper.FCurveWrapperErrEnum.ID)
        if not ID.animation_data:
            return (False, FCurveWrapper.FCurveWrapperErrEnum.ANIMATION_DATA)
        fixes = [i for i, f in enumerate(ID.animation_data.drivers) if f.data_path==path]
        if not fixes:
            return (False, FCurveWrapper.FCurveWrapperErrEnum.PATH)
        if len(fixes) > 1:
            return (False, FCurveWrapper.FCurveWrapperErrEnum.DUPLICATE)
        return (True, fixes[0])

    def add_driver(self, path) -> bpy.types.FCurve:
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
    
    def remove_driver(self, path):
        try:
            self.driver_remove(path)
        except Exception as e:
            print(e)

    def init(self):
        self.ID = self.id_data
        self.path = self.path_from_id("data")
        res, fix = self.fcurve_path_observer(self.ID, self.path)
        if not res:
            if fix == FCurveWrapper.FCurveWrapperErrEnum.ID:
                raise Exception("invalid ID data-block")
            if fix == FCurveWrapper.FCurveWrapperErrEnum.ANIMATION_DATA:
                self.ID.animation_data_create()
            if fix == FCurveWrapper.FCurveWrapperErrEnum.PATH or fix == FCurveWrapper.FCurveWrapperErrEnum.ANIMATION_DATA:
                self.add_driver("data")
                _, fix = self.fcurve_path_observer(self.ID, self.path)
            if fix == FCurveWrapper.FCurveWrapperErrEnum.DUPLICATE:
                raise Exception("duplicate fcurve data path")
        self.anim_index = fix
        return self

    def fcurve(self) -> bpy.types.FCurve:
        res, fix = self.fcurve_path_observer(self.ID, self.path)
        if not res:
            self.init()
        elif self.anim_index != fix:
            self.anim_index = fix
        return self.ID.animation_data.drivers[self.anim_index]
    
    def rerouting_fcurve(self, path: str):
        res, fix = self.fcurve_path_observer(self.ID, self.path)
        if not fix == "PATH":
            print("path is not already exist")
            return

