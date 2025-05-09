import mathutils
import rmlib
import bpy, bmesh

def find_furthest( elems, dir_vec, center ):
	plane_pos = None
	avg_pos = mathutils.Vector()
	vcount = 0
	for rmmesh, groups in elems.items():
		xfrm = rmmesh.world_transform
		for g in groups:
			#find the plane_position (min_pos)
			avg_pos += xfrm @ g[0].co
			vcount += len( g )
			group_plane_pos = xfrm @ g[0].co
			max_dot = dir_vec.dot( group_plane_pos )
			for i in range( 1, len( g ) ):
				vpos = xfrm @ g[i].co
				avg_pos += vpos
				dot = dir_vec.dot( vpos )
				if dot > max_dot:
					max_dot = dot
					group_plane_pos = vpos
			if plane_pos is None:
				plane_pos = group_plane_pos.copy()
			else:
				if dir_vec.dot( group_plane_pos ) > dir_vec.dot( plane_pos ):
					plane_pos = group_plane_pos
				

	#for horizontal/vertical, plane_pos is the avg pos
	if center:
		avg_pos *= 1.0 / float( vcount )
		plane_pos = avg_pos

	return plane_pos


def move_to_furthest( elems, plane_pos, plane_nml, constrain, center, local ):	
	for rmmesh, groups in elems.items():
		for g in groups:
			
			if local:
				local_elems = { rmmesh : [g] }
				plane_pos = find_furthest( local_elems, -plane_nml, center )
			
			inv_rot_mat = rmmesh.world_transform.to_3x3().inverted()
			plane_nml_objspc = ( inv_rot_mat @ -plane_nml ).normalized()

			inv_xfrm = rmmesh.world_transform.inverted()
			plane_pos_objspc = inv_xfrm @ plane_pos

			if constrain:
				new_pos = [ None ] * len( g )
				for i, v in enumerate( g ):			
					max_dot = -1
					edge_dir = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
					for e in v.link_edges:
						other_v = e.other_vert( v )
						edge_vec = other_v.co - v.co
						dot = plane_nml_objspc.dot( edge_vec.normalized() )
						if dot >= max_dot:
							max_dot = dot
							edge_dir = edge_vec
							
					if max_dot <= 0.00001:
						new_pos[i] = v.co
						continue
					
					intersection_pos = mathutils.geometry.intersect_line_plane( v.co, v.co + edge_dir, plane_pos_objspc, plane_nml_objspc )
					if intersection_pos is None:
						new_pos[i] = v.co + edge_dir
					elif ( v.co - intersection_pos ).length > edge_dir.length:
						new_pos[i] = v.co + edge_dir
					else:
						new_pos[i] = intersection_pos
						
				for i, v in enumerate( g ):
					v.co = new_pos[i]
					
			else:		
				for v in g:
					dist = mathutils.geometry.distance_point_to_plane( v.co.copy(), plane_pos_objspc, plane_nml_objspc )
					v.co = v.co.copy() + ( -plane_nml_objspc * dist )
					
		bmesh.update_edit_mesh( rmmesh.mesh, loop_triangles=True, destructive=True )
				
				
