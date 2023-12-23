bl_info = {
    "name": "Sonic Frontiers Collision Importer",
    "description": "Collision model importer for Sonic Frontiers .btmesh format",
    "author": "AdelQ",
    "version": (0, 2, 0),
    "blender": (3, 6, 5),
    "location": "File > Import",
    "category": "Import-Export",
}

import bpy
import bmesh
import struct
import mathutils
import os
import math
from io import BytesIO 
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty
from bpy.types import Operator

class FrontiersBTMeshImport(Operator, ImportHelper):
    bl_idname = "custom_import_scene.frontiersbtmesh"
    bl_label = "Import"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".btmesh"
    filter_glob: bpy.props.StringProperty(
        default="*.btmesh",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    types = (
        "@NONE",
        "@STONE",
        "@EARTH",
        "@WOOD",
        "@GRASS",
        "@IRON",
        "@SAND",
        "@LAVA",
        "@GLASS",
        "@SNOW",
        "@NO_ENTRY",
        "@ICE",
        "@WATER",
        "@SEA",
        "@DAMAGE",
        "@DEAD",
        "@FLOWER0",
        "@FLOWER1",
        "@FLOWER2",
        "@AIR",
        "@DEADLEAVES",
        "@WIREMESH",
        "@DEAD_ANYDIR",
        "@DAMAGE_THROUGH",
        "@DRY_GRASS",
        "@RELIC",
        "@GIANT",
        "@GRAVEL",
        "@MUD_WATER",
        "@SAND2",
        "@SAND3"
    )

    layers = (
        "@NONE",
        "@SOLID",
        "@LIQUID",
        "@THROUGH",
        "@CAMERA",
        "@SOLID_ONEWAY", 
        "@SOLID_THROUGH", 
        "@SOLID_TINY",
        "@SOLID_DETAIL",
        "@LEAF",
        "@LAND",
        "@RAYBLOCK", 
        "@EVENT",
        "@RESERVED13",
        "@RESERVED14", 
        "@PLAYER",
        "@ENEMY",
        "@ENEMY_BODY",
        "@GIMMICK",
        "@DYNAMICS",
        "@RING", 
        "@CHARACTER_CONTROL", 
        "@PLAYER_ONLY",
        "@DYNAMICS_THROUGH",
        "@ENEMY_ONLY",
        "@SENSOR_PLAYER", 
        "@SENSOR_RING",
        "@SENSOR_GIMMICK",
        "@SENSOR_LAND",
        "@SENSOR_ALL",
        "@RESERVED30",
        "@RESERVED31"
    )

    flags = (
        "@NOT_STAND",
        "@BREAKABLE",
        "@REST",
        "@UNSUPPORTED",
        "@REFLECT_LASER" ,
        "@LOOP",
        "@WALL",
        "@SLIDE",
        "@PARKOUR",
        "@DECELERATE",
        "@MOVABLE",
        "@PARKOUR_KNUCKLES",
        "@PRESS_DEAD",
        "@RAYBLOCK",
        "@WALLJUMP",
        "@PUSH_BOX",
        "@STRIDER_FLOOR",
        "@GIANT_TOWER",
        "@PUSHOUT_LANDING",
        "@TEST_GRASS",
        "@TEST_WATER"
    )
    
    filepath: StringProperty(subtype='FILE_PATH',)
    files: CollectionProperty(type=bpy.types.PropertyGroup)
    
    fill_convex: BoolProperty(
        name="Fill Convex",
        description="(For convex collisions only) Check to create convex hulls from point clouds, leave unchecked to keep only the vertices",
        default=True,
        )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "fill_convex")
    
    
    def execute(self, context):
        for col_file in self.files:
            col_filepath = os.path.join(os.path.dirname(self.filepath), col_file.name)
            with open(col_filepath, "rb") as file:
                filename = os.path.basename(col_filepath)
                file_read = file.read()
                filedata = BytesIO(file_read)
            col_name = filename.split(".")[0]
            
            collection = bpy.data.collections.new(col_name)
            bpy.context.scene.collection.children.link(collection) 
            layer_collection = bpy.context.view_layer.layer_collection.children[collection.name]
            bpy.context.view_layer.active_layer_collection = layer_collection
            
            filedata.seek(0x50, 0)
            mesh_count = struct.unpack("<i", filedata.read(4))[0]
            filedata.read(12)
            
            for i in range(mesh_count):
                convex = struct.unpack("<i", filedata.read(4))[0]
                layer = struct.unpack("<i", filedata.read(4))[0]
                vertex_count = struct.unpack("<i", filedata.read(4))[0]
                face_count = struct.unpack("<i", filedata.read(4))[0]
                bvh_size = struct.unpack("<i", filedata.read(4))[0]
                filedata.read(12)
                vert_offset = struct.unpack("<q", filedata.read(8))[0] + 0x40
                face_offset = struct.unpack("<q", filedata.read(8))[0] + 0x40
                filedata.read(16)
                offset = filedata.tell()
                
                name = "col" + str(i)
                
                bm = bmesh.new()
                me = bpy.data.meshes.new(col_name + str(i))

                vertices = []
                filedata.seek(vert_offset, 0)
                for _ in range(vertex_count):
                    vert = struct.unpack("<fff", filedata.read(12))
                    vertices.append(vert)
                for v in vertices:
                    bm.verts.new(v)
                bm.verts.ensure_lookup_table()

                faces = []
                filedata.seek(face_offset, 0)
                for _ in range(face_count):
                    face = struct.unpack("<HHH", filedata.read(6))
                    faces.append(face)
                for f in faces:
                    for i in f:
                        face = [bm.verts[i] for i in f]
                    bm.faces.new(face)
                bm.faces.ensure_lookup_table()

                bm.to_mesh(me)
                bm.free()

                ### Append tags AFTER creating duplicate names
                name_append = self.layers[layer]
                if convex == 2:
                    name_append += "@CONVEX"
                
                objlist = [obj.name for obj in bpy.context.scene.objects]
                if name + name_append in objlist:
                    name_int = 1
                    newname = name + "." + str(name_int).zfill(3)
                    while newname + name_append in objlist:
                        name_int += 1
                        newname = name + "." + str(name_int).zfill(3)
                    name = newname + name_append
                else:
                    name += name_append

                obj = bpy.data.objects.new(name, me)
                bpy.context.collection.objects.link(obj)
                
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                
                if convex == 2 and self.fill_convex == True:
                    utils_set_mode('EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.convex_hull(
                        delete_unused=False, 
                        use_existing_faces=False, 
                        make_holes=False, 
                        join_triangles=False, 
                        )
                    utils_set_mode('OBJECT')
                
                obj.rotation_euler = ((math.pi / 2),0,0)
                filedata.seek(offset, 0)

        return {'FINISHED'}
    
    
    
def utils_set_mode(mode):
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode=mode, toggle=False)

def menu_func_import(self, context):
    self.layout.operator(FrontiersBTMeshImport.bl_idname, text="Sonic Frontiers Collision (.btmesh)")

def register():
    bpy.utils.register_class(FrontiersBTMeshImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(FrontiersBTMeshImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
