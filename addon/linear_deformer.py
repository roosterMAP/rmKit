
#important node: starting point for the code was a operator called mira.linear_deformer written by mifth and is included in Mira Tools. This is heavily modified version
#written to meet my specific needs.

import bpy, bmesh, mathutils, bpy_extras, gpu
from gpu_extras.batch import batch_for_shader
from .. import rmlib

import math, string, random

pass_keys = { 'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_3', 'NUMPAD_4', 
			 'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 
			 'NUMPAD_9', 'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 
			 'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TRACKPADPAN', 'TRACKPADZOOM' }

EPSILON = 0.00001

APPLY_VERT_ID = 0
APPLY_VERT_WEIGHT = 1
APPLY_VERT_POSITION = 2

ENDPOINT_HANDLE_SIZE = 6.0
LINE_WIDTH_SIZE = 1.0

POINT_HANDLE_INVALID = -1
POINT_HANDLE_START = 0
POINT_HANDLE_MIDDLE = 1
POINT_HANDLE_END = 2

CONSTRAIN_AXIS_HORIZONTAL = 0
CONSTRAIN_AXIS_VERTICAL = 1

QUADRATIC_EASING_LIN = 0
QUADRATIC_EASING_IN = 1
QUADRATIC_EASING_OUT = 2
QUADRATIC_EASING_COUNT = 3


class MouseState():
	def __init__( self, context ):
		self.__context = context

		self.m_mouse_current_3d = None

		self.m_mouse_current_2d = None
		self.m_mmb_start_2d = None

		self.m_mouse_move_start_3d = None
		self.m_mouse_rotate_start_vec_2d = None
		self.m_mouse_scale_start_2d = None

	def UpdateCurrentMouse( self, event, start_point ):
		self.m_mouse_current_2d = mathutils.Vector( ( event.mouse_region_x, event.mouse_region_y ) )
		self.m_mouse_current_3d = rmlib.rmViewport( self.__context ).get_mouse_on_plane( self.__context, start_point, None, self.m_mouse_current_2d )


class ToolState():
	# class constructor
	def __init__( self ):
		self.start_point = None
		self.middle_point = None
		self.end_point = None
		self.quadratic_easing = QUADRATIC_EASING_LIN
		self.constrain_axis_idx = -1
		self.contrain_axis_2d = CONSTRAIN_AXIS_HORIZONTAL
		self.transform_origin = None

	def ComputeTransformOrigin( self, context, bm ):
		#set transform_origin
		transform_pivot = context.scene.tool_settings.transform_pivot_point
		if transform_pivot == 'BOUNDING_BOX_CENTER':
			if len( self.apply_tool_verts ) > 0:
				bbmin = self.apply_tool_verts[ 0 ][ 2 ].copy()
				bbmax = self.apply_tool_verts[ 0 ][ 2 ].copy()
				for vert_data in self.apply_tool_verts:
					bbmin[ 0 ] = min( vert_data[ 2 ][ 0 ], bbmin[ 0 ] )
					bbmax[ 0 ] = min( vert_data[ 2 ][ 0 ], bbmax[ 0 ] )
					bbmin[ 1 ] = min( vert_data[ 2 ][ 1 ], bbmin[ 1 ] )
					bbmax[ 1 ] = min( vert_data[ 2 ][ 1 ], bbmax[ 1 ] )
					bbmin[ 2 ] = min( vert_data[ 2 ][ 2 ], bbmin[ 2 ] )
					bbmax[ 2 ] = min( vert_data[ 2 ][ 2 ], bbmax[ 2 ] )
				xfrm_inv = active_obj.matrix_world.inverted()
				self.transform_origin = xfrm_inv @ ( ( bbmax + bbmin ) * 0.5 )
		elif transform_pivot == 'CURSOR':
			self.transform_origin = context.scene.cursor.location
		elif transform_pivot == 'INDIVIDUAL_ORIGINS':
			self.transform_origin = self.start_point
		elif transform_pivot == 'MEDIAN_POINT':
			self.transform_origin = self.start_point
		elif transform_pivot == 'ACTIVE_ELEMENT':
			active_elem = bm.select_history.active
			xfrm_inv = active_obj.matrix_world.inverted()
			if active_elem is not None and isinstance( active_elem, bmesh.types.BMVert ):
				self.transform_origin = xfrm_inv @ active_elem.co
			elif active_elem is not None and isinstance( active_elem, bmesh.types.BMEdge ):
				active_verts = list( active_elem.verts )
				self.transform_origin = ( active_verts[ 0 ].co + active_verts[ 1 ].co ) * 0.5
				self.transform_origin = xfrm_inv @ self.transform_origin
			elif active_elem is not None and isinstance( active_elem, bmesh.types.BMFace ):
				active_verts = list( active_elem.verts )
				self.transform_origin = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
				for v in active_verts:
					self.transform_origin += v.co
				self.transform_origin *= 1.0 / len( active_verts )
				self.transform_origin = xfrm_inv @ self.transform_origin

	def Invert( self ):
		temp = self.start_point
		self.start_point = self.end_point
		self.end_point = temp

	def UpdateMiddlePoint( self ):
		lw_dir = ( self.end_point - self.start_point )
		lw_len = ( lw_dir ).length
		lw_dir = lw_dir.normalized()

		self.middle_point = self.start_point + ( lw_dir * ( lw_len / 2.0 ) )

	def PickEndpointHandle( self, context, mouse_coords_tuple ):
		v = bpy_extras.view3d_utils.location_3d_to_region_2d( context.region, context.region_data, self.start_point )
		if ( v - mathutils.Vector( mouse_coords_tuple ) ).length < 9.0:
			return POINT_HANDLE_START

		v = bpy_extras.view3d_utils.location_3d_to_region_2d( context.region, context.region_data, self.middle_point )
		if ( v - mathutils.Vector( mouse_coords_tuple ) ).length < 9.0:
			return POINT_HANDLE_MIDDLE

		v = bpy_extras.view3d_utils.location_3d_to_region_2d( context.region, context.region_data, self.end_point )
		if ( v - mathutils.Vector( mouse_coords_tuple ) ).length < 9.0:
			return POINT_HANDLE_END
			
		return -1


