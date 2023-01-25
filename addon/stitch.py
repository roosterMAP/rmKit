import bpy, bmesh, mathutils
from .. import rmlib
import math


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
				prev_loop.tag = False
				break	
		
	return rmlib.rmUVLoopSet( sorted_loops, uvlayer=loops.uvlayer )


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
	#determines if we should stitch at midpoint between source and target loops
	target_loops_selected = True
	for tl in target_loops:
		if not tl[uvlayer].select_edge:
			target_loops_selected = False
			break
		
	#complete lists of source and target loops so that their very lists match
	source_loops.append( source_loops[-1].link_loop_next )
	target_loops.reverse()
	target_loops.append( target_loops[-1].link_loop_next )
	
	#determine if source and target are the same loop
	target_island = target_loops.group_vertices( element=True )[0]
	is_same_island = source_loops[0] in target_island
	
	#transform target island such that the endpoints of target_loops lie on top of the endpoints of source_loops
	if not is_same_island:
		source_poslist = [ mathutils.Vector( l[uvlayer].uv.copy() ) for l in source_loops ]
		target_poslist = [ mathutils.Vector( l[uvlayer].uv.copy() ) for l in target_loops ]
		
		source_avg = mathutils.Vector( ( 0.0, 0.0 ) )
		for pos in source_poslist:
			source_avg += pos
		source_avg /= len( source_poslist )
		target_avg = mathutils.Vector( ( 0.0, 0.0 ) )
		for pos in target_poslist:
			target_avg += pos
		target_avg /= len( target_poslist )
		
		source_vec = source_poslist[0] - source_poslist[-1]
		source_pos = ( source_poslist[0] + source_poslist[-1] + source_avg ) * 0.33333
		target_vec = target_poslist[0] - target_poslist[-1]
		target_pos = ( target_poslist[0] + target_poslist[-1] + target_avg ) * 0.33333
		
		#compute scale
		scale_factor = source_vec.length / target_vec.length
		
		source_vec.normalize()
		target_vec.normalize()
		
		#compute rotation
		rotation_angle = rmlib.util.CCW_Angle2D( target_vec, source_vec )
		r1 = [ math.cos( rotation_angle ), -math.sin( rotation_angle ) ]
		r2 = [ math.sin( rotation_angle ), math.cos( rotation_angle ) ]
		rot = mathutils.Matrix( [ r1, r2 ] )
		target_vec = rot @ target_vec
		if source_vec.dot( target_vec ) > 0:
			rotation_angle += math.pi
		
		#compute translation
		offset = source_pos - target_pos
		
		#scale offset by half if we are stitching at midpoint
		if target_loops_selected:
			rotation_angle *= 0.5
			offset *= 0.5	
		
		#build orientation matrix
		r1 = [ math.cos( rotation_angle ), -math.sin( rotation_angle ) ]
		r2 = [ math.sin( rotation_angle ), math.cos( rotation_angle ) ]
		rot = mathutils.Matrix( [ r1, r2 ] )
		scl = mathutils.Matrix( [ [ scale_factor, 0.0 ], [ 0.0, scale_factor ] ] )
		targ_mat = scl @ rot
		
		#transform target island into position		
		for l in target_island:
			new_uv = mathutils.Vector( l[uvlayer].uv )
			new_uv -= target_pos
			new_uv = targ_mat @ new_uv
			new_uv += target_pos + offset
			l[uvlayer].uv = new_uv
			
		#transform source island by inverse of target island transform if we are stitching at midpoint
		if target_loops_selected:
			source_island = source_loops.group_vertices( element=True )[0]
			r1 = [ math.cos( rotation_angle ), -math.sin( rotation_angle ) ]
			r2 = [ math.sin( rotation_angle ), math.cos( rotation_angle ) ]
			rot = mathutils.Matrix( [ r1, r2 ] )
			src_mat = rot.inverted()			
			for l in source_island:
				new_uv = mathutils.Vector( l[uvlayer].uv )
				new_uv -= source_pos
				new_uv = src_mat @ new_uv
				new_uv += source_pos - offset
				l[uvlayer].uv = new_uv
		
	#stitch target loops to source loops		
	tagged_loops = set()
	for i in range( len( source_loops ) ):
		sl = source_loops[i]		
		sv = sl.vert
		if sv.tag:
			continue
		sl_uv = sl[uvlayer].uv
		s_linkloops = []
		for nl in sv.link_loops:
			if rmlib.util.AlmostEqual_v2( sl[uvlayer].uv, nl[uvlayer].uv ):
				s_linkloops.append( nl )
				tagged_loops.add( nl )
		for j in range( len( target_loops ) ):
			tl = target_loops[j]
			tv = tl.vert
			if tl.tag or sv != tv:
				continue
			t_linkloops = []
			for nl in tv.link_loops:
				if rmlib.util.AlmostEqual_v2( tl[uvlayer].uv, nl[uvlayer].uv ):
					t_linkloops.append( nl )
					tagged_loops.add( nl )
			if is_same_island:
				mp_uv = ( sl_uv + tl[uvlayer].uv ) * 0.5
				for l in s_linkloops + t_linkloops:
					l[uvlayer].uv = mp_uv
			else:
				for l in s_linkloops + t_linkloops:
					l[uvlayer].uv = sl_uv
			tv.tag = True
		sv.tag = True

	#untag stitched loops
	for l in tagged_loops:
		l.vert.tag = False
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

			sel_sync = context.tool_settings.use_uv_select_sync
			if sel_sync:
				edge_selection = rmlib.rmEdgeSet.from_selection( rmmesh )
				edgeloop_selection = rmlib.rmUVLoopSet( [], uvlayer=uvlayer )
				for p in edge_selection.polygons:
					for l in p.loops:
						l[uvlayer].select_edge = False
						if l.edge.select and len( l.edge.link_faces ) > 1:
							edgeloop_selection.append( l )
				border_edgeloop_selection = edgeloop_selection.border_loops()
				for l in border_edgeloop_selection:
					l[uvlayer].select_edge = True
			else:
				#get all selected uv edges that have corresponding disontinuous uv edge to stitch to
				edgeloop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh, uvlayer=uvlayer )
				border_edgeloop_selection = rmlib.rmUVLoopSet( [ l for l in edgeloop_selection if len( l.edge.link_faces ) > 1 ], uvlayer=uvlayer ).border_loops()
			
			#break up into groups
			edgeloop_groups = border_edgeloop_selection.group_edges()

			#iterate through each group and stitch their islands
			source_groups = []
			target_groups = []
			processed_loops = set()
			for group in edgeloop_groups:				
				#start by sorting each edgeloop group
				loop_chain = sort_loop_chain( group )
				
				#its is possible for a chain of loops group to stitch to multiple other uv islands.
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
						
						tl = nl.link_loop_next
						if ( ( len( source_loops ) == 0 and len( target_loops ) == 0 ) or
						rmlib.util.AlmostEqual_v2( continuity_test_loop[uvlayer].uv, tl[uvlayer].uv ) ):
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

			#stiched source loops to target loops
			for i in range( len( source_groups ) ):
				stitch( source_groups[i], target_groups[i], uvlayer )

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvstitcht )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvstitcht )