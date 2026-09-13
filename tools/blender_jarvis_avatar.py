import math
from pathlib import Path
import bpy
from mathutils import Vector


def _wipe():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _mat(name, color, emit=6.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = emit
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def _sphere(name, loc, scale, mat, segs=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return obj


def _cyl(name, loc, scale, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def build():
    _wipe()
    cyan = _mat("JarvisCyan", (0.25, 0.72, 1.0), 8.0)
    core = _mat("JarvisCore", (0.9, 0.98, 1.0), 14.0)
    dark = _mat("JarvisDark", (0.05, 0.25, 0.5), 2.4)
    parts = []
    parts.append(_sphere("Head", (0, 0, 1.68), (0.13, 0.12, 0.15), cyan, 24))
    parts.append(_sphere("Visor", (0, -0.07, 1.70), (0.10, 0.04, 0.05), core, 16))
    parts.append(_cyl("Neck", (0, 0, 1.50), (0.04, 0.04, 0.06), dark))
    chest = _sphere("Chest", (0, 0, 1.22), (0.22, 0.13, 0.24), cyan, 20)
    parts.append(chest)
    parts.append(_sphere("Core", (0, -0.12, 1.22), (0.05, 0.04, 0.05), core, 16))
    parts.append(_sphere("Pelvis", (0, 0, 0.88), (0.16, 0.10, 0.10), dark, 16))
    for sx, side in ((1, "L"), (-1, "R")):
        parts.append(_sphere(f"Shoulder_{side}", (0.26 * sx, 0, 1.38), (0.06, 0.06, 0.06), cyan, 12))
        parts.append(_cyl(f"UpperArm_{side}", (0.38 * sx, 0, 1.18), (0.035, 0.035, 0.16), cyan, (0, 0.4 * sx, 0)))
        parts.append(_cyl(f"Forearm_{side}", (0.48 * sx, 0, 0.90), (0.03, 0.03, 0.14), dark, (0, 0.2 * sx, 0)))
        parts.append(_sphere(f"Hand_{side}", (0.54 * sx, 0, 0.74), (0.045, 0.035, 0.05), core, 12))
        parts.append(_cyl(f"Thigh_{side}", (0.08 * sx, 0, 0.62), (0.05, 0.05, 0.18), cyan))
        parts.append(_cyl(f"Calf_{side}", (0.08 * sx, 0, 0.28), (0.04, 0.04, 0.16), dark))
        parts.append(_sphere(f"Foot_{side}", (0.08 * sx, -0.04, 0.06), (0.05, 0.08, 0.03), cyan, 12))
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = chest
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = "JarvisBody"
    wire = body.modifiers.new("Wire", "WIREFRAME")
    wire.thickness = 0.012
    wire.use_replace = False
    arm_data = bpy.data.armatures.new("JarvisArmature")
    arm = bpy.data.objects.new("JarvisRig", arm_data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones

    def bone(name, head, tail, parent=None):
        b = eb.new(name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        if parent:
            b.parent = eb[parent]

    bone("root", (0, 0, 0), (0, 0, 0.2))
    bone("spine", (0, 0, 0.85), (0, 0, 1.25), "root")
    bone("chest", (0, 0, 1.25), (0, 0, 1.48), "spine")
    bone("neck", (0, 0, 1.48), (0, 0, 1.60), "chest")
    bone("head", (0, 0, 1.60), (0, 0, 1.82), "neck")
    bpy.ops.object.mode_set(mode="OBJECT")
    body.parent = arm
    return body


def export_glb():
    dests = [
        Path.home() / ".local/share/jarvis-linux/avatar.glb",
        Path.home() / "Escritorio/jarvis-linux/assets/jarvis_humanoid.glb",
    ]
    for d in dests:
        d.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(d), export_format="GLB", export_animations=True, export_apply=True)
        print("Exported", d)


if __name__ == "__main__":
    build()
    export_glb()
    print("Listo.")