class ToolHistory():
	def __init__( self ):
		self.m_undo = []
		self.m_redo = []
		self.m_initial_vert_positions = []

	def CacheInitialVertPositions( self, bm ):
		self.m_initial_vert_positions = [ v.co.copy() for v in bm.verts ]

	def ResetToInitialVertPositions( self, bm ):
		for i in range( len( self.m_initial_vert_positions ) ):
			bm.verts[ i ].co = self.m_initial_vert_positions[ i ]

	def AddHistory( self, verts ):
		history = []
		for vert in verts:
			history.append( ( vert.index, vert.co.copy() ) )

		self.m_undo.append( history )

	def UndoHistory( self, bm, active_obj ):
		if self.m_undo:
			pre_history = self.m_undo[ -1 ]
			if len( self.m_undo ) > 1:  # 0 index is always original verts
				self.m_undo.remove( pre_history )
				self.m_redo.append( pre_history )

			history = self.m_undo[ -1 ]
			for h_vert in history:
				bm.verts[ h_vert[ 0 ] ].co = h_vert[ 1 ].copy()

			bm.normal_update()
			bmesh.update_edit_mesh( active_obj.data )

	def RedoHistory( self, bm, active_obj ):
		if self.m_redo:
			history = self.m_redo[ -1 ]
			for h_vert in history:
				bm.verts[ h_vert[ 0 ] ].co = h_vert[ 1 ].copy()

			self.m_redo.remove( history )
			self.m_undo.append( history )

			bm.normal_update()
			bmesh.update_edit_mesh( active_obj.data )

	def ClearUndo( self ):
		self.m_undo.clear()

	def ClearRedo( self ):
		self.m_redo.clear()

	def ClearAll( self ):
		self.ClearUndo()
		self.ClearRedo()


