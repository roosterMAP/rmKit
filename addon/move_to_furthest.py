import mathutils
from .. import rmlib
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


def GetUnsyncUVVisibleFaces( rmmesh, sel_mode ):
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
		
	return visible_faces


class MESH_OT_uvmovetofurthest( bpy.types.Operator ):
	"""Align selection to a uv axis most aligned with a direction relative to viewport camera."""
	bl_idname = 'mesh.rm_uvmovetofurthest'
	bl_label = 'UV Move To Furthest'
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

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			rmlib.clear_tags( rmmesh.bmesh )

			uvlayer = rmmesh.active_uv

			loop_groups = []

			sel_mode = context.tool_settings.mesh_select_mode[:]
			
			sel_sync = context.tool_settings.use_uv_select_sync
			if sel_sync:
				if sel_mode[0]:
					vert_selection = rmlib.rmVertexSet.from_selection( rmmesh )
					loop_selection = rmlib.rmUVLoopSet( vert_selection.loops, uvlayer=uvlayer )
					if self.local:
						loop_groups += loop_selection.group_vertices()
					else:
						loop_groups.append( loop_selection )

				elif sel_mode[1]:
					edge_selection = rmlib.rmEdgeSet.from_selection( rmmesh )
					loop_selection = rmlib.rmUVLoopSet( edge_selection.vertices.loops, uvlayer=uvlayer )
					if self.local:
						loop_groups += loop_selection.group_vertices()
					else:
						loop_groups.append( loop_selection )

				elif sel_mode[2]:
					face_selection = rmlib.rmPolygonSet.from_selection( rmmesh )
					loopset = set()
					for f in face_selection:
						loopset |= set( f.loops )
					loop_selection = rmlib.rmUVLoopSet( loopset, uvlayer=uvlayer )
					if self.local:
						loop_groups += loop_selection.group_vertices()
					else:
						loop_groups.append( loop_selection )

			else:
				visible_faces = GetUnsyncUVVisibleFaces( rmmesh, sel_mode )
				uv_sel_mode = context.tool_settings.uv_select_mode
				if uv_sel_mode == 'VERTEX':
					loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
					visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
					for l in loop_selection:
						if l.face in visible_faces:
							visible_loop_selection.append( l )
					if self.local:
						loop_groups += visible_loop_selection.group_vertices()
					else:
						loop_groups.append( visible_loop_selection )
					
				elif uv_sel_mode == 'EDGE':
					loop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh=rmmesh, uvlayer=uvlayer )
					visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
					for l in loop_selection:
						if l.face in visible_faces:
							visible_loop_selection.append( l )
					if self.local:
						loop_groups = visible_loop_selection.group_edges()
						for i in range( len( loop_groups ) ):
							loop_groups[i].add_overlapping_loops( True )
					else:
						loop_groups.append( visible_loop_selection )
						loop_groups[0].add_overlapping_loops( True )

				else: #FACE mode
					loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
					visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
					for l in loop_selection:
						if l.face in visible_faces:
							visible_loop_selection.append( l )
					if self.local:
						loop_groups += loop_selection.group_faces()
					else:
						loop_groups.append( visible_loop_selection )
				
			for g in loop_groups:
				min_u = 99999999.9
				min_v = 99999999.9
				max_u = -99999999.9
				max_v = -99999999.9
				for l in g:
					u, v = l[uvlayer].uv
					if u < min_u:
						min_u = u
					if u > max_u:
						max_u = u
					if v < min_v:
						min_v = v
					if v > max_v:
						max_v = v
						
				avg_u = ( min_u + max_u ) * 0.5
				avg_v = ( min_v + max_v ) * 0.5
				
				for l in g:
					u, v = l[uvlayer].uv
					if self.str_dir == 'up':
						l[uvlayer].uv = ( u, max_v )
					elif self.str_dir == 'down':
						l[uvlayer].uv = ( u, min_v )
					elif self.str_dir == 'left':
						l[uvlayer].uv = ( min_u, v )
					elif self.str_dir == 'right':
						l[uvlayer].uv = ( max_u, v )
					elif self.str_dir == 'vertical':
						l[uvlayer].uv = ( u, avg_v )
					elif self.str_dir == 'horizontal':
						l[uvlayer].uv = ( avg_u, v )
					else:
						continue

			rmlib.clear_tags( rmmesh.bmesh )
			
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
	"""Align selection to a grid axis most aligned with a direction relative to viewport camera."""
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
	"""Align selection to a grid axis most aligned with a direction relative to viewport camera."""
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
	"""Align selection to a grid axis most aligned with a direction relative to viewport camera."""
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