class MESH_OT_movetofurthest( bpy.types.Operator ):
	"""Align selection to a grid axis most aligned with a direction relative to viewport camera."""
	bl_idname = 'mesh.rm_movetofurthest'
	bl_label = 'Move To Furthest'
	#bl_options = { 'REGISTER', 'UNDO' }
	bl_options = { 'UNDO' }

	str_dir: bpy.props.EnumProperty(
		items=[ ( "up", "Up", "", 1 ),
				( "down", "Down", "", 2 ),
				( "left", "Left", "", 3 ),
				( "right", "Right", "", 4 ),
				( "horizontal", "Horizontal", "", 5 ),
				( "vertical", "Vertical", "", 6 ) ],
		name="Direction",
		default="right"
	)

	local: bpy.props.BoolProperty(
		name='Local',
		description='Group selection based on 3d continuity and align each respectively.',
		default=False
	)
	
	constrain: bpy.props.BoolProperty(
		name='Constrain',
		description='Constrain all vert translation along linked edges.',
		default=False
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		co = context.scene.transform_orientation_slots[0].custom_orientation
		grid_matrix = mathutils.Matrix.Identity( 3 )
		if co is not None:
			grid_matrix = mathutils.Matrix( co.matrix ).to_3x3()
			
		rm_vp = rmlib.rmViewport( context )
		dir_idx, cam_dir_vec, grid_dir_vec = rm_vp.get_nearest_direction_vector( self.str_dir, grid_matrix )
		
		sel_mode = context.tool_settings.mesh_select_mode[:]
		elems = {}
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			elems[ rmmesh ] = None
			
			bm = bmesh.from_edit_mesh( rmmesh.mesh )
			rmmesh.bmesh = bm
			
			if sel_mode[0]:
				selected_verts = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( selected_verts ) < 1:
					return { 'CANCELLED' }
				if self.local:
					vert_groups = selected_verts.group()
				else:
					vert_groups = [ selected_verts ]
				elems[ rmmesh ] = vert_groups
			elif sel_mode[1]:
				selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				if len( selected_edges ) < 1:
					return { 'CANCELLED' }
				if self.local:
					vert_groups = [ g.vertices for g in selected_edges.group() ]
				else:
					vert_groups = [ selected_edges.vertices ]
				elems[ rmmesh ] = vert_groups
			elif sel_mode[2]:
				selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				if len( selected_polys ) < 1:
					return { 'CANCELLED' }
				if self.local:
					vert_groups = [ g.vertices for g in selected_polys.group() ]
				else:
					vert_groups = [ selected_polys.vertices ]
				elems[ rmmesh ] = vert_groups			
			else:
				return { 'CANCELLED' }

		center = self.str_dir == 'horizontal' or self.str_dir == 'vertical'
		plane_pos = mathutils.Vector()
		if not self.local:
			plane_pos = find_furthest( elems, grid_dir_vec, center )		
		move_to_furthest( elems, plane_pos, -grid_dir_vec, self.constrain, center, self.local )
			
		return { 'FINISHED' }


class VIEW3D_MT_PIE_movetofurthest( bpy.types.Menu ):
	"""Align selection to a grid axis most aligned with a direction relative to viewport camera."""
	bl_idname = 'VIEW3D_MT_PIE_movetofurthest'
	bl_label = 'Move To Furthest'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_l = pie.operator( 'mesh.rm_movetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_l.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		op_r = pie.operator( 'mesh.rm_movetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_r.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		op_d = pie.operator( 'mesh.rm_movetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_d.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		op_u = pie.operator( 'mesh.rm_movetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_u.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		pie.operator( 'wm.call_menu_pie', text='Con' ).name = 'VIEW3D_MT_PIE_movetofurthest_constrain'
		
		pie.operator( 'wm.call_menu_pie', text='Local' ).name = 'VIEW3D_MT_PIE_movetofurthest_local'
		
		op_h = pie.operator( 'mesh.rm_movetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_h.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
				
		op_v = pie.operator( 'mesh.rm_movetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_v.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		
class VIEW3D_MT_PIE_movetofurthest_local( bpy.types.Menu ):
	"""Align selection to a grid axis most aligned with a direction relative to viewport camera."""
	bl_idname = 'VIEW3D_MT_PIE_movetofurthest_local'
	bl_label = 'Move To Furthest LOCAL'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_movetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_l.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		op_r = pie.operator( 'mesh.rm_movetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_r.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		op_d = pie.operator( 'mesh.rm_movetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_d.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		op_u = pie.operator( 'mesh.rm_movetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_u.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
		pie.operator( 'wm.call_menu_pie', text='Constrain' ).name = 'VIEW3D_MT_PIE_movetofurthest_both'
		
		pie.separator()
		
		op_h = pie.operator( 'mesh.rm_movetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_h.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
				
		op_v = pie.operator( 'mesh.rm_movetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_v.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		
	
class VIEW3D_MT_PIE_movetofurthest_constrain( bpy.types.Menu ):
	"""Align selection to a grid axis most aligned with a direction relative to viewport camera."""
	bl_idname = 'VIEW3D_MT_PIE_movetofurthest_constrain'
	bl_label = 'Move To Furthest LOCAL'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_movetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_l.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		op_r = pie.operator( 'mesh.rm_movetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_r.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		op_d = pie.operator( 'mesh.rm_movetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_d.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		op_u = pie.operator( 'mesh.rm_movetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_u.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		pie.separator()
		
		pie.operator( 'wm.call_menu_pie', text='Local' ).name = 'VIEW3D_MT_PIE_movetofurthest_both'
		
		op_h = pie.operator( 'mesh.rm_movetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_h.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
				
		op_v = pie.operator( 'mesh.rm_movetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_off
		op_v.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		
class VIEW3D_MT_PIE_movetofurthest_both( bpy.types.Menu ):
	"""Align selection to a grid axis most aligned with a direction relative to viewport camera."""
	bl_idname = 'VIEW3D_MT_PIE_movetofurthest_both'
	bl_label = 'Move To Furthest LOCAL'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_movetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_l.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		op_r = pie.operator( 'mesh.rm_movetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_r.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		op_d = pie.operator( 'mesh.rm_movetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_d.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		op_u = pie.operator( 'mesh.rm_movetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_u.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		
		pie.separator()
		
		pie.separator()
		
		op_h = pie.operator( 'mesh.rm_movetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_h.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
				
		op_v = pie.operator( 'mesh.rm_movetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on
		op_v.constrain = context.scene.rmkit_props.movetofurthestprops.mtf_prop_on


def register():
	bpy.utils.register_class( MESH_OT_movetofurthest )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_local )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_constrain )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_both )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_movetofurthest )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_local )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_constrain )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_both )
