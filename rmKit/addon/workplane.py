import bpy
import bgl
import gpu
from gpu_extras.batch import batch_for_shader
import math, time
import mathutils
import rmKit.rmlib as rmlib

def LookAt( look, up, pos ):	
	d = look.normalized()
	u = up.normalized()
	r = d.cross( u ).normalized()

	R = mathutils.Matrix( ( r, u, -d ) )
	R.transpose()
	
	return mathutils.Matrix.LocRotScale( pos, R, None )


GRID_RENDER = None


class GridRenderManager:	
	coords = []
	colors = []
	shader = None
	batch = None
	handle = None
	active = False
	matrix = mathutils.Matrix.Identity( 4 )

	def __init__( self ):
		GridRenderManager.coords = []
		GridRenderManager.colors = []
		n = 1.0
		m = 10
		for i in range( -m, m+1 ):
			GridRenderManager.coords.append( ( n * i, -m, 0.0 ) )
			GridRenderManager.coords.append( ( n * i, m, 0.0 ) )
			GridRenderManager.coords.append( ( -m, n * i, 0.0 ) )
			GridRenderManager.coords.append( ( m, n * i, 0.0 ) )

			if m == 0:
				GridRenderManager.colors.append( ( 1.0, 0.0, 0.0, 0.5 ) )
				GridRenderManager.colors.append( ( 1.0, 0.0, 0.0, 0.5 ) )
				GridRenderManager.colors.append( ( 0.0, 1.0, 0.0, 0.5 ) )
				GridRenderManager.colors.append( ( 0.0, 1.0, 0.0, 0.5 ) )
			else:
				GridRenderManager.colors.append( ( 0.5, 0.5, 0.5, 0.5 ) )
				GridRenderManager.colors.append( ( 0.5, 0.5, 0.5, 0.5 ) )
				GridRenderManager.colors.append( ( 0.5, 0.5, 0.5, 0.5 ) )
				GridRenderManager.colors.append( ( 0.5, 0.5, 0.5, 0.5 ) )
		
		GridRenderManager.shader = gpu.shader.from_builtin( '3D_SMOOTH_COLOR' )
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
			print( 'DRAW :: {}'.format( GridRenderManager.matrix ) )
			
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
	bl_idname = 'view3d.workplane'
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
			if not context.scene.transform_orientation_slots[0].type == 'WORKPLANE':
				print( 'NO LONGER WORKPLANE!!!' )
				GRID_RENDER.stopDraw( context )
				
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
			GRID_RENDER = GridRenderManager()

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
						
						GridRenderManager.matrix = LookAt( v_n, v_t, v.co )

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
						
						GridRenderManager.matrix = LookAt( e_n, e_t, e_p )
						print( 'EXECUTE :: {}'.format( GRID_RENDER.matrix ) )

				elif sel_mode[2]:
					sel_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
					if len( sel_polys ) > 0:
						p = sel_polys[0]
						
						GridRenderManager.matrix = LookAt( p.normal, p.calc_tangent_edge_pair(), p.calc_center_median() )

		elif not GridRenderManager.active and context.mode != 'OBJECT' and context.object is not None:
			GridRenderManager.matrix = mathutils.Matrix( context.object.matrix_world )

		#toggle the render state of the GRID_RENDER global
		if GridRenderManager.active:
			context.scene.transform_orientation_slots[0].type = 'GLOBAL'
			GRID_RENDER.stopDraw( context )
		else:
			bpy.ops.transform.create_orientation( name='WORKPLANE', use=True, use_view=True, overwrite=True )
			orientation = context.scene.transform_orientation_slots[0].custom_orientation
			orientation.matrix = GRID_RENDER.matrix.to_3x3()

			GRID_RENDER.doDraw()

		return { 'FINISHED' }

	
def register():
	bpy.utils.register_class( MESH_OT_workplane )
	
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_workplane )
	
if __name__ == '__main__':
	register()