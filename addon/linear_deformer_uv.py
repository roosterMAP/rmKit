import bpy, bmesh, mathutils, bpy_extras, gpu
from gpu_extras.batch import batch_for_shader
from .. import rmlib
import math

pass_keys = { 'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_3', 'NUMPAD_4', 
			 'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 
			 'NUMPAD_9', 'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 
			 'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TRACKPADPAN', 'TRACKPADZOOM' }

EPSILON = 0.000001

APPLY_VERT_ID = 0
APPLY_VERT_WEIGHT = 1
APPLY_VERT_POSITION = 2

ENDPOINT_HANDLE_SIZE = 6.0
LINE_WIDTH_SIZE = 1.0

POINT_HANDLE_INVALID = -1
POINT_HANDLE_START = 0
POINT_HANDLE_MIDDLE = 1
POINT_HANDLE_END = 2

CONSTRAIN_AXIS_NONE = -1
CONSTRAIN_AXIS_HORIZONTAL = 0
CONSTRAIN_AXIS_VERTICAL = 1

QUADRATIC_EASING_LIN = 0
QUADRATIC_EASING_IN = 1
QUADRATIC_EASING_OUT = 2
QUADRATIC_EASING_COUNT = 3


class WorkVert():
	def __init__( self, loop, uvlayer ):
		self.__idx = loop.index
		self.__pos = loop[uvlayer].uv


class MouseState():
	def __init__( self, context ):
		self.__context = context
		self.m_current_region = None
		self.m_current_view = None
		self.m_start_view = None
		self.m_start_mmb_region = None

	def UpdateCurrentMouse( self, context, event ):
		self.m_current_region = mathutils.Vector( ( event.mouse_region_x, event.mouse_region_y ) )
		self.m_current_view = mathutils.Vector( context.region.view2d.region_to_view( self.m_current_region.x, self.m_current_region.y ) )

	def GetCurrentViewPosition( self ):
		return self.m_current_view.copy()
	
	def GetCurrentRegionPosition( self ):
		return self.m_current_region.copy()
	
	def CurrentlyWithinRegion( self ):
		return ( self.m_current_region.x >= 0 and
				self.m_current_region.x < self.__context.region.width and
				self.m_current_region.y >= 0 and
				self.m_current_region.y < self.__context.region.height )

	def InitTransformStart( self, context, event ):
		self.m_start_view = mathutils.Vector( context.region.view2d.region_to_view( event.mouse_region_x, event.mouse_region_y ) )

	def GetMMBDelta( self ):
		return self.m_current_region - self.m_start_mmb_region

	def GetMoveDelta( self ):
		return self.m_current_view - self.m_start_view

	def GetScaleAmount( self, constraint, tool_state ):
		relative_length = ( tool_state.end_point - tool_state.start_point ).length
		delta = ( self.m_current_view - self.m_start_view )
		if constraint == CONSTRAIN_AXIS_NONE:
			return ( delta.x + delta.y + relative_length * 2.0 ) * 0.5  / relative_length
		elif constraint == CONSTRAIN_AXIS_HORIZONTAL:
			return ( delta.x + relative_length ) / relative_length
		else:
			return ( delta.y + relative_length ) / relative_length

	def GetRotateAmount( self, tool_state ):
		a = ( self.m_start_view - tool_state.start_point ).normalized()
		b = ( self.m_current_view - tool_state.start_point ).normalized()		
		return math.atan2( a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y )

	def InitMMBStart( self, event ):
		self.m_start_mmb_region = mathutils.Vector( ( event.mouse_region_x, event.mouse_region_y ) )

	def ClearMMB( self ):
		self.m_start_mmb_region = None

	def TestMMB( self ):
		return self.m_start_mmb_region is not None


class ToolState():
	def __init__( self, context=None, event=None ):
		self.start_point = None
		self.middle_point = None
		self.end_point = None
		self.quadratic_easing = QUADRATIC_EASING_LIN
		self.constraint_axis_idx = CONSTRAIN_AXIS_NONE
		self.active_handle_idx = POINT_HANDLE_END
		self.transform_origin = None
		
		if context is not None and event is not None:
			self.start_point = mathutils.Vector( context.region.view2d.region_to_view( event.mouse_region_x, event.mouse_region_y ) )
			self.middle_point = self.start_point.copy()
			self.end_point = self.start_point.copy()

	def ComputeTransformOrigin( self, context, tool_verts ):
		#set transform_origin
		self.transform_origin = self.start_point #backup
		transform_pivot = context.scene.tool_settings.transform_pivot_point
		if transform_pivot == 'BOUNDING_BOX_CENTER':
			if len( tool_verts ) > 0:
				bbmin = tool_verts[ 0 ][ APPLY_VERT_POSITION ].copy()
				bbmax = tool_verts[ 0 ][ APPLY_VERT_POSITION ].copy()
				for vert_data in tool_verts:
					bbmin[ 0 ] = min( vert_data[ APPLY_VERT_POSITION ][ 0 ], bbmin[ 0 ] )
					bbmax[ 0 ] = min( vert_data[ APPLY_VERT_POSITION ][ 0 ], bbmax[ 0 ] )
					bbmin[ 1 ] = min( vert_data[ APPLY_VERT_POSITION ][ 1 ], bbmin[ 1 ] )
					bbmax[ 1 ] = min( vert_data[ APPLY_VERT_POSITION ][ 1 ], bbmax[ 1 ] )
				self.transform_origin = ( bbmax + bbmin ) * 0.5
		elif transform_pivot == 'CURSOR':
			if context.area.type == 'IMAGE_EDITOR':
				self.transform_origin = context.space_data.cursor_location

	def GetTransformOrigin( self ):
		return self.transform_origin

	def SetActiveHandlePosition( self, new_pos ):
		if self.active_handle_idx == POINT_HANDLE_START:
			self.start_point = new_pos.copy()
		elif self.active_handle_idx == POINT_HANDLE_MIDDLE:
			delta = new_pos - self.middle_point
			self.start_point += delta
			self.end_point += delta
		else:
			self.end_point = new_pos.copy()

		self.RecomputeMiddlePoint()

	def RecomputeMiddlePoint( self ):
		self.middle_point = ( self.start_point + self.end_point ) * 0.5

	def SetActiveHandle( self, flag ):
		self.active_handle_idx = flag
		
	def TestHandle( self, region, mouse_region_pos ):
		start_region = mathutils.Vector( region.view2d.view_to_region( self.start_point.x, self.start_point.y ) )
		if ( start_region - mouse_region_pos ).length <= 9.0:
			self.SetActiveHandle( POINT_HANDLE_START )
			return True
		
		middle_region = mathutils.Vector( region.view2d.view_to_region( self.middle_point.x, self.middle_point.y ) )
		if ( middle_region - mouse_region_pos ).length <= 9.0:
			self.SetActiveHandle( POINT_HANDLE_MIDDLE )
			return True
		
		end_region = mathutils.Vector( region.view2d.view_to_region( self.end_point.x, self.end_point.y ) )
		if ( end_region - mouse_region_pos ).length <= 9.0:
			self.SetActiveHandle( POINT_HANDLE_END )
			return True
		
		self.SetActiveHandle( POINT_HANDLE_INVALID )
		return False

	def ComputeWeightAtPosition( self, pos ):
		handle_vec = self.end_point - self.start_point
		vec = rmlib.util.ProjectVector( ( pos - self.start_point ), handle_vec )
		return vec.length / handle_vec.length
		
	def Test( self ):
		return self.start_point is not None

	def SetAxisConstraint( self, idx ):
		self.constraint_axis_idx = idx
		
	def GetAxisConstraint( self ):
		return self.constraint_axis_idx
		

