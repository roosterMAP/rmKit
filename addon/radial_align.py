import bpy
import bmesh
from .. import rmlib
import mathutils
import math

def circularize( vert_loop, matrix ):
	vcount = len( vert_loop )
	pos_loop = [ v.co.copy() for v in vert_loop ]
	
	#init delta vec by findin a vec that most aligns with a grid axis.
	#this vec is a sum of the cross vecs. each cross is between a boudary edge vec and the axis of rotation.
	#we skip baundary edge vecs that are too closely aligned with the prev one.
	rot_axis = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	center = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	prev_vec = ( vert_loop[0].co - vert_loop[-1].co ).normalized()
	prev_vert = vert_loop[-1]
	max_dot = -1.0
	delta_vec_before_first_rot = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	delta_vec_verts = []
	count = 0
	for i in range( vcount ):
		curr_vec = ( pos_loop[(i+1)%vcount] - pos_loop[i] ).normalized()
		if curr_vec.angle( prev_vec ) <= math.radians( 0.1 ):
			continue
		rot_axis += prev_vec.cross( curr_vec )
		center += pos_loop[i]
		prev_vec = curr_vec
		count += 1

		vec_out = ( pos_loop[i-1] - pos_loop[i] ).normalized()
		vec_out = vec_out.cross( rot_axis ).normalized()
		for j in range( 3 ):
			dot_out = abs( vec_out.dot( matrix[j] ) )
			if dot_out >= max_dot:
				max_dot = dot_out
				delta_vec_verts = [prev_vert, vert_loop[i]]
				delta_vec_before_first_rot = vec_out

		prev_vert = vert_loop[i]

	rot_axis.normalize()
	center *= 1.0 / count
	radius = 0.0
	for p in pos_loop:
		radius += ( p - center ).length
	radius *= 1.0 / float( vcount )
	
	#set new vert positions
	rot_quat = mathutils.Quaternion( rot_axis, math.pi * 2.0 / vcount )
	v = ( pos_loop[0] - center ).normalized()
	vert_loop[0].co = center + v * radius
	for i in range( 1, vcount ):
		v.rotate( rot_quat )
		vert_loop[i].co = center + v * radius
	
	#get the value of delta vec after initial rotation
	delta_vec_after_first_rot = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	if len( delta_vec_verts ) == 1:
		delta_vec_after_first_rot = ( delta_vec_verts[0].co - center ).normalized()
	else:
		delta_vec_after_first_rot = ( delta_vec_verts[0].co - delta_vec_verts[1].co ).normalized()
		delta_vec_after_first_rot = delta_vec_after_first_rot.cross( rot_axis ).normalized()
		
	#apply rotation from delta_vec to all verts to axis align the loop
	theta = rmlib.util.Angle2( delta_vec_before_first_rot, delta_vec_after_first_rot, rot_axis )
	rot_quat = mathutils.Quaternion( rot_axis, -theta )
	for i in range( vcount ):
		v = ( vert_loop[i].co - center ).normalized()
		v.rotate( rot_quat )
		vert_loop[i].co = center + v * radius
	

class MESH_OT_radialalign( bpy.types.Operator ):
	"""Map the verts that make up the edge selection or boundary of face selection to a circle."""
	bl_idname = 'mesh.rm_radialalign'
	bl_label = 'Radial Align'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			return { 'CANCELLED' }
			
		rm_wp = rmlib.rmCustomOrientation.from_selection( context )
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			if sel_mode[1]:
				edges = rmlib.rmEdgeSet.from_selection( rmmesh )
			elif sel_mode[2]:
				polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				edges = rmlib.rmEdgeSet()
				for p in polys:
					for e in p.edges:
						if e.is_boundary:
							edges.append( e )
							continue
						has_unselected_neigh = False
						for n_p in e.link_faces:
							if n_p != p and not n_p.select and e not in edges:
								edges.append( e )
								break
							
			for chain in edges.chain():
				if chain[0][0] != chain[-1][-1]:
					continue

				vert_loop = [ pair[0] for pair in chain ]
				circularize( vert_loop, rm_wp.matrix )

		return { 'FINISHED' }
	
def register():
	print( 'register :: {}'.format( MESH_OT_radialalign.bl_idname ) )
	bpy.utils.register_class( MESH_OT_radialalign )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_radialalign.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_radialalign )