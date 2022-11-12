import mathutils
import rmKit.rmlib as rmlib
import bpy

def move_to_furthest( groups, dir_vec, constrain, center ):
	plane_nml = -dir_vec
	for g in groups:		
		#find the plane_position (min_pos)
		avg_pos = g[0].co.copy()
		plane_pos = g[0].co.copy()
		max_dot = dir_vec.dot( g[0].co )
		for i in range( 1, len( g ) ):
			v = g[i]
			avg_pos += v.co
			dot = dir_vec.dot( v.co )
			if dot > max_dot:
				max_dot = dot
				plane_pos = v.co.copy()

		#for horizontal/vertical, plane_pos is the avg pos
		avg_pos *= 1.0 / len( g )
		if center:
			plane_pos = avg_pos
				
		if constrain:
			new_pos = [ None ] * len( g )
			for i, v in enumerate( g ):			
				max_dot = -1
				edge_dir = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
				for e in v.link_edges:
					other_v = e.other_vert( v )
					edge_vec = other_v.co - v.co
					dot = dir_vec.dot( edge_vec.normalized() )
					if dot >= max_dot:
						max_dot = dot
						edge_dir = edge_vec
						
				if max_dot <= 0.00001:
					new_pos[i] = v.co
					continue
				
				intersection_pos = mathutils.geometry.intersect_line_plane( v.co, v.co + edge_dir, plane_pos, plane_nml )
				if intersection_pos is None:
					new_pos[i] = v.co + edge_dir
				else:
					new_pos[i] = intersection_pos
					
			for i, v in enumerate( g ):
				v.co = new_pos[i]
				
		else:
			for v in g:
				dist = mathutils.geometry.distance_point_to_plane( v.co, plane_pos, plane_nml )
				v.co = v.co + ( -plane_nml * dist )
				
				
class MESH_OT_movetofurthest( bpy.types.Operator ):
	"""Align selection in direction relative to viewport camera."""
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
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
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

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		with rmmesh as rmmesh:		
			if sel_mode[0]:
				selected_verts = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( selected_verts ) < 1:
					return { 'CANCELLED' }
				if self.local:
					vert_groups = selected_verts.group()
				else:
					vert_groups = [ selected_verts ]
			elif sel_mode[1]:
				selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				if len( selected_edges ) < 1:
					return { 'CANCELLED' }
				if self.local:
					vert_groups = [ g.vertices for g in selected_edges.group() ]
				else:
					vert_groups = [ selected_edges.vertices ]
			elif sel_mode[2]:
				selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				if len( selected_polys ) < 1:
					return { 'CANCELLED' }
				if self.local:
					vert_groups = [ g.vertices for g in selected_polys.group() ]
				else:
					vert_groups = [ selected_polys.vertices ]					
			else:
				return { 'CANCELLED' }
			
			center = self.str_dir == 'horizontal' or self.str_dir == 'vertical'
			move_to_furthest( vert_groups, grid_dir_vec, self.constrain, center )
			
		return { 'FINISHED' }


class VIEW3D_MT_PIE_movetofurthest( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_movetofurthest'
	bl_label = 'Move To Furthest'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_l = pie.operator( 'mesh.rm_movetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.object.mtf_prop_off
		op_l.constrain = context.object.mtf_prop_off
		
		op_r = pie.operator( 'mesh.rm_movetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.object.mtf_prop_off
		op_r.constrain = context.object.mtf_prop_off
		
		op_d = pie.operator( 'mesh.rm_movetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.object.mtf_prop_off
		op_d.constrain = context.object.mtf_prop_off
		
		op_u = pie.operator( 'mesh.rm_movetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.object.mtf_prop_off
		op_u.constrain = context.object.mtf_prop_off
		
		pie.operator( 'wm.call_menu_pie', text='Con' ).name = 'VIEW3D_MT_PIE_movetofurthest_constrain'
		
		pie.operator( 'wm.call_menu_pie', text='Local' ).name = 'VIEW3D_MT_PIE_movetofurthest_local'
		
		op_h = pie.operator( 'mesh.rm_movetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.object.mtf_prop_off
		op_h.constrain = context.object.mtf_prop_off
				
		op_v = pie.operator( 'mesh.rm_movetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.object.mtf_prop_off
		op_v.constrain = context.object.mtf_prop_off
		
		
class VIEW3D_MT_PIE_movetofurthest_local( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_movetofurthest_local'
	bl_label = 'Move To Furthest LOCAL'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_movetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.object.mtf_prop_on
		op_l.constrain = context.object.mtf_prop_off
		
		op_r = pie.operator( 'mesh.rm_movetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.object.mtf_prop_on
		op_r.constrain = context.object.mtf_prop_off
		
		op_d = pie.operator( 'mesh.rm_movetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.object.mtf_prop_on
		op_d.constrain = context.object.mtf_prop_off
		
		op_u = pie.operator( 'mesh.rm_movetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.object.mtf_prop_on
		op_u.constrain = context.object.mtf_prop_off
		
		pie.operator( 'wm.call_menu_pie', text='Constrain' ).name = 'VIEW3D_MT_PIE_movetofurthest_both'
		
		pie.separator()
		
		op_h = pie.operator( 'mesh.rm_movetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.object.mtf_prop_on
		op_h.constrain = context.object.mtf_prop_off
				
		op_v = pie.operator( 'mesh.rm_movetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.object.mtf_prop_on
		op_v.constrain = context.object.mtf_prop_off
		
	
class VIEW3D_MT_PIE_movetofurthest_constrain( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_movetofurthest_constrain'
	bl_label = 'Move To Furthest LOCAL'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_movetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.object.mtf_prop_off
		op_l.constrain = context.object.mtf_prop_on
		
		op_r = pie.operator( 'mesh.rm_movetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.object.mtf_prop_off
		op_r.constrain = context.object.mtf_prop_on
		
		op_d = pie.operator( 'mesh.rm_movetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.object.mtf_prop_off
		op_d.constrain = context.object.mtf_prop_on
		
		op_u = pie.operator( 'mesh.rm_movetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.object.mtf_prop_off
		op_u.constrain = context.object.mtf_prop_on
		
		pie.separator()
		
		pie.operator( 'wm.call_menu_pie', text='Local' ).name = 'VIEW3D_MT_PIE_movetofurthest_both'
		
		op_h = pie.operator( 'mesh.rm_movetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.object.mtf_prop_off
		op_h.constrain = context.object.mtf_prop_on
				
		op_v = pie.operator( 'mesh.rm_movetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.object.mtf_prop_off
		op_v.constrain = context.object.mtf_prop_on
		
		
class VIEW3D_MT_PIE_movetofurthest_both( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_movetofurthest_both'
	bl_label = 'Move To Furthest LOCAL'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_movetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.object.mtf_prop_on
		op_l.constrain = context.object.mtf_prop_on
		
		op_r = pie.operator( 'mesh.rm_movetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.object.mtf_prop_on
		op_r.constrain = context.object.mtf_prop_on
		
		op_d = pie.operator( 'mesh.rm_movetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.object.mtf_prop_on
		op_d.constrain = context.object.mtf_prop_on
		
		op_u = pie.operator( 'mesh.rm_movetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.object.mtf_prop_on
		op_u.constrain = context.object.mtf_prop_on
		
		pie.separator()
		
		pie.separator()
		
		op_h = pie.operator( 'mesh.rm_movetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.object.mtf_prop_on
		op_h.constrain = context.object.mtf_prop_on
				
		op_v = pie.operator( 'mesh.rm_movetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.object.mtf_prop_on
		op_v.constrain = context.object.mtf_prop_on


def register():
	print( 'register :: {}'.format( MESH_OT_movetofurthest.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_movetofurthest.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_movetofurthest_local.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_movetofurthest_constrain.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_movetofurthest_both.bl_idname ) )
	bpy.utils.register_class( MESH_OT_movetofurthest )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_local )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_constrain )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_both )
	bpy.types.Object.mtf_prop_on = bpy.props.BoolProperty( default=True	)
	bpy.types.Object.mtf_prop_off = bpy.props.BoolProperty( default=False )	
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_movetofurthest.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_movetofurthest.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_movetofurthest_local.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_movetofurthest_constrain.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_movetofurthest_both.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_movetofurthest )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_local )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_constrain )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_both )
	del bpy.types.Object.mtf_prop_on
	del bpy.types.Object.mtf_prop_off