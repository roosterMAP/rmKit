import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

BACKGROUND_LAYERNAME = 'rm_background'

def SetSelsetMembership( bm, elems, layername ):
	if len( elems ) < 1:
		return
	if isinstance( elems[0], bmesh.types.BMVert ):
		intlayers = bm.verts.layers.int
		selset = intlayers.get( layername, None )
		if selset is None:
			selset = intlayers.new( layername )
		for v in bm.verts:
			v[selset] = 0
	elif isinstance( elems[0], bmesh.types.BMEdge ):
		intlayers = bm.edges.layers.int
		selset = intlayers.get( layername, None )
		if selset is None:
			selset = intlayers.new( layername )
		for e in bm.edges:
			e[selset] = 0
	elif isinstance( elems[0], bmesh.types.BMFace ):
		intlayers = bm.faces.layers.int
		selset = intlayers.get( layername, None )
		if selset is None:
			selset = intlayers.new( layername )
		for f in bm.faces:
			f[selset] = 0
	else:
		return

	for e in elems:
		e[selset] = 1
		
def GetSelsetMembership( bm, type, layername):
	if type == 'VERT':
		intlayers = bm.verts.layers.int
	elif type == 'EDGE':
		intlayers = bm.edges.layers.int
	elif type == 'FACE':
		intlayers = bm.faces.layers.int
	else:
		return []

	selset = intlayers.get( layername, None )
	if selset is None:
		return []

	if type == 'VERT':
		return rmlib.rmVertexSet( [ v for v in bm.verts if bool( v[selset] ) ] )
	elif type == 'EDGE':
		return rmlib.rmEdgeSet( [ e for e in bm.edges if bool( e[selset] ) ] )
	else:
		return rmlib.rmPolygonSet( [ f for f in bm.faces if bool( f[selset] ) ] )
	

class MESH_OT_changetomode( bpy.types.Operator ):
	bl_idname = 'mesh.rm_changemodeto'
	bl_label = 'Change Mode To'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	mode_to: bpy.props.EnumProperty(
		items=[ ( "VERT", "Vertex", "", 1 ),
				( "EDGE", "Edge", "", 2 ),
				( "FACE", "Face", "", 3 ) ],
		name="Selection Mode",
		default="VERT"
	)
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' )
		
	def execute( self, context ):
		if context.mode != 'OBJECT' and not context.object.data.is_editmode:
			return { 'CANCELLED' }
		
		if context.object.type == 'MESH':
			sel_mode = context.tool_settings.mesh_select_mode[:]

			if sel_mode[0]:
				rmmesh = rmlib.rmMesh.GetActive( context )
				with rmmesh as rmmesh:
					verts = rmlib.rmVertexSet.from_selection( rmmesh )
					SetSelsetMembership( rmmesh.bmesh, verts, BACKGROUND_LAYERNAME )

			elif sel_mode[1]:
				rmmesh = rmlib.rmMesh.GetActive( context )
				with rmmesh as rmmesh:
					edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					SetSelsetMembership( rmmesh.bmesh, edges, BACKGROUND_LAYERNAME )

			else:
				rmmesh = rmlib.rmMesh.GetActive( context )
				with rmmesh as rmmesh:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
					SetSelsetMembership( rmmesh.bmesh, faces, BACKGROUND_LAYERNAME )

		bpy.ops.mesh.select_mode( type=self.mode_to )

		bpy.ops.mesh.select_all( action='DESELECT' )

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			rmmesh.readonly = True
			for elem in GetSelsetMembership( rmmesh.bmesh, self.mode_to, BACKGROUND_LAYERNAME ):
				elem.select = True
				
		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_changetomode.bl_idname ) )
	bpy.utils.register_class( MESH_OT_changetomode )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_changetomode.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_changetomode )