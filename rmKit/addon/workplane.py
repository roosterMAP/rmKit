import bpy
import bgl
import gpu
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_location_3d
import math, time
import mathutils
import rmKit.rmlib as rmlib

GRID_RENDER = None


class GridRenderManager:	
	coords = []
	colors = []
	shader = None
	batch = None
	handle = None
	active = False
	matrix = mathutils.Matrix.Identity( 4 )
	scale = 1.0

	def __init__( self, context ):
		GridRenderManager.shader = gpu.shader.from_builtin( '3D_SMOOTH_COLOR' )
		self.update_scale( context )

	def update_scale( self, context ):
		if context.area is None:
			return

		width = context.region.width
		height = context.region.height
		top = ( width * 0.5, height )
		left = ( 0.0, height * 0.5 )
		right = ( width, height * 0.5 )
		bottom = ( width * 0.5, 0.0 )
		center = ( width * 0.5, height * 0.5 )
		screen_pts = ( top, left, right, bottom, center )

		hit_list = []
		pp = GridRenderManager.matrix.to_translation()
		pn = GridRenderManager.matrix.to_3x3().col[2]
		for pt in screen_pts:
			dir = region_2d_to_vector_3d( context.region, context.region_data, pt ) 
			pos = region_2d_to_location_3d( context.region, context.region_data, pt, dir )
			a = pos
			b = a + ( dir * 1000.0 )
			a = a - ( dir * 1000.0 )
			hit_pos = mathutils.geometry.intersect_line_plane( a, b, pp, pn )
			if hit_pos is None:
				continue
			hit_list.append( hit_pos )

		min_dist = 500
		for p in hit_list[:-1]:
			d = ( p - hit_list[-1] ).length
			min_dist = min( d, min_dist )

		scale_idx = math.floor( math.log2( min_dist ) )
		GridRenderManager.scale = math.pow( 2, scale_idx - 2 )

		self.shader_batch()

	def shader_batch( self ):
		GridRenderManager.coords.clear()
		GridRenderManager.colors.clear()
		n = 1.0
		s = GridRenderManager.scale

		for i in range( -10, 10 + 1 ):
			GridRenderManager.coords.append( ( n * i * s, -10.0 * s, 0.0 ) )
			GridRenderManager.coords.append( ( n * i * s, 10.0 * s, 0.0 ) )
			GridRenderManager.coords.append( ( -10.0 * s, n * i * s, 0.0 ) )
			GridRenderManager.coords.append( ( 10.0 * s, n * i * s, 0.0 ) )

			if i == 0:
				GridRenderManager.colors.append( ( 1.0, 0.0, 0.0, 0.5 ) )
				GridRenderManager.colors.append( ( 1.0, 0.0, 0.0, 0.5 ) )
				GridRenderManager.colors.append( ( 0.0, 1.0, 0.0, 0.5 ) )
				GridRenderManager.colors.append( ( 0.0, 1.0, 0.0, 0.5 ) )
			else:
				GridRenderManager.colors.append( ( 0.5, 0.5, 0.5, 0.5 ) )
				GridRenderManager.colors.append( ( 0.5, 0.5, 0.5, 0.5 ) )
				GridRenderManager.colors.append( ( 0.5, 0.5, 0.5, 0.5 ) )
				GridRenderManager.colors.append( ( 0.5, 0.5, 0.5, 0.5 ) )
				
		content = { 'pos' : GridRenderManager.coords, 'color' : GridRenderManager.colors }
		GridRenderManager.batch = batch_for_shader( GridRenderManager.shader, 'LINES', content )

	def draw( self ):
		if GridRenderManager.batch:
			bgl.glEnable( bgl.GL_BLEND )
			bgl.glEnable( bgl.GL_DEPTH_TEST )
			bgl.glEnable( bgl.GL_LINE_SMOOTH )
			bgl.glLineWidth( 2 )
			
			gpu.matrix.push()
			gpu.matrix.load_matrix( GridRenderManager.matrix )			
			gpu.matrix.push_projection()    
			gpu.matrix.load_projection_matrix( bpy.context.region_data.perspective_matrix )
			
			GridRenderManager.shader.bind()
			GridRenderManager.batch.draw( GridRenderManager.shader )

			# restore opengl defaults
			gpu.matrix.pop()
			gpu.matrix.pop_projection()

			bgl.glDisable( bgl.GL_BLEND )
			bgl.glDisable( bgl.GL_DEPTH_TEST )
			bgl.glDisable( bgl.GL_LINE_SMOOTH )
			bgl.glLineWidth( 1 )

	def doDraw( self ):
		GridRenderManager.handle = bpy.types.SpaceView3D.draw_handler_add( self.draw, (), 'WINDOW', 'POST_VIEW' )
		GridRenderManager.active = True
		
	def stopDraw( self, context ):
		bpy.types.SpaceView3D.draw_handler_remove( GridRenderManager.handle, 'WINDOW' )
		GridRenderManager.active = False

		for window in context.window_manager.windows:
			for area in window.screen.areas:
				if area.type == 'VIEW_3D':
					for region in area.regions:
						if region.type == 'WINDOW':
							region.tag_redraw()


class MESH_OT_workplane( bpy.types.Operator ):    
	"""Draw workplane"""
	bl_idname = 'view3d.rm_workplane'
	bl_label = 'Workplane'
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return context.area.type == 'VIEW_3D'
		
	def invoke(self, context, event):
		#add a timer to modal
		wm = context.window_manager
		self._timer = wm.event_timer_add(1.0/8.0, window=context.window)
		wm.modal_handler_add(self)	

		self.execute( context )

		return {'RUNNING_MODAL'}

	def modal(self, context, event):
		global GRID_RENDER

		#kill modal if inactive
		if not GRID_RENDER.active:
			return {'FINISHED'}

		#check if user manually left workplane transform orientation mode
		if event.type == 'TIMER':
			GRID_RENDER.update_scale( context )

			if not context.scene.transform_orientation_slots[0].type == 'WORKPLANE':
				GRID_RENDER.stopDraw( context )
				bpy.context.space_data.overlay.show_floor = True
				bpy.context.space_data.overlay.show_axis_x = True
				bpy.context.space_data.overlay.show_axis_y = True
				
				selected_type = context.scene.transform_orientation_slots[0].type
				try:
					context.scene.transform_orientation_slots[0].type = 'WORKPLANE'
					bpy.ops.transform.delete_orientation()
					context.scene.transform_orientation_slots[0].type = selected_type
				except TypeError:
					pass
				
				return {'FINISHED'}

		return {"PASS_THROUGH"}

	def execute(self, context):
		global GRID_RENDER
		if GRID_RENDER is None:
			GRID_RENDER = GridRenderManager( context )

		if not GridRenderManager.active and context.mode == 'EDIT_MESH':
			sel_mode = context.tool_settings.mesh_select_mode[:]
			rmmesh = rmlib.rmMesh.GetActive( context )
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				if sel_mode[0]:
					sel_verts = rmlib.rmVertexSet.from_selection( rmmesh )
					if len( sel_verts ) > 0:
						v = sel_verts[0]

						v_n = v.normal

						v_t = mathutils.Vector( ( 0.0, 0.0001, 1.0 ) )
						for e in v.link_edges:
							v1, v2 = e.verts
							v_t = v2.co - v1.co
							v_t = v_n.cross( v_t.normalized() )
						
						GridRenderManager.matrix = rmlib.util.LookAt( v_n, v_t, v.co )

				elif sel_mode[1]:
					sel_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					if len( sel_edges ) > 0:
						e = sel_edges[0]

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
						
						GridRenderManager.matrix = rmlib.util.LookAt( e_n, e_t, e_p )

				elif sel_mode[2]:
					sel_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
					if len( sel_polys ) > 0:
						p = sel_polys[0]
						
						GridRenderManager.matrix = rmlib.util.LookAt( p.normal, p.calc_tangent_edge_pair(), p.calc_center_median() )

		elif not GridRenderManager.active and context.mode != 'OBJECT' and context.object is not None:
			GridRenderManager.matrix = mathutils.Matrix( context.object.matrix_world )

		#toggle the render state of the GRID_RENDER global
		if GridRenderManager.active:
			bpy.context.space_data.overlay.show_floor = bpy.context.scene.workplaneprops['prop_show_floor']
			bpy.context.space_data.overlay.show_axis_x = bpy.context.scene.workplaneprops['prop_show_x']
			bpy.context.space_data.overlay.show_axis_y = bpy.context.scene.workplaneprops['prop_show_y']
			bpy.context.space_data.overlay.show_axis_z = bpy.context.scene.workplaneprops['prop_show_z']

			context.scene.transform_orientation_slots[0].type = 'GLOBAL'
			GRID_RENDER.stopDraw( context )
		else:
			bpy.context.scene.workplaneprops['prop_show_floor'] = bpy.context.space_data.overlay.show_floor
			bpy.context.scene.workplaneprops['prop_show_x'] = bpy.context.space_data.overlay.show_axis_x
			bpy.context.scene.workplaneprops['prop_show_y'] = bpy.context.space_data.overlay.show_axis_y
			bpy.context.scene.workplaneprops['prop_show_z'] = bpy.context.space_data.overlay.show_axis_z

			bpy.context.space_data.overlay.show_floor = False
			bpy.context.space_data.overlay.show_axis_x = False
			bpy.context.space_data.overlay.show_axis_y = False
			bpy.context.space_data.overlay.show_axis_z = False

			bpy.ops.transform.create_orientation( name='WORKPLANE', use=True, use_view=True, overwrite=True )
			orientation = context.scene.transform_orientation_slots[0].custom_orientation
			orientation.matrix = GRID_RENDER.matrix.to_3x3()

			GRID_RENDER.doDraw()

		return { 'FINISHED' }


class MESH_OT_togglegrid( bpy.types.Operator ):
	bl_idname = 'view3d.rm_togglegrid'
	bl_label = 'Toggle Grid'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' )
		
	def execute( self, context ):
		b1 = bpy.context.space_data.overlay.show_floor
		b2 = bpy.context.space_data.overlay.show_axis_x
		b3 = bpy.context.space_data.overlay.show_axis_y
		b4 = bpy.context.space_data.overlay.show_axis_z

		if b1 or b2 or b3 or b4:
			bpy.context.scene.workplaneprops['prop_show_floor'] = b1
			bpy.context.scene.workplaneprops['prop_show_x'] = b2
			bpy.context.scene.workplaneprops['prop_show_y'] = b3
			bpy.context.scene.workplaneprops['prop_show_z'] = b4
			bpy.context.space_data.overlay.show_floor = False
			bpy.context.space_data.overlay.show_axis_x = False
			bpy.context.space_data.overlay.show_axis_y = False
			bpy.context.space_data.overlay.show_axis_z = False
		else:
			bpy.context.space_data.overlay.show_floor = bpy.context.scene.workplaneprops['prop_show_floor']
			bpy.context.space_data.overlay.show_axis_x = bpy.context.scene.workplaneprops['prop_show_x']
			bpy.context.space_data.overlay.show_axis_y = bpy.context.scene.workplaneprops['prop_show_y']
			bpy.context.space_data.overlay.show_axis_z = bpy.context.scene.workplaneprops['prop_show_z']
				
		return { 'FINISHED' }


class GridVisibility( bpy.types.PropertyGroup ):
	prop_show_floor: bpy.props.BoolProperty( name="Show Floor", default=True )
	prop_show_x: bpy.props.BoolProperty( name="Show X Axis", default=True )
	prop_show_y: bpy.props.BoolProperty( name="Show Y Axis", default=True )
	prop_show_z: bpy.props.BoolProperty( name="Show Z Axis", default=False )

	
def register():
	print( 'register :: {}'.format( MESH_OT_workplane.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_togglegrid.bl_idname ) )
	bpy.utils.register_class( MESH_OT_workplane )
	bpy.utils.register_class( MESH_OT_togglegrid )
	bpy.utils.register_class( GridVisibility )
	bpy.types.Scene.workplaneprops = bpy.props.PointerProperty( type=GridVisibility )
	
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_workplane.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_togglegrid.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_workplane )
	bpy.utils.unregister_class( MESH_OT_togglegrid )
	bpy.utils.unregister_class( GridVisibility )
	del bpy.types.Scene.workplaneprops