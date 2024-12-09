import bpy, gpu, mathutils, blf
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import location_3d_to_region_2d
from .. import rmlib

class DimensionsManager:
	shader = None
	batch = None
	handle = None
	handle_text = None
	active = False
	nodraw = False
	_joint = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_x_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_y_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_z_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_x_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_y_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_z_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )

	@staticmethod
	def Zero():
		DimensionsManager._joint = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		DimensionsManager._x_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		DimensionsManager._y_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		DimensionsManager._z_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		DimensionsManager._x_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		DimensionsManager._y_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		DimensionsManager._z_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )

	def __init__( self, context ):
		self.factor = 1.0
		DimensionsManager.shader = gpu.shader.from_builtin( 'POLYLINE_SMOOTH_COLOR' )
		self.shader_batch()

	def update( self, context ):
		imperial = context.scene.unit_settings.system == 'IMPERIAL'
		length_unit = context.scene.unit_settings.length_unit
		self.factor = 1.0
		if imperial:
			if length_unit == 'INCHES':
				self.factor = 39.3701
			elif length_unit == 'FEET':
				self.factor = 3.28084
			elif length_unit == 'THOU':
				self.factor = 39370.1
			elif length_unit == 'MILES':
				self.factor = 0.000621371
			else:
				self.factor = 39.3701
		else:
			if length_unit == 'CENTIMETERS':
				self.factor = 100.0
			elif length_unit == 'KILOMETERS':
				self.factor = 1000.0
			elif length_unit == 'MILLIMETERS':
				self.factor = 0.01
			else:
				self.factor = 1.0

		self.shader_batch()
		try:
			DimensionsManager._x_handle = location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=DimensionsManager._x_max )
			DimensionsManager._y_handle = location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=DimensionsManager._y_max )
			DimensionsManager._z_handle = location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=DimensionsManager._z_max )
		except AttributeError:
			return

		for window in context.window_manager.windows:
			for area in window.screen.areas:
				if area.type == 'VIEW_3D':
					for region in area.regions:
						if region.type == 'WINDOW':
							region.tag_redraw()

	def shader_batch( self ):
		coords = []
		coords.append( DimensionsManager._joint )
		coords.append( DimensionsManager._x_max )
		coords.append( DimensionsManager._joint )
		coords.append( DimensionsManager._y_max )
		coords.append( DimensionsManager._joint )
		coords.append( DimensionsManager._z_max )

		colors = []
		colors.append( ( 1.0, 0.0, 0.0, 0.5 ) )
		colors.append( ( 1.0, 0.0, 0.0, 0.5 ) )
		colors.append( ( 0.0, 1.0, 0.0, 0.5 ) )
		colors.append( ( 0.0, 1.0, 0.0, 0.5 ) )
		colors.append( ( 0.0, 0.0, 1.0, 0.5 ) )
		colors.append( ( 0.0, 0.0, 1.0, 0.5 ) )
				
		content = { 'pos':coords, 'color':colors }
		DimensionsManager.batch = batch_for_shader( DimensionsManager.shader, 'LINES', content )

	def draw( self ):
		if DimensionsManager.batch:			
			DimensionsManager.shader.bind()

			DimensionsManager.shader.uniform_float( 'lineWidth', 1 )
			region = bpy.context.region
			DimensionsManager.shader.uniform_float( 'viewportSize', ( region.width, region.height ) )

			DimensionsManager.batch.draw( DimensionsManager.shader )

	def draw_text( self ):
		if DimensionsManager._x_handle is None:
			return

		blf.color( 0, 1.0, 0.0, 0.0, 1.0 )
		blf.position( 0, DimensionsManager._x_handle[0], DimensionsManager._x_handle[1], 0 )
		blf.size( 0, 16 )
		d = ( DimensionsManager._x_max - DimensionsManager._joint ).length
		d *= self.factor
		d = round( d, 4 )
		blf.draw( 0, '{}'.format( d ) )

		blf.color( 0, 0.0, 1.0, 0.0, 1.0 )
		blf.position( 0, DimensionsManager._y_handle[0], DimensionsManager._y_handle[1], 0 )
		blf.size( 0, 16 )
		d = ( DimensionsManager._y_max - DimensionsManager._joint ).length
		d *= self.factor
		d = round( d, 4 )
		blf.draw( 0, '{}'.format( d ) )

		blf.color( 0, 0.0, 0.0, 1.0, 1.0 )
		blf.position( 0, DimensionsManager._z_handle[0], DimensionsManager._z_handle[1], 0 )
		blf.size( 0, 16 )
		d = ( DimensionsManager._z_max - DimensionsManager._joint ).length
		d *= self.factor
		d = round( d, 4 )
		blf.draw( 0, '{}'.format( d ) )

	def doDraw( self ):
		DimensionsManager.handle = bpy.types.SpaceView3D.draw_handler_add( self.draw, (), 'WINDOW', 'POST_VIEW' )
		DimensionsManager.handle_text = bpy.types.SpaceView3D.draw_handler_add( self.draw_text, (), 'WINDOW', 'POST_PIXEL' )
		DimensionsManager.active = True
		
	def stopDraw( self, context ):
		try:
			bpy.types.SpaceView3D.draw_handler_remove( DimensionsManager.handle, 'WINDOW' )		
			bpy.types.SpaceView3D.draw_handler_remove( DimensionsManager.handle_text, 'WINDOW' )
		except ValueError:
			pass
		DimensionsManager.active = False

		for window in context.window_manager.windows:
			for area in window.screen.areas:
				if area.type == 'VIEW_3D':
					for region in area.regions:
						if region.type == 'WINDOW':
							region.tag_redraw()


