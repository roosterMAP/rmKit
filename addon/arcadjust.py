import bpy
import bmesh
from .. import rmlib
import mathutils

def ScaleLine( p0, p1, scale ):
	v = p1 - p0
	m = v.length
	v.normalize()
	p0 -= v * m * 0.5 * scale
	p1 += v * m * 0.5 * scale
	return ( p0, p1 )

def arc_adjust( bm, scale ):
	edges = rmlib.rmEdgeSet( [ e for e in bm.edges if e.select ] )
	chains = edges.chain()
	for chain in chains:
		if len( chain ) < 3:
			continue

		a, b = ScaleLine( chain[0][0].co.copy(), chain[0][1].co.copy(), 10000.0 )
		c, d = ScaleLine( chain[-1][0].co.copy(), chain[-1][1].co.copy() , 10000.0 )
		p0, p1 = mathutils.geometry.intersect_line_line( a, b, c, d )
		c = ( p0 + p1 ) * 0.5
		s = mathutils.Matrix.Identity( 3 )
		s[0][0] = scale
		s[1][1] = scale
		s[2][2] = scale

		verts = rmlib.rmVertexSet()
		for pair in chain[1:]:
			if pair[0] not in verts:
				verts.append( pair[0] )
		for v in verts:
			pos = v.co - c
			pos = s @ pos
			v.co = pos + c

		if abs( scale ) <= 0.0000001:
			bmesh.ops.remove_doubles( bm, verts=verts, dist=0.00001 )

def ComputePlane( chain ):
	a, b = ScaleLine( chain[0].co.copy(), chain[1].co.copy(), 10000.0 )
	c, d = ScaleLine( chain[-1].co.copy(), chain[-2].co.copy() , 10000.0 )
	p0, p1 = mathutils.geometry.intersect_line_line( a, b, c, d )
	plane_pos = ( p0 + p1 ) * 0.5
	
	start_vec = chain[1].co - plane_pos
	start_vec.normalize()
	
	end_vec = chain[-2].co - plane_pos
	end_vec.normalize()

	plane_normal = start_vec.cross( end_vec )
	plane_normal.normalize()
	
	return plane_pos, plane_normal


def ComputeCircleCenter( chain ):
	plane_pos, plane_normal = ComputePlane( chain )
	
	start_vec = plane_pos - chain[1].co
	start_vec.normalize()
	
	end_vec = plane_pos - chain[-2].co
	end_vec.normalize()
	
	start_vec = start_vec.cross( plane_normal )
	start_vec.normalize()
	
	end_vec = plane_normal.cross( end_vec )
	end_vec.normalize()
	
	a, b = ScaleLine( chain[1].co.copy(), chain[1].co.copy() + start_vec, 10000.0 )
	c, d = ScaleLine( chain[-2].co.copy(), chain[-2].co.copy() + end_vec , 10000.0 )
	try:
		p0, p1 = mathutils.geometry.intersect_line_line( a, b, c, d )
	except TypeError:
		#no intersection
		return None, None
	circle_center = ( p0 + p1 ) * 0.5
	
	diagonal_vector = ( circle_center - plane_pos ).normalized()
	
	return circle_center, diagonal_vector
		

def GetFirstChainIdx( bm, chains ):
	active_edge = bm.select_history.active
	for i in range( len( chains ) ):
		for v in chains[i]:
			for e in v.link_edges:
				if e == active_edge:
					return i
	return 0


def RemapChain( chain, nearest_center ):
	plane_pos, plane_normal = ComputePlane( chain )
	d = rmlib.util.PlaneDistance( nearest_center, chain[1].co.copy(), plane_normal )
	center = nearest_center - ( plane_normal * d )
	
	vec = ( chain[0].co.copy() - chain[1].co.copy() ).normalized()
	in_vec = vec.cross( plane_normal )
	a, b = ScaleLine( center.copy(), center.copy() + in_vec, 10000.0 )
	c, d = ScaleLine( chain[1].co.copy(), chain[0].co.copy(), 10000.0 )
	foo, start_p = mathutils.geometry.intersect_line_line( a, b, c, d )
	
	vec = ( chain[-1].co.copy() - chain[-2].co.copy() ).normalized()
	in_vec = vec.cross( plane_normal )
	a, b = ScaleLine( center.copy(), center.copy() + in_vec, 10000.0 )
	c, d = ScaleLine( chain[-2].co.copy(), chain[-1].co.copy(), 10000.0 )
	foo, end_p = mathutils.geometry.intersect_line_line( a, b, c, d )
		
	start_vec = ( start_p - center ).normalized()
	end_vec = ( end_p - center ).normalized()
	
	cross_vec = start_vec.cross( end_vec )
	cross_vec.normalize()
	if plane_normal.dot( cross_vec ) < 0:
		plane_normal *= -1.0
		
	radian_step = start_vec.angle( end_vec ) / ( len( chain ) - 3 )
	rot_quat = mathutils.Quaternion( plane_normal, radian_step )
	
	vec = ( start_p - center )
	radius = vec.length
	vec.normalize()
	chain[1].co = start_p
	for i in range( 2, len( chain ) - 1 ):
		vec.rotate( rot_quat )
		chain[i].co = vec * radius + center	


def radial_arc_adjust( bm, scale ):
	edges = rmlib.rmEdgeSet( [ e for e in bm.edges if e.select ] )
	if len( edges ) < 3:
		return False
	
	chains = edges.vert_chain()
	for i in range( 1, len( chains ) ):
		a = ( chains[i][-2].co - chains[0][1].co ).length
		b = ( chains[i][1].co - chains[0][1].co ).length
		if a < b:
			chains[i].reverse()
						
	chain_idx = GetFirstChainIdx( bm, chains )
	circle_center, diagonal_vector = ComputeCircleCenter( chains[chain_idx] )
	if circle_center is None:
		return False
	circle_center += diagonal_vector * scale
	
	for chain in chains:
		if len( chain ) < 4:
			continue
		RemapChain( chain, circle_center )

	return True

class MESH_OT_arcadjust( bpy.types.Operator ):
	
	bl_idname = 'mesh.rm_arcadjust'
	bl_label = 'Arc Adjust'
	bl_options = { 'REGISTER', 'UNDO' }
	
	scale: bpy.props.FloatProperty(
		name='Scale',
		description='Scale applied to selected arc',
		default=1.0
	)

	radial: bpy.props.BoolProperty(
		name='Radial',
		default=False
	)

	def __init__( self ):
		self.bmesh = None

	def __del__( self ):
		try:
			if self.bmesh is not None:
				self.bmesh.free()
		except AttributeError:
			pass
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )
		
		bm = self.bmesh.copy()
		
		if self.radial:
			success = radial_arc_adjust( bm, self.scale - 1.0 )
			if not success:
				self.report( { 'WARNING' }, 'Invalid edge selection!!!' )
				return { 'CANCELLED' }
		else:
			arc_adjust( bm, self.scale )

		targetMesh = context.active_object.data
		bm.to_mesh( targetMesh )
		bm.calc_loop_triangles()
		targetMesh.update()
		bm.free()
		
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )
		
		return { 'FINISHED' }

	def modal( self, context, event ):
		if event.type == 'LEFTMOUSE':
			return { 'FINISHED' }
		elif event.type == 'RIGHTMOUSE':
			if event.value == 'RELEASE':
				self.radial = not self.radial
		elif event.type == 'MOUSEMOVE':
			delta_x = float( event.mouse_x - event.mouse_prev_press_x ) / context.region.width
			#delta_y = float( event.mouse_prev_press_y - event.mouse_y ) / context.region.height
			self.scale = 1.0 + ( delta_x * 4.0 )
			self.execute( context )			
		elif event.type == 'ESC':
			return { 'CANCELLED' }

		return { 'RUNNING_MODAL' }
	
	def invoke( self, context, event ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readme = True
				self.bmesh = rmmesh.bmesh.copy()
				
		context.window_manager.modal_handler_add( self )
		return { 'RUNNING_MODAL' }


class MESH_OT_unbevel( bpy.types.Operator ):
	bl_idname = 'mesh.rm_unbevel'
	bl_label = 'Unbevel'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		#get the selection mode
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }		

		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				arc_adjust( rmmesh.bmesh, 0.0 )
				
		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_arcadjust.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_unbevel.bl_idname ) )
	bpy.utils.register_class( MESH_OT_arcadjust )
	bpy.utils.register_class( MESH_OT_unbevel )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_arcadjust.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_arcadjust.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_arcadjust )
	bpy.utils.unregister_class( MESH_OT_unbevel )