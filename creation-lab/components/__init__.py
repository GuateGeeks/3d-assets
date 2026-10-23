"""Deterministic mesh components; importing this package never needs bpy."""
from .geometry import CutawayProfile, FlattenedCisterna, MeshData, sphere, validate_mesh
from .blender import material, mesh_object

__all__ = ["CutawayProfile", "FlattenedCisterna", "MeshData", "sphere",
           "validate_mesh", "material", "mesh_object"]
