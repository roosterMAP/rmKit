import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib
import math


def sort_loop_chain( loops ):
	for l in loops:
		l.tag = True

	sorted_loops = []
	for i in range( len( loops ) ):
		next_front_loop = sorted_loops[-1].next_link_loop
		for nl in next_front_loop.vert.link_loops:
			if nl.tag:
				sorted_loops.append( nl )
				break

		for nl in sorted_loops[0].vert.link_loops:
			prev_loop = nl.prev_link_loop
			if prev_loop.tag:
				sorted_loops.inset( 0, prev_loop )
				break

	for l in loops:
		l.tag = False
		
	return rmlib.rmUVLoopSet( sorted_loops, uvlayer=loops.uvlayer )


def lsf_line( poslist ):
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

	slope = len( poslist ) * sum_xy - sum_x * sum_y / ( len( poslist ) * sum_xx - sum_x * sum_x )
	y_intercept = ( sum_y * sum_xx - sum_x * sum_xy ) / ( len( poslist ) * sum_xx - sum_x * sum_x )

	return slope, y_intercept


def uv_flipped( tri_verts, uvlayer ):
	p1 = tri_verts[0][uvlayer].uv
	p2 = tri_verts[1][uvlayer].uv
	p3 = tri_verts[2][uvlayer].uv

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

	return m.determinant() < 0.0
	

def stitch( source_loops, target_loops, uvlayer ):
	source_loops = source_loops.add_overlapping_loops()
	target_loops = target_loops.add_overlapping_loops()
	target_island = target_loops.group_vertices( element=True )[0]

	is_same_island = source_loops[0] in target_island

	if not is_same_island:
		source_poslist = [ mathutils.Vector( l[uvlayer].uv ) for l in source_loops ]
		target_poslist = [ mathutils.Vector( l[uvlayer].uv ) for l in target_loops ]
	
		#compute the amt by which the target island must be scales
		source_scale = ( source_poslist[0] - source_poslist[-1] ).length()
		target_scale = ( target_poslist[0] - target_poslist[-1] ).length()
		scale_factor = source_scale / target_scale

		#compuite the amt by which the target island must be rotated
		source_slope = lsf_line( source_poslist )[0]
		target_slope = lsf_line( target_poslist )[0]
		rotation_angle = math.tan2( ( source_slope - target_slope ) / ( 1.0 + source_slope * target_slope ) )

		#check if target island needs to be rotated an additional 180 degrees
		v1 = ( source_poslist[0] - target_poslist[0] ).normalized()
		v2 = ( source_poslist[-1] - target_poslist[-1] ).normalized()
		v3 = ( source_poslist[0] - target_poslist[-1] ).normalized()
		v4 = ( source_poslist[-1] - target_poslist[-1] ).normalized()
		if v1.dot( v2 ) < v3.dot( v4 ):
			rotation_angle += math.pi

		#determine if target island needs to be flipped
		source_tri = source_loops[0].face.vertices[:3]
		source_flipped = uv_flipped( source_tri )
		target_tri = source_loops[0].face.vertices[:3]
		target_flipped = uv_flipped( target_tri )
		if source_flipped != target_flipped:
			scale_factor *= -1.0
			rotation_angle += math.pi

		#compute the transform required to move the target island into position for stitching
		source_midpoint = ( source_poslist[0] + source_poslist[-1] ) * 0.5
		target_midpoint = ( target_poslist[0] + target_poslist[-1] ) * 0.5
		source_v = source_midpoint - source_poslist[0]
		source_center = source_poslist[0] + source_v.proj( source_midpoint )
		target_v = target_midpoint - target_poslist[0]
		target_center = target_poslist[0] + source_v.proj( target_midpoint )
		offset = target_center - source_center

		#build transform matrix for target island
		euler = mathutils.Euler( 0.0, 0.0, rotation_angle )
		scale = mathutils.Vector( scale_factor, scale_factor, scale_factor )
		transform = mathutils.Matrix.LocRotScale( offset, euler, scale ).to_3x3()

		#transform target island into position
		for l in target_island:
			l[uvlayer].uv = transform @ mathutils.Vector( l[uvlayer].uv )

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
				tl[uvlayer].uv = ( tl[uvlayer].uv + sl[uvlayer].uv ) * 0.5
			else:
				tl[uvlayer].uv = sl[uvlayer].uv
			tl_idx += 1
		sv.tag = True

	#tag stitched loops
	for l in source_loops:
		l.tag = True
	for l in target_loops:
		l.tag = True


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

			#get all selected uv edges that have corresponding disontinuous uv edge to stitch to
			edgeloop_selection = rmlib.rmUVLoopSet.from_edge_selection( context, uvlayer=uvlayer )
			border_edgeloop_selection = rmlib.rmUVLoopSet( [ l for l in edgeloop_selection if len( l.edge.link_faces ) < 2 ], uvlayer=uvlayer ).border_loops()
			
			#break up into groups
			edgeloop_groups = border_edgeloop_selection.group_edges()

			#iterate through each group and stitch their islands
			for group in edgeloop_groups:
				loop_chain = sort_loop_chain( group )
				continuity_test_loop = loop_chain[0]

				source_loops = rmlib.rmUVLoopSet( [], uvlayer=uvlayer )
				target_loops = rmlib.rmUVLoopSet( [], uvlayer=uvlayer )
				for l in loop_chain:
					if l.tag:
						continue

					source_loops.append( l )

					for nl in l.next_link_loop.vert.link_loops:
						if nl.edge != l.edge:
							continue
						
						tl = nl.prev_link_loop
						if rmlib.util.AlmostEquals_v2( continuity_test_loop[uvlayer].uv, tl[uvlayer].uv ):
							target_loops.append( tl )
						else:
							stitch( source_loops[:-1], target_loops, uvlayer )
							source_loops = rmlib.rmUVLoopSet( [l], uvlayer=uvlayer )
							target_loops = rmlib.rmUVLoopSet( [tl], uvlayer=uvlayer )
						continuity_test_loop = nl

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvstitcht )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvstitcht )