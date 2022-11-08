import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib


class MESH_OT_extend( bpy.types.Operator ):
	bl_idname = 'mesh.rm_extend'
	bl_label = 'Extend'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		#get the selection mode
		if context.object is None:
			return { 'CANCELLED' }

		if context.mode == 'OBJECT':
			bpy.ops.object.duplicate_move_linked( 'INVOKE_DEFAULT' )
		

		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			bpy.ops.mesh.rip_edge_move( 'INVOKE_DEFAULT' )
		elif sel_mode[1]:
			bpy.ops.mesh.extrude_edges_move( 'INVOKE_DEFAULT' )
		elif sel_mode[2]:
			bpy.ops.mesh.duplicate_move( 'INVOKE_DEFAULT' )
		else:
			return { 'CANCELLED' }
				
		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_extend.bl_idname ) )
	bpy.utils.register_class( MESH_OT_extend )
	
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_extend.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_extend )