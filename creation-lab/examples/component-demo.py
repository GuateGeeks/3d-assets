"""Separated component blockout; no final cell and no biological approval.

Call build() with the iteration runner. This generator does not save files,
export, render, clear user scenes or choose a production asset budget.
"""
import math
from components import CutawayProfile, FlattenedCisterna, material, mesh_object, sphere


def build():
    shell_mat = material('Demo · shell', (0.045, 0.32, 0.34))
    fill_mat = material('Demo · contained fill', (0.63, 0.79, 0.69), roughness=0.65)
    sheet_mat = material('Demo · flattened sheet', (0.13, 0.38, 0.66))
    bead_mat = material('Demo · anchors', (0.035, 0.075, 0.13))
    sphere_mat = material('Demo · single-pole sphere', (0.88, 0.43, 0.14))

    # The largest dimension is 0.30 m; scale is a blockout convention.
    profile = CutawayProfile(radii=(0.075, 0.063, 0.052), center=(-0.075, 0, 0.002),
                             cut_fraction=0.10, wall_fraction=0.09)
    shell_mesh = profile.shell(segments=32, rings=12)
    mesh_object('continuous lip', 'shell', shell_mesh, shell_mat, smooth=False)
    mesh_object('contained solid', 'contained_fill',
                profile.fill(clearance=0.03, inset=0.09, segments=32, rings=12), fill_mat,
                smooth=False)
    sheet = FlattenedCisterna(radii=(0.060, 0.041, 0.005), wave=0.004,
                              center=(0.070, 0.017, 0.006))
    mesh_object('wavy sheet', 'cisterna', sheet.mesh(segments=32, rings=16), sheet_mat)
    # Grid-aligned anchors touch the very same authored mesh vertices.
    bead_radius = 0.0022
    for j in (3, 5, 7):
        for i in (2, 8, 14, 20, 26):
            center, _normal = sheet.anchor(math.pi*j/16, math.tau*i/32, offset=bead_radius)
            mesh_object(f'surface anchor {j}-{i}', 'anchors',
                        sphere((bead_radius,)*3, center=center, segments=10, rings=6), bead_mat)
    # A cut profile's latitude grid need not hit its analytic equator. Fit the
    # requested dimension to actual vertices rather than assuming an ideal bbox.
    sphere_center = (min(v[0] for v in shell_mesh.vertices)+0.30-0.020, -0.060, -0.030)
    mesh_object('pole regression', 'sphere',
                sphere((0.020, 0.020, 0.020), center=sphere_center,
                       segments=24, rings=12), sphere_mat)

    return {
        'title': 'Componentes geométricos · blockout de prueba',
        'design_notes': [
            'Demostración de componentes separados. No es una célula final ni biología aprobada.',
            'Envoltura con labio continuo y relleno contraído dentro del mismo perfil facetado.',
            'Cisterna estilizada aplanada; anclajes muestreados sobre su misma superficie.',
            'Esfera con polos únicos. Convención de maqueta: dimensión X de 0.30 m.',
        ],
        'parts': {
            'shell': {'label_position': [-0.14, 0, 0.0072]},
            'contained_fill': {'label_position': [-0.075, 0, 0.00252]},
            'cisterna': {'label_position': [0.07, 0.017, 0.011]},
            'anchors': {'label_position': [0.07, 0.017, 0.016]},
            'sphere': {'label_position': [sphere_center[0], -0.06, -0.01]},
        },
    }
