import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

def has_open_vert_member( verts ):
	for v in verts:
		for e in v.link_edges:
			if e.is_boundary:
				return True
	return False

def collapse_verts( verts ):
	collapse_groups = [ [], ]
	for g in verts.group():
		if has_open_vert_member( g ):
			collapse_groups[0] += g
		else:
			collapse_groups.append( g )

	for g in collapse_groups:
		avg = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		for v in g:
			avg += v.co
		avg *= 1.0 / len( g )
		for v in g:
			v.co = avg

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
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		#get the selection mode
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]

		
		if sel_mode[0]: #vert mode
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				sel_verts = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( sel_verts ) > 0:
					if self.reduce_mode == 'DEL':
						bpy.ops.mesh.delete( type='VERT' )
					elif self.reduce_mode == 'COL':
						rmmesh.readonly = False
						verts = rmlib.rmVertexSet.from_selection( rmmesh )
						collapse_verts( verts )
						bmesh.ops.remove_doubles( rmmesh.bmesh, verts=verts, dist=0.00001 )
					else:
						bpy.ops.mesh.dissolve_verts()

		if sel_mode[1]: #edge mode
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				sel_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				if len( sel_edges ) > 0:
					if self.reduce_mode == 'DEL':
						rmmesh.readonly = False
						bmesh.ops.delete( rmmesh.bmesh, geom=sel_edges.polygons, context='FACES' )
					elif self.reduce_mode == 'COL':
						bpy.ops.mesh.edge_collapse()
					elif self.reduce_mode == 'DIS':
						bpy.ops.mesh.dissolve_edges( use_verts=False, use_face_split=False )
					else:
						bpy.ops.mesh.dissolve_edges( use_verts=True, use_face_split=False )

		if sel_mode[2]: #poly mode
			with rmmesh as rmmesh:
				rmmesh.readonly = True
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