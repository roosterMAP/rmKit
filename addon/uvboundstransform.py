import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib
import gpu
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_location_3d

class Bounds2D():
	size = 6.0

	def __init__( self, context ):
		self.context = context
		self._min = mathutils.Vector( ( 0.0, 0.0 ) )
		self._max = mathutils.Vector( ( 1.0, 1.0 ) )
		self.regions = []
		
	def GenerateRegions( self ):
		a = mathutils.Vector( ( self._max.x - Bounds2D.size, self._min.y + Bounds2D.size ) )
		b = mathutils.Vector( ( self._max.x + Bounds2D.size, self._max.y - Bounds2D.size ) )
		c = mathutils.Vector( ( self._max.x - Bounds2D.size, self._min.y - Bounds2D.size ) )
		d = mathutils.Vector( ( self._max.x + Bounds2D.size, self._min.y + Bounds2D.size ) )
		e = mathutils.Vector( ( self._max.x - Bounds2D.size, self._max.y - Bounds2D.size ) )
		f = mathutils.Vector( ( self._max.x + Bounds2D.size, self._max.y + Bounds2D.size ) )
		g = mathutils.Vector( ( self._min.x + Bounds2D.size, self._max.y - Bounds2D.size ) )
		h = mathutils.Vector( ( self._max.x - Bounds2D.size, self._max.y + Bounds2D.size ) )
		i = mathutils.Vector( ( self._min.x - Bounds2D.size, self._max.y - Bounds2D.size ) )
		j = mathutils.Vector( ( self._min.x + Bounds2D.size, self._max.y + Bounds2D.size ) )
		k = mathutils.Vector( ( self._min.x - Bounds2D.size, self._min.y + Bounds2D.size ) )
		l = mathutils.Vector( ( self._min.x - Bounds2D.size, self._min.y - Bounds2D.size ) )
		m = mathutils.Vector( ( self._min.x + Bounds2D.size, self._min.y + Bounds2D.size ) )
		n = mathutils.Vector( ( self._min.x + Bounds2D.size, self._min.y - Bounds2D.size ) )

		self.regions.clear()
		self.regions.append( ( a, b ) )
		self.regions.append( ( c, d ) )
		self.regions.append( ( e, f ) )
		self.regions.append( ( g, h ) )
		self.regions.append( ( i, j ) )
		self.regions.append( ( k, g ) )
		self.regions.append( ( l, m ) )
		self.regions.append( ( n, a ) )
		self.regions.append( ( m, e ) )

	def TestRegion( self, i, mx, my ):
		r = self.regions[i]
		if mx > r[0][0] and my > r[0][1] and mx < r[1][0] and my < r[1][1]:
			return True
		return False
	
	@classmethod
	def from_uvs( cls, context, uvcoords ):
		points = []
		for uv in uvcoords:
			p  = context.region.view2d.view_to_region( uv[0], uv[1] )
			points.append( p )
		
		bounds = cls( context )
		bounds._min = mathutils.Vector( ( points[0][0], points[0][1] ) )
		bounds._max = mathutils.Vector( ( points[0][0], points[0][1] ) )
		for p in points:
			if p[0] < bounds._min[0]:
				bounds._min[0] = p[0]
			if p[1] < bounds._min[1]:
				bounds._min[1] = p[1]
			if p[0] > bounds._max[0]:
				bounds._max[0] = p[0]
			if p[1] > bounds._max[1]:
				bounds._max[1] = p[1]
		bounds.GenerateRegions()
		return bounds
		
	@classmethod
	def from_points( cls, context, points ):
		bounds = cls( context )
		bounds._min = mathutils.Vector( ( points[0][0], points[0][1] ) )
		bounds._max = mathutils.Vector( ( points[0][0], points[0][1] ) )
		for p in points:
			if p[0] < bounds._min[0]:
				bounds._min[0] = p[0]
			if p[1] < bounds._min[1]:
				bounds._min[1] = p[1]
			if p[0] > bounds._max[0]:
				bounds._max[0] = p[0]
			if p[1] > bounds._max[1]:
				bounds._max[1] = p[1]
		bounds.GenerateRegions()
		return bounds

	@property
	def center( self ):
		return ( self._min + self._max ) * 0.5

	def IsInside( self, u, v ):
		return u >= self._min[0] and u <= self._max[0] and v >= self._min[1] and v <= self._max[1]

	@property
	def corners( self ):
		return [ self._min, mathutils.Vector( ( self._min[0], self._max[1] ) ), self._max, mathutils.Vector( ( self._max[0], self._min[1] ) ) ]