class ToolHistory():
	def __init__( self ):
		self.m_undo = []
		self.m_redo = []

	def ResetToInitialVertPositions( self, uvlayer, loops ):
		for idx, uv in self.m_undo[0]:
			l[uvlayer].uv = uv.copy()

	def AddHistory( self, uvlayer, work_loop_data ):
		history = []
		for idx, weight, uv in work_loop_data:
			history.append( ( idx, uv.copy() ) )
		self.m_undo.append( history )

	def UndoHistory( self, rmmesh, uvlayer, loops ):
		if self.m_undo:
			pre_history = self.m_undo[ -1 ]
			if len( self.m_undo ) > 1:  # 0 index is always original verts
				self.m_undo.remove( pre_history )
				self.m_redo.append( pre_history )

			history = self.m_undo[ -1 ]
			for i in range( len( history ) ):
				loops[i][uvlayer].uv = history[ i ][ 1 ].copy()

			bmesh.update_edit_mesh( rmmesh.mesh )

	def RedoHistory( self, rmmesh, uvlayer, loops ):
		if self.m_redo:
			history = self.m_redo[ -1 ]
			for i in range( len( history ) ):
				loops[i][uvlayer].uv = history[ i ][ 1 ].copy()

			self.m_redo.remove( history )
			self.m_undo.append( history )

			bmesh.update_edit_mesh( rmmesh.mesh )

	def ClearRedo( self ):
		self.m_redo.clear()

	def ClearAll( self ):
		self.m_undo.clear()
		self.m_redo.clear()

	def Test( self ):
		return len( self.m_undo ) > 0


class DrawHandler():
	def __init__( self, context ):
		self.m_region = context.region
		self.m_rv3d = context.region_data
		self.m_shader2d = gpu.shader.from_builtin( 'UNIFORM_COLOR' )
		self.m_axis_constraint_handle = None
		self.m_lin_deform_handle = None		
		self.m_toolState = ToolState()

	def UpdateFromToolState( self, state ):
		if state is None:
			return
		self.m_toolState.start_point = state.start_point
		self.m_toolState.middle_point = state.middle_point
		self.m_toolState.end_point = state.end_point
		self.m_toolState.quadratic_easing = state.quadratic_easing
		self.m_toolState.constraint_axis_idx = state.constraint_axis_idx

	def RegisterDrawCallbacks( self ):
		self.m_axis_constraint_handle = bpy.types.SpaceImageEditor.draw_handler_add( self.__drawAxisConstraint, (), 'WINDOW', 'POST_PIXEL' )
		self.m_lin_deform_handle = bpy.types.SpaceImageEditor.draw_handler_add( self.__drawLinearFalloffHandles, (), 'WINDOW', 'POST_PIXEL' )

	def UnregisterDrawCallbacks( self ):
		bpy.types.SpaceImageEditor.draw_handler_remove( self.m_axis_constraint_handle, 'WINDOW' )
		bpy.types.SpaceImageEditor.draw_handler_remove( self.m_lin_deform_handle, 'WINDOW' )
		self.m_axis_constraint_handle = None
		self.m_lin_deform_handle = None

	def __drawAxisConstraint( self ):
		if not self.m_toolState.Test():
			return

		if self.m_toolState.constraint_axis_idx == CONSTRAIN_AXIS_NONE:
			return
		
		middle_2d = mathutils.Vector( self.m_region.view2d.view_to_region( self.m_toolState.middle_point.x, self.m_toolState.middle_point.y, clip=False ) )

		coords = ( ( middle_2d.x, -999999.9 ), ( middle_2d.x, 999999.9 ) )
		color = ( 0.0, 0.0, 1.0, 1.0 )
		if self.m_toolState.constraint_axis_idx == CONSTRAIN_AXIS_HORIZONTAL:
			coords = ( ( -999999.9, middle_2d.y ), ( 999999.9, middle_2d.y ) )
			color = ( 0.0, 1.0, 0.0, 1.0 )

		gpu.state.line_width_set( LINE_WIDTH_SIZE )
		gpu.state.point_size_set( ENDPOINT_HANDLE_SIZE )

		batch = batch_for_shader( self.m_shader2d, 'LINE_STRIP', { 'pos': coords } )
		self.m_shader2d.bind()
		self.m_shader2d.uniform_float( 'color', color )
		batch.draw( self.m_shader2d )

	def __drawLinearFalloffHandles( self ):		
		if not self.m_toolState.Test():
			return

		start_2d = mathutils.Vector( self.m_region.view2d.view_to_region( self.m_toolState.start_point.x, self.m_toolState.start_point.y, clip=False ) )
		middle_2d = mathutils.Vector( self.m_region.view2d.view_to_region( self.m_toolState.middle_point.x, self.m_toolState.middle_point.y, clip=False ) )
		end_2d = mathutils.Vector( self.m_region.view2d.view_to_region( self.m_toolState.end_point.x, self.m_toolState.end_point.y, clip=False ) )
		
		ortho_dir = ( self.m_toolState.end_point - self.m_toolState.start_point ).normalized()
		ortho_dir = mathutils.Vector( ( -ortho_dir.y, ortho_dir.x ) )

		end_p1_view = self.m_toolState.end_point + ortho_dir * 0.1
		end_p2_view = self.m_toolState.end_point - ortho_dir * 0.1
		
		end_p1 = mathutils.Vector( self.m_region.view2d.view_to_region( end_p1_view.x, end_p1_view.y, clip=False ) )
		end_p2 = mathutils.Vector( self.m_region.view2d.view_to_region( end_p2_view.x, end_p2_view.y, clip=False ) )

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


def GetSelectedLoops( context, rmmesh ):
	uvlayer = rmmesh.active_uv

	sel_mode = context.tool_settings.mesh_select_mode[:]
	visible_faces = rmlib.rmPolygonSet()
	if sel_mode[0]:		
		for f in rmmesh.bmesh.faces:
			if f.hide:
				continue
			visible = True
			for v in f.verts:
				if not v.select:
					visible = False
					break
			if visible:
				visible_faces.append( f )
	elif sel_mode[1]:
		for f in rmmesh.bmesh.faces:
			if f.hide:
				continue
			visible = True
			for e in f.edges:
				if not e.select:
					visible = False
					break
			if visible:
				visible_faces.append( f )
	else:
		visible_faces = rmlib.rmPolygonSet.from_selection( rmmesh )

	if context.tool_settings.use_uv_select_sync:
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
		if sel_mode == 'EDGE':
			loop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			loops = rmlib.rmUVLoopSet( uvlayer=uvlayer )
			for l in loop_selection:
				if l.face in visible_faces:
					loops.append( l )
			loops.add_overlapping_loops( True )
			return loops
		else:
			loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			loops = rmlib.rmUVLoopSet( uvlayer=uvlayer )
			for l in loop_selection:
				if l.face in visible_faces:
					loops.append( l )
			return loops


