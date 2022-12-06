import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

def sort_loop_chain( loops ):
	#sorts the loops by the "flow" of the winding of the member faces.
	for l in loops:
		l.tag = True

	sorted_loops = [ loops[0] ]
	loops[0].tag = False
	for i in range( 1, len( loops ) ):
		next_front_loop = sorted_loops[-1].link_loop_next
		for nl in next_front_loop.vert.link_loops:
			if nl.tag and nl in loops:
				sorted_loops.append( nl )
				nl.tag = False
				break

		for nl in sorted_loops[0].vert.link_loops:
			prev_loop = nl.link_loop_prev
			if prev_loop.tag and nl in loops:
				sorted_loops.insert( 0, prev_loop )
				nl.tag = False
				break	
		
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

			#get selection of faces
			faces = rmlib.rmPolygonSet()
			sel_sync = context.tool_settings.use_uv_select_sync
			if sel_sync or context.area.type == 'VIEW_3D':
				sel_mode = context.tool_settings.mesh_select_mode[:]
				if sel_mode[2]:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
				else:
					return { 'CANCELLED' }
				for f in rmmesh.bmesh.faces:
					f.select = False
			else:
				return { 'CANCELLED' }

			if len( faces ) < 1:
				return { 'CANCELLED' }
			
			bpy.ops.uv.unwrap( 'INVOKE_DEFAULT', method='CONFORMAL' )
			
			for group in faces.group( use_seam=True ):				
				#tag faces in group
				for f in group:
					f.tag = True
					
				print( '*********************************' )
					
				#get list of boundary loops
				bounary_loops = set()
				for f in group:
					for l in f.loops:
						e = l.edge
						if is_boundary( l ):
							bounary_loops.add( l )
				if len( bounary_loops ) < 4:
					continue

				#identify the four corners
				print( [ l.vert.index for l in list( bounary_loops ) ] )
				sorted_boundary_loops = sort_loop_chain( rmlib.rmUVLoopSet( bounary_loops, uvlayer=uvlayer ) )
				print( [ l.vert.index for l in sorted_boundary_loops ] )
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
				poop = []
				starting_idx = sorted_boundary_loops.index( corner_loops[0] )
				for i in range( lcount ):
					l = sorted_boundary_loops[ ( starting_idx + i ) % lcount ]
					poop.append( l.vert.index )
					if l in corner_loops:
						print( l.vert.index )
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
					for nl in l.vert.link_loops:
						if not nl.face.tag:
							continue
						print( "{}  {}".format( nl.vert.index, corner_uvs[corner_count] ) )
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
					for nl in l.vert.link_loops:
						if not nl.face.tag:
							continue
						if corner_count == 0:							
							nl[uvlayer].uv = ( uv[0], 0.0 )
						elif corner_count == 1:
							nl[uvlayer].uv = ( w, uv[1] )
						elif corner_count == 2:
							nl[uvlayer].uv = ( uv[0], h )
						else:
							l[uvlayer].uv = ( 0.0, uv[1] )
						nl[uvlayer].pin_uv = True
				
						
				#unwrap
				bpy.ops.uv.unwrap( 'INVOKE_DEFAULT', method='CONFORMAL' )
				for f in group:
					f.select = False
					for l in f.loops:
						l[uvlayer].pin_uv = False
				
				clear_tags( rmmesh )
			
			for f in faces:
				f.select = True
			
		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvrectangularize )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvrectangularize )