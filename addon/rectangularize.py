import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib
import sys

def shortest_path( source, end_verts, verts ):
	for v in verts:
		v.tag = True

	#fill dist_lookup with max values
	dist_lookup = {}
	for v in verts:
		dist_lookup[v] = sys.float_info.max
	dist_lookup[source] = 0.0

	innerSet = set( [ v for v in end_verts ] )

	#expand and fill dist_lookup until an end vert is found
	current = source
	while len( innerSet ) > 0:
		nearest_neighbor = None
		smallest_tentative_dist = sys.float_info.max
		for ne in current.link_edges:
			neighbor = ne.other_vert( current )
			if not neighbor.tag:
				continue
			dist = ( mathutils.Vector( current.co ) - mathutils.Vector( neighbor.co ) ).length
			tentative_dist = dist_lookup[current] + dist
			if tentative_dist < dist_lookup[neighbor]:
				dist_lookup[neighbor] = tentative_dist
			else:
				tentative_dist = dist_lookup[neighbor]
			if tentative_dist < smallest_tentative_dist:
				smallest_tentative_dist = tentative_dist
				nearest_neighbor = neighbor
		if nearest_neighbor is None:
			break
		current.tag = False
		current = nearest_neighbor
		if current in innerSet:
			innerSet.remove( current )

	min_dist = sys.float_info.max
	nearest_end_vert = None
	for nv in end_verts:
		if dist_lookup[nv] < min_dist:
			min_dist = dist_lookup[nv]
			nearest_end_vert = nv
	if nearest_end_vert is None:
		return []

	#go backwards to find the shortest path
	current = nearest_end_vert
	shortest_path = []
	while current != source:
		min_dist = sys.float_info.max
		prev_neighbor = None
		for ne in current.link_edges:
			neighbor = ne.other_vert( current )
			if neighbor.tag:
				continue
			if dist_lookup[neighbor] < min_dist and dist_lookup[neighbor] < dist_lookup[current]:
				min_dist = dist_lookup[neighbor]
				prev_neighbor = neighbor
		shortest_path.append( current )	
		if prev_neighbor is None:
			break
		current = prev_neighbor
	shortest_path.append( source )

	for v in verts:
		v.tag = False

	return shortest_path[::-1]


def next_boundary_loop( loop ):
	next_loop = loop.link_loop_next
	while not is_boundary( next_loop ):
		l = next_loop
		next_loop = None
		for other_f in l.edge.link_faces:
			if other_f != l.face:
				break
		for nl in other_f.loops:
			if nl.edge == l.edge:
				next_loop = nl.link_loop_next
				break
		if next_loop is None:
			next_loop = l
			break
	return next_loop


def prev_boundary_loop( loop ):
	prev_loops = [ loop.link_loop_prev ]
	prev_loop = prev_loops[0]
	while not is_boundary( prev_loop ):
		l = prev_loop
		prev_loop = None
		for other_f in l.edge.link_faces:
			if other_f != l.face:
				break
		for nl in other_f.loops:
			if nl.edge == l.edge:
				prev_loop = nl.link_loop_prev
				prev_loops.append( prev_loop )
				break
		if prev_loop is None:
			prev_loop = l
			break
	return prev_loops


def sort_loop_chain( loops ):
	#sorts the loops by the "flow" of the winding of the member faces.
	for l in loops:
		l.tag = True

	sorted_loops = [ loops[0] ]
	loops[0].tag = False
	for i in range( 1, len( loops ) ):

		#append to end
		nl = next_boundary_loop( sorted_loops[-1] )
		if nl.tag:
			nl.tag = False
			sorted_loops.append( nl )

		#insert to start
		pls = prev_boundary_loop( sorted_loops[0] )
		pl = pls[-1]
		if pl.tag:
			pl.tag = False
			sorted_loops.insert( 0, pl )

		if len( sorted_loops ) >= len( loops ):
			break

	print( [ l.vert.index for l in sorted_loops ] )
		
	return rmlib.rmUVLoopSet( sorted_loops, uvlayer=loops.uvlayer )


def clear_tags( rmmesh ):
	for v in rmmesh.bmesh.verts:
		v.tag = False
	for e in rmmesh.bmesh.edges:
		e.tag = False
	for f in rmmesh.bmesh.faces:
		f.tag = False
		for l in f.loops:
			l.tag = False
			
def is_boundary( l ):
	if l.edge.seam or l.edge.is_boundary:
		return True
	else:
		for nf in l.edge.link_faces:
			if nf != l.face and not nf.tag:
				return True
	return False

def GetBoundaryLoops( faces ):
	bounary_loops = set()
	for f in faces:
		for l in f.loops:
			if is_boundary( l ):
				bounary_loops.add( l )
	return bounary_loops

class MESH_OT_uvrectangularize( bpy.types.Operator ):
	"""Map the selection to a box."""
	bl_idname = 'mesh.rm_uvrectangularize'
	bl_label = 'Rectangularize'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( ( context.area.type == 'VIEW_3D' or context.area.type == 'IMAGE_EDITOR' ) and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		face_indexes = set()
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			clear_tags( rmmesh )

			initial_selection = set()
			initial_loop_selection = set()

			#get selection of faces
			faces = rmlib.rmPolygonSet()
			sel_sync = context.tool_settings.use_uv_select_sync
			sel_mode = context.tool_settings.mesh_select_mode[:]
			uv_sel_mode = context.tool_settings.uv_select_mode
			if sel_sync or context.area.type == 'VIEW_3D':
				
				if sel_mode[2]:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
				else:
					return { 'CANCELLED' }
				for f in rmmesh.bmesh.faces:
					f.select = False
			else:
				sel_mode = context.tool_settings.mesh_select_mode[:]
				if sel_mode[0]:
					for v in rmmesh.bmesh.verts:
						if v.select:
							initial_selection.add( v )
				elif sel_mode[1]:
					for e in rmmesh.bmesh.edges:
						if e.select:
							initial_selection.add( e )
				elif sel_mode[2]:
					for f in rmmesh.bmesh.faces:
						if f.select:
							initial_selection.add( f )

				if uv_sel_mode == 'FACE':
					loops = rmlib.rmUVLoopSet.from_selection( rmmesh, uvlayer=uvlayer )
					initial_loop_selection = set( [ l for l in loops ] )
					loop_faces = set()
					for l in loops:
						loop_faces.add( l.face )
						l.tag = True
					for f in loop_faces:
						all_loops_tagged = True
						for l in f.loops:
							if not l.tag:
								all_loops_tagged = False
							else:
								l.tag = False
						if all_loops_tagged:
							faces.append( f )

					context.tool_settings.use_uv_select_sync = True
					bpy.ops.mesh.select_mode( type='FACE' )
					bpy.ops.mesh.select_all( action = 'DESELECT' )

				else:
					return { 'CANCELLED' }

			if len( faces ) < 1:
				return { 'CANCELLED' }
			
			for group in faces.group( use_seam=True ):
				clear_tags( rmmesh )

				#tag faces in group
				for f in group:
					f.tag = True
					
				#get list of boundary loops
				bounary_loops = GetBoundaryLoops( group )
				if len( bounary_loops ) < 4:
						continue

				#if there are exactly two boundary_loop_groups then we assume the shape a cylinder and
				#we need to add seam edges to map it to a plane.
				boundary_edge_groups = rmlib.rmEdgeSet( [ l.edge for l in bounary_loops ] ).chain()
				if ( len( boundary_edge_groups ) == 2 and
				boundary_edge_groups[0][0][0] == boundary_edge_groups[0][-1][-1] and
				boundary_edge_groups[-1][0][0] == boundary_edge_groups[-1][-1][-1] ):
					starting_vert = boundary_edge_groups[0][0][0]
					end_verts = [ pair[0] for pair in boundary_edge_groups[-1] ]
					all_verts = group.vertices
					path_verts = shortest_path( starting_vert, end_verts, all_verts )
					for i in range( 1, len( path_verts ) ):
						e = rmlib.rmEdgeSet.from_endpoints( path_verts[i-1], path_verts[i] )
						e.seam = True
					bounary_loops = GetBoundaryLoops( group )
					if len( bounary_loops ) < 4:
							continue

				print( 'boundary_edge_groups :: {}'.format( len( boundary_edge_groups ) ) )

				#identify the four corners
				sorted_boundary_loops = sort_loop_chain( rmlib.rmUVLoopSet( bounary_loops, uvlayer=uvlayer ) )
				sorted_tuples = []
				lcount = len( sorted_boundary_loops )
				for i, l in enumerate( sorted_boundary_loops ):
					prev_l = sorted_boundary_loops[i-1]
					next_l = sorted_boundary_loops[(i+1)%lcount]
					v1 = ( mathutils.Vector( prev_l.vert.co ) - mathutils.Vector( l.vert.co ) ).normalized()
					v2 = ( mathutils.Vector( next_l.vert.co ) - mathutils.Vector( l.vert.co ) ).normalized()
					sorted_tuples.append( ( abs( v1.dot( v2 ) ), l ) )
				sorted_tuples = sorted( sorted_tuples, key=lambda x: x[0] )
				corner_loops = [ p[1] for p in sorted_tuples ][:4]

				#compute the distance between the cornders
				distance_between_corners = []
				starting_idx = sorted_boundary_loops.index( corner_loops[0] )
				for i in range( lcount ):
					l = sorted_boundary_loops[ ( starting_idx + i ) % lcount ]
					if l in corner_loops:
						distance_between_corners.append( 0.0 )
					next_l = sorted_boundary_loops[ ( starting_idx + i + 1 ) % lcount ]
					d = ( mathutils.Vector( next_l.vert.co ) - mathutils.Vector( l.vert.co ) ).length
					distance_between_corners[-1] += d

				#normalize distances
				max_dist = -1.0
				for d in distance_between_corners:
					max_dist = max( max_dist, d )
				for i in range( 4 ):
					distance_between_corners[i] /= max_dist

				#set and pin loops to said corners
				w = ( distance_between_corners[0] + distance_between_corners[2] ) / 2.0
				h = ( distance_between_corners[1] + distance_between_corners[3] ) / 2.0
				corner_uvs = [ ( 0.0, 0.0 ), ( w, 0.0 ), ( w, h ), ( 0.0, h ) ]
				pinned_loops = set()
				corner_count = -1
				for i in range( lcount ):					
					l = sorted_boundary_loops[ ( starting_idx + i ) % lcount ]
					if l not in corner_loops:
						continue
					corner_count += 1
					uv = l[uvlayer].uv.copy()
					pls = prev_boundary_loop( l )
					for nl in pls:
						nl = nl.link_loop_next
						nl[uvlayer].uv = corner_uvs[corner_count]
						nl[uvlayer].pin_uv = True
						pinned_loops.add( nl )
					
				#unwrap
				for f in group:
					f.select = True
				bpy.ops.uv.unwrap( 'INVOKE_DEFAULT', method='CONFORMAL' )

				corner_count = -1
				for i in range( lcount ):
					l = sorted_boundary_loops[ ( starting_idx + i ) % lcount ]
					uv = l[uvlayer].uv.copy()
					if l in corner_loops:
						corner_count += 1
					for nl in prev_boundary_loop( l ):
						nl = nl.link_loop_next
						if corner_count == 0:
							nl[uvlayer].uv = ( uv[0], 0.0 )
						elif corner_count == 1:
							nl[uvlayer].uv = ( w, uv[1] )
						elif corner_count == 2:
							nl[uvlayer].uv = ( uv[0], h )
						else:
							nl[uvlayer].uv = ( 0.0, uv[1] )
						nl[uvlayer].pin_uv = True
						
				#unwrap				
				bpy.ops.uv.unwrap( 'INVOKE_DEFAULT', method='CONFORMAL' )
				for f in group:
					f.select = False
					for l in f.loops:
						l[uvlayer].pin_uv = False
				
				clear_tags( rmmesh )
			
			#restore selection if not in sync_mode
			if not sel_sync and uv_sel_mode == 'FACE':
				context.tool_settings.use_uv_select_sync = False
				if sel_mode[0]:
					bpy.ops.mesh.select_mode( type='VERT' )
				elif sel_mode[1]:
					bpy.ops.mesh.select_mode( type='EDGE' )
				elif sel_mode[2]:
					bpy.ops.mesh.select_mode( type='FACE' )
				bpy.ops.mesh.select_all( action = 'DESELECT' )
				for elem in initial_selection:
					elem.select = True
				for l in initial_loop_selection:
					l[uvlayer].select = True
			else:
				for f in faces:
					f.select = True


		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvrectangularize )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvrectangularize )