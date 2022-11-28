import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib
import math, sys


def sort_loop_chain( loops ):
	#sorts the loops by the "flow" of the winding of the member faces.
	for l in loops:
		l.tag = True

	sorted_loops = [ loops[0] ]
	loops[0].tag = False
	for i in range( 1, len( loops ) ):
		next_front_loop = sorted_loops[-1].link_loop_next
		for nl in next_front_loop.vert.link_loops:
			if nl.tag:
				sorted_loops.append( nl )
				nl.tag = False
				break

		for nl in sorted_loops[0].vert.link_loops:
			prev_loop = nl.link_loop_prev
			if prev_loop.tag:
				sorted_loops.insert( 0, prev_loop )
				nl.tag = False
				break	
		
	return rmlib.rmUVLoopSet( sorted_loops, uvlayer=loops.uvlayer )


def lsf_line( poslist ):
	#uses least fit square to find a 2d line that best fits the poslist
	sum_x = 0.0
	sum_y = 0.0
	sum_xy = 0.0
	sum_xx = 0.0
	sum_yy = 0.0
	for p in poslist:
		sum_x += p[0]
		sum_y += p[1]
		sum_xy += p[0] * p[1]
		sum_xx += p[0] * p[0]
		sum_yy += p[1] * p[1]
		
	n = float( len( poslist ) )
	
	denom = n * sum_xx - sum_x * sum_x
	if denom > 0.00000001:
		slope = ( n * sum_xy - sum_x * sum_y ) / denom
		sign = 1.0
		if slope < 0.0:
			sign = -1.0
		y_intercept = ( sum_y - slope * sum_x ) / n
		p0 = mathutils.Vector( ( 0.0, y_intercept ) )
		p1 = mathutils.Vector( ( 1.0 / slope, y_intercept + 1.0 ) )
		return ( p1 - p0 ).normalized(), p0
	else:
		x_intercept = sum_x / n
		p0 = mathutils.Vector( ( x_intercept, 0.0 ) )
		return mathutils.Vector( ( 0.0, 1.0 ) ), p0


def tri_area( tri_loops, uvlayer ):
	#uses triangle determinant to compute triangle area. sign determines swizzle of verts
	p1 = tri_loops[0][uvlayer].uv
	p2 = tri_loops[1][uvlayer].uv
	p3 = tri_loops[2][uvlayer].uv

	m = mathutils.Matrix.Identity( 3 )
	m[0][0] = p1.x
	m[0][1] = p1.y
	m[0][2] = 1.0
	m[1][0] = p2.x
	m[1][1] = p2.y
	m[1][2] = 1.0
	m[2][0] = p3.x
	m[2][1] = p3.y
	m[2][2] = 1.0

	return m.determinant()


def ccw_angle2d( a, b ):
	det = a[0] * b[1] - a[1] * b[0] #determinant
	return math.atan2( det, a.dot( b ) )


def clear_all_tags( bmesh ):
	#should not be needed unless theres a bug in a previously run op
	for v in bmesh.verts:
		v.tag = False
	for e in bmesh.edges:
		e.tag = False
	for f in bmesh.faces:
		f.tag = False
		for l in f.loops:
			l.tag = False
	

def stitch( source_loops, target_loops, uvlayer ):
	target_loops_selected = True
	for tl in target_loops:
		if not tl[uvlayer].select_edge:
			target_loops_selected = False
			break
		
	source_loops.add_overlapping_loops( True )
	target_loops.add_overlapping_loops( True )
	target_loops.reverse()
	target_island = target_loops.group_vertices( element=True )[0]
	
	#print( '\tsource_loops :: {}'.format( source_loops ) )
	#print( '\ttarget_loops :: {}'.format( target_loops ) )
	#print( '\ttarget_island :: {}\n'.format( target_island ) )

	is_same_island = source_loops[0] in target_island

	if not is_same_island:
		source_poslist = [ mathutils.Vector( l[uvlayer].uv.copy() ) for l in source_loops ]
		target_poslist = [ mathutils.Vector( l[uvlayer].uv.copy() ) for l in target_loops ]
	
		#compute the amt by which the target island must be scales
		source_scale = ( source_poslist[0] - source_poslist[-1] ).length
		target_scale = ( target_poslist[0] - target_poslist[-1] ).length
		scale_factor = source_scale / target_scale

		#compuite the amt by which the target island must be rotated
		source_lfs_vec, source_lfs_pos = lsf_line( source_poslist )
		target_lfs_vec, target_lfs_pos = lsf_line( target_poslist )
		rotation_angle = ccw_angle2d( target_lfs_vec, source_lfs_vec )
		
		#print( 'source_lfs_pos :: {}'.format( source_lfs_pos ) )
		#print( 'target_lfs_pos :: {}'.format( target_lfs_pos ) )
		#print( 'source_lfs_vec :: {}'.format( source_lfs_vec ) )
		#print( 'target_lfs_vec :: {}'.format( target_lfs_vec ) )
		
		#check if target island needs to be rotated an additional 180 degrees
		intersection_2d = mathutils.geometry.intersect_line_line_2d( source_poslist[0], target_poslist[0], source_poslist[-1], target_poslist[-1] )
		if intersection_2d is not None:
			rotation_angle += math.pi
			
		#print( 'rotation_angle :: {}'.format( math.degrees( rotation_angle ) ) )

		'''
		#determine if target island needs to be flipped
		source_tri = source_loops[0].face.loops[:3]
		source_flipped = tri_area( source_tri, uvlayer )
		target_tri = source_loops[0].face.loops[:3]
		target_flipped = tri_area( target_tri, uvlayer )
		if ( source_flipped < 0.0 and target_flipped < 0.0 ) or ( source_flipped > 0.0 and target_flipped > 0.0  ):
			scale_factor *= -1.0
			rotation_angle = math.pi - rotation_angle
			print( 'inverted island' )
		'''
			
		#print( 'scale_factor :: {}'.format( scale_factor ) )

		#compute the transform required to move the target island into position for stitching
		source_midpoint = ( source_poslist[0] + source_poslist[-1] ) * 0.5
		target_midpoint = ( target_poslist[0] + target_poslist[-1] ) * 0.5
		source_v = source_midpoint - source_lfs_pos
		source_center = source_lfs_pos + rmlib.util.ProjectVector( source_v, source_lfs_vec )
		target_v = target_midpoint - target_lfs_pos
		target_center = target_lfs_pos + rmlib.util.ProjectVector( target_v, target_lfs_vec )
		offset = source_center - target_center
				
		#print( 'source_center :: {}'.format( source_center ) )
		#print( 'target_center :: {}'.format( target_center ) )
		
		if target_loops_selected:
			rotation_angle *= 0.5
			scale_factor *= 0.5
			offset *= 0.5			
		
		r1 = [ math.cos( rotation_angle ), -math.sin( rotation_angle ) ]
		r2 = [ math.sin( rotation_angle ), math.cos( rotation_angle ) ]
		rot = mathutils.Matrix( [ r1, r2 ] )
		scl = mathutils.Matrix( [ [ scale_factor, 0.0 ], [ 0.0, scale_factor ] ] )
		targ_mat = scl @ rot

		#transform target island into position
		for l in target_island:
			new_uv = mathutils.Vector( l[uvlayer].uv )
			new_uv -= target_center
			new_uv = targ_mat @ new_uv
			new_uv += target_center + offset
			l[uvlayer].uv = new_uv
			
		if target_loops_selected:
			source_island = source_loops.group_vertices( element=True )[0]
			src_mat = targ_mat.transposed()			
			for l in source_island:
				new_uv = mathutils.Vector( l[uvlayer].uv )
				new_uv -= source_center
				new_uv = src_mat @ new_uv
				new_uv += source_center - offset
				l[uvlayer].uv = new_uv
			
			
	#stitch target loops to source loops
	tl_idx = 0
	for sl in source_loops:
		sv = sl.vert
		if sv.tag:
			continue
		for i in range( tl_idx, len( target_loops ) ):
			tl = target_loops[i]
			tv = tl.vert
			if tv != sv:
				break
			if is_same_island:
				mid_pt = ( tl[uvlayer].uv + sl[uvlayer].uv ) * 0.5
				tl[uvlayer].uv = mid_pt
				sl[uvlayer].uv = mid_pt
			else:
				tl[uvlayer].uv = sl[uvlayer].uv
			tl_idx += 1
		sv.tag = True

	#untag stitched loops
	for l in source_loops:
		l.vert.tag = False
		l.tag = False
	for l in target_island:
		l.tag = False


class MESH_OT_uvstitcht( bpy.types.Operator ):
	"""Stitch together uv islands based on the user's uv edge selection."""
	bl_idname = 'mesh.rm_stitch'
	bl_label = 'Stitch'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			
			clear_all_tags( rmmesh.bmesh ) #shouldnt be needed

			#get all selected uv edges that have corresponding disontinuous uv edge to stitch to
			edgeloop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh, uvlayer=uvlayer )
			border_edgeloop_selection = rmlib.rmUVLoopSet( [ l for l in edgeloop_selection if len( l.edge.link_faces ) > 1 ], uvlayer=uvlayer ).border_loops()
			
			#print( '\n' )
			
			#break up into groups
			edgeloop_groups = border_edgeloop_selection.group_edges()

			#iterate through each group and stitch their islands
			source_groups = []
			target_groups = []
			processed_loops = set()
			for group in edgeloop_groups:				
				#start by sorting each edgeloop group
				loop_chain = sort_loop_chain( group )
				
				#print( 'loop_chain :: {}'.format( [ l.vert.index for l in loop_chain ] ) )

				#its is possible for a loop group to stitch to multiple other uv islands.
				#we iterate through each edge loop (source) and find the edge loop it stitches to (target).
				#use check if the current target is continuous with the previous target using the continuity_test_loop.
				#if we find a discontinuity, we stitch what we have and start over as we work down the edgeloop group
				source_loops = rmlib.rmUVLoopSet( [], uvlayer=uvlayer )
				target_loops = rmlib.rmUVLoopSet( [], uvlayer=uvlayer )
				continuity_test_loop = loop_chain[0]
				for l in loop_chain:
					if l in processed_loops:
						continue
					processed_loops.add( l )

					for nl in l.link_loop_next.vert.link_loops:
						if nl.edge != l.edge:
							continue
						processed_loops.add( nl )
						
						tl = nl
						if ( len( source_loops ) == 0 and len( target_loops ) == 0 ) or rmlib.util.AlmostEqual_v2( continuity_test_loop[uvlayer].uv, nl[uvlayer].uv ):
							source_loops.append( l )
							target_loops.append( nl )
						else:
							source_groups.append( source_loops )
							target_groups.append( target_loops )
							source_loops = rmlib.rmUVLoopSet( [l], uvlayer=uvlayer )
							target_loops = rmlib.rmUVLoopSet( [nl], uvlayer=uvlayer )

						continuity_test_loop = nl

					if len( source_loops ) > 0 and len( target_loops ) > 0:
						source_groups.append( source_loops )
						target_groups.append( target_loops )
						source_loops = rmlib.rmUVLoopSet( [], uvlayer=uvlayer )
						target_loops = rmlib.rmUVLoopSet( [], uvlayer=uvlayer )
					
			#print( 'STITCH START ::' )
			
			#for f in rmmesh.bmesh.faces:				
			#	print( 'f:{} -> {}  {}'.format( f.index, [ v.index for v in f.verts ], [ l.index for l in f.loops ] ) )

			#stiched source loops to target loops
			for i in range( len( source_groups ) ):				
				#print( '\t stitch {} to {}'.format( [ lp.vert.index for lp in source_groups[i] ], [ lp.vert.index for lp in target_groups[i] ] ) )
				stitch( source_groups[i], target_groups[i], uvlayer )
				
			'''
			for v in rmmesh.bmesh.verts:
				if v.tag: print( 'v' )
				v.tag = False
			for e in rmmesh.bmesh.edges:
				if e.tag: print( 'e' )
				e.tag = False
			for f in rmmesh.bmesh.faces:
				f.tag = False
				if f.tag: print( 'f' )
				for l in f.loops:
					if l.tag: print( 'l' )
					l.tag = False
			'''

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvstitcht )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvstitcht )