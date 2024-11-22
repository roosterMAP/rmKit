import bpy, mathutils
from .. import rmlib
import math

def GetUnsyncUVVisibleFaces( rmmesh, sel_mode ):
	visible_faces = rmlib.rmPolygonSet()
	if sel_mode[0]:		
		for f in rmmesh.bmesh.faces:
			if f.hide:
				continue
			visible = True
			for v in f.verts:
				if not v.select:
					visible = False
					break
			if visible:
				visible_faces.append( f )
	elif sel_mode[1]:
		for f in rmmesh.bmesh.faces:
			if f.hide:
				continue
			visible = True
			for e in f.edges:
				if not e.select:
					visible = False
					break
			if visible:
				visible_faces.append( f )
	else:
		visible_faces = rmlib.rmPolygonSet.from_selection( rmmesh )
		
	return visible_faces

def clear_tags( rmmesh ):
	for v in rmmesh.bmesh.verts:
		v.tag = False
	for e in rmmesh.bmesh.edges:
		e.tag = False
	for f in rmmesh.bmesh.faces:
		f.tag = False
		for l in f.loops:
			l.tag = False

class MESH_OT_uvunrotate( bpy.types.Operator ):
	"""Unrotate UV Islands based on the current selection."""
	bl_idname = 'mesh.rm_uvunrotate'
	bl_label = 'Unrotate'
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
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			loop_groups = []

			sel_sync = context.tool_settings.use_uv_select_sync
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if sel_sync:
				if sel_mode[0]:
					vert_selection = rmlib.rmVertexSet.from_selection( rmmesh )
					loopset = set()
					for v in vert_selection:
						loopset |= set( v.link_loops )
					loop_selection = rmlib.rmUVLoopSet( loopset, uvlayer=uvlayer )
					loop_groups = loop_selection.group_vertices( element=True )
				elif sel_mode[1]:
					edge_selection = rmlib.rmEdgeSet.from_selection( rmmesh )
					loop_selection = rmlib.rmUVLoopSet( edge_selection.vertices.loops, uvlayer=uvlayer )
					loop_groups = loop_selection.group_vertices( element=True )
				else:
					face_selection = rmlib.rmPolygonSet.from_selection( rmmesh )
					loopset = set()
					for f in face_selection:
						loopset |= set( f.loops )
					loop_selection = rmlib.rmUVLoopSet( loopset, uvlayer=uvlayer )
					loop_groups = loop_selection.group_vertices( element=True )

			else:
				sel_mode_uv = context.tool_settings.uv_select_mode
				visible_faces = GetUnsyncUVVisibleFaces( rmmesh, sel_mode )
				if sel_mode_uv == 'VERTEX':
					loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
					visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
					for l in loop_selection:
						if l.face in visible_faces:
							visible_loop_selection.append( l )
					clear_tags( rmmesh )
					loop_groups = visible_loop_selection.group_vertices()
					
				elif sel_mode_uv == 'EDGE':
					loop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh=rmmesh, uvlayer=uvlayer )
					visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
					for l in loop_selection:
						if l.face in visible_faces:
							visible_loop_selection.append( l )
					clear_tags( rmmesh )
					loop_groups = visible_loop_selection.group_vertices( element=True )

				else: #face
					loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
					visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
					for l in loop_selection:
						if l.face in visible_faces:
							visible_loop_selection.append( l )
					clear_tags( rmmesh )
					loop_groups = visible_loop_selection.group_vertices( element=True )

			if len( loop_groups ) == 0:
				return { 'CANCELLED' }

			for g in loop_groups:
				drive_vec = mathutils.Vector( ( 0.0, 0.0 ) )
				drive_center = mathutils.Vector( ( 0.0, 0.0 ) )
				if not sel_sync and sel_mode_uv == 'EDGE':
					#get uv edges to drive unrotate on this group					
					max_len = -1.0
					for l in g:
						if l[uvlayer].select_edge:
							pos1 = mathutils.Vector( l[uvlayer].uv )
							pos2 = mathutils.Vector( l.link_loop_next[uvlayer].uv )
							length = ( pos2 - pos1 ).length
							if length >= max_len:
								max_len = length
								drive_vec = ( pos2 - pos1 ).normalized()
								drive_center = ( pos2 + pos1 ) * 0.5
					regroup = g.group_vertices( element=True )
					g = regroup[0]
					for i in range( 1, len( regroup ) ):
						g += regroup[i]

				elif sel_sync and sel_mode[1]:
					#get bmedges that drive unrotate on this group
					max_len = -1.0
					for l in g:
						if l.edge.select:
							pos1 = mathutils.Vector( l[uvlayer].uv )
							pos2 = mathutils.Vector( l.link_loop_next[uvlayer].uv )
							length = ( pos2 - pos1 ).length
							if length >= max_len:
								max_len = length
								drive_vec = ( pos2 - pos1 ).normalized()
								drive_center = ( pos2 + pos1 ) * 0.5

				else:
					#find longest uv edge to drive unrotate on this group
					max_len = -1.0
					for l in g:
						pos1 = mathutils.Vector( l[uvlayer].uv )
						pos2 = mathutils.Vector( l.link_loop_next[uvlayer].uv )
						length = ( pos2 - pos1 ).length
						if length >= max_len:
							max_len = length
							drive_loop = l
							drive_vec = ( pos2 - pos1 ).normalized()
							drive_center = ( pos2 + pos1 ) * 0.5

				#find the axis vec most aligned with drive_vec
				test_vecs = ( mathutils.Vector( ( 1.0, 0.0 ) ),
							mathutils.Vector( ( -1.0, 0.0 ) ),
							mathutils.Vector( ( 0.0, 1.0 ) ),
							mathutils.Vector( ( 0.0, -1.0 ) ) )
				target_vec = test_vecs[0]
				max_dot = -1.0
				for v in test_vecs:
					dot = v.dot( drive_vec )
					if abs( dot ) > max_dot:
						target_vec = v
						max_dot = dot

				#compute rot matrix to align drive_vec to axis vec
				theta = rmlib.util.CCW_Angle2D( drive_vec, target_vec )
				r1 = [ math.cos( theta ), -math.sin( theta ) ]
				r2 = [ math.sin( theta ), math.cos( theta ) ]
				rot_mat = mathutils.Matrix( [ r1, r2 ] )

				#transform uvs
				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv.copy() )
					uv -= drive_center
					uv = rot_mat @ uv
					uv += drive_center
					l[uvlayer].uv = uv

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvunrotate )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvunrotate )