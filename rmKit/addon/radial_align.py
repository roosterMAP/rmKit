import bpy
import bmesh
import rmKit.rmlib as rmlib
import mathutils
import math

def lookat_from_edge( e ):
	e_n = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	for p in e.link_faces:
		e_n += p.normal
	if e_n.length < 0.00000001:
		mathutils.Vector( ( 0.0, 0.0001, 1.0 ) )
	e_n.normalize()

	v1, v2 = e.verts
	e_t = v2.co - v1.co
	e_t = e_n.cross( e_t.normalized() )

	e_p = ( v1.co + v2.co ) * 0.5
	
	return rmlib.util.LookAt( e_n, e_t, e_p )

def circularize( vert_loop, context ):
	
	test_edges = set()
	for v in vert_loop:
		for e in v.link_edges:
			if e.other_vert( v ) in vert_loop:
				continue
			test_edges.add( e )
			
	co = context.scene.transform_orientation_slots[0].custom_orientation
	grid_matrix = mathutils.Matrix.Identity( 3 )
	if co is not None:
		grid_matrix = mathutils.Matrix( co.matrix ).to_3x3()
	
	min_dot = 1.0
	min_idx = -1
	for idx, e in enumerate( test_edges ):
		vec = ( e.verts[0].co - e.verts[1].co ).normalized()
		dot = 1.0
		for i in range( 3 ):
			dot = max( dot, abs( vec.dot( grid_matrix[i] ) ) )
		if dot <= min_dot:
			min_dot = dot
			min_idx = idx
			
	print( min_dot )
			
	vert_loop = vert_loop[min_idx:] + vert_loop[:min_idx]

	vcount = len( vert_loop )
	pos_loop = [ v.co.copy() for v in vert_loop ]
	
	#compute axis of rotation by summing all cross vecs
	rot_axis = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )	
	center = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	for i in range( vcount ):
		prev_p = pos_loop[i-1]
		p = pos_loop[i]
		center += p
		v = ( p - prev_p ).normalized()
		for j in range( vcount ):
			next_idx = ( i + j ) % vcount
			next_v = ( pos_loop[next_idx] - p ).normalized()
			cross = v.cross( next_v )
			if cross.length > 0.0001:
				rot_axis += cross
				break
	rot_axis.normalize()
	center *= 1.0 / float( vcount )
	
	#compute radius of circle
	radius = 0.0
	for p in pos_loop:
		radius += ( p - center ).length
	radius *= 1.0 / float( vcount )
	
	#set new vert positions
	new_pos_loop = []
	rot_quat = mathutils.Quaternion( rot_axis, math.pi * 2.0 / vcount )
	v = ( pos_loop[0] - center ).normalized()
	for i in range( vcount ):
		v.rotate( rot_quat )
		new_pos_loop.append( center + ( v * radius ) )
		vert_loop[i].co = new_pos_loop[-1]

class MESH_OT_radialalign( bpy.types.Operator ):
	bl_idname = 'mesh.rm_radialalign'
	bl_label = 'Radial Align'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			return { 'CANCELLED' }
			
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
				circularize( vert_loop, context )

		return { 'FINISHED' }
	
def register():
	print( 'register :: {}'.format( MESH_OT_radialalign.bl_idname ) )
	bpy.utils.register_class( MESH_OT_radialalign )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_radialalign.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_radialalign )