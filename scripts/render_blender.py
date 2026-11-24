"""Render the board and its box with Blender's Cycles, so the jacks, pins and pads look like metal.

Run with: python scripts/render_blender.py BOARD_GLB ENCLOSURE_DIR OUT_DIR [VIEW...]
"""

import colorsys
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

GLB, BOX, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
BOARD_TOP = 0.001595
CENTER = Vector((0.042, -0.025, BOARD_TOP + 0.004))
WIDTH, HEIGHT, SAMPLES = 1800, 1150, 96
FILL_WIDTH, FILL_HEIGHT = 0.93, 0.83
# view: (azimuth, elevation, box parts and how far each is lifted in meters)
VIEWS = {
    "board-3d": (-128, 30, {}),
    "board-3d-top": (-96, 62, {}),
    "board-3d-bottom": (-96, -62, {}),
    "enclosure-open": (-118, 30, {"base": 0.0, "lid": 0.034}),
    "enclosure-closed": (-128, 28, {"base": 0.0, "lid": 0.0}),
    "enclosure-usb": (-72, 26, {"base": 0.0, "lid": 0.0}),
}


def shade(material, color, metallic, roughness, alpha=1.0, coat=0.0):
    bsdf = material.node_tree.nodes["Principled BSDF"]
    for name, value in (
        ("Base Color", (*color, 1.0)),
        ("Metallic", metallic),
        ("Roughness", roughness),
        ("Alpha", alpha),
        ("Coat Weight", coat),
    ):
        for link in list(bsdf.inputs[name].links):
            material.node_tree.links.remove(link)
        bsdf.inputs[name].default_value = value


def restyle(material):
    """Swap KiCad's flat colors for physical materials."""
    bsdf = material.node_tree.nodes["Principled BSDF"]
    r, g, b, _ = bsdf.inputs["Base Color"].default_value
    alpha = bsdf.inputs["Alpha"].default_value
    hue, saturation, value = colorsys.rgb_to_hsv(r, g, b)
    if alpha < 0.85:
        shade(material, (0.004, 0.075, 0.032), 0.0, 0.5, 0.9, 0.15)
    elif alpha < 0.95:
        shade(material, (0.9, 0.9, 0.9), 0.0, 0.7)
    elif (round(r, 2), round(g, 2), round(b, 2)) == (0.5, 0.5, 0.5):
        shade(material, (0.83, 0.82, 0.79), 1.0, 0.35)
    elif saturation > 0.6 and 0.05 < hue < 0.2 and value > 0.4:
        shade(material, (1.0, 0.72, 0.28), 1.0, 0.22)
    elif saturation < 0.15 and value > 0.4:
        shade(material, (0.86, 0.87, 0.89), 1.0, 0.2)
    elif saturation < 0.05 and 0.1 < value < 0.2:
        shade(material, (0.62, 0.62, 0.63), 1.0, 0.38)
    elif value < 0.05:
        shade(material, (0.012, 0.012, 0.013), 0.0, 0.42)
    else:
        shade(material, (r, g, b), 0.0, 0.45)


def area(location, size, energy):
    light = bpy.data.lights.new("softbox", "AREA")
    light.size, light.energy = size, energy
    lamp = bpy.data.objects.new("softbox", light)
    lamp.location = CENTER + Vector(location)
    lamp.rotation_euler = (CENTER - lamp.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(lamp)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for material in bpy.data.materials:
    restyle(material)
board = [o for o in bpy.data.objects if o.type == "MESH"]

nylon = bpy.data.materials.new("nylon")
nylon.use_nodes = True
shade(nylon, (0.045, 0.046, 0.05), 0.0, 0.62)
box = {}
for name in ("base", "lid"):
    bpy.ops.wm.stl_import(filepath=str(BOX / f"{name}.stl"), global_scale=0.001)
    part = bpy.context.selected_objects[0]
    part.data.materials.clear()
    part.data.materials.append(nylon)
    bevel = part.modifiers.new("edge", "BEVEL")
    bevel.width, bevel.segments, bevel.limit_method = 0.0003, 3, "ANGLE"
    box[name] = part

floor_mesh = bpy.data.meshes.new("floor")
floor_mesh.from_pydata([(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)], [], [(0, 1, 2, 3)])
floor = bpy.data.objects.new("floor", floor_mesh)
floor.is_shadow_catcher = True
bpy.context.collection.objects.link(floor)

world = bpy.data.worlds.new("studio")
world.use_nodes = True
nodes, links = world.node_tree.nodes, world.node_tree.links
coordinates, split = nodes.new("ShaderNodeTexCoord"), nodes.new("ShaderNodeSeparateXYZ")
ramp = nodes.new("ShaderNodeValToRGB")
for position, level in ((0.0, 0.08), (0.46, 0.16), (0.5, 0.9), (0.62, 0.35), (1.0, 0.75)):
    stop = ramp.color_ramp.elements.new(position)
    stop.color = (level, level, level * 1.03, 1.0)
scale = nodes.new("ShaderNodeMapRange")
scale.inputs["From Min"].default_value = -1.0
links.new(coordinates.outputs["Generated"], split.inputs[0])
links.new(split.outputs["Z"], scale.inputs["Value"])
links.new(scale.outputs["Result"], ramp.inputs["Fac"])
links.new(ramp.outputs["Color"], nodes["Background"].inputs["Color"])
nodes["Background"].inputs["Strength"].default_value = 0.55
area((-0.22, -0.16, 0.3), 0.2, 1.5)
area((0.28, -0.2, 0.2), 0.12, 1.5)
area((0.02, 0.3, 0.22), 0.25, 1.3)

scene = bpy.context.scene
scene.world = world
scene.render.engine = "CYCLES"
scene.cycles.samples, scene.cycles.use_denoising = SAMPLES, True
scene.render.film_transparent = True
scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
lens = bpy.data.cameras.new("camera")
lens.lens, lens.clip_start, lens.clip_end = 70, 0.001, 10
camera = bpy.data.objects.new("camera", lens)
bpy.context.collection.objects.link(camera)
scene.camera = camera

for view in sys.argv[4:] or VIEWS:
    azimuth, elevation, parts = VIEWS[view]
    for name, part in box.items():
        part.hide_render = name not in parts
        part.location = (0, 0, BOARD_TOP + parts.get(name, 0.0))
    below = elevation < 0
    for lamp in (o for o in bpy.data.objects if o.type == "LIGHT"):
        offset = lamp.location - CENTER
        lamp.location = CENTER + Vector((offset.x, offset.y, -abs(offset.z) if below else abs(offset.z)))
        lamp.rotation_euler = (CENTER - lamp.location).to_track_quat("-Z", "Y").to_euler()
    floor.hide_render = below
    shown = board + [box[name] for name in parts]
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ Vector(c) for o in shown for c in o.bound_box]
    floor.location = (0, 0, min(c.z for c in corners))
    a, e = math.radians(azimuth), math.radians(elevation)
    direction = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    fitted, _ = camera.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), [v for c in corners for v in c])
    camera.location = fitted + direction * 0.03
    lens.lens, lens.shift_x, lens.shift_y = 70, 0.0, 0.0
    for _ in range(3):
        bpy.context.view_layer.update()
        points = [
            world_to_camera_view(scene, camera, o.matrix_world @ v.co)
            for o in shown
            for v in list(o.data.vertices)[:: max(1, len(o.data.vertices) // 400)]
        ]
        (left, right), (low, high) = ((min(axis), max(axis)) for axis in zip(*((q.x, q.y) for q in points)))
        lens.shift_x += (left + right) / 2 - 0.5
        lens.shift_y += ((low + high) / 2 - 0.5) * HEIGHT / WIDTH
        lens.lens *= min(FILL_WIDTH / (right - left), FILL_HEIGHT / (high - low))
    scene.render.filepath = str(OUT / f"{view}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", view)
