import bpy
import bmesh
import rmKit.rmlib as rmlib
import mathutils
import math

class MESH_OT_push( bpy.types.Operator ):
	"""Offset vert/edge/face selection based off of vert normals."""
	bl_idname = 'mesh.rm_push'
	bl_label = 'Push'
	bl_options = { 'REGISTER', 'UNDO' }

	offset: bpy.props.FloatProperty(
		name='Distance',
		default=0.0
	)
	
	mode: bpy.props.EnumProperty(
		items=[ ( "selection", "Selection", "", 1 ),
				( "average", "Average", "", 2 ) ],
		name="Offset Mode",
		default="selection"
	)

	def __init__( self ):
		self.bmesh = None
		self.bbox_dist = 0.0
		
	def __del__( self ):
		if self.bmesh is not None:
			self.bmesh.free()
			self.bmesh = None
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )
		
		bm = self.bmesh.copy()

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			verts = rmlib.rmVertexSet( [ v for v in bm.verts if v.select ] )
		elif sel_mode[1]:
			edges = rmlib.rmEdgeSet( [ e for e in bm.edges if e.select ] )
			verts = edges.vertices
		elif sel_mode[2]:
			faces = rmlib.rmPolygonSet( [ f for f in bm.faces if f.select ] )
			verts = faces.vertices
		
		for v in verts:
			nml = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
			for f in v.link_faces:
				if f.hide:
					continue
				if sel_mode[2] and self.mode == 'selection' and not f.select:
					continue
				nml += f.normal.copy()
			v.co += nml.normalized() * self.offset

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
			delta_x = float( event.mouse_prev_press_x - event.mouse_x ) / context.region.width
			#delta_y = float( event.mouse_prev_press_y - event.mouse_y ) / context.region.height
			self.offset = delta_x * self.bbox_dist * 10.0
			self.execute( context )			
		elif event.type == 'ESC':
			return { 'CANCELLED' }

		return { 'RUNNING_MODAL' }
	
	def invoke( self, context, event ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readme = True
				self.bmesh = rmmesh.bmesh.copy()

				#init bbox_dist for haul sensitivity
				sel_mode = context.tool_settings.mesh_select_mode[:]
				if sel_mode[0]:
					verts = rmlib.rmVertexSet.from_selection( rmmesh )
				elif sel_mode[1]:
					edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					verts = edges.vertices
				elif sel_mode[2]:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
					verts = faces.vertices
				min = verts[0].co.copy()
				max = verts[0].co.copy()
				for v in verts:
					for i in range( 3 ):
						if v.co[i] < min[i]:
							min[i] = v.co[i]
						if v.co[i] > max[i]:
							max[i] = v.co[i]
				self.bbox_dist = ( max - min ).length
				
		context.window_manager.modal_handler_add( self )
		return { 'RUNNING_MODAL' }

def register():
	print( 'register :: {}'.format( MESH_OT_push.bl_idname ) )
	bpy.utils.register_class( MESH_OT_push )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_push.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_push )