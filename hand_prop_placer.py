import bpy
from mathutils import Vector, Euler
import math

bl_info = {
    "name": "Hand Prop Placer (Armature Ready)",
    "author": "R.O.Studios (Idea by R.O.Studios, created by Google Gemini and fixed by ChatGPT)",
    "version": (1, 15),
    "blender": (4, 3, 0),
    "location": "3D View > Sidebar > Prop Placer",
    "description": "Helps place and orient props on a model's right or left hand bone.",
    "warning": "May cause instability if context is not clean.",
    "category": "Object",
}

class HandPropPlacerProperties(bpy.types.PropertyGroup):
    armature_obj: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Target Armature",
        description="Select the Armature object containing the hand bone"
    )

    target_hand_bone_name: bpy.props.StringProperty(
        name="Target Hand Bone",
        description="The name of the selected hand bone",
        default=""
    )

    prop_obj: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Prop Object",
        description="Select the prop object to place on the hand"
    )

    hand_side: bpy.props.EnumProperty(
        items=[
            ('RIGHT', "Right Hand", "Place prop on the right hand"),
            ('LEFT', "Left Hand", "Place prop on the left hand"),
        ],
        name="Hand Side",
        description="Specify if the target is the right or left hand",
        default='RIGHT'
    )

    offset_x: bpy.props.FloatProperty(name="Offset X", default=0.0, min=-10.0, max=10.0)
    offset_y: bpy.props.FloatProperty(name="Offset Y", default=0.0, min=-10.0, max=10.0)
    offset_z: bpy.props.FloatProperty(name="Offset Z", default=0.0, min=-10.0, max=10.0)

    rotate_x: bpy.props.FloatProperty(name="Rotate X", default=0.0, min=-360.0, max=360.0, subtype='ANGLE')
    rotate_y: bpy.props.FloatProperty(name="Rotate Y", default=0.0, min=-360.0, max=360.0, subtype='ANGLE')
    rotate_z: bpy.props.FloatProperty(name="Rotate Z", default=0.0, min=-360.0, max=360.0, subtype='ANGLE')

    parent_prop: bpy.props.BoolProperty(name="Parent Prop to Bone", default=True)
    apply_prop_scale: bpy.props.BoolProperty(name="Apply Prop Scale", default=True)

class HANDPROP_OT_place_prop(bpy.types.Operator):
    bl_idname = "object.hand_prop_placer_place_prop"
    bl_label = "Place Prop on Hand Bone"
    bl_description = "Moves and orients the prop to the selected hand bone."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.hand_prop_placer_props
        return (
            props.armature_obj and
            props.armature_obj.type == 'ARMATURE' and
            props.prop_obj and
            props.prop_obj != props.armature_obj and
            props.target_hand_bone_name in props.armature_obj.data.bones
        )

    def execute(self, context):
        props = context.scene.hand_prop_placer_props
        armature_obj = props.armature_obj
        prop_obj = props.prop_obj
        bone_name = props.target_hand_bone_name

        pose_bone = armature_obj.pose.bones.get(bone_name)
        if not pose_bone:
            self.report({'ERROR'}, f"Bone '{bone_name}' not found in pose bones.")
            return {'CANCELLED'}

        original_active = context.view_layer.objects.active
        original_selection = context.selected_objects.copy()

        # Apply scale safely
        if props.apply_prop_scale:
            prop_obj.scale = Vector((1.0, 1.0, 1.0))
            if prop_obj.type == 'MESH' and hasattr(prop_obj.data, "update"):
                prop_obj.data.update()

        # Get bone matrix and apply transform
        bone_matrix_world = pose_bone.matrix.copy()
        new_matrix = bone_matrix_world.copy()

        offset = Vector((props.offset_x, props.offset_y, props.offset_z))
        new_matrix.translation += bone_matrix_world.to_quaternion() @ offset

        rotation_euler = Euler((
            math.radians(props.rotate_x),
            math.radians(props.rotate_y),
            math.radians(props.rotate_z)
        ), 'XYZ')
        rotation_matrix = rotation_euler.to_quaternion().to_matrix().to_4x4()

        new_matrix = new_matrix @ rotation_matrix
        prop_obj.matrix_world = new_matrix

        # Parenting
        if props.parent_prop:
            for c in prop_obj.constraints:
                if c.type == 'CHILD_OF':
                    prop_obj.constraints.remove(c)

            constraint = prop_obj.constraints.new(type='CHILD_OF')
            constraint.target = armature_obj
            constraint.subtarget = bone_name

            bpy.context.view_layer.update()

            try:
                bpy.ops.object.select_all(action='DESELECT')
                prop_obj.select_set(True)
                context.view_layer.objects.active = prop_obj
                bpy.ops.constraint.childof_set_inverse(constraint=constraint.name)
                self.report({'INFO'}, "Constraint inverse set.")
            except RuntimeError as e:
                self.report({'WARNING'}, f"Failed to set inverse: {e}")

        else:
            for c in prop_obj.constraints:
                if c.type == 'CHILD_OF':
                    prop_obj.constraints.remove(c)

        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            obj.select_set(True)
        context.view_layer.objects.active = original_active

        return {'FINISHED'}

class HANDPROP_PT_main_panel(bpy.types.Panel):
    bl_label = "Hand Prop Placer (Armature)"
    bl_idname = "HANDPROP_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Prop Placer"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        props = context.scene.hand_prop_placer_props

        layout.label(text="1. Select Target Armature:")
        layout.prop(props, "armature_obj")

        if props.armature_obj:
            if props.armature_obj.type != 'ARMATURE':
                layout.label(text="Selected object is not an Armature!", icon='ERROR')
            else:
                layout.label(text="2. Select Hand Bone:")
                layout.prop_search(props, "target_hand_bone_name", props.armature_obj.data, "bones", text="Bone")

        layout.separator()
        layout.label(text="3. Select Prop Object:")
        layout.prop(props, "prop_obj")

        layout.separator()
        layout.label(text="4. Hand Side & Placement:")
        layout.prop(props, "hand_side", expand=True)
        layout.prop(props, "parent_prop")
        layout.prop(props, "apply_prop_scale")

        layout.separator()
        layout.label(text="Offset:")
        layout.prop(props, "offset_x")
        layout.prop(props, "offset_y")
        layout.prop(props, "offset_z")

        layout.label(text="Rotation (Degrees):")
        layout.prop(props, "rotate_x")
        layout.prop(props, "rotate_y")
        layout.prop(props, "rotate_z")

        layout.separator()
        layout.operator("object.hand_prop_placer_place_prop", icon='CONSTRAINT')

classes = (
    HandPropPlacerProperties,
    HANDPROP_OT_place_prop,
    HANDPROP_PT_main_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.hand_prop_placer_props = bpy.props.PointerProperty(type=HandPropPlacerProperties)

def unregister():
    if hasattr(bpy.types.Scene, "hand_prop_placer_props"):
        del bpy.types.Scene.hand_prop_placer_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
