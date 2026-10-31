"""Deterministic mesh components; importing this package never needs bpy."""
from .geometry import CutawayProfile, FlattenedCisterna, MeshData, sphere, validate_mesh
from .shapes import circle_outline, cylinder, extruded_outline, refined_plate, rounded_box, rounded_rect_outline
from .blender import material, mesh_object

__all__ = ["CutawayProfile", "FlattenedCisterna", "MeshData", "sphere",
           "validate_mesh", "material", "mesh_object", "rounded_rect_outline",
           "circle_outline", "extruded_outline", "refined_plate", "rounded_box", "cylinder"]