class BoundsHandle():
	bounds = None
	shader = None
	batches = []
	handle = None
	active = False
	tool_handles_boxes = {}

	def __init__( self, context, bounds ):
		self.context = context
		BoundsHandle.bounds = bounds
		BoundsHandle.shader = gpu.shader.from_builtin( '2D_UNIFORM_COLOR' )
		self.shader_batch()
		self.mouse = ( 0.0, 0.0 )

	def update( self, context, m_x, m_y ):
		self.mouse = ( float( m_x ), float( m_y ) )
		self.shader_batch()
		
		for window in context.window_manager.windows:
			for area in window.screen.areas:
				if area.type == 'IMAGE_EDITOR':
					for region in area.regions:
						if region.type == 'WINDOW':
							region.tag_redraw()
									

	def shader_batch( self ):
		BoundsHandle.batches.clear()
		for r in BoundsHandle.bounds.regions:
			coords = [ r[0], mathutils.Vector( ( r[0][0], r[1][1] ) ), r[1], mathutils.Vector( ( r[1][0], r[0][1] ) ) ]
			BoundsHandle.batches.append( batch_for_shader( BoundsHandle.shader, 'LINES', { 'pos': ( coords[0], coords[1], coords[1], coords[2], coords[2], coords[3], coords[3], coords[0] ) } ) )

	def draw( self, context ):
		if len( BoundsHandle.batches ) >= 4:
			gpu.state.line_width_set( 2.0 )
			
			BoundsHandle.shader.bind()
			
			highlight_idx = -1
			BoundsHandle.shader.uniform_float( 'color', ( 0.4, 0.4, 0.4, 1.0 ) )
			for i in range( len( BoundsHandle.batches ) ):
				if BoundsHandle.bounds.TestRegion( i, self.mouse[0], self.mouse[1] ):
					highlight_idx = i					
				BoundsHandle.batches[i].draw( BoundsHandle.shader )
			if highlight_idx > -1:
				BoundsHandle.shader.uniform_float( 'color', ( 0.8, 0.75, 0.4, 1.0 ) )
				BoundsHandle.batches[highlight_idx].draw( BoundsHandle.shader )

			gpu.state.line_width_set( 1.0 )

	def doDraw( self, context ):
		BoundsHandle.handle = bpy.types.SpaceImageEditor.draw_handler_add( self.draw, (context, ), 'WINDOW', 'POST_PIXEL' )
		BoundsHandle.active = True
		
	def stopDraw( self, context ):
		bpy.types.SpaceImageEditor.draw_handler_remove( BoundsHandle.handle, 'WINDOW' )
		BoundsHandle.active = False

		for window in context.window_manager.windows:
			for area in window.screen.areas:
				if area.type == 'IMAGE_EDITOR':
					for region in area.regions:
						if region.type == 'WINDOW':
							region.tag_redraw()


def GetLoopSelection( context, rmmesh, uvlayer ):
	sel_sync = context.tool_settings.use_uv_select_sync
	if sel_sync:
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			vert_selection = rmlib.rmVertexSet.from_selection( rmmesh )
			return rmlib.rmUVLoopSet( vert_selection.loops, uvlayer=uvlayer )

		elif sel_mode[1]:
			edge_selection = rmlib.rmEdgeSet.from_selection( rmmesh )
			return rmlib.rmUVLoopSet( edge_selection.vertices.loops, uvlayer=uvlayer )

		elif sel_mode[2]:
			face_selection = rmlib.rmPolygonSet.from_selection( rmmesh )
			loopset = set()
			for f in face_selection:
				loopset |= set( f.loops )
			return rmlib.rmUVLoopSet( loopset, uvlayer=uvlayer )

	else:
		sel_mode = context.tool_settings.uv_select_mode
		if sel_mode == 'VERTEX':
			return rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )

		elif sel_mode == 'EDGE':
			loop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			loop_selection.add_overlapping_loops( True )
			return loop_selection

		elif sel_mode == 'FACE':
			return rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )

	return rmlib.rmUVLoopSet( [], uvlayer=uvlayer )


class MESH_OT_uvboundstransform( bpy.types.Operator ):
	"""Transform UV Selection with bbox tool handles."""
	bl_idname = 'mesh.rm_uvboundstransform'
	bl_label = 'Transform Bounds'
	bl_options = { 'REGISTER', 'UNDO' }
	BOUNDS_RENDER = None
	
	def __init__( self ):
		self.hit_idx = -1
		self.prev_press_x = 0.0
		self.prev_press_y = 0.0
		self.m_delta = ( 0.0, 0.0 )
		self.bmesh = None

	def __del__( self ):
		if self.bmesh is not None:
			self.bmesh.free()

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		if not MESH_OT_uvboundstransform.BOUNDS_RENDER:
			return { 'CANCELLED' }

		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )
		
		#fetch bmesh member and wrap in rmMesh to get loop selection
		bm = self.bmesh.copy()
		rmmesh = rmlib.rmMesh.from_bmesh( context.active_object, bm )
		if rmmesh is None:
			bpy.ops.object.mode_set( mode='EDIT', toggle=False )
			return { 'CANCELLED' }
		uvlayer = rmmesh.active_uv
		loop_selection = GetLoopSelection( context, rmmesh, uvlayer )
		if len( loop_selection ) < 2:
			bpy.ops.object.mode_set( mode='EDIT', toggle=False )
			return { 'CANCELLED' }

		#fetch tool bounding box from BOUNDS_RENDER
		tool_bounds = MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds
		uvmin = mathutils.Vector( context.region.view2d.region_to_view( tool_bounds._min[0], tool_bounds._min[1] ) )
		uvmax = mathutils.Vector( context.region.view2d.region_to_view( tool_bounds._max[0], tool_bounds._max[1] ) )
		tool_width = uvmax[0] - uvmin[0]
		tool_height = uvmax[1] - uvmin[1]
		tool_center = ( uvmin + uvmax ) * 0.5

		#compute loop_selection bounding box
		loop_sel_min = loop_selection[0][uvlayer].uv.copy()
		loop_sel_max = loop_selection[0][uvlayer].uv.copy()
		for l in loop_selection:
			uvcoord = l[uvlayer].uv.copy()
			for i in range( 2 ):
				if uvcoord[i] < loop_sel_min[i]:
					loop_sel_min[i] = uvcoord[i]
				if uvcoord[i] > loop_sel_max[i]:
					loop_sel_max[i] = uvcoord[i]
		loop_sel_width = loop_sel_max[0] - loop_sel_min[0]
		loop_sel_height = loop_sel_max[1] - loop_sel_min[1]
		loop_sel_center = ( loop_sel_max + loop_sel_min ) * 0.5

		#compute transformation matrix
		trans_mat = mathutils.Matrix.Identity( 3 )
		trans_mat[0][2] = loop_sel_center[0] * -1.0
		trans_mat[1][2] = loop_sel_center[1] * -1.0
		
		trans_mat_inverse = mathutils.Matrix.Identity( 3 )
		trans_mat_inverse[0][2] = tool_center[0]
		trans_mat_inverse[1][2] = tool_center[1]
		
		scl_mat = mathutils.Matrix.Identity( 3 )
		scl_mat[0][0] = tool_width / loop_sel_width
		scl_mat[1][1] = tool_height / loop_sel_height

		mat = trans_mat_inverse @ scl_mat @ trans_mat

		#transform uv coords
		for l in loop_selection:
			uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
			uv[2] = 1.0
			uv = mat @ uv
			l[uvlayer].uv = uv.to_2d()

		#commit bmesh to mesh obj
		targetMesh = context.active_object.data
		bm.to_mesh( targetMesh )
		targetMesh.update()
		bm.free()
		
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )
		
		return { 'FINISHED' }

	def modal( self, context, event ):
		if not MESH_OT_uvboundstransform.BOUNDS_RENDER:
			rmmesh = rmlib.rmMesh.from_bmesh( context.active_object, self.bmesh )
			rmmesh.readonly = True
			if len( self.bmesh.loops.layers.uv.values() ) < 1:
				return { 'CANCELLED' }
			uvlayer = rmmesh.active_uv
			loops = GetLoopSelection( context, rmmesh, uvlayer )
			if len( loops ) < 2:
				bpy.ops.object.mode_set( mode='EDIT', toggle=False )
				return { 'CANCELLED' }
			uvs = [ mathutils.Vector( l[uvlayer].uv ) for l in loops ]
			bounds = Bounds2D.from_uvs( context, uvs )

			MESH_OT_uvboundstransform.BOUNDS_RENDER = BoundsHandle( context, bounds )
			MESH_OT_uvboundstransform.BOUNDS_RENDER.doDraw( context )

		'''
		#allow view2d events (like panning and zooming) to pass through modal
		if MESH_OT_uvboundstransform.BOUNDS_RENDER:
			for kc in context.window_manager.keyconfigs:
				for km in kc.keymaps:
					found_keymap = km.keymap_items.match_event( event )
					if found_keymap is not None and found_keymap.idname.startswith('view2d'):
						#make MESH_OT_uvboundstransform.BOUNDS_RENDER keep up with pan without modifying it.
						delta_x = float( event.mouse_x - event.mouse_prev_press_x )
						delta_y = float( event.mouse_y - event.mouse_prev_press_y )
						BoundsHandle.bounds._min[0] += delta_x
						BoundsHandle.bounds._min[1] += delta_y
						BoundsHandle.bounds._max[0] += delta_x
						BoundsHandle.bounds._max[1] += delta_y
						BoundsHandle.bounds.GenerateRegions()
						MESH_OT_uvboundstransform.BOUNDS_RENDER.update( context, event.mouse_region_x, event.mouse_region_y )
		'''

		if event.type == 'LEFTMOUSE' and MESH_OT_uvboundstransform.BOUNDS_RENDER:
			self.hit_idx = -1

			if event.value == 'PRESS':
				for i in range( len( BoundsHandle.bounds.regions ) ):
					if BoundsHandle.bounds.TestRegion( i, event.mouse_region_x, event.mouse_region_y ):
						self.hit_idx = i
						self.prev_press_x = event.mouse_region_x
						self.prev_press_y = event.mouse_region_y
						break

				if self.hit_idx < 0 and not MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds.IsInside( event.mouse_region_x, event.mouse_region_y ):
					MESH_OT_uvboundstransform.BOUNDS_RENDER.stopDraw( context )
					MESH_OT_uvboundstransform.BOUNDS_RENDER = None
					return { 'FINISHED' }

			if event.value == 'RELEASE':
				self.hit_idx = -1
				self.lmb_down = False

		elif event.type == 'MOUSEMOVE' and MESH_OT_uvboundstransform.BOUNDS_RENDER:			
			MESH_OT_uvboundstransform.BOUNDS_RENDER.update( context, event.mouse_region_x, event.mouse_region_y )
			bounds = MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds
			if self.hit_idx == 0:
				bounds._max[0] = event.mouse_region_x
			elif self.hit_idx == 1:
				bounds._max[0] = event.mouse_region_x
				bounds._min[1] = event.mouse_region_y
			elif self.hit_idx == 2:
				bounds._max[0] = event.mouse_region_x
				bounds._max[1] = event.mouse_region_y
			elif self.hit_idx == 3:
				bounds._max[1] = event.mouse_region_y
			elif self.hit_idx == 4:
				bounds._min[0] = event.mouse_region_x
				bounds._max[1] = event.mouse_region_y
			elif self.hit_idx == 5:
				bounds._min[0] = event.mouse_region_x
			elif self.hit_idx == 6:
				bounds._min[0] = event.mouse_region_x
				bounds._min[1] = event.mouse_region_y
			elif self.hit_idx == 7:
				bounds._min[1] = event.mouse_region_y
			elif self.hit_idx == 8:
				delta_x = float( event.mouse_region_x - self.prev_press_x )
				delta_y = float( event.mouse_region_y - self.prev_press_y )
				bounds._min[0] += delta_x
				bounds._min[1] += delta_y
				bounds._max[0] += delta_x
				bounds._max[1] += delta_y
				self.prev_press_x = event.mouse_region_x
				self.prev_press_y = event.mouse_region_y

			if bounds._min[0] > bounds._max[0]:
				temp = MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds._min[0]
				MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds._min[0] = MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds._max[0]
				MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds._max[0] = temp
			if bounds._min[1] > bounds._max[1]:
				temp = MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds._min[1]
				MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds._min[1] = MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds._max[1]
				MESH_OT_uvboundstransform.BOUNDS_RENDER.bounds._max[1] = temp

			if self.hit_idx > -1:
				bounds.GenerateRegions()

			self.execute( context )
		
		elif event.type == 'ESC':
			if MESH_OT_uvboundstransform.BOUNDS_RENDER:
				MESH_OT_uvboundstransform.BOUNDS_RENDER.stopDraw( context )
				MESH_OT_uvboundstransform.BOUNDS_RENDER = None
			return { 'CANCELLED' }
		
		return { 'RUNNING_MODAL' }
		#return { 'PASS_THROUGH' }


	def invoke( self, context, event ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readme = True
				self.bmesh = rmmesh.bmesh.copy()

		rmmesh = rmlib.rmMesh.from_bmesh( context.active_object, self.bmesh )
		if len( self.bmesh.loops.layers.uv.values() ) < 1:
			return { 'CANCELLED' }
		uvlayer = rmmesh.active_uv
		loops = GetLoopSelection( context, rmmesh, uvlayer )
		if len( loops ) < 2:
			bpy.ops.object.mode_set( mode='EDIT', toggle=False )
			return { 'CANCELLED' }

		wm = context.window_manager
		wm.modal_handler_add( self )
		return { 'RUNNING_MODAL' }


def register():
	print( 'register :: {}'.format( MESH_OT_uvboundstransform.bl_idname ) )
	bpy.utils.register_class( MESH_OT_uvboundstransform )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_uvboundstransform.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_uvboundstransform )