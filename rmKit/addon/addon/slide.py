import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib


class MESH_OT_slide( bpy.types.Operator ):
	"""Calls Vertex Slide in vert mode and Edge slide in edge mode."""
	bl_idname = 'mesh.rm_slide'
	bl_label = 'Slide'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		#get the selection mode
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }		

		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			bpy.ops.transform.vert_slide( 'INVOKE_DEFAULT' )
		elif sel_mode[1]:
			bpy.ops.transform.edge_slide( 'INVOKE_DEFAULT' )
				
		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_slide.bl_idname ) )
	bpy.utils.register_class( MESH_OT_slide )
	
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_slide.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_slide )