import bpy
import bmesh
import rmlib
import mathutils

def BridgeSurfaces( bm, faces1, faces2 ):
	new_faces = rmlib.rmPolygonSet( [] )

	#create edge loops from two poly surfaces
	loops_a = rmlib.rmEdgeSet( [ e for e in faces1.edges if e.is_boundary ] ).vert_chain()
	loops_b = rmlib.rmEdgeSet( [ e for e in faces2.edges if e.is_boundary ] ).vert_chain()

	for l_a in loops_a:
		p1 = mathutils.Vector( l_a[0].co.copy() )
		nearest_loop = None
		nearest_dist = 99999.9
		for l_b in loops_b:
			for v in l_b:
				p2 = mathutils.Vector( v.co.copy() )
				dist = ( p2 - p1 ).length
				if dist < nearest_dist:
					nearest_dist = dist
					nearest_loop = l_b
		if nearest_loop is None:
			continue

		loops = [ l_a, nearest_loop ]
	
		#check if loop1 is sorted based of a neigh face
		for i in range( 2 ):
			epts = ( loops[i][0], loops[i][1] )
			edge = rmlib.rmEdgeSet.from_endpoints( epts[0], epts[1] )
			face_verts = list( edge.link_faces[0].verts )
			vert_idx = face_verts.index( epts[1] )
			if face_verts[vert_idx-1] == epts[0]:
				loops[i].reverse()
		
		#align loop1 and loop2
		sample_pos = loops[0][0].co.copy()
		min_len = 9999999.9
		min_idx = -1
		for i, v in enumerate( loops[1] ):
			d = ( v.co - sample_pos ).length
			if d < min_len:
				min_len = d
				min_idx = i
			
		#bridge the loops
		vcount = len( loops[0] )
		for i in range( vcount ):
			j = ( min_idx + i ) % vcount
			quad = ( loops[0][i-1], loops[0][i], loops[1][j], loops[1][j-1] )
			new_faces.append( bm.faces.new( quad, faces1[0] ) )

	return new_faces


class MESH_OT_thicken( bpy.types.Operator ):
	"""Same as solidify, just with better controls."""
	bl_idname = 'mesh.rm_thicken'
	bl_label = 'Thicken'
	bl_options = { 'REGISTER', 'UNDO' }
	
	thickness: bpy.props.FloatProperty(
		name='Thickenss',
		default=1.0
	)

	center: bpy.props.BoolProperty(
		name='From Center',
		default=False
	)

	def cancel( self, context ):
		if hasattr( self, 'bmesh' ):
			if self.bmesh is not None:
				self.bmesh.free()
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )
		
		bm = self.bmesh.copy()

		polys = rmlib.rmPolygonSet( [ f for f in bm.faces if f.select ] )
		for g in polys.group():
			geom1 = bmesh.ops.duplicate( bm, geom=g )
			faces1 = rmlib.rmPolygonSet()
			for elem in geom1['geom']:
				if isinstance( elem, bmesh.types.BMFace ):
					faces1.append( elem )

			geom2 = bmesh.ops.duplicate( bm, geom=g )
			faces2 = rmlib.rmPolygonSet()
			for elem in geom2['geom']:
				if isinstance( elem, bmesh.types.BMFace ):
					faces2.append( elem )

			bm.verts.ensure_lookup_table()
			
			#bridget the two surfaces
			bridge_faces = BridgeSurfaces( bm, faces1, faces2 )			

			#offset verts
			if self.center:
				for v in faces1.vertices:
					v.co += mathutils.Vector( v.normal ) * abs( self.thickness ) * 0.5
				for v in faces2.vertices:
					v.co -= mathutils.Vector( v.normal ) * abs( self.thickness ) * 0.5
			else:
				for v in faces1.vertices:
					v.co += mathutils.Vector( v.normal ) * self.thickness

			#flip faces2
			bmesh.ops.reverse_faces( bm, faces=faces2, flip_multires=True )
			if self.thickness < 0.0:
				bmesh.ops.reverse_faces( bm, faces=( bridge_faces + faces1 + faces2 ), flip_multires=True )

		#delete original geo
		bmesh.ops.delete( bm, geom=polys, context='FACES' )

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
		elif event.type == 'MOUSEMOVE':
			delta_x = float( event.mouse_x - event.mouse_prev_press_x ) / context.region.width
			if delta_x != self.prev_delta:
				self.prev_delta = delta_x
				self.thickness = delta_x * 4.0
				self.execute( context )			
		elif event.type == 'ESC':
			return { 'CANCELLED' }

		return { 'RUNNING_MODAL' }
	
	def invoke( self, context, event ):
		self.bmesh = None
		self.prev_delta = 0

		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readme = True
				self.bmesh = rmmesh.bmesh.copy()
				
		context.window_manager.modal_handler_add( self )
		return { 'RUNNING_MODAL' }


def register():
	bpy.utils.register_class( MESH_OT_thicken )
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_thicken )