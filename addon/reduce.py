import bpy, bmesh, mathutils
from .. import rmlib

def FindStartLoop( faces ):
	for f in faces:		
		for l in f.loops:
			if not l.vert.tag:
				return l
	return None


def UnselectedEdgeCount( loop ):
	unselected_edges = 0
	for e in loop.vert.link_edges:
		if not e.select:
			unselected_edges += 1
	return unselected_edges


def CreateFace( rmmesh, loop_list, proto ):
	if len( loop_list ) > 2 and len( loop_list ) == len( set( loop_list ) ):
		try:
			new_face = rmmesh.bmesh.faces.new( [l.vert for l in loop_list], proto )
		except ValueError:
			return

		#copy over uv data
		if rmmesh.bmesh.loops.layers.uv is not None:
			for uvlayer in rmmesh.bmesh.loops.layers.uv.values():
				for i, new_face_loop in enumerate( new_face.loops ):
					new_face_loop[uvlayer].uv = loop_list[i][uvlayer].uv

		#copy over vcolor data
		if rmmesh.bmesh.loops.layers.color is not None:
			for colorlayer in rmmesh.bmesh.loops.layers.color:
				for i, new_face_loop in enumerate( new_face.loops ):
					new_face_loop[colorlayer] = loop_list[i][colorlayer]

			#edge data processing
		clyr = rmmesh.bmesh.edges.layers.float.get( 'crease_edge', None )
		if clyr is None:
			clyr = rmmesh.bmesh.edges.layers.float.get( 'crease_edge' )

		blyr = rmmesh.bmesh.edges.layers.float.get( 'bevel_weight_edge', None )
		if blyr is None:
			blyr = rmmesh.bmesh.edges.layers.float.get( 'bevel_weight_edge' )
			
		for i, new_face_loop in enumerate( new_face.loops ):
			if clyr is not None:
				new_face_loop.edge[clyr] = loop_list[i].edge[clyr]
			if blyr is not None:
				new_face_loop.edge[blyr] = loop_list[i].edge[blyr]
			new_face_loop.edge.smooth = loop_list[i].edge.smooth
			new_face_loop.edge.seam = loop_list[i].edge.seam
		
			
def GetNewPolygonLoopList( loop_list, loop, first_loop ):
	loop.face.tag = True
	
	#determine if current vert get appended
	if loop.vert.tag:
		if UnselectedEdgeCount( loop ) > 2:
			loop_list.append( loop )	
	else:
		loop_list.append( loop )
			
	#determine which is the next loop
	if loop.vert.tag:			
		while( loop.edge.select ):
			loop = loop.link_loop_radial_next.link_loop_next
	else:
		if loop.link_loop_next.vert.tag and UnselectedEdgeCount( loop.link_loop_next ) == 1:
			loop = loop.link_loop_radial_next.link_loop_next

	if first_loop.vert == loop.link_loop_next.vert:
		return loop_list
		
	return GetNewPolygonLoopList( loop_list, loop.link_loop_next, first_loop )


def ClearTags( rmmesh ):
	for v in rmmesh.bmesh.verts:
		v.tag = False
	for f in rmmesh.bmesh.faces:
		f.tag = False
	

def pop_edges( rmmesh, sel_edges ):
	ClearTags( rmmesh )
	
	for v in sel_edges.vertices:
		v.tag = True
	
	active_faces = sel_edges.polygons

	cap_faces = rmlib.rmPolygonSet()
	for f in sel_edges.vertices.polygons:
		sel_edge_count = 0		
		for e in f.edges:
			if e.select:
				sel_edge_count += 1

		tag_vert_count = 0
		for v in f.verts:
			if v.tag:
				tag_vert_count += 1
				
		if sel_edge_count == 0 and tag_vert_count > 0:
			cap_faces.append( f )

	next_active_faces = active_faces.copy()
	while( len( next_active_faces ) > 0 ):
		start_loop = FindStartLoop( next_active_faces )
		if start_loop is None:
			break
		
		loop_list = GetNewPolygonLoopList( [], start_loop, start_loop )

		CreateFace( rmmesh, loop_list, start_loop.face )
			
		next_active_faces.clear()
		for f in active_faces:
			if not f.tag:
				next_active_faces.append( f )

	for f in cap_faces:
		loop_list = []
		for l in f.loops:
			if l.vert.tag:
				if UnselectedEdgeCount( l ) > 2:
					loop_list.append( l )
			else:
				loop_list.append( l )
		if len( loop_list ) < len( f.loops ):
			CreateFace( rmmesh, loop_list, f )
			active_faces.append( f )
		
	bmesh.ops.delete( rmmesh.bmesh, geom=active_faces, context='FACES' )
	
	ClearTags( rmmesh )

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
		if len( g ) < 1:
			continue
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

		sel_mode = context.tool_settings.mesh_select_mode[:]

		for rmmesh in rmlib.item.iter_edit_meshes( context ):
			
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
					sel_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					if len( sel_edges ) > 0:
						if self.reduce_mode == 'DEL':
							lone_edges = [ e for e in sel_edges if len( e.link_faces ) == 0 ]
							bmesh.ops.delete( rmmesh.bmesh, geom=sel_edges.polygons , context='FACES' )
							bmesh.ops.delete( rmmesh.bmesh, geom=lone_edges , context='EDGES' )

						elif self.reduce_mode == 'COL':
							bpy.ops.mesh.edge_collapse()
						elif self.reduce_mode == 'DIS':
							bpy.ops.mesh.dissolve_edges( use_verts=False, use_face_split=False )
						else: #'POP'
							active_edges = rmlib.rmEdgeSet()
							for e in sel_edges:
								if e.is_boundary:
									e.select = False
								else:
									active_edges.append( e )
							if len( active_edges ) > 0:
								pop_edges( rmmesh, active_edges )

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