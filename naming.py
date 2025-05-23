import bpy, bmesh, mathutils
import rmlib


class MESH_OT_itemnametomeshname( bpy.types.Operator ):
	"""Name all meshes the same as their parent object."""
	bl_idname = 'mesh.rm_itemnametomeshname'
	bl_label = 'Item Name to Mesh Name'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return context.area.type == 'VIEW_3D'

	def execute( self, context ):
		for obj in bpy.context.selected_objects:
			try:
				obj.data.name = obj.name
			except:
				continue

		return { 'FINISHED' }
	

def register():
	bpy.utils.register_class( MESH_OT_itemnametomeshname )
	
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_itemnametomeshname )