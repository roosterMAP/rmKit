import bpy, bmesh, mathutils
from .. import rmlib

BACKGROUND_LAYERNAME = 'rm_background'

def GetSelsetEdges( bm, layername ):
	intlayers = bm.edges.layers.int
	selset = intlayers.get( layername, None )
	if selset is None:
		return rmlib.rmEdgeSet()
	return rmlib.rmEdgeSet( [ e for e in bm.edges if bool( e[selset] ) ] )

def VecFromEdge( v, e ):
	pos1 = mathutils.Vector( v.co.copy() )
	v2 = e.other_vert( v )
	pos2 = mathutils.Vector( v2.co.copy() )
	return ( pos2 - pos1 ).normalized()

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
						link_edges = rmlib.rmEdgeSet( list( v.link_edges ) )

						selected_edges = GetSelsetEdges( rmmesh.bmesh, BACKGROUND_LAYERNAME )
						first_edge = None
						if len( selected_edges ) > 0:
							first_edge = selected_edges[0]
							for i, e in enumerate( link_edges ):
								if e in selected_edges:
									first_edge = link_edges.pop( i )
									break
						if first_edge is None:
							if len( link_edges ) > 1:
								first_edge = link_edges[1]

						if first_edge is None or len( link_edges ) < 1:
							v_n = v.normal
							v_t = mathutils.Vector( ( 0.0, 0.0001, 1.0 ) )
							for e in v.link_edges:
								v1, v2 = e.verts
								v_t = v2.co - v1.co
								v_t = v_n.cross( v_t.normalized() )
						else:
							v_t = VecFromEdge( v, first_edge )
							v_n = VecFromEdge( v, link_edges[0] )
							crossvec = v_t.cross( v_n ).normalized()
							v_n = crossvec.cross( v_t ).normalized()

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


class MESH_OT_unrotatefromcursor( bpy.types.Operator ):
	"""Unrotate selection baed on cursor orientation."""
	bl_idname = 'view3d.rm_unrotate_relative_to_cursor'
	bl_label = 'Unrotate Relative to Cursor'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' )

	def execute( self, context ):
		cursor_pos = mathutils.Vector( context.scene.cursor.location )
		cursor_xfrm = mathutils.Matrix( context.scene.cursor.matrix )
		cursor_xfrm_inv = cursor_xfrm.inverted()

		if context.mode == 'EDIT_MESH':
			sel_mode = context.tool_settings.mesh_select_mode[:]
			rmmesh = rmlib.rmMesh.GetActive( context )
			if rmmesh is None:
				return { 'CANCELLED' }
			with rmmesh as rmmesh:
				xfrm_inv = rmmesh.world_transform.inverted()

				if sel_mode[0]:
					sel_verts = rmlib.rmVertexSet.from_selection( rmmesh )
					for group in sel_verts.group( True ):
						for v in group:
							v_wld = rmmesh.world_transform @ v.co #bring to world space
							v_wld = cursor_xfrm_inv @ v_wld #transform by inverse of cursor
							v_wld += cursor_pos
							v_obj = xfrm_inv @ v_wld #bring back into obj space
							v.co = v_obj

				elif sel_mode[1]:
					sel_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					for egroup in sel_edges.group( True ):
						group = egroup.vertices
						for v in group:
							v_wld = rmmesh.world_transform @ v.co #bring to world space
							v_wld = cursor_xfrm_inv @ v_wld #transform by inverse of cursor
							v_wld += cursor_pos
							v_obj = xfrm_inv @ v_wld #bring back into obj space
							v.co = v_obj

				elif sel_mode[2]:
					sel_faces = rmlib.rmPolygonSet.from_selection( rmmesh )
					for fgroup in sel_faces.group( True ):
						group = fgroup.vertices
						for v in group:
							v_wld = rmmesh.world_transform @ v.co #bring to world space
							v_wld = cursor_xfrm_inv @ v_wld #transform by inverse of cursor
							v_wld += cursor_pos
							v_obj = xfrm_inv @ v_wld #bring back into obj space
							v.co = v_obj
							

		elif context.object is not None and context.mode == 'OBJECT':
			obj = context.object
			obj.matrix_world = cursor_xfrm_inv @ obj.matrix_world
			obj.location += cursor_pos

		return { 'FINISHED' }


class OBJECT_OT_origintocursor( bpy.types.Operator ):
	"""Move the pivot point of selected objects to the 3D Cursor. All linked meshes xforms are compensated for this transformation."""
	bl_idname = 'object.rm_origin_to_cursor'
	bl_label = 'Pivot to Cursor'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return context.area.type == 'VIEW_3D'

	def execute( self, context ):
		ao = context.active_object
		if ao.type != 'MESH':
			self.report( { 'ERROR' }, 'Active Object must be a mesh.' )
			return
		
		cursor_pos = context.scene.cursor.location.copy()
		cursor_pos_obj = ao.matrix_world.inverted() @ cursor_pos

		most_parent_instance = ao
		p = ao.parent
		while( p is not None ):
			if p.type != 'MESH':
				p = p.parent
				continue
			if p.data == ao.data:
				most_parent_instance = p
			p = p.parent
		ao = most_parent_instance

		instances = []
		for o in context.scene.objects:
			if o.type != 'MESH' or o == ao:
				continue
			if o.data == ao.data:
				instances.append( o )
		
		prev_mode = context.mode
		if prev_mode == 'EDIT_MESH':
			prev_mode = 'EDIT'
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )
			
		#move the mesh such that its new origin is the cursor position
		ao.data.transform( mathutils.Matrix.Translation( -cursor_pos_obj ) )
		
		#move the obj to compensate for mesh translation
		delta = ao.matrix_world.to_3x3() @ cursor_pos_obj
		ao.location += delta
		
		for child in ao.children:
			child.location -= delta
			
		for inst in instances:
			inst_delta = inst.matrix_world.to_3x3() @ cursor_pos_obj
			inst.location += inst_delta
			for child in inst.children:
				child.location -= inst_delta
				
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

		pie.operator( 'object.rm_origin_to_cursor', text='Object Pivot to Cursor' )

		pie.operator( 'view3d.rm_zerocursor', text='Cursor to Origin' )

		pie.operator( 'view3d.rm_unrotate_relative_to_cursor', text='Unrotate Relative to Cursor' )

		pie.operator( 'wm.call_menu', text='Apply Transform' ).name = 'VIEW3D_MT_object_apply'

	
def register():
	bpy.utils.register_class( MESH_OT_cursortoselection )
	bpy.utils.register_class( OBJECT_OT_origintocursor )
	bpy.utils.register_class( VIEW3D_MT_PIE_cursor )
	bpy.utils.register_class( MESH_OT_unrotatefromcursor )
	
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_cursortoselection )
	bpy.utils.unregister_class( OBJECT_OT_origintocursor )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_cursor )
	bpy.utils.unregister_class( MESH_OT_unrotatefromcursor )