class DrawHandler():
	def __init__( self, context ):
		self.m_region = context.region
		self.m_rv3d = context.region_data
		self.m_shader3d = gpu.shader.from_builtin( 'UNIFORM_COLOR' )
		self.m_shader2d = gpu.shader.from_builtin( 'UNIFORM_COLOR' )
		self.m_lin_deform_handle_2d = None
		self.m_axis_constraints_mousehelper = None
		self.m_axis_constraints_3d = None
		self.m_toolState = ToolState()

	def UpdateFromToolState( self, state ):
		if not state:
			return
		self.m_toolState.start_point = state.start_point
		self.m_toolState.middle_point = state.middle_point
		self.m_toolState.end_point = state.end_point
		self.m_toolState.quadratic_easing = state.quadratic_easing
		self.m_toolState.constrain_axis_idx = state.constrain_axis_idx

	def RegisterDrawCallbacks( self ):
		self.m_lin_deform_handle_2d = bpy.types.SpaceView3D.draw_handler_add( self.__drawAxisConstraint, (), 'WINDOW', 'POST_VIEW' )
		self.m_axis_constraints_mousehelper = bpy.types.SpaceView3D.draw_handler_add( self.__drawAxisConstraintMouseHelper, (), 'WINDOW', 'POST_PIXEL' )
		self.m_axis_constraints_3d = bpy.types.SpaceView3D.draw_handler_add( self.__drawLinearFalloffHandles, (), 'WINDOW', 'POST_PIXEL' )

	def UnregisterDrawCallbacks( self ):
		bpy.types.SpaceView3D.draw_handler_remove( self.m_lin_deform_handle_2d, 'WINDOW' )
		bpy.types.SpaceView3D.draw_handler_remove( self.m_axis_constraints_3d, 'WINDOW' )
		bpy.types.SpaceView3D.draw_handler_remove( self.m_axis_constraints_mousehelper, 'WINDOW' )
		self.m_lin_deform_handle_2d = None
		self.m_axis_constraints_3d = None
		self.m_axis_constraints_mousehelper = None

	def __drawAxisConstraint( self ):
		if not self.m_toolState.start_point or not self.m_toolState.end_point:
			return

		if self.m_toolState.constrain_axis_idx < 0:
			return

		coords = ( ( 0.0, 0.0, -999999.9 ), ( 0.0, 0.0, 999999.9 ) )
		color = ( 0.0, 0.0, 1.0, 1.0 )
		if self.m_toolState.constrain_axis_idx == 0:
			coords = ( ( -999999.9, 0.0, 0.0 ), ( 999999.9, 0.0, 0.0 ) )
			color = ( 1.0, 0.0, 0.0, 1.0 )
		elif self.m_toolState.constrain_axis_idx == 1:
			coords = ( ( 0.0, -999999.9, 0.0 ), ( 0.0, 999999.9, 0.0 ) )
			color = ( 0.0, 1.0, 0.0, 1.0 )

		gpu.state.line_width_set( LINE_WIDTH_SIZE )
		gpu.state.point_size_set( ENDPOINT_HANDLE_SIZE )

		batch = batch_for_shader( self.m_shader3d, 'LINE_STRIP', { 'pos': coords } )
		self.m_shader3d.bind()
		self.m_shader3d.uniform_float( 'color', color )
		batch.draw( self.m_shader3d )

	def __drawAxisConstraintMouseHelper( self ):
		if not self.m_toolState.start_point or not self.m_toolState.end_point:
			return

		start_2d = bpy_extras.view3d_utils.location_3d_to_region_2d( self.m_region, self.m_rv3d, self.m_toolState.start_point )
		end_2d = bpy_extras.view3d_utils.location_3d_to_region_2d( self.m_region, self.m_rv3d, self.m_toolState.end_point )
		coords = ( ( start_2d[ 0 ], start_2d[ 1 ] ), ( end_2d[ 0 ], end_2d[ 1 ] ) )
		color = ( 0.8, 0.8, 0.8, 0.3 )

		gpu.state.line_width_set( LINE_WIDTH_SIZE )
		gpu.state.point_size_set( ENDPOINT_HANDLE_SIZE )

		batch = batch_for_shader( self.m_shader2d, 'LINE_STRIP', { 'pos': coords } )
		self.m_shader2d.bind()
		self.m_shader2d.uniform_float( 'color', color )
		batch.draw( self.m_shader2d )

	def __drawLinearFalloffHandles( self ):
		if not self.m_toolState.start_point or not self.m_toolState.end_point:
			return

		lw_dir = ( self.m_toolState.start_point - self.m_toolState.end_point ).normalized()
		cam_view = ( self.m_rv3d.view_rotation @ mathutils.Vector( ( 0.0, 0.0, -1.0 ) ) ).normalized()
		cross_up_dir = lw_dir.cross( cam_view ).normalized()

		start_2d = bpy_extras.view3d_utils.location_3d_to_region_2d( self.m_region, self.m_rv3d, self.m_toolState.start_point )
		end_2d = bpy_extras.view3d_utils.location_3d_to_region_2d( self.m_region, self.m_rv3d, self.m_toolState.end_point )
		middle_2d = bpy_extras.view3d_utils.location_3d_to_region_2d( self.m_region, self.m_rv3d, self.m_toolState.middle_point )

		dist_ends = ( ( self.m_toolState.start_point - self.m_toolState.end_point ).length * 0.1 ) * cross_up_dir
		end_p1 = bpy_extras.view3d_utils.location_3d_to_region_2d( self.m_region, self.m_rv3d, self.m_toolState.end_point + dist_ends )
		end_p2 = bpy_extras.view3d_utils.location_3d_to_region_2d( self.m_region, self.m_rv3d, self.m_toolState.end_point - dist_ends )

		if start_2d and end_2d and end_p1 and end_p2:
			gpu.state.line_width_set( LINE_WIDTH_SIZE )
			gpu.state.point_size_set( ENDPOINT_HANDLE_SIZE )

			coords = ( ( start_2d[ 0 ], start_2d[ 1 ] ), ( end_2d[ 0 ], end_2d[ 1 ] ) )
			batch = batch_for_shader( self.m_shader2d, 'LINE_STRIP', { 'pos': coords } )
			self.m_shader2d.bind()
			self.m_shader2d.uniform_float( 'color', ( 0.99, 0.5, 0.99, 1.0 ) )
			batch.draw( self.m_shader2d )

			coords = []
			if self.m_toolState.quadratic_easing == QUADRATIC_EASING_LIN:
				coords.append( ( start_2d[ 0 ], start_2d[ 1 ] ) )
				coords.append( ( end_p1[ 0 ], end_p1[ 1 ] ) )
				coords.append( ( end_p2[ 0 ], end_p2[ 1 ] ) )
				
			elif self.m_toolState.quadratic_easing == QUADRATIC_EASING_IN:
				cross = ( end_p2 - end_p1 ) * 0.5
				vec = end_2d - start_2d
				n = 12
				for i in range( n + 1 ):
					t = float( i ) / float( n )
					coords.append( start_2d + ( vec * rmlib.util.EaseOutCircular( t ) + cross * t ) )
				for i in range( n + 1 ):
					t = float( n - i ) / float( n )
					coords.append( start_2d + ( vec * rmlib.util.EaseOutCircular( t ) - cross * t ) )

			elif self.m_toolState.quadratic_easing == QUADRATIC_EASING_OUT:
				cross = ( end_p2 - end_p1 ) * 0.5
				vec = end_2d - start_2d
				n = 12
				for i in range( n + 1 ):
					t = float( i ) / float( n )
					coords.append( start_2d + ( vec * rmlib.util.EaseInCircular( t ) + cross * t ) )
				for i in range( n + 1 ):
					t = float( n - i ) / float( n )
					coords.append( start_2d + ( vec * rmlib.util.EaseInCircular( t ) - cross * t ) )

			batch = batch_for_shader( self.m_shader2d, 'LINE_LOOP', { 'pos': coords } )
			self.m_shader2d.bind()
			self.m_shader2d.uniform_float( 'color', ( 0.0, 0.5, 0.99, 1.0 ) )
			batch.draw( self.m_shader2d )

		coords = ( ( start_2d[0], start_2d[1] ), ( middle_2d[0], middle_2d[1] ), ( end_2d[0], end_2d[1] ) )
		batch = batch_for_shader( self.m_shader2d, 'POINTS', { 'pos': coords } )
		self.m_shader2d.bind()
		self.m_shader2d.uniform_float( 'color', ( 0.99, 0.8, 0.0, 1.0 ) )
		batch.draw( self.m_shader2d )


