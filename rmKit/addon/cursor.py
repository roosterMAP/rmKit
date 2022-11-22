import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

class MESH_OT_cursortoselection( bpy.types.Operator ):
	"""Move and orient the 3D Cursor to the vert/edge/face selection."""
	bl_idname = 'view3d.rm_cursor_to_selection'
	bl_label = 'Move and Orient 3D Cursor to Selection'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' )

	def execute( self, context ):
		if context.mode == 'EDIT_MESH':
			sel_mode = context.tool_settings.mesh_select_mode[:]
			rmmesh = rmlib.rmMesh.GetActive( context )
			if rmmesh is None:
				return { 'CANCELLED' }
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

						v_p = rmmesh.world_transform @ v.co.copy()
						v_t = rmmesh.world_transform.to_3x3() @ v_t
						v_n = rmmesh.world_transform.to_3x3() @ v_n
						m4 = rmlib.util.LookAt( v_n, v_t, v_p )
						context.scene.cursor.matrix = m4
						context.scene.cursor.location = v_p


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
						
						e_p = rmmesh.world_transform @ e_p
						e_t = rmmesh.world_transform.to_3x3() @ e_t
						e_n = rmmesh.world_transform.to_3x3() @ e_n
						m4 = rmlib.util.LookAt( e_n, e_t, e_p )						
						context.scene.cursor.matrix = m4
						context.scene.cursor.location = e_p

				elif sel_mode[2]:
					sel_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
					if len( sel_polys ) > 0:
						p = sel_polys[0]
						
						p_p = rmmesh.world_transform @ p.calc_center_median()
						p_t = rmmesh.world_transform.to_3x3() @ p.calc_tangent_edge_pair()
						p_n = rmmesh.world_transform.to_3x3() @ p.normal
						m4 = rmlib.util.LookAt( p_n, p_t, p_p )
						context.scene.cursor.matrix = m4
						context.scene.cursor.location = p_p

		elif context.object is not None and context.mode == 'OBJECT':
			obj = context.object
			context.scene.cursor.matrix = obj.matrix_world

			#needed to refresh cursor viewport draw
			obj.select_set( False )
			obj.select_set( True )

		return { 'FINISHED' }


class MESH_OT_origintocursor( bpy.types.Operator ):
	"""Move the pivot point of selected objects to the 3D Cursor. All linked meshes xforms are compensated for this transformation."""
	bl_idname = 'view3d.rm_origin_to_cursor'
	bl_label = 'Pivot to Cursor'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return context.area.type == 'VIEW_3D'

	def execute( self, context ):
		prev_mode = context.mode
		if prev_mode == 'EDIT_MESH':
			prev_mode = 'EDIT'
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )

		unique_meshes = set()
		unique_objects = []
		unique_initial_positions = []
		for obj in bpy.context.selected_objects:
			if obj.type != 'MESH':
				continue
			if obj.data not in unique_meshes:
				unique_meshes.add( obj.data )
				unique_objects.append( obj )
				unique_initial_positions.append( obj.location.copy() )

		if len( unique_objects ) < 1:
			return { 'CANCELLED' }

		#move pivot for all unique objects
		cursor_location = mathutils.Vector( context.scene.cursor.location )
		obj_spc_offsets = []
		for obj in unique_objects:
			if obj.type != 'MESH':
				continue
			obj_mat_inv = obj.matrix_world.inverted( mathutils.Matrix.Identity( 4 ) )
			obj_spc_cursor_loc = obj_mat_inv @ cursor_location
			obj_spc_offsets.append( obj_spc_cursor_loc )
			rmmesh = rmlib.rmMesh( obj )
			with rmmesh as rmmesh:
				for v in rmmesh.bmesh.verts:
					v.co -= obj_spc_cursor_loc
			wld_spc_offset = obj.matrix_world.to_3x3() @ obj_spc_cursor_loc
			obj.location += wld_spc_offset

		#compensate for change in positions of linked objects
		for i, obj in enumerate( unique_objects ):
			for link_obj in context.scene.objects:
				if obj == link_obj or link_obj.type != 'MESH' or link_obj.data != obj.data:
					continue
				wld_spc_offset = link_obj.matrix_world.to_3x3() @ obj_spc_offsets[i]
				link_obj.location += wld_spc_offset

		bpy.ops.object.mode_set( mode=prev_mode, toggle=False )

		return { 'FINISHED' }


class VIEW3D_MT_PIE_cursor( bpy.types.Menu ):
	"""A seriese of commands related to the 3D Cursor"""
	bl_idname = 'VIEW3D_MT_PIE_cursor'
	bl_label = '3D Cursor Ops'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		pie.operator( 'view3d.snap_selected_to_cursor', text='Selection to Cursor' ).use_offset = True

		pie.operator( 'view3d.snap_cursor_to_grid', text='Cursor to Grid' )

		pie.operator( 'view3d.snap_cursor_to_selected', text='Cursor to Selection' )

		pie.operator( 'view3d.rm_cursor_to_selection', text='Cursor to Selection and Orient' )

		pie.operator( 'view3d.rm_origin_to_cursor', text='Object Pivot to Cursor' )

		pie.operator( 'view3d.snap_cursor_to_center', text='Cursor to Origin' )

	
def register():
	print( 'register :: {}'.format( MESH_OT_cursortoselection.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_origintocursor.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_cursor.bl_idname ) )
	bpy.utils.register_class( MESH_OT_cursortoselection )
	bpy.utils.register_class( MESH_OT_origintocursor )
	bpy.utils.register_class( VIEW3D_MT_PIE_cursor )
	
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_cursortoselection.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_origintocursor.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_cursor.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_cursortoselection )
	bpy.utils.unregister_class( MESH_OT_origintocursor )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_cursor )