class IMAGE_EDITOR_MT_PIE_uvmovetofurthest( bpy.types.Menu ):
	"""Align selection to a uv axis most aligned with a direction relative to viewport camera."""
	bl_idname = 'IMAGE_EDITOR_MT_PIE_uvmovetofurthest'
	bl_label = 'UV Move To Furthest'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_uvmovetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.object.mtf_prop_off
		
		op_r = pie.operator( 'mesh.rm_uvmovetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.object.mtf_prop_off
		
		op_d = pie.operator( 'mesh.rm_uvmovetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.object.mtf_prop_off
		
		op_u = pie.operator( 'mesh.rm_uvmovetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.object.mtf_prop_off

		pie.separator()
		
		pie.operator( 'wm.call_menu_pie', text='Local' ).name = 'IMAGE_EDITOR_MT_PIE_uvmovetofurthest_local'
		
		op_h = pie.operator( 'mesh.rm_uvmovetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.object.mtf_prop_off
				
		op_v = pie.operator( 'mesh.rm_uvmovetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.object.mtf_prop_off


class IMAGE_EDITOR_MT_PIE_uvmovetofurthest_local( bpy.types.Menu ):
	"""Align selection to a uv axis most aligned with a direction relative to viewport camera."""
	bl_idname = 'IMAGE_EDITOR_MT_PIE_uvmovetofurthest_local'
	bl_label = 'UV Move To Furthest LOCAL'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		op_l = pie.operator( 'mesh.rm_uvmovetofurthest', text='Left' )
		op_l.str_dir = 'left'
		op_l.local = context.object.mtf_prop_on
		
		op_r = pie.operator( 'mesh.rm_uvmovetofurthest', text='Right' )
		op_r.str_dir = 'right'
		op_r.local = context.object.mtf_prop_on
		
		op_d = pie.operator( 'mesh.rm_uvmovetofurthest', text='Down' )
		op_d.str_dir = 'down'
		op_d.local = context.object.mtf_prop_on
		
		op_u = pie.operator( 'mesh.rm_uvmovetofurthest', text='Up' )
		op_u.str_dir = 'up'
		op_u.local = context.object.mtf_prop_on
		
		pie.separator()
		
		pie.separator()
		
		op_h = pie.operator( 'mesh.rm_uvmovetofurthest', text='Horizontal' )
		op_h.str_dir = 'vertical'
		op_h.local = context.object.mtf_prop_on
				
		op_v = pie.operator( 'mesh.rm_uvmovetofurthest', text='Vertical' )
		op_v.str_dir = 'horizontal'
		op_v.local = context.object.mtf_prop_on


def register():
	print( 'register :: {}'.format( MESH_OT_movetofurthest.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvmovetofurthest.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_movetofurthest.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_movetofurthest_local.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_movetofurthest_constrain.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_movetofurthest_both.bl_idname ) )
	print( 'register :: {}'.format( IMAGE_EDITOR_MT_PIE_uvmovetofurthest.bl_idname ) )
	print( 'register :: {}'.format( IMAGE_EDITOR_MT_PIE_uvmovetofurthest_local.bl_idname ) )
	bpy.utils.register_class( MESH_OT_movetofurthest )
	bpy.utils.register_class( MESH_OT_uvmovetofurthest )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_local )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_constrain )
	bpy.utils.register_class( VIEW3D_MT_PIE_movetofurthest_both )
	bpy.utils.register_class( IMAGE_EDITOR_MT_PIE_uvmovetofurthest )
	bpy.utils.register_class( IMAGE_EDITOR_MT_PIE_uvmovetofurthest_local )
	bpy.types.Object.mtf_prop_on = bpy.props.BoolProperty( default=True	)
	bpy.types.Object.mtf_prop_off = bpy.props.BoolProperty( default=False )	
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_movetofurthest.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvmovetofurthest.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_movetofurthest.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_movetofurthest_local.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_movetofurthest_constrain.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_movetofurthest_both.bl_idname ) )
	print( 'unregister :: {}'.format( IMAGE_EDITOR_MT_PIE_uvmovetofurthest.bl_idname ) )
	print( 'unregister :: {}'.format( IMAGE_EDITOR_MT_PIE_uvmovetofurthest_local.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_movetofurthest )
	bpy.utils.unregister_class( MESH_OT_uvmovetofurthest )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_local )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_constrain )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_movetofurthest_both )
	bpy.utils.unregister_class( IMAGE_EDITOR_MT_PIE_uvmovetofurthest )
	bpy.utils.unregister_class( IMAGE_EDITOR_MT_PIE_uvmovetofurthest_local )
	del bpy.types.Object.mtf_prop_on
	del bpy.types.Object.mtf_prop_off