class MESH_OT_Linear_Deformer_UV( bpy.types.Operator ):
	'''Modo Style Falloff Transform Tool'''
	bl_idname = 'mesh.rm_uvfalloff'
	bl_label = 'Falloff UV Transform Tool'
	bl_description = 'Modo Style Falloff Transform'
	bl_options = { 'REGISTER', 'UNDO' }
	 
	min_wld_pos: bpy.props.FloatVectorProperty(
		size=2,
		options={ 'HIDDEN' }
	 )

	max_wld_pos: bpy.props.FloatVectorProperty(
		size=2,
		options={ 'HIDDEN' }
	 )

	tool_modes = ( 'IDLE', 'MOVE_POINT', 'DRAW_TOOL', 'SCALE_ALL', 'MOVE_ALL', 'ROTATE_ALL' )
	s_mode = 'IDLE'

	s_history = ToolHistory()
	s_draw = None
	s_mouse = None
	s_tool = None

	def __init__( self ):
		self.m_work_loop_data = []
		
	def InitWorkLoops( self, loops, uvlayer ):
		self.m_work_loop_data.clear()
		for l in loops:
			uv = mathutils.Vector( l[uvlayer].uv )
			self.m_work_loop_data.append( ( l.index, MESH_OT_Linear_Deformer_UV.s_tool.ComputeWeightAtPosition( uv ), uv ) )

	def UpdateWorkLoops( self, loops, uvlayer ):
		for i in range( loops ):
			uv = mathutils.Vector( l[uvlayer].uv )
			self.m_work_loop_data[i] = ( ( self.m_work_loop_data[i][APPLY_VERT_ID], self.m_work_loop_data[i][APPLY_VERT_WEIGHT], uv ) )

	def invoke( self, context, event ):
		if context.area.type == 'IMAGE_EDITOR':
			rmmesh = rmlib.rmMesh.GetActive( context )
			if rmmesh is None:
				self.report( { 'WARNING' }, 'Active mesh not found' )
				return { 'CANCELLED' }

			MESH_OT_Linear_Deformer_UV.s_tool = None
			MESH_OT_Linear_Deformer_UV.s_draw = DrawHandler( context )
			MESH_OT_Linear_Deformer_UV.s_mouse = MouseState( context )
			MESH_OT_Linear_Deformer_UV.s_draw.RegisterDrawCallbacks()
			context.window_manager.modal_handler_add( self )
			self.s_history.ClearAll()

			if ( mathutils.Vector( list( self.min_wld_pos ) ) - mathutils.Vector( list( self.max_wld_pos ) ) ).length > EPSILON:
				MESH_OT_Linear_Deformer_UV.s_tool = ToolState()
				MESH_OT_Linear_Deformer_UV.s_tool.start_point = mathutils.Vector( list( self.min_wld_pos ) )
				MESH_OT_Linear_Deformer_UV.s_tool.end_point = mathutils.Vector( list( self.max_wld_pos ) )
				MESH_OT_Linear_Deformer_UV.s_tool.middle_point = mathutils.Vector( ( 0.0, 0.0 ) )
				MESH_OT_Linear_Deformer_UV.s_tool.RecomputeMiddlePoint()
				MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )

			return { 'RUNNING_MODAL' }
		else:
			self.report( { 'WARNING' }, 'View3D not found, cannot run operator' )
			return { 'CANCELLED' }

	def modal( self, context, event ):
		context.area.tag_redraw()
		
		region = context.region

		rmmesh = rmlib.item.rmMesh.from_bmesh( context.active_object, bmesh.from_edit_mesh( context.active_object.data ) )
		uv_layer = rmmesh.active_uv

		MESH_OT_Linear_Deformer_UV.s_mouse.UpdateCurrentMouse( context, event )

		tooltip_text = 'I:Invert, V:Invert, S:Scale, G:Move, R:Rotate, C:NextEasingMode, Ctrl+Z:Undo, Ctrl+Shift+Z:Redo'
		context.workspace.status_text_set( text=tooltip_text )
		
		if MESH_OT_Linear_Deformer_UV.s_mode == 'IDLE' and not MESH_OT_Linear_Deformer_UV.s_mouse.CurrentlyWithinRegion():
			return { 'PASS_THROUGH' }
	
		keys_pass = event.type in pass_keys

		loops = GetSelectedLoops( context, rmmesh )

		#manage axis constraints with mmb
		if MESH_OT_Linear_Deformer_UV.s_mode in { 'MOVE_ALL', 'SCALE_ALL' }:
			if MESH_OT_Linear_Deformer_UV.s_mode != 'IDLE' and event.type == 'MIDDLEMOUSE':
				if event.value == 'PRESS':
					MESH_OT_Linear_Deformer_UV.s_mouse.InitMMBStart( event )
				elif event.value == 'RELEASE':
					MESH_OT_Linear_Deformer_UV.s_mouse.ClearMMB()		
			if MESH_OT_Linear_Deformer_UV.s_mouse.TestMMB():
				mmb_delta = MESH_OT_Linear_Deformer_UV.s_mouse.GetMMBDelta()
				axis_constraint = CONSTRAIN_AXIS_HORIZONTAL if abs( mmb_delta.x ) > abs( mmb_delta.y ) else CONSTRAIN_AXIS_VERTICAL
				MESH_OT_Linear_Deformer_UV.s_tool.SetAxisConstraint( axis_constraint )				
				MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )

		#manage lmb
		if event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
			if MESH_OT_Linear_Deformer_UV.s_mode == 'IDLE':
				if event.value == 'PRESS':
					if MESH_OT_Linear_Deformer_UV.s_tool is None:
						print( '******' )
						MESH_OT_Linear_Deformer_UV.s_tool = ToolState( context, event )
						MESH_OT_Linear_Deformer_UV.s_mode = 'MOVE_POINT'
					else:
						if MESH_OT_Linear_Deformer_UV.s_tool.TestHandle( region, MESH_OT_Linear_Deformer_UV.s_mouse.GetCurrentRegionPosition() ):
							MESH_OT_Linear_Deformer_UV.s_mode = 'MOVE_POINT'
						else:
							context.workspace.status_text_set( text=None )
							self.s_draw.UnregisterDrawCallbacks()
							return { 'FINISHED' }
					MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )

			elif MESH_OT_Linear_Deformer_UV.s_mode == 'MOVE_POINT':
				if  event.value == 'RELEASE':
					MESH_OT_Linear_Deformer_UV.s_mode = 'IDLE'
					MESH_OT_Linear_Deformer_UV.s_tool.SetActiveHandle( POINT_HANDLE_INVALID )

			elif MESH_OT_Linear_Deformer_UV.s_mode in { 'MOVE_ALL', 'ROTATE_ALL', 'SCALE_ALL' }:
				if event.value == 'PRESS':
					MESH_OT_Linear_Deformer_UV.s_mode = 'IDLE'
					MESH_OT_Linear_Deformer_UV.s_tool.SetAxisConstraint( CONSTRAIN_AXIS_NONE )				
					MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )

		#manage transformations
		elif MESH_OT_Linear_Deformer_UV.s_mode == 'IDLE' and event.value == 'RELEASE' and keys_pass is False:
			if event.type in { 'S', 'G', 'R' }:
				self.InitWorkLoops( loops, uv_layer )

				if not MESH_OT_Linear_Deformer_UV.s_history.Test():
					MESH_OT_Linear_Deformer_UV.s_history.AddHistory( uv_layer, self.m_work_loop_data )

				if event.type == 'G':
					MESH_OT_Linear_Deformer_UV.s_mode = 'MOVE_ALL'
					MESH_OT_Linear_Deformer_UV.s_mouse.InitTransformStart( context, event )
					MESH_OT_Linear_Deformer_UV.s_tool.ComputeTransformOrigin( context, self.m_work_loop_data )
				elif event.type == 'S':
					MESH_OT_Linear_Deformer_UV.s_mode = 'SCALE_ALL'
					MESH_OT_Linear_Deformer_UV.s_mouse.InitTransformStart( context, event )
					MESH_OT_Linear_Deformer_UV.s_tool.ComputeTransformOrigin( context, self.m_work_loop_data )
				elif event.type == 'R':
					MESH_OT_Linear_Deformer_UV.s_mode = 'ROTATE_ALL'
					MESH_OT_Linear_Deformer_UV.s_mouse.InitTransformStart( context, event )
					MESH_OT_Linear_Deformer_UV.s_tool.ComputeTransformOrigin( context, self.m_work_loop_data )

			elif event.type == 'Z' and event.ctrl and MESH_OT_Linear_Deformer_UV.s_history.Test():
				if event.shift:
					self.s_history.RedoHistory( rmmesh, uv_layer, loops )
				else:
					self.s_history.UndoHistory( rmmesh, uv_layer, loops )

		else:
			if MESH_OT_Linear_Deformer_UV.s_mode == 'MOVE_POINT':
				MESH_OT_Linear_Deformer_UV.s_tool.SetActiveHandlePosition( MESH_OT_Linear_Deformer_UV.s_mouse.GetCurrentViewPosition() )
				MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )

			elif MESH_OT_Linear_Deformer_UV.s_mode == 'MOVE_ALL':
				if event.value == 'RELEASE' and event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
					self.s_history.ClearRedo()
					self.UpdateWorkLoops( loops, uv_layer )
					self.s_history.AddHistory( uv_layer, self.m_work_loop_data )
					self.tool_mode = 'IDLE'				
				else:					
					delta = MESH_OT_Linear_Deformer_UV.s_mouse.GetMoveDelta()
					if MESH_OT_Linear_Deformer_UV.s_tool.GetAxisConstraint() == CONSTRAIN_AXIS_HORIZONTAL:
						delta.y = 0.0
					elif MESH_OT_Linear_Deformer_UV.s_tool.GetAxisConstraint() == CONSTRAIN_AXIS_VERTICAL:
						delta.x = 0.0
						
					for i, l in enumerate( loops ):
						d = self.m_work_loop_data[i]
						l[uv_layer].uv = d[APPLY_VERT_POSITION] + delta * d[APPLY_VERT_WEIGHT]
					bmesh.update_edit_mesh( rmmesh.mesh )
					MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )

			elif MESH_OT_Linear_Deformer_UV.s_mode == 'SCALE_ALL':
				if event.value == 'RELEASE' and event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
					self.s_history.ClearRedo()
					self.UpdateWorkLoops( loops, uv_layer )
					self.s_history.AddHistory( uv_layer, self.m_work_loop_data )
					self.tool_mode = 'IDLE'

				else:								
					scale_amt = MESH_OT_Linear_Deformer_UV.s_mouse.GetScaleAmount( MESH_OT_Linear_Deformer_UV.s_tool.GetAxisConstraint(), MESH_OT_Linear_Deformer_UV.s_tool )
					for i, l in enumerate( loops ):
						d = self.m_work_loop_data[i]
						lerp_scale = ( scale_amt - 1.0 ) * d[APPLY_VERT_WEIGHT] + 1.0
						sclMat = mathutils.Matrix.Scale( lerp_scale, 2 )
						if MESH_OT_Linear_Deformer_UV.s_tool.GetAxisConstraint() == CONSTRAIN_AXIS_HORIZONTAL:
							sclMat[1][1] = 1.0
						elif MESH_OT_Linear_Deformer_UV.s_tool.GetAxisConstraint() == CONSTRAIN_AXIS_VERTICAL:
							sclMat[0][0] = 1.0
						uv = d[APPLY_VERT_POSITION] - MESH_OT_Linear_Deformer_UV.s_tool.GetTransformOrigin()
						uv = sclMat @ uv
						uv += MESH_OT_Linear_Deformer_UV.s_tool.GetTransformOrigin()
						l[uv_layer].uv = uv.copy()
						
					bmesh.update_edit_mesh( rmmesh.mesh )
					MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )

			elif MESH_OT_Linear_Deformer_UV.s_mode == 'ROTATE_ALL':
				if event.value == 'RELEASE' and event.type in { 'LEFTMOUSE', 'SELECTMOUSE' }:
					self.s_history.ClearRedo()
					self.UpdateWorkLoops( loops, uv_layer )
					self.s_history.AddHistory( uv_layer, self.m_work_loop_data )
					self.tool_mode = 'IDLE'

				else:					
					rotate_amt = MESH_OT_Linear_Deformer_UV.s_mouse.GetRotateAmount( MESH_OT_Linear_Deformer_UV.s_tool )
					for i, l in enumerate( loops ):
						d = self.m_work_loop_data[i]
						lerp_rot = rotate_amt * d[APPLY_VERT_WEIGHT]
						r1 = [ math.cos( lerp_rot ), -math.sin( lerp_rot ) ]
						r2 = [ math.sin( lerp_rot ), math.cos( lerp_rot ) ]
						rot_mat = mathutils.Matrix( [ r1, r2 ] )
						uv = d[APPLY_VERT_POSITION] - MESH_OT_Linear_Deformer_UV.s_tool.GetTransformOrigin()
						uv = rot_mat @ uv
						uv += MESH_OT_Linear_Deformer_UV.s_tool.GetTransformOrigin()
						l[uv_layer].uv = uv.copy()
						
					bmesh.update_edit_mesh( rmmesh.mesh )
					MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )
		
		#exit
		if event.type in { 'RIGHTMOUSE', 'ESC' } and event.value == 'RELEASE':
			for i, l in enumerate( loops ):
				l[uv_layer].uv = self.m_work_loop_data[i][APPLY_VERT_POSITION]
			bmesh.update_edit_mesh( rmmesh.mesh )
						
			if MESH_OT_Linear_Deformer_UV.s_mode not in { 'MOVE_ALL', 'ROTATE_ALL', 'SCALE_ALL' }:
				MESH_OT_Linear_Deformer_UV.s_draw.UnregisterDrawCallbacks()
				return { 'CANCELLED' }
			
			MESH_OT_Linear_Deformer_UV.s_mode = 'IDLE'
			MESH_OT_Linear_Deformer_UV.s_tool.SetAxisConstraint( CONSTRAIN_AXIS_NONE )

		if keys_pass and MESH_OT_Linear_Deformer_UV.s_mode == 'IDLE':
			MESH_OT_Linear_Deformer_UV.s_draw.UpdateFromToolState( MESH_OT_Linear_Deformer_UV.s_tool )
			return { 'PASS_THROUGH' }

		return { 'RUNNING_MODAL' }