class MESH_OT_Linear_Deformer( bpy.types.Operator ):
	'''Modo Style Falloff Transform Tool'''
	bl_idname = 'mesh.rm_falloff'
	bl_label = 'Falloff Transform Tool'
	bl_description = 'Modo Style Falloff Transform'
	bl_options = { 'REGISTER', 'UNDO' }
	 
	min_wld_pos: bpy.props.FloatVectorProperty( 
		options={ 'HIDDEN' }
	 )

	max_wld_pos: bpy.props.FloatVectorProperty( 
		options={ 'HIDDEN' }
	 )

	# curve tool mode
	tool_modes = ( 'IDLE', 'MOVE_POINT', 'DRAW_TOOL', 'SCALE_ALL', 'MOVE_ALL', 'ROTATE_ALL' )
	tool_mode = 'IDLE'

	do_update = None
	active_lw_point_id = POINT_HANDLE_INVALID

	start_point_2d = None
	mmb_current2d = None
	mmb_plane_axis = False

	start_work_center = None
	work_verts = None
	apply_tool_verts = None

	s_history = ToolHistory()
	s_draw = None
	s_mouse = None
	s_tool = None

	def __get_tool_verts( self, verts_ids, bm, obj ):
		if self.s_tool is None:
			return

		apply_tool_verts = []
		final_dir = ( self.s_tool.end_point - self.s_tool.start_point )
		max_dist = final_dir.length
		for vert_id in verts_ids:
			v_pos = obj.matrix_world @ bm.verts[ vert_id ].co
			value = mathutils.geometry.distance_point_to_plane( v_pos, self.s_tool.start_point, final_dir )
			if value > 0:
				if value > max_dist:
					value = 1.0
				else:
					value /= max_dist

				if self.s_tool.quadratic_easing == QUADRATIC_EASING_IN:
					value = rmlib.util.EaseInCircular( value )
				elif self.s_tool.quadratic_easing == QUADRATIC_EASING_OUT:
					value = rmlib.util.EaseOutCircular( value )

				pos_final = bm.verts[ vert_id ].co.copy()

				apply_tool_verts.append( ( vert_id, value, pos_final ) )

		return apply_tool_verts

	def invoke( self, context, event ):
		self.reset_params()

		self.s_draw = DrawHandler( context )
		self.s_mouse = MouseState( context )

		if ( mathutils.Vector( list( self.min_wld_pos ) ) - mathutils.Vector( list( self.max_wld_pos ) ) ).length > EPSILON:
			self.s_tool = ToolState()
			self.s_tool.start_point = mathutils.Vector( list( self.min_wld_pos ) )
			self.s_tool.end_point = mathutils.Vector( list( self.max_wld_pos ) )
			self.s_tool.middle_point = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
			self.s_tool.UpdateMiddlePoint()

		if context.area.type == 'VIEW_3D':
			# the arguments we pass the the callbackection
			args = ( self, context )
			active_obj = context.active_object
			bm = bmesh.from_edit_mesh( active_obj.data )
			
			self.s_history.CacheInitialVertPositions( bm )

			if bm.verts:
				pre_work_verts = [ v for v in bm.verts if v.select ]
				if not pre_work_verts:
					pre_work_verts = [ v for v in bm.verts if v.hide is False ]

				if pre_work_verts:
					if self.s_tool is None:
						self.start_work_center = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
						for vert in pre_work_verts:
							self.start_work_center += vert.co
						self.start_work_center *= 1.0 / len( pre_work_verts )
						self.start_work_center = active_obj.matrix_world @ self.start_work_center
					else:
						self.start_work_center = self.s_tool.middle_point.copy()

					self.work_verts = [ vert.index for vert in pre_work_verts ]

					# add original vert to history
					self.s_history.AddHistory( pre_work_verts )

					# Add the region OpenGL drawing callback
					self.s_draw.RegisterDrawCallbacks()
					
					context.window_manager.modal_handler_add( self )

					return { 'RUNNING_MODAL' }

				else:
					self.report( { 'WARNING' }, 'No verts!!' )
					return { 'CANCELLED' }

			else:
				self.report( { 'WARNING' }, 'No verts!!' )
				return { 'CANCELLED' }
		else:
			self.report( { 'WARNING' }, 'View3D not found, cannot run operator' )
			return { 'CANCELLED' }


	def modal( self, context, event ):
		context.area.tag_redraw()

		lin_def_settings = False

		region = context.region
		rv3d = context.region_data
		active_obj = context.active_object
		bm = bmesh.from_edit_mesh( active_obj.data )

		if self.s_tool and self.s_tool.start_point:
			self.s_mouse.UpdateCurrentMouse( event, self.s_tool.start_point )

		self.do_update = True

		# tooltip
		tooltip_text = 'I:Invert, Z:Z-Constraint, X:X-Constraint, V:Invert, S:Scale, G:Move, R:Rotate, C:NextEasingMode, Ctrl+Z:Undo, Ctrl+Shift+Z:Redo'

		context.workspace.status_text_set( text=tooltip_text )

		keys_pass = event.type in pass_keys

		rm_vp = rmlib.rmViewport( context )

		# axis constraints
		if self.tool_mode != 'IDLE' and event.type == 'MIDDLEMOUSE':
			if event.value == 'PRESS':
				self.s_mouse.m_mmb_start_2d = mathutils.Vector( ( event.mouse_region_x, event.mouse_region_y ) )
				self.start_point_2d = self.s_mouse.m_mmb_start_2d.copy()
				self.s_draw.UpdateFromToolState( self.s_tool )
				return { 'RUNNING_MODAL' }
			elif event.value == 'RELEASE':
				self.start_point_2d = None
		if self.start_point_2d is not None:
			self.s_tool.constrain_axis_idx = rm_vp.get_nearest_direction_vector_from_mouse( context, self.start_point_2d, self.s_mouse.m_mouse_current_2d )
			xdelta = abs( self.s_mouse.m_mouse_current_2d.x - self.s_mouse.m_mmb_start_2d.x )
			ydelta = abs( self.s_mouse.m_mouse_current_2d.y - self.s_mouse.m_mmb_start_2d.y )
			self.s_tool.contrain_axis_2d = CONSTRAIN_AXIS_HORIZONTAL if xdelta > ydelta else CONSTRAIN_AXIS_VERTICAL
			self.mmb_plane_axis = event.shift

		if event.value == 'RELEASE' and event.type in { 'V', 'C', 'RIGHTMOUSE' }:
			self.s_tool.constrain_axis_idx = -1
			if event.type == 'C':
				self.s_tool.quadratic_easing = ( self.s_tool.quadratic_easing + 1 ) % QUADRATIC_EASING_COUNT
			elif event.type == 'V':
				self.s_tool.Invert()

			if self.apply_tool_verts is not None:
				for h_vert in self.apply_tool_verts:
					bm.verts[ h_vert[ 0 ] ].co = h_vert[ 2 ].copy()

				bm.normal_update()
				bmesh.update_edit_mesh( active_obj.data )

			self.do_update = False
			self.tool_mode = 'IDLE'
			self.s_draw.UpdateFromToolState( self.s_tool )
			return { 'RUNNING_MODAL' }

		# key pressed
		if self.tool_mode == 'IDLE' and event.value == 'PRESS' and keys_pass is False:
			if event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
				if self.s_tool:
					# pick linear widget point
					picked_point_id = self.s_tool.PickEndpointHandle( context, self.s_mouse.m_mouse_current_2d )
					if picked_point_id == POINT_HANDLE_INVALID:
						context.workspace.status_text_set( text=None )
						self.s_draw.UnregisterDrawCallbacks()
						return { 'FINISHED' }
					else:
						self.active_lw_point_id = picked_point_id
						self.tool_mode = 'MOVE_POINT'
				else:
					mouse_pos = mathutils.Vector( ( event.mouse_region_x, event.mouse_region_y ) )
					picked_point = rm_vp.get_mouse_on_plane( context, self.start_work_center, None, mouse_pos )
					if picked_point:
						self.s_tool = ToolState()

						self.s_tool.start_point = picked_point.copy()
						self.s_tool.middle_point = picked_point.copy()
						self.s_tool.end_point = picked_point

						self.active_lw_point_id = POINT_HANDLE_END

						self.s_mouse.UpdateCurrentMouse( event, self.s_tool.start_point )

						self.tool_mode = 'MOVE_POINT'

			elif event.type in { 'S', 'G', 'R' }:
				# get tool verts
				self.apply_tool_verts = self.__get_tool_verts( self.work_verts, bm, active_obj )

				self.s_tool.ComputeTransformOrigin( context, bm )

				# set tool type
				if event.type == 'S':
					self.tool_mode = 'SCALE_ALL'
				elif event.type == 'R':
					self.tool_mode = 'ROTATE_ALL'
				elif event.type == 'G':
					self.tool_mode = 'MOVE_ALL'

				# set some settings for tools
				if self.tool_mode == 'SCALE_ALL':
					self.s_mouse.m_mouse_scale_start_2d = self.s_mouse.m_mouse_current_2d.copy()

				elif self.tool_mode == 'MOVE_ALL':
					self.s_mouse.m_mouse_move_start_3d = rm_vp.get_mouse_on_plane( context, self.s_tool.start_point, None, self.s_mouse.m_mouse_current_2d )  # 3d location

				elif self.tool_mode == 'ROTATE_ALL':
					start_point_2d = bpy_extras.view3d_utils.location_3d_to_region_2d( region, rv3d, self.s_tool.start_point )
					self.s_mouse.m_mouse_rotate_start_vec_2d = ( self.s_mouse.m_mouse_current_2d - start_point_2d ).normalized()

			elif event.type == 'Z' and event.ctrl:
				if event.shift:
					self.s_history.RedoHistory( bm, active_obj )
				else:
					self.s_history.UndoHistory( bm, active_obj )
				

		# TOOL WORK!
		if self.tool_mode == 'MOVE_POINT':
			if event.value == 'RELEASE':
				self.tool_mode = 'IDLE'
				self.s_draw.UpdateFromToolState( self.s_tool )
				return { 'RUNNING_MODAL' }
			else:
				# move points
				if self.active_lw_point_id == POINT_HANDLE_START:
					self.s_tool.start_point = rm_vp.get_mouse_on_plane( context, self.s_tool.start_point, None, self.s_mouse.m_mouse_current_2d )
					self.s_tool.UpdateMiddlePoint()
				elif self.active_lw_point_id == POINT_HANDLE_END:
					self.s_tool.end_point = rm_vp.get_mouse_on_plane( context, self.s_tool.end_point, None, self.s_mouse.m_mouse_current_2d )
					self.s_tool.UpdateMiddlePoint()
				elif self.active_lw_point_id == POINT_HANDLE_MIDDLE:
					new_point_pos = rm_vp.get_mouse_on_plane( context, self.s_tool.middle_point, None, self.s_mouse.m_mouse_current_2d )
					self.s_tool.start_point += new_point_pos - self.s_tool.middle_point
					self.s_tool.end_point += new_point_pos - self.s_tool.middle_point
					self.s_tool.middle_point = new_point_pos

				self.s_draw.UpdateFromToolState( self.s_tool )
				return { 'RUNNING_MODAL' }

		elif self.tool_mode == 'SCALE_ALL':
			if event.value == 'RELEASE' and event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
				bm.normal_update()

				self.s_tool.constrain_axis_idx = -1

				# add to undo history
				self.s_history.ClearRedo()
				pre_work_verts = [ bm.verts[ v_id ] for v_id in self.work_verts ]
				self.s_history.AddHistory( pre_work_verts )

				self.tool_mode = 'IDLE'

			elif self.do_update:
				# move points
				start_point_2d = bpy_extras.view3d_utils.location_3d_to_region_2d( region, rv3d, self.s_tool.start_point )
				if start_point_2d:
					#determine the scale amt based on mouse offset drag from start_point_2d
					tool_vec = start_point_2d - self.s_mouse.m_mouse_scale_start_2d
					new_vec = start_point_2d - self.s_mouse.m_mouse_current_2d				
					apply_value = 1.0
					if self.s_tool.constrain_axis_idx >= 0 and not self.mmb_plane_axis:
						mmb_vec = self.s_mouse.m_mouse_current_2d - self.s_mouse.m_mouse_scale_start_2d
						if self.s_tool.contrain_axis_2d == CONSTRAIN_AXIS_HORIZONTAL:
							apply_value = new_vec.x / tool_vec.x
						else:
							apply_value = new_vec.y / tool_vec.y
					else:
						apply_value = new_vec.length / tool_vec.length

					if tool_vec.normalized().dot( new_vec.normalized() ) < 0.0:
						apply_value *= -1.0

					if apply_value != 0.0:
						xfrm = active_obj.matrix_world
						xfrm_inv = xfrm.inverted()
						for vert_data in self.apply_tool_verts:
							lerp_scale = ( apply_value - 1.0 ) * vert_data[ APPLY_VERT_WEIGHT ] + 1.0
							sclMat = mathutils.Matrix.Scale( lerp_scale, 4 )
							if self.s_tool.constrain_axis_idx >= 0:
								if self.mmb_plane_axis:
									vScaleAxis = mathutils.Vector( ( self.s_tool.constrain_axis_idx != 0, self.s_tool.constrain_axis_idx != 1, self.s_tool.constrain_axis_idx != 2 ) )
								else:
									vScaleAxis = mathutils.Vector( ( self.s_tool.constrain_axis_idx == 0, self.s_tool.constrain_axis_idx == 1, self.s_tool.constrain_axis_idx == 2 ) )
								sclMat[ 0 ].x = vScaleAxis.x * lerp_scale if vScaleAxis.x else 1.0
								sclMat[ 1 ].y = vScaleAxis.y * lerp_scale if vScaleAxis.y else 1.0
								sclMat[ 2 ].z = vScaleAxis.z * lerp_scale if vScaleAxis.z else 1.0

							offsetMat = mathutils.Matrix.Translation( self.s_tool.transform_origin )
							offsetMat_inv = mathutils.Matrix.Translation( self.s_tool.transform_origin * -1.0 )

							bm.verts[ vert_data[ APPLY_VERT_ID ] ].co = ( xfrm_inv @ offsetMat @ sclMat @ offsetMat_inv @ xfrm ) @ vert_data[ APPLY_VERT_POSITION ]

						bm.normal_update()
						bmesh.update_edit_mesh( active_obj.data )

			self.do_update = False
			self.s_draw.UpdateFromToolState( self.s_tool )
			return { 'RUNNING_MODAL' }

		elif self.tool_mode == 'MOVE_ALL':
			if event.value == 'RELEASE' and event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
				bm.normal_update()

				self.s_tool.constrain_axis_idx = -1

				# add to undo history
				self.s_history.ClearRedo()
				pre_work_verts = [ bm.verts[ v_id ] for v_id in self.work_verts ]
				self.s_history.AddHistory( pre_work_verts )

				self.tool_mode = 'IDLE'

			elif self.do_update:
				mouse_pos_3d = self.s_mouse.m_mouse_current_3d
				start_pos = self.s_tool.start_point
				orig_pos = self.s_mouse.m_mouse_move_start_3d
				orig_vec = orig_pos - start_pos
				move_vec = ( mouse_pos_3d - start_pos ) - orig_vec

				for vert_data in self.apply_tool_verts:
					move_value = vert_data[ APPLY_VERT_WEIGHT ]
					new_vec = ( move_vec * move_value )
					if self.s_tool.constrain_axis_idx >= 0:
						if self.mmb_plane_axis:
							new_vec = new_vec - rmlib.util.ProjectVector( new_vec, mathutils.Matrix.Identity( 3 )[ self.s_tool.constrain_axis_idx ] )
						else:
							new_vec = rmlib.util.ProjectVector( new_vec, mathutils.Matrix.Identity( 3 )[ self.s_tool.constrain_axis_idx ] )
					bm.verts[ vert_data[ APPLY_VERT_ID ] ].co = vert_data[ APPLY_VERT_POSITION ] + new_vec

				bm.normal_update()
				bmesh.update_edit_mesh( active_obj.data )
				self.do_update = False

			self.s_draw.UpdateFromToolState( self.s_tool )
			return { 'RUNNING_MODAL' }

		elif self.tool_mode == 'ROTATE_ALL':
			if event.value == 'RELEASE' and event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
				bm.normal_update()

				self.s_tool.constrain_axis_idx = -1

				# add to undo history
				self.s_history.ClearRedo()
				pre_work_verts = [ bm.verts[ v_id ] for v_id in self.work_verts ]
				self.s_history.AddHistory( pre_work_verts )

				self.tool_mode = 'IDLE'

			elif self.do_update:
				# move points
				start_point_2d = bpy_extras.view3d_utils.location_3d_to_region_2d( region, rv3d, self.s_tool.start_point )
				if start_point_2d:
					new_vec_dir = ( self.s_mouse.m_mouse_current_2d - start_point_2d ).normalized()
					rot_angle = new_vec_dir.angle( self.s_mouse.m_mouse_rotate_start_vec_2d )

					if rot_angle != 0.0:
						# check for left or right direction to rotate
						new_vec_dir_ortho = mathutils.Vector( ( new_vec_dir.y, -new_vec_dir.x ) )
						if new_vec_dir_ortho.dot( self.s_mouse.m_mouse_rotate_start_vec_2d ) > 0.0:
							rot_angle *= -1.0
						
						xfrm = active_obj.matrix_world
						xfrm_inv = xfrm.inverted()
						for vert_data in self.apply_tool_verts:
							lerp_rot = rot_angle * vert_data[ APPLY_VERT_WEIGHT ]
							look_dir = ( rv3d.view_rotation @ mathutils.Vector( ( 0.0, 0.0, -1.0 ) ) ).normalized()
							rotMat = mathutils.Matrix.Rotation( lerp_rot, 4, look_dir )
							if self.s_tool.constrain_axis_idx >= 0:
								vRotAxis = mathutils.Vector( ( self.s_tool.constrain_axis_idx == 0, self.s_tool.constrain_axis_idx == 1, self.s_tool.constrain_axis_idx == 2 ) )
								rotMat = mathutils.Matrix.Rotation( lerp_rot, 4, vRotAxis )

							offsetMat = mathutils.Matrix.Translation( self.s_tool.transform_origin )
							offsetMat_inv = mathutils.Matrix.Translation( self.s_tool.transform_origin * -1.0 )

							bm.verts[ vert_data[ APPLY_VERT_ID ] ].co = ( xfrm_inv @ offsetMat @ rotMat @ offsetMat_inv @ xfrm ) @ vert_data[ APPLY_VERT_POSITION ]

						bm.normal_update()
						bmesh.update_edit_mesh( active_obj.data )

				self.do_update = False

			self.s_draw.UpdateFromToolState( self.s_tool )
			return { 'RUNNING_MODAL' }

		else:
			if event.value == 'RELEASE' and event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
				self.tool_mode = 'IDLE'
				self.s_draw.UpdateFromToolState( self.s_tool )
				return { 'RUNNING_MODAL' }

		# get keys
		if keys_pass is True:
			# allow navigation
			self.s_draw.UpdateFromToolState( self.s_tool )
			return { 'PASS_THROUGH' }

		elif event.type in { 'RIGHTMOUSE', 'ESC' }:
			self.s_history.ResetToInitialVertPositions( bm )
			bm.normal_update()
			bmesh.update_edit_mesh( active_obj.data )
			context.workspace.status_text_set( text=None )
			self.s_draw.UnregisterDrawCallbacks()
			return { 'CANCELLED' }					

		self.s_draw.UpdateFromToolState( self.s_tool )
		return { 'RUNNING_MODAL' }


	def reset_params( self ):
		self.tool_mode = 'IDLE'

		self.do_update = False
		self.s_tool = None
		self.active_lw_point_id = POINT_HANDLE_INVALID

		self.start_work_center = None
		self.work_verts = None
		self.apply_tool_verts = None

		self.s_history.ClearAll()
				
				
