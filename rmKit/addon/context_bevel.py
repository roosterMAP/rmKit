import bpy
from .. import rmlib

class MESH_OT_contextbevel( bpy.types.Operator ):
	"""Activate bevel tool based on selection mode."""
	bl_idname = 'mesh.rm_contextbevel'
	bl_label = 'Context Bevel'

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]: #vert mode
			bpy.ops.mesh.bevel( 'INVOKE_DEFAULT', affect='VERTICES' )
		elif sel_mode[1]: #edge mode
			rmmesh = rmlib.rmMesh.GetActive( context )
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				sel_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				open_edges = rmlib.rmEdgeSet()
				closed_edges = rmlib.rmEdgeSet()
				for e in sel_edges:
					if e.is_boundary:
						open_edges.append( e )
					elif e.is_contiguous:
						closed_edges.append( e )
				if len( open_edges ) > 0:
					open_edges.select( replace=True )
					bpy.ops.mesh.extrude_edges_move( 'INVOKE_DEFAULT' )
				elif len( closed_edges ) > 0:
					bpy.ops.mesh.bevel( 'INVOKE_DEFAULT', affect='EDGES' )
				else:
					return { 'CANCELLED' }
		if sel_mode[2]: #poly mode
			bpy.ops.mesh.inset( 'INVOKE_DEFAULT', use_outset=False )

		return { 'FINISHED' }
	
def register():
	print( 'register :: {}'.format( MESH_OT_contextbevel.bl_idname ) )
	bpy.utils.register_class( MESH_OT_contextbevel )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_contextbevel.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_contextbevel )