class MESH_OT_quicklineardeform_UV( bpy.types.Operator ):
	'''Set the FalloffTransform Tool based on uv space direction.'''
	bl_idname = 'mesh.rm_uvquicklineardeform'
	bl_label = 'Quick Falloff Transform UV'
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
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		if context.area.type == 'IMAGE_EDITOR':
			rmmesh = rmlib.rmMesh.GetActive( context )
			if rmmesh is None:
				self.report( { 'WARNING' }, 'Active mesh not found' )
				return { 'CANCELLED' }

			with rmmesh as rmmesh:
				uv_layer = rmmesh.active_uv
				
				loops = GetSelectedLoops( context, rmmesh )
				bbox_min = loops[0][uv_layer].uv.copy()
				bbox_max = loops[0][uv_layer].uv.copy()
				for l in loops:
					uv = l[uv_layer].uv.copy()
					bbox_min.x = min( uv.x, bbox_min.x )
					bbox_min.y = min( uv.y, bbox_min.y )
					bbox_max.x = max( uv.x, bbox_max.x )
					bbox_max.y = max( uv.y, bbox_max.y )

				u_avg = ( bbox_min.x + bbox_max.x ) * 0.5
				v_avg = ( bbox_min.y + bbox_max.y ) * 0.5
				falloff_min = ( u_avg, bbox_min.y )
				falloff_max = ( u_avg, bbox_max.y )
				if self.str_dir == 'down':
					falloff_min = ( u_avg, bbox_max.y )
					falloff_max = ( u_avg, bbox_min.y )
				elif self.str_dir == 'left':
					falloff_min = ( bbox_max.x, v_avg )
					falloff_max = ( bbox_min.x, v_avg )
				elif self.str_dir == 'right':
					falloff_min = ( bbox_min.x, v_avg )
					falloff_max = ( bbox_max.x, v_avg )

				bpy.ops.mesh.rm_uvfalloff( 'INVOKE_DEFAULT', min_wld_pos=falloff_min, max_wld_pos=falloff_max )

			return { 'FINISHED' }
		else:
			self.report( { 'WARNING' }, 'IMAGE_EDITOR not found, cannot run operator' )
			return { 'CANCELLED' }


class VIEW3D_MT_PIE_quicklineardeform_UV( bpy.types.Menu ):
	'''Set the FalloffTransform Tool based on camera space direction.'''
	bl_idname = 'VIEW3D_MT_PIE_uvquicklineardeform'
	bl_label = 'Quick Linear Transform UV Pie'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_uvquicklineardeform', text='Left' )
		op_l.str_dir = 'left'
		
		op_r = pie.operator( 'mesh.rm_uvquicklineardeform', text='Right' )
		op_r.str_dir = 'right'
		
		op_d = pie.operator( 'mesh.rm_uvquicklineardeform', text='Down' )
		op_d.str_dir = 'down'
		
		op_u = pie.operator( 'mesh.rm_uvquicklineardeform', text='Up' )
		op_u.str_dir = 'up'
		
		pie.separator()
		
		pie.separator()

		pie.separator()
		
		pie.separator()


def register():
	print( 'register :: {}'.format( MESH_OT_Linear_Deformer_UV.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_quicklineardeform_UV.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_quicklineardeform_UV.bl_idname ) )
	bpy.utils.register_class( MESH_OT_Linear_Deformer_UV )
	bpy.utils.register_class( MESH_OT_quicklineardeform_UV )
	bpy.utils.register_class( VIEW3D_MT_PIE_quicklineardeform_UV )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_Linear_Deformer_UV.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_quicklineardeform_UV.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_quicklineardeform_UV.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_Linear_Deformer_UV )
	bpy.utils.unregister_class( MESH_OT_quicklineardeform_UV )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_quicklineardeform_UV )