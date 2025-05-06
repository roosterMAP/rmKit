import bpy, bmesh, mathutils
import rmlib


class MESH_OT_extend( bpy.types.Operator ):
	"""Runs Extend Vert in vert mode, Edge Extude in edge mode, and DuplicateMode in face mode."""
	bl_idname = 'mesh.rm_extend'
	bl_label = 'Extend'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return context.area.type == 'VIEW_3D'
		
	def execute( self, context ):
		#get the selection mode
		if context.object is None:
			return { 'CANCELLED' }

		if context.mode == 'OBJECT':
			bpy.ops.object.duplicate_move_linked( 'INVOKE_DEFAULT' )
			return { 'FINISHED' }
		

		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			use_extrude = True
			rmmesh = rmlib.rmMesh.GetActive( context )
			if rmmesh is None:
				return { 'CANCELLED' }
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				vert_selection = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( vert_selection ) == 0:
					return { 'CANCELLED' }				
				for e in vert_selection.edges:
					if len( list( e.link_faces ) ) > 0:
						use_extrude = False
						break
			if use_extrude:
				bpy.ops.mesh.extrude_vertices_move( 'INVOKE_DEFAULT' )
			else:
				bpy.ops.mesh.rip_edge_move( 'INVOKE_DEFAULT' )
			
		elif sel_mode[1]:
			bpy.ops.mesh.extrude_edges_move( 'INVOKE_DEFAULT' )
		elif sel_mode[2]:
			bpy.ops.mesh.duplicate_move( 'INVOKE_DEFAULT' )
		else:
			return { 'CANCELLED' }
				
		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_extend )
	
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_extend )