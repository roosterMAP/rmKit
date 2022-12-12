import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib
import bgl
import gpu
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_location_3d

BOUNDS_RENDER = None

class Bounds2D():
	def __init__( self, context ):
		self.context = context
		self._min = mathutils.Vector( ( 0.0, 0.0 ) )
		self._max = mathutils.Vector( ( 1.0, 1.0 ) )
		self.regions = []
		
	def GenerateRegions( self, a ):
		self.regions.clear()
		self.regions.append( ( mathutils.Vector( ( self._min[0] + a, self._min[1] - a ) ), mathutils.Vector( ( self._max[0] - a, self._min[1] + a ) ) ) )
		self.regions.append( ( mathutils.Vector( ( self._max[0] - a, self._min[1] + a ) ), mathutils.Vector( ( self._max[0] + a, self._max[1] - a ) ) ) )
		self.regions.append( ( mathutils.Vector( ( self._min[0] + a, self._max[1] - a ) ), mathutils.Vector( ( self._max[0] - a, self._max[1] + a ) ) ) )
		self.regions.append( ( mathutils.Vector( ( self._min[0] - a, self._min[1] + a ) ), mathutils.Vector( ( self._min[0] + a, self._max[1] - a ) ) ) )
	
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
		bounds.GenerateRegions( 6 )
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
		bounds.GenerateRegions( 6 )
		return bounds

	@property
	def center( self ):
		return ( self._min + self._max ) * 0.5

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

	def update( self, m_x, m_y ):
		self.mouse = ( float( m_x ), float( m_y ) )
		self.shader_batch()
		self.draw()

	def shader_batch( self ):
		BoundsHandle.batches.clear()
		corners = BoundsHandle.bounds.corners
		coords = []
		for i in range( 4 ):
			coords.append( corners[i-1] )
			coords.append( corners[i] )

		region_coords = []
		for r in BoundsHandle.bounds.regions:
			region_coords.append( ( r[0] ) )
			region_coords.append( ( r[1] ) )
		
		BoundsHandle.batches.append( batch_for_shader( BoundsHandle.shader, 'LINES', { 'pos': coords[0:2] } ) )
		BoundsHandle.batches.append( batch_for_shader( BoundsHandle.shader, 'LINES', { 'pos': coords[2:4] } ) )
		BoundsHandle.batches.append( batch_for_shader( BoundsHandle.shader, 'LINES', { 'pos': coords[4:6] } ) )
		BoundsHandle.batches.append( batch_for_shader( BoundsHandle.shader, 'LINES', { 'pos': coords[6:8] } ) )

		BoundsHandle.batches.append( batch_for_shader( BoundsHandle.shader, 'LINES', { 'pos': region_coords } ) )

	def draw( self ):
		if len( BoundsHandle.batches ) >= 4:	
			bgl.glEnable( bgl.GL_BLEND )
			bgl.glEnable( bgl.GL_DEPTH_TEST )
			bgl.glEnable( bgl.GL_LINE_SMOOTH )
			bgl.glLineWidth( 2 )
			
			BoundsHandle.shader.bind()
			
			for i in range( 4 ):
				if BoundsHandle.bounds.TestRegion( i, self.mouse[0], self.mouse[1] ):
					BoundsHandle.shader.uniform_float( 'color', ( 1.0, 0.0, 0.0, 1.0 ) )					
				else:
					BoundsHandle.shader.uniform_float( 'color', ( 0.0, 0.5, 0.5, 1.0 ) )
				BoundsHandle.batches[i].draw( BoundsHandle.shader )				

			#BoundsHandle.shader.uniform_float( 'color', ( 1.0, 0.0, 0.0, 1.0 ) )
			#for i in range( 4, len( BoundsHandle.batches ) ):
			#	BoundsHandle.batches[i].draw( BoundsHandle.shader )

			bgl.glDisable( bgl.GL_BLEND )
			bgl.glDisable( bgl.GL_DEPTH_TEST )
			bgl.glDisable( bgl.GL_LINE_SMOOTH )
			bgl.glLineWidth( 1 )

	def doDraw( self ):
		BoundsHandle.handle = bpy.types.SpaceImageEditor.draw_handler_add( self.draw, (), 'WINDOW', 'POST_PIXEL' )
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


class MESH_OT_uvboundstransform( bpy.types.Operator ):
	"""Transform UV Selection with bbox tool handles."""
	bl_idname = 'mesh.rm_uvboundstransform'
	bl_label = 'Transform Bounds'
	bl_options = { 'REGISTER', 'UNDO' }
	
	def __init__( self ):
		self.bounds = None
		self.hit_idx = -1
		self.m_delta = ( 0.0, 0.0 )

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode and
				not context.tool_settings.use_uv_select_sync )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
			
		#with rmmesh as rmmesh:
		#	uvlayer = rmmesh.active_uv
	
		return { 'FINISHED' }


	def modal( self, context, event ):
		global BOUNDS_RENDER

		if event.type == 'LEFTMOUSE':
			self.hit_idx = -1
			for i in range( 4 ):
				if BoundsHandle.bounds.TestRegion( i, event.mouse_region_x, event.mouse_region_y ):
					self.hit_idx = i
					break
			if self.hit_idx < 0:
				BOUNDS_RENDER.stopDraw( context )
				return { 'FINISHED' }

		elif event.type == 'MOUSEMOVE':
			BOUNDS_RENDER.update( event.mouse_region_x, event.mouse_region_y )
			print( self.hit_idx )

			delta_x = float( event.mouse_region_x - event.mouse_prev_press_x ) / context.region.width
			delta_y = float( event.mouse_region_y - event.mouse_prev_press_y ) / context.region.height
			self.m_delta = ( delta_x, delta_y )
			self.execute( context )

			return { 'RUNNING_MODAL' }
		
		elif event.type == 'ESC':
			BOUNDS_RENDER.stopDraw( context )
			return { 'CANCELLED' }
		
		return { 'PASS_THROUGH' }


	def invoke( self, context, event ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			rmmesh.readonly = True

			uvlayer = rmmesh.active_uv
			loops = rmlib.rmUVLoopSet.from_selection( rmmesh, uvlayer=uvlayer )
			uvs = [ mathutils.Vector( l[uvlayer].uv ) for l in loops ]
			self.bounds = Bounds2D.from_uvs( context, uvs )

		wm = context.window_manager
		wm.modal_handler_add( self )

		global BOUNDS_RENDER
		BOUNDS_RENDER = BoundsHandle( context, self.bounds )
		BOUNDS_RENDER.doDraw()

		return { 'RUNNING_MODAL' }


def register():
	bpy.utils.register_class( MESH_OT_uvboundstransform )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvboundstransform )

register()