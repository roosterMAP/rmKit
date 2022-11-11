import bpy
import bmesh
import rmKit.rmlib as rmlib
import mathutils
import math

def circularize( vert_loop, workplane ):
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

	#sort verts such that the first rotation occurs on one most aligned with an axis
	m = workplane.matrix
	max_dot = -1.0
	start_idx = 0
	for i in range( vcount ):
		vec = ( pos_loop[i] - center ).normalized()
		for j in range( 3 ):
			dot = abs( vec.dot( m[j] ) )
			if dot > max_dot:
				max_dot = dot
				start_idx = i
	vert_loop = vert_loop[start_idx:] + vert_loop[:start_idx]
	pos_loop = pos_loop[start_idx:] + pos_loop[:start_idx]
	
	#compute radius of circle
	radius = 0.0
	for p in pos_loop:
		radius += ( p - center ).length
	radius *= 1.0 / float( vcount )
	
	#set new vert positions
	new_pos_loop = []
	rot_quat = mathutils.Quaternion( rot_axis, math.pi * 2.0 / vcount )
	v = ( pos_loop[0] - center ).normalized()
	vert_loop[0].co = center + v * radius
	for i in range( 1, vcount ):
		v.rotate( rot_quat )
		vert_loop[i].co = center + v * radius	
	

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