def GetWorldSpaceBounds( rmmesh, bounds ):
	mat = rmmesh.world_transform
	min_p = bounds[0]
	max_p = bounds[1]

	corners = []
	corners.append( min_p )
	corners.append( mathutils.Vector( ( max_p[0], min_p[1], min_p[2] ) ) )
	corners.append( mathutils.Vector( ( min_p[0], max_p[1], min_p[2] ) ) )
	corners.append( mathutils.Vector( ( min_p[0], min_p[1], max_p[2] ) ) )
	corners.append( mathutils.Vector( ( max_p[0], max_p[1], min_p[2] ) ) )
	corners.append( mathutils.Vector( ( min_p[0], max_p[1], max_p[2] ) ) )
	corners.append( mathutils.Vector( ( max_p[0], min_p[1], max_p[2] ) ) )
	corners.append( max_p )

	for i in range( 8 ):
		corners[i] = mat @ corners[i]

	min_p = mathutils.Vector( corners[0].copy() )
	max_p = mathutils.Vector( corners[0].copy() )
	for c in corners:
		for i in range( 3 ):
			if c[i] < min_p[i]:
				min_p[i] = c[i]
			if c[i] > max_p[i]:
				max_p[i] = c[i]
	
	return ( min_p, max_p )


BACKGROUND_LAYERNAME = 'rm_background'

def GetSelsetPolygons( bm, layername ):
	intlayers = bm.faces.layers.int
	selset = intlayers.get( layername, None )
	if selset is None:
		return rmlib.rmPolygonSet()
	return rmlib.rmPolygonSet( [ f for f in bm.faces if bool( f[selset] ) ] )


def GetBoundingBox( context ):		
		bounding_box = None
		
		if context.mode == 'EDIT_MESH':
			sel_mode = context.tool_settings.mesh_select_mode[:]

			rmmesh = rmlib.rmMesh.GetActive( context )
			if rmmesh is None:
				return bounding_box
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				if sel_mode[0]:
					verts = rmlib.rmVertexSet.from_selection( rmmesh )
					if len( verts ) == 0:
						verts = rmlib.rmVertexSet.from_mesh( rmmesh )
					if len( verts ) == 0:
						return bounding_box
				elif sel_mode[1]:
					edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					if len( edges ) == 0:
						edges = rmlib.rmEdgeSet.from_mesh( rmmesh )
					if len( edges ) == 0:
						return bounding_box
					verts = edges.vertices

				if sel_mode[2] or context.scene.dimensions_use_background_face_selection:
					if sel_mode[2]:
						faces = rmlib.rmPolygonSet.from_selection( rmmesh )
					else:
						faces = GetSelsetPolygons( rmmesh.bmesh, BACKGROUND_LAYERNAME )
					if len( faces ) == 0:
						faces = rmlib.rmPolygonSet.from_mesh( rmmesh )
					if len( faces ) == 0:
						return bounding_box
					verts = faces.vertices
				
				min_p = mathutils.Vector( verts[0].co.copy() )
				max_p = mathutils.Vector( verts[0].co.copy() )
				for v in verts:
					for i in range( 3 ):
						if v.co[i] < min_p[i]:
							min_p[i] = v.co[i]
						if v.co[i] > max_p[i]:
							max_p[i] = v.co[i]

				bounding_box = GetWorldSpaceBounds( rmmesh, ( min_p, max_p ) )

				
		elif context.mode == 'OBJECT':
			bbox_corners = []
			for obj in context.selected_objects:
				if obj.type != 'MESH':
					continue				
				bbox_corners += [ mathutils.Matrix( obj.matrix_world ) @ mathutils.Vector( t ) for t in obj.bound_box ]
			if len( bbox_corners ) == 0:
				bbox_corners = [ ( 0.0, 0.0, 0.0 ) ]
			
			min_p = mathutils.Vector( ( bbox_corners[0][0], bbox_corners[0][1], bbox_corners[0][2] ) )
			max_p = mathutils.Vector( ( bbox_corners[0][0], bbox_corners[0][1], bbox_corners[0][2] ) )
			for p in bbox_corners:
				for i in range( 3 ):
					if p[i] < min_p[i]:
						min_p[i] = p[i]
					if p[i] > max_p[i]:
						max_p[i] = p[i]
												
			bounding_box = ( min_p, max_p )
			
		return bounding_box


