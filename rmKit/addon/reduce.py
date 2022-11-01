import bpy
import bmesh
from .. import rmlib

class MESH_OT_reduce( bpy.types.Operator ):
	"""Delete/Remove/Collapse selected components."""
	bl_idname = 'mesh.rm_remove'
	bl_label = 'Reduce Selection'
	#bl_options = { 'REGISTER', 'UNDO' }
	bl_options = { 'UNDO' }

	reduce_mode: bpy.props.EnumProperty(
		items=[ ( "DEL", "Delete", "", 1 ),
				( "COL", "Collapse", "", 2 ),
				( "DIS", "Dissolve", "", 3 ),
				( "POP", "Pop", "", 4 ) ],
		name="Reduce Mode",
		default="DEL"
	)

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		#get the selection mode
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]

		print( self.reduce_mode )

		with rmmesh as rmmesh:
			if sel_mode[0]: #vert mode
				sel_verts = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( sel_verts ) > 0:
					if self.reduce_mode == 'DEL':
						bpy.ops.mesh.delete( type='VERT' )
					elif self.reduce_mode == 'COL':
						bpy.ops.mesh.edge_collapse()
					else:
						bpy.ops.mesh.dissolve_verts()

			if sel_mode[1]: #edge mode
				sel_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				if len( sel_edges ) > 0:
					if self.reduce_mode == 'DEL':
						bpy.ops.mesh.delete( type='EDGE' )
					elif self.reduce_mode == 'COL':
						bpy.ops.mesh.edge_collapse()
					elif self.reduce_mode == 'DIS':
						bpy.ops.mesh.dissolve_edges( use_verts=False, use_face_split=False )
					else:
						bpy.ops.mesh.dissolve_edges( use_verts=True, use_face_split=False )

			if sel_mode[2]: #poly mode
				sel_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				if len( sel_polys ) > 0:
					if self.reduce_mode == 'COL':
						bpy.ops.mesh.edge_collapse()
					else:
						bpy.ops.mesh.delete( type='FACE' )

		return { 'FINISHED' }
	
def register():
	print( 'register :: {}'.format( MESH_OT_reduce.bl_idname ) )
	bpy.utils.register_class( MESH_OT_reduce )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_reduce.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_reduce )