class MESH_OT_quicklineardeform( bpy.types.Operator ):
	'''Set the FalloffTransform Tool based on camera space direction.'''
	bl_idname = 'mesh.rm_quicklineardeform'
	bl_label = 'Quick Falloff Transform'
	#bl_options = { 'REGISTER', 'UNDO' }
	bl_options = { 'UNDO' }

	str_dir: bpy.props.EnumProperty( 
		items=[ ( 'up', 'Up', '', 1 ), 
				( 'down', 'Down', '', 2 ), 
				( 'left', 'Left', '', 3 ), 
				( 'right', 'Right', '', 4 ) ], 
		name='Direction', 
		default='right'
	 )

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def __find_furthest( self, elems, dir_vec, dir_vec_fwd ):
		bbox_transform = rmlib.util.LookAt( dir_vec, dir_vec.cross( dir_vec_fwd ), mathutils.Vector( ( 0.0, 0.0, 0.0 ) ) )
		bbox_transform_inv = bbox_transform.inverted()

		bbox_min = None
		bbox_max = None
		for rmmesh, g in elems.items():
			xfrm = rmmesh.world_transform
			group_bbox_min = bbox_transform_inv @ xfrm @ g[ 0 ].co
			group_bbox_max = bbox_transform_inv @ xfrm @ g[ 0 ].co
			max_dot = dir_vec.dot( group_bbox_min )
			min_dot = dir_vec.dot( group_bbox_max )
			for i in range( 1, len( g ) ):
				vpos = bbox_transform_inv @ xfrm @ g[ i ].co
				group_bbox_min.x = min( vpos.x, group_bbox_min.x )
				group_bbox_min.y = min( vpos.y, group_bbox_min.y )
				group_bbox_min.z = min( vpos.z, group_bbox_min.z )
				group_bbox_max.x = max( vpos.x, group_bbox_max.x )
				group_bbox_max.y = max( vpos.y, group_bbox_max.y )
				group_bbox_max.z = max( vpos.z, group_bbox_max.z )

			if bbox_min is None:
				bbox_min = group_bbox_min.copy()
			else:
				bbox_min.x = min( vpos.x, group_bbox_min.x )
				bbox_min.y = min( vpos.y, group_bbox_min.y )
				bbox_min.z = min( vpos.z, group_bbox_min.z )

			if bbox_max is None:
				bbox_max = group_bbox_max.copy()
			else:
				bbox_max.x = max( vpos.x, group_bbox_max.x )
				bbox_max.y = max( vpos.y, group_bbox_max.y )
				bbox_max.z = max( vpos.z, group_bbox_max.z )

		bbox_min.x = ( bbox_min.x + bbox_max.x ) / 2.0
		bbox_min.y = ( bbox_min.y + bbox_max.y ) / 2.0
		bbox_max.x = bbox_min.x
		bbox_max.y = bbox_min.y

		return bbox_transform @ bbox_min, bbox_transform @ bbox_max

	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		co = context.scene.transform_orientation_slots[ 0 ].custom_orientation
		grid_matrix = mathutils.Matrix.Identity( 3 )
		if co is not None:
			grid_matrix = mathutils.Matrix( co.matrix ).to_3x3()
			
		rm_vp = rmlib.rmViewport( context )
		dir_idx, cam_dir_vec, grid_dir_vec = rm_vp.get_nearest_direction_vector( self.str_dir, grid_matrix )
		dir_idx_fwd, cam_dir_vec_fwd, grid_dir_vec_fwd = rm_vp.get_nearest_direction_vector( 'front', grid_matrix )
		
		sel_mode = context.tool_settings.mesh_select_mode[ : ]
		elems = {}
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			elems[ rmmesh ] = None
			
			bm = bmesh.from_edit_mesh( rmmesh.mesh )
			rmmesh.bmesh = bm
			
			if sel_mode[ 0 ]:
				selected_verts = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( selected_verts ) < 1:
					return { 'CANCELLED' }
				elems[ rmmesh ] = selected_verts
			elif sel_mode[ 1 ]:
				selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				if len( selected_edges ) < 1:
					return { 'CANCELLED' }
				elems[ rmmesh ] = selected_edges.vertices
			elif sel_mode[ 2 ]:
				selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				if len( selected_polys ) < 1:
					return { 'CANCELLED' }
				elems[ rmmesh ] = selected_polys.vertices			
			else:
				return { 'CANCELLED' }
				
		plane_pos_min, plane_pos_max = self.__find_furthest( elems, grid_dir_vec * -1.0, grid_dir_vec_fwd )
		if plane_pos_min is None or plane_pos_max is None:
			return { 'CANCELLED' }

		bpy.ops.mesh.rm_falloff( 'INVOKE_DEFAULT', min_wld_pos=plane_pos_min, max_wld_pos=plane_pos_max )
			
		return { 'FINISHED' }


class VIEW3D_MT_PIE_quicklineardeform( bpy.types.Menu ):
	'''Set the FalloffTransform Tool based on camera space direction.'''
	bl_idname = 'VIEW3D_MT_PIE_quicklineardeform'
	bl_label = 'Quick Linear Transform Pie'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_quicklineardeform', text='Left' )
		op_l.str_dir = 'left'
		
		op_r = pie.operator( 'mesh.rm_quicklineardeform', text='Right' )
		op_r.str_dir = 'right'
		
		op_d = pie.operator( 'mesh.rm_quicklineardeform', text='Down' )
		op_d.str_dir = 'down'
		
		op_u = pie.operator( 'mesh.rm_quicklineardeform', text='Up' )
		op_u.str_dir = 'up'
		
		pie.separator()
		
		pie.separator()

		pie.separator()
		
		pie.separator()


def register():
	print( 'register :: {}'.format( MESH_OT_Linear_Deformer.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_quicklineardeform.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_quicklineardeform.bl_idname ) )
	bpy.utils.register_class( MESH_OT_Linear_Deformer )
	bpy.utils.register_class( MESH_OT_quicklineardeform )
	bpy.utils.register_class( VIEW3D_MT_PIE_quicklineardeform )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_Linear_Deformer.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_quicklineardeform.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_quicklineardeform.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_Linear_Deformer )
	bpy.utils.unregister_class( MESH_OT_quicklineardeform )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_quicklineardeform )