class MESH_OT_dimensions( bpy.types.Operator ):
	"""Draw helpers in the viewport to visualize the dimensions of selected mesh elements."""
	bl_idname = 'view3d.rm_dimensions'
	bl_label = 'Dimensions'

	DIMENSIONS_RENDER = None
	
	@classmethod
	def poll( cls, context ):
		return context.area.type == 'VIEW_3D'
		
	def invoke(self, context, event):
		#add a timer to modal
		wm = context.window_manager
		self._timer = wm.event_timer_add( 1.0 / 64.0, window=context.window )
		wm.modal_handler_add( self )

		self.execute( context )

		return { 'RUNNING_MODAL' }

	def modal( self, context, event ):
		if not MESH_OT_dimensions.DIMENSIONS_RENDER.active:
			return { 'FINISHED' }
			
		if event.type == 'TIMER':
			bounding_box = GetBoundingBox( context )
			if bounding_box is None or ( bounding_box[1] - bounding_box[0] ).length < rmlib.util.FLOAT_EPSILON:
				DimensionsManager.Zero()
				
				if not DimensionsManager.nodraw:
					DimensionsManager.nodraw = True
					bpy.types.SpaceView3D.draw_handler_remove( DimensionsManager.handle, 'WINDOW' )
					bpy.types.SpaceView3D.draw_handler_remove( DimensionsManager.handle_text, 'WINDOW' )
					for window in context.window_manager.windows:
						for area in window.screen.areas:
							if area.type == 'VIEW_3D':
								for region in area.regions:
									if region.type == 'WINDOW':
										region.tag_redraw()

			else:
				DimensionsManager._joint = bounding_box[0]
				DimensionsManager._x_max = mathutils.Vector( ( bounding_box[1][0], bounding_box[0][1], bounding_box[0][2] ) )
				DimensionsManager._y_max = mathutils.Vector( ( bounding_box[0][0], bounding_box[1][1], bounding_box[0][2] ) )
				DimensionsManager._z_max = mathutils.Vector( ( bounding_box[0][0], bounding_box[0][1], bounding_box[1][2] ) )

				if DimensionsManager.nodraw:
					DimensionsManager.nodraw = False
					DimensionsManager.handle = bpy.types.SpaceView3D.draw_handler_add( MESH_OT_dimensions.DIMENSIONS_RENDER.draw, (), 'WINDOW', 'POST_VIEW' )
					DimensionsManager.handle_text = bpy.types.SpaceView3D.draw_handler_add( MESH_OT_dimensions.DIMENSIONS_RENDER.draw_text, (), 'WINDOW', 'POST_PIXEL' )

			MESH_OT_dimensions.DIMENSIONS_RENDER.update( context )

		return { 'PASS_THROUGH' }

	def execute( self, context ):
		if MESH_OT_dimensions.DIMENSIONS_RENDER is None:
			MESH_OT_dimensions.DIMENSIONS_RENDER = DimensionsManager( context )

		if DimensionsManager.active:
			MESH_OT_dimensions.DIMENSIONS_RENDER.stopDraw( context )
			return { 'FINISHED' }
		else:
			MESH_OT_dimensions.DIMENSIONS_RENDER.doDraw()

		return { 'FINISHED' }


def register():
	bpy.types.Scene.dimensions_use_background_face_selection = bpy.props.BoolProperty( name='Use Background Face Sel' )
	bpy.utils.register_class( MESH_OT_dimensions )
	

def unregister():
	del bpy.types.Scene.dimensions_use_background_face_selection
	bpy.utils.unregister_class( MESH_OT_dimensions )