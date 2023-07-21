import bpy, bmesh, mathutils
from .. import rmlib

BACKGROUND_LAYERNAME = 'rm_background'

def SetSelsetMembership( bm, type, elems, layername ):	
	if type == 'VERT':
		intlayers = bm.verts.layers.int
		selset = intlayers.get( layername, None )
		for v in bm.verts:
			v[selset] = v in elems
	elif type == 'EDGE':
		intlayers = bm.edges.layers.int
		selset = intlayers.get( layername, None )
		for e in bm.edges:
			e[selset] = e in elems
	elif type == 'FACE':
		intlayers = bm.faces.layers.int
		selset = intlayers.get( layername, None )
		for f in bm.faces:
			f[selset] = f in elems
	else:
		return
		
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
	"""Change to vert/edge/face selection mode and cache the current selection. Upon returning to previouse mode, the cached selection will be reestablished."""
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
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' )
		
	def execute( self, context ):
		if context.mode != 'OBJECT' and not context.object.data.is_editmode:
			return { 'CANCELLED' }
			
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):

			#create selsets if needed
			with rmmesh as rmmesh:
				intlayers_v = rmmesh.bmesh.verts.layers.int
				selset = intlayers_v.get( BACKGROUND_LAYERNAME, None )
				if selset is None:
					selset = intlayers_v.new( BACKGROUND_LAYERNAME )

				intlayers_e = rmmesh.bmesh.edges.layers.int
				selset = intlayers_e.get( BACKGROUND_LAYERNAME, None )
				if selset is None:
					selset = intlayers_e.new( BACKGROUND_LAYERNAME )

				intlayers_f = rmmesh.bmesh.faces.layers.int
				selset = intlayers_f.get( BACKGROUND_LAYERNAME, None )
				if selset is None:
					selset = intlayers_f.new( BACKGROUND_LAYERNAME )

			#exit early if we are already in the mode we are switching to
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if context.mode != 'OBJECT':
				if ( sel_mode[0] and self.mode_to == 'VERT' ) or ( sel_mode[1] and self.mode_to == 'EDGE' ) or ( sel_mode[2] and self.mode_to == 'FACE' ):
					return { 'FINISHED' }

			#init component selset for current mode (before switching)
			if sel_mode[0]:
				with rmmesh as rmmesh:
					verts = rmlib.rmVertexSet.from_selection( rmmesh )
					SetSelsetMembership( rmmesh.bmesh, 'VERT', verts, BACKGROUND_LAYERNAME )
			elif sel_mode[1]:
				with rmmesh as rmmesh:
					edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					SetSelsetMembership( rmmesh.bmesh, 'EDGE', edges, BACKGROUND_LAYERNAME )
			elif sel_mode[2]:
				with rmmesh as rmmesh:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
					SetSelsetMembership( rmmesh.bmesh, 'FACE', faces, BACKGROUND_LAYERNAME )

		#switch to target mode and clear selection
		if context.mode == 'OBJECT':
			bpy.ops.object.editmode_toggle()
		bpy.ops.mesh.select_mode( type=self.mode_to )
		bpy.ops.mesh.select_all( action='DESELECT' )

		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):

			#set new selection
			with rmmesh as rmmesh:
				for elem in GetSelsetMembership( rmmesh.bmesh, self.mode_to, BACKGROUND_LAYERNAME ):
					elem.select = True
				
		return { 'FINISHED' }


class MESH_OT_convertmodeto( bpy.types.Operator ):
	"""Convert current selection to new mode. Also caches prev selection."""
	bl_idname = 'mesh.rm_convertmodeto'
	bl_label = 'Convert Mode To'
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
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		#get the selection mode
		if context.mode == 'OBJECT':
			return { 'CANCELLED' }
			
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):

			#create selsets if needed
			with rmmesh as rmmesh:
				intlayers_v = rmmesh.bmesh.verts.layers.int
				selset = intlayers_v.get( BACKGROUND_LAYERNAME, None )
				if selset is None:
					selset = intlayers_v.new( BACKGROUND_LAYERNAME )

				intlayers_e = rmmesh.bmesh.edges.layers.int
				selset = intlayers_e.get( BACKGROUND_LAYERNAME, None )
				if selset is None:
					selset = intlayers_e.new( BACKGROUND_LAYERNAME )

				intlayers_f = rmmesh.bmesh.faces.layers.int
				selset = intlayers_f.get( BACKGROUND_LAYERNAME, None )
				if selset is None:
					selset = intlayers_f.new( BACKGROUND_LAYERNAME )

			#exit early if we are already in the mode we are converting to
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if ( sel_mode[0] and self.mode_to == 'VERT' ) or ( sel_mode[1] and self.mode_to == 'EDGE' ) or ( sel_mode[2] and self.mode_to == 'FACE' ):
				return { 'FINISHED' }

			#init component selset for current mode (before converting)
			if sel_mode[0]:
				with rmmesh as rmmesh:
					verts = rmlib.rmVertexSet.from_selection( rmmesh )
					if self.mode_to == 'EDGE':
						SetSelsetMembership( rmmesh.bmesh, self.mode_to, verts.edges, BACKGROUND_LAYERNAME )
					elif self.mode_to == 'FACE':
						SetSelsetMembership( rmmesh.bmesh, self.mode_to, verts.polygons, BACKGROUND_LAYERNAME )

			elif sel_mode[1]:
				with rmmesh as rmmesh:
					edges = rmlib.rmEdgeSet.from_selection( rmmesh )

					sel_faces = set()
					if self.mode_to == 'FACE':
						for v in edges.vertices:
							sel_count = 0
							is_open = False
							selected_boundary = False
							for e in v.link_edges:
								if e.is_boundary:
									if e.select:
										selected_boundary = True
									is_open = True
								if e.select:
									sel_count += 1
							if ( is_open and not selected_boundary ) or sel_count > 1:
								for f in v.link_faces:
									sel_faces.add( f )
									
					if self.mode_to == 'VERT':
						SetSelsetMembership( rmmesh.bmesh, self.mode_to, edges.vertices, BACKGROUND_LAYERNAME )
					elif self.mode_to == 'FACE':
						faces = set( edges.polygons ).union( sel_faces )
						SetSelsetMembership( rmmesh.bmesh, self.mode_to, faces, BACKGROUND_LAYERNAME )

			elif sel_mode[2]:
				with rmmesh as rmmesh:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
					if self.mode_to == 'VERT':
						SetSelsetMembership( rmmesh.bmesh, self.mode_to, faces.vertices, BACKGROUND_LAYERNAME )
					elif self.mode_to == 'EDGE':
						SetSelsetMembership( rmmesh.bmesh, self.mode_to, faces.edges, BACKGROUND_LAYERNAME )
						
		#change mode and clear component selection
		bpy.ops.mesh.select_mode( type=self.mode_to )
		bpy.ops.mesh.select_all( action='DESELECT' )

		#select result
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				for elem in GetSelsetMembership( rmmesh.bmesh, self.mode_to, BACKGROUND_LAYERNAME ):
					elem.select = True
				
		return { 'FINISHED' }


class MESH_OT_continuous( bpy.types.Operator ):    
	"""Extend current element selection by 3d continuity."""
	bl_idname = 'mesh.rm_continuous'
	bl_label = 'Select Continuous'
	bl_options = { 'UNDO' }

	add: bpy.props.BoolProperty(
			name='Add',
			description='Add to existing selection.',
			default=False
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and len( context.editable_objects ) > 0 )

	def execute( self, context ):
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			with rmmesh as rmmesh:
				sel_mode = context.tool_settings.mesh_select_mode[:]
				if sel_mode[0]:
					selected_verts = rmlib.rmVertexSet.from_selection( rmmesh )				
					bpy.ops.mesh.select_linked( delimit=set() )
					if self.add:
						selected_verts.select( False )
				elif sel_mode[1]:
					bpy.ops.mesh.rm_loop( force_boundary=True )
				else:
					selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
					bpy.ops.mesh.select_linked( delimit=set() )
					if self.add:
						selected_polys.select( False )
		return { 'FINISHED' }


class MESH_OT_invertcontinuous( bpy.types.Operator ):
	bl_idname = 'mesh.rm_invertcontinuous'
	bl_label = 'Invert Continuous'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and len( context.editable_objects ) > 0 )
		
	def execute( self, context ):
		#get the selection mode
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }		

		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			with rmmesh as rmmesh:
				sel_mode = context.tool_settings.mesh_select_mode[:]

				if sel_mode[0]:
					verts = rmlib.rmVertexSet.from_selection( rmmesh )
					allverts = rmlib.rmVertexSet()
					for g in verts.group( element=True ):
						allverts += g
					for v in allverts:
						v.select = v not in verts


				elif sel_mode[1]:
					edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					alledges = rmlib.rmEdgeSet()
					for g in edges.group( element=True ):
						alledges += g
					for e in alledges:
						e.select = e not in edges

				elif sel_mode[2]:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
					allfaces = rmlib.rmPolygonSet()
					for g in faces.group( element=True ):
						allfaces += g
					for f in allfaces:
						f.select = f not in faces
				
		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_changetomode.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_convertmodeto.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_invertcontinuous.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_continuous.bl_idname ) )
	bpy.utils.register_class( MESH_OT_changetomode )
	bpy.utils.register_class( MESH_OT_convertmodeto )
	bpy.utils.register_class( MESH_OT_invertcontinuous )
	bpy.utils.register_class( MESH_OT_continuous )

	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_changetomode.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_convertmodeto.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_invertcontinuous.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_continuous.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_changetomode )
	bpy.utils.unregister_class( MESH_OT_convertmodeto )
	bpy.utils.unregister_class( MESH_OT_invertcontinuous )
	bpy.utils.unregister_class( MESH_OT_continuous )