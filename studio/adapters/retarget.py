"""Explicit Mixamo naming profile; rest orientations must match before transfer."""
import math

MIXAMO_TO_HUMANOID = {'mixamorig:Hips':'hips','mixamorig:Spine':'spine','mixamorig:Spine1':'chest','mixamorig:Spine2':'upper_chest','mixamorig:LeftShoulder':'clavicle.L','mixamorig:RightShoulder':'clavicle.R','mixamorig:Neck':'neck','mixamorig:Head':'head','mixamorig:LeftArm':'upper_arm.L','mixamorig:LeftForeArm':'forearm.L','mixamorig:LeftHand':'hand.L','mixamorig:RightArm':'upper_arm.R','mixamorig:RightForeArm':'forearm.R','mixamorig:RightHand':'hand.R','mixamorig:LeftUpLeg':'thigh.L','mixamorig:LeftLeg':'shin.L','mixamorig:LeftFoot':'foot.L','mixamorig:RightUpLeg':'thigh.R','mixamorig:RightLeg':'shin.R','mixamorig:RightFoot':'foot.R'}

def convert_vector(vector, source, target):
    if source not in ('Y_UP','Z_UP') or target not in ('Y_UP','Z_UP'):
        raise ValueError('Explicit Y_UP or Z_UP axes required')
    if len(vector)!=3 or not all(isinstance(x,(float,int)) and math.isfinite(x) for x in vector):
        raise ValueError('Finite three-component vector required')
    x,y,z=vector
    if source==target: return list(vector)
    return [x,z,-y] if source=='Z_UP' else [x,-z,y]

def validate_mapping(mapping, source_bones, target_bones):
    if not isinstance(mapping,dict) or not mapping or not all(isinstance(k,str) and isinstance(v,str) and k and v for k,v in mapping.items()):
        raise ValueError('Nonempty source-to-target bone mapping required')
    if len(set(mapping.values()))!=len(mapping): raise ValueError('Duplicate target bones')
    if set(mapping)-set(source_bones) or set(mapping.values())-set(target_bones): raise ValueError('Mapping references absent bones')
    return mapping
