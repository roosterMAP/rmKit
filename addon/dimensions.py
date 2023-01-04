import bpy, gpu, mathutils, blf
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import location_3d_to_region_2d
import math, time
import rmKit.rmlib as rmlib

class DimensionsManager:
	shader = None
	batch = None
	handle = None
	handle_text = None
	active = False
	_joint = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_x_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_y_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_z_max = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_x_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_y_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	_z_handle = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )

	def __init__( self, context ):
		DimensionsManager.shader = gpu.shader.from_builtin( '3D_SMOOTH_COLOR' )
		self.shader_batch()

	def update( self, context ):
		self.shader_batch()

		DimensionsManager._x_handle = location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=DimensionsManager._x_max )
		DimensionsManager._y_handle = location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=DimensionsManager._y_max )
		DimensionsManager._z_handle = location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=DimensionsManager._z_max )

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
		colors.append( ( 1.0, 0.0, 0.0, 1.0 ) )
		colors.append( ( 1.0, 0.0, 0.0, 1.0 ) )
		colors.append( ( 0.0, 1.0, 0.0, 1.0 ) )
		colors.append( ( 0.0, 1.0, 0.0, 1.0 ) )
		colors.append( ( 0.0, 0.0, 1.0, 1.0 ) )
		colors.append( ( 0.0, 0.0, 1.0, 1.0 ) )
				
		content = { 'pos':coords, 'color':colors }
		DimensionsManager.batch = batch_for_shader( DimensionsManager.shader, 'LINES', content )

	def draw( self ):
		if DimensionsManager.batch:
			gpu.state.line_width_set( 2.0 )
			
			DimensionsManager.shader.bind()
			DimensionsManager.batch.draw( DimensionsManager.shader )

			gpu.state.line_width_set( 1.0 )

	def draw_text( self ):
			blf.color( 0, 1.0, 0.0, 0.0, 1.0 )
			blf.position( 0, DimensionsManager._x_handle[0], DimensionsManager._x_handle[1], 0 )
			blf.size( 0, 16, 72 )
			blf.draw( 0, str( ( DimensionsManager._x_max - DimensionsManager._joint ).length ) )

			blf.color( 0, 0.0, 1.0, 0.0, 1.0 )
			blf.position( 0, DimensionsManager._y_handle[0], DimensionsManager._y_handle[1], 0 )
			blf.size( 0, 16, 72 )
			blf.draw( 0, str( ( DimensionsManager._y_max - DimensionsManager._joint ).length ) )

			blf.color( 0, 0.0, 0.0, 1.0, 1.0 )
			blf.position( 0, DimensionsManager._z_handle[0], DimensionsManager._z_handle[1], 0 )
			blf.size( 0, 16, 72 )
			blf.draw( 0, str( ( DimensionsManager._z_max - DimensionsManager._joint ).length ) )

	def doDraw( self ):
		DimensionsManager.handle = bpy.types.SpaceView3D.draw_handler_add( self.draw, (), 'WINDOW', 'POST_VIEW' )
		DimensionsManager.handle_text = bpy.types.SpaceView3D.draw_handler_add( self.draw_text, (), 'WINDOW', 'POST_PIXEL' )
		DimensionsManager.active = True
		
	def stopDraw( self, context ):
		bpy.types.SpaceView3D.draw_handler_remove( DimensionsManager.handle, 'WINDOW' )
		bpy.types.SpaceView3D.draw_handler_remove( DimensionsManager.handle_text, 'WINDOW' )
		DimensionsManager.active = False

		for window in context.window_manager.windows:
			for area in window.screen.areas:
				if area.type == 'VIEW_3D':
					for region in area.regions:
						if region.type == 'WINDOW':
							region.tag_redraw()


def GetBoundingBox( context ):		
		bounding_box = None
		
		if context.object.data.is_editmode:
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
					verts = edges.verties
				elif sel_mode[2]:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
					if len( faces ) == 0:
						faces = rmlib.rmPolygonSet.from_mesh( rmmesh )
					if len( faces ) == 0:
						return bounding_box
					verts = faces.vertices
				else:
					return bounding_box
				
				min_p = mathutils.Vector( verts[0].co.copy() )
				max_p = mathutils.Vector( verts[0].co.copy() )
				for v in verts:
					for i in range( 3 ):
						if v.co[i] < min_p[i]:
							min_p[i] = v.co[i]
						if v.co[i] > max_p[i]:
							max_p[i] = v.co[i]
							
				mat = rmmesh.world_transform
				bounding_box = ( mat @ min_p, mat @ max_p )
				
		elif context.mode == 'OBJECT':
			bbox_corners = []
			for obj in context.selected_objects:
				if obj.type != 'MESH':
					continue
				bbox_corners += [ mathutils.Vector( t ) + mathutils.Vector( obj.location ) for t in obj.bound_box ]
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
	bl_idname = 'view3d.rm_dimensions'
	bl_label = 'Dimensions'

	DIMENSIONS_RENDER = None
	
	@classmethod
	def poll( cls, context ):
		return context.area.type == 'VIEW_3D'
		
	def invoke(self, context, event):
		#add a timer to modal
		wm = context.window_manager
		self._timer = wm.event_timer_add( 1.0 / 8.0, window=context.window )
		wm.modal_handler_add( self )

		self.execute( context )

		return { 'RUNNING_MODAL' }

	def modal( self, context, event ):
		if not MESH_OT_dimensions.DIMENSIONS_RENDER.active:
			return { 'FINISHED' }
			
		if event.type == 'TIMER':
			bounding_box = GetBoundingBox( context )
			DimensionsManager._joint = bounding_box[0]
			DimensionsManager._x_max = mathutils.Vector( ( bounding_box[1][0], bounding_box[0][1], bounding_box[0][2] ) )
			DimensionsManager._y_max = mathutils.Vector( ( bounding_box[0][0], bounding_box[1][1], bounding_box[0][2] ) )
			DimensionsManager._z_max = mathutils.Vector( ( bounding_box[0][0], bounding_box[0][1], bounding_box[1][2] ) )

			MESH_OT_dimensions.DIMENSIONS_RENDER.update( context )

		return {"PASS_THROUGH"}

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
	print( 'register :: {}'.format( MESH_OT_dimensions.bl_idname ) )
	bpy.utils.register_class( MESH_OT_dimensions )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_dimensions.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_dimensions )