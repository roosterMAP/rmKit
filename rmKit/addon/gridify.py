import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

def pair_has_one_member_link_face( pair, faces ):
	count = 0
	for f in pair[0].link_faces:
		if f in faces:
			count += 1
	return count == 1


def GetRings( faces ):
	#ensure group is all quads
	allQuads = True
	for p in faces:
		if len( p.verts ) != 4:
			allQuads = False
			break
	if not allQuads:
		return []

	#find outer edges
	outer_edges = rmlib.rmEdgeSet()
	for e in faces.edges:
		neigh_faces = list( e.link_faces )
		if len( neigh_faces ) < 2:
			outer_edges.append( e )
		member_count = 0
		for nf in neigh_faces:
			if nf in faces:
				member_count += 1
		if member_count == 1:
			outer_edges.append( e )

	#ensure exactly one continuous closed loop of open edges
	chains = outer_edges.chain()
	if len( chains ) != 1:
		return []
	if len( chains[0] ) < 3:
		return []
	if chains[0][0][0] != chains[0][-1][-1]:
		return []
	chain = chains[0]

	#ensure each vert either boardered 4 manifold edges or 1 manifold and 2 boundary edges
	invalidTopo = False
	for v in faces.vertices:
		boundary_count = 0
		contiguous_count = 0
		for e in v.link_edges:
			if e.is_boundary:
				boundary_count += 1
			if e.is_contiguous:
				contiguous_count += 1
		if not ( boundary_count == 2 and contiguous_count == 1 ):
			invalidTopo = True
			break
		if not ( boundary_count == 4 and contiguous_count == 0 ):
			invalidTopo = True
			break
	if not invalidTopo:
		return []

	#get first ring
	outer_verts = rmlib.rmVertexSet( [ pair[0] for pair in chain ] )
	for start_idx, pair in enumerate( chain ):
		if pair_has_one_member_link_face( pair, faces ):
			break
	first_ring = rmlib.rmVertexSet( [ chain[start_idx][0] ] )
	vcount = len( chain )
	for i in range( 1, vcount ):
		pair = chain[( start_idx + i ) % vcount]
		first_ring.append( pair[0] )
		if pair_has_one_member_link_face( pair, faces ):
			break

	#break up faces into list of verts each of same size (rings of tube)
	rings = [first_ring]
	for v in rings[-1]:
		v.tag = True
	while( True ):
		new_ring = set()
		for p in rings[-1].polygons:
			if p.tag:
				continue
			p.tag = True
			for v in p.verts:
				if v.tag:
					continue
				v.tag = True
				new_ring.add( v )
		if len( new_ring ) < 3:
			break
		rings.append( rmlib.rmVertexSet( new_ring ) )
	if len( rings ) < 2:
		return []


class MESH_OT_uvmaptogrid( bpy.types.Operator ):
	"""Map the uv verts of the selected UV Islands to a Grid"""
	bl_idname = 'mesh.rm_uvgridify'
	bl_label = 'Gridify'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode and
				context.tool_settings.use_uv_select_sync )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if not sel_mode[2]:
				return { 'CANCELLED' }

			uvlayer = rmmesh.active_uv

			faces = rmlib.rmPolygonSet.from_selection( rmmesh )
			for group in faces.group( use_seam=True ):
				rings = GetRings( group )

				#compute aspect ratio of grid
				avg_ring_len = 0.0
				avg_loop_len = 0.0
				for r in rings:
					for i in range( 1, len( r ) ):
						avg_ring_len += ( r[i].co - r[i-1].co ).length
				for i in range( len( rings[0] ) ):
					for j in range( 1, len( rings ) ):
						avg_loop_len += ( rings[j][i].co - rings[j-1][i].co ).length
				avg_ring_len /= len( rings )
				avg_loop_len /= len( rings[0] )
				aspect_ratio = avg_ring_len / avg_loop_len

				#set uv values
				u_step = 1.0 / len( rings )
				v_step = 1.0 / len( rings[0] )
				v = 0.0
				for i, r in enumerate( rings ):
					u = 0.0
					v += v_step
					for j, v in enumerate( r ):
						v[uvlayer].uv = ( u, v * aspect_ratio )
						u += u_step
			
		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvmaptogrid )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvmaptogrid )