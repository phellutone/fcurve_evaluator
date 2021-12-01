from typing import Union
from enum import Enum
import bpy

class FCurveWrapper(bpy.types.PropertyGroup):
    class FCurveErrEnum(Enum):
        ID = "ID"
        ANIMATION_DATA = "ANIMATION_DATA"
        PATH = "PATH"
        DUPLICATE = "DUPLICATE"
    class WrapperErrEnum(Enum):
        ID = "ID"
        PATH = "PATH"

    # bpy.types.Scene
    ID: bpy.props.PointerProperty(type=bpy.types.ID)

    # property that has fcurve
    data: bpy.props.FloatProperty()

    # path to FCurveWrapper.data from FCurveWrapper.ID
    path: bpy.props.StringProperty(
        default="undefined"
    )

    # index number of FCurveWrapper.ID.animation_data.drivers
    anim_index: bpy.props.IntProperty(
        default=-1
    )

    name: bpy.props.StringProperty()
    
    def wrapper_path_observer(self) -> Union[tuple[False, WrapperErrEnum], tuple[True, None]]:
        if self.ID != self.id_data:
            return (False, FCurveWrapper.WrapperErrEnum.ID)
        if self.path != self.path_from_id("data"):
            return (False, FCurveWrapper.WrapperErrEnum.PATH)
        return (True, None)

    def wrapper_path_resolver(self) -> None:
        wres, wrsn = self.wrapper_path_observer()
        if not wres:
            if wrsn == FCurveWrapper.WrapperErrEnum.ID:
                self.ID = self.id_data
                _, wrsn = self.wrapper_path_observer()
            if wrsn == FCurveWrapper.WrapperErrEnum.PATH:
                fres, _ = self.fcurve_path_observer(self.ID, self.path)
                if fres:
                    self.rerouting_fcurve(self.path, self.path_from_id("data"))
                self.path = self.path_from_id("data")

    def fcurve_path_observer(self, ID: bpy.types.ID, path: str) -> Union[tuple[False, FCurveErrEnum], tuple[True, int]]:
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
                frsn = FCurveWrapper.FCurveErrEnum.PATH
            if frsn == FCurveWrapper.FCurveErrEnum.PATH:
                self.add_driver("data")
                _, frsn = self.fcurve_path_observer(self.ID, self.path)
            if frsn == FCurveWrapper.FCurveErrEnum.DUPLICATE:
                raise Exception("duplicate fcurve data path")
        self.anim_index = frsn

    def add_driver(self, path: str) -> bpy.types.FCurve:
        try:
            f: bpy.types.FCurve = self.driver_add(path)
            f.keyframe_points.add(2)
            f.modifiers.remove(f.modifiers[0])
            for i in range(2):
                p: bpy.types.Keyframe = f.keyframe_points[i]
                p.co = [float(i), float(i)]
                p.handle_left = [i-0.2, i-0.2]
                p.handle_right = [i+0.2, i+0.2]
            fd: bpy.types.Driver = f.driver
            fd.type = "SCRIPTED"
            fd.expression = "1.0"
            return f
        except Exception as e:
            print(e)
            self.remove_driver(path)
            raise Exception("couldn't add driver")
    
    def remove_driver(self, path: str) -> None:
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
        f: bpy.types.FCurve = self.ID.animation_data.drivers[orsn]
        f.data_path = new_path
