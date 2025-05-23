import math
import bpy, bmesh, mathutils
import rmlib

class MESH_OT_screenreflect( bpy.types.Operator ):
	"""Reflect polygon selection based on relative screen direction."""
	bl_idname = 'mesh.rm_screenreflect'
	bl_label = 'ScreenReflect'
	bl_options = { 'UNDO' }

	str_dir: bpy.props.EnumProperty(
		items=[ ( "up", "Up", "", 1 ),
				( "down", "Down", "", 2 ),
				( "left", "Left", "", 3 ),
				( "right", "Right", "", 4 ) ],
		name="Direction",
		default="right"
	)

	mode: bpy.props.IntProperty(
		name='Mode',
		description='0::Reflect about fartest point of mesh on desired axis. 1::Slice and mirror about cursor pos. 2::Mirror about cursor pos.'
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' )
		
	def execute( self, context ):
		if context.object is None:
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }
		
		rm_vp = rmlib.rmViewport( context )
		rm_wp = rmlib.rmCustomOrientation.from_selection( context )

		if context.mode == 'EDIT_MESH':
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if not sel_mode[2]:
				return { 'CANCELLED' }
			
			#retrieve active mesh
			rmmesh = rmlib.rmMesh.GetActive( context )
			with rmmesh as rmmesh:
				#get selected polyons and init geom list for slicing
				active_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				if len( active_polys ) < 1:
					return { 'CANCELLED' }
				active_verts = active_polys.vertices
				geom = []
				geom.extend( active_polys.vertices )
				geom.extend( active_polys.edges )
				geom.extend( active_polys )			
				
				dir_idx, cam_dir_vec, grid_dir_vec = rm_vp.get_nearest_direction_vector( self.str_dir, rm_wp.matrix )

				inv_rot_mat = rmmesh.world_transform.to_3x3().inverted()
				grid_dir_vec = inv_rot_mat @ grid_dir_vec
				
				if self.mode == 0:
					#find the farthest point in the direction of the desired axis aligned direction
					reflection_center = active_verts[0].co.copy()
					max_dot = grid_dir_vec.dot( active_verts[0].co )
					for i in range( 1, len( active_verts ) ):
						v = active_verts[i]
						dot = grid_dir_vec.dot( v.co )
						if dot > max_dot:
							max_dot = dot
							reflection_center = v.co.copy()

				elif self.mode == 1:
					#slice geo and delete everything on outer side of slice plane
					cursor_pos = mathutils.Vector( bpy.context.scene.cursor.location )
					reflection_center = rmmesh.world_transform.inverted() @ cursor_pos# @ rmmesh.world_transform
					d = bmesh.ops.bisect_plane( rmmesh.bmesh, geom=geom, dist=0.00001, plane_co=reflection_center, plane_no=grid_dir_vec, use_snap_center=False, clear_outer=True, clear_inner=False )
					geom = d[ 'geom' ]

				elif self.mode == 2:
					cursor_pos = mathutils.Vector( bpy.context.scene.cursor.location )
					reflection_center = rmmesh.world_transform.inverted() @ cursor_pos# @ rmmesh.world_transform
					
				#mirror selection across reflection/slice plane
				reflection = rmlib.util.ReflectionMatrix( reflection_center, grid_dir_vec )
				d = bmesh.ops.duplicate( rmmesh.bmesh, geom=geom )
				rev_faces = []
				for elem in d['geom']:
					if isinstance( elem, bmesh.types.BMVert ):
						elem.co = reflection @ elem.co
					elif isinstance( elem, bmesh.types.BMFace ):
						rev_faces.append( elem )
				bmesh.ops.reverse_faces( rmmesh.bmesh, faces=rev_faces )

				if self.mode == 1:
					#merge vertices that are on the slice plane
					epsilon = 0.0001
					merge_verts = rmlib.rmVertexSet()
					for v in rmmesh.bmesh.verts:
						if abs( rmlib.util.PlaneDistance( v.co, reflection_center, grid_dir_vec ) ) < epsilon:
							merge_verts.append( v )
					bmesh.ops.remove_doubles( rmmesh.bmesh, verts=merge_verts, dist=epsilon )
			
		elif context.mode == 'OBJECT':
			dir_idx, cam_dir_vec, grid_dir_vec = rm_vp.get_nearest_direction_vector( self.str_dir, rm_wp.matrix )
			
			obj_selection = list( bpy.context.selected_objects )

			if self.mode == 0:
				reflection_center = None
				for obj in obj_selection:
					if obj.type != 'MESH':
						continue
					
					rmmesh = rmlib.rmMesh( obj )
					mat = rmmesh.world_transform
					inv_mat = mat.inverted()
					inv_rot_mat = mat.to_3x3().inverted()
					with rmmesh as rmmesh:
						rmmesh.readonly = True
						
						grid_dir_vec_objspc = inv_rot_mat @ grid_dir_vec

						#find the farthest point in the direction of the desired axis aligned direction
						active_verts = rmlib.rmVertexSet.from_mesh( rmmesh=rmmesh, filter_hidden=True )
						rc = active_verts[0].co.copy()
						max_dot = grid_dir_vec_objspc.dot( active_verts[0].co )
						for i in range( 1, len( active_verts ) ):
							v = active_verts[i]
							dot = grid_dir_vec_objspc.dot( v.co )
							if dot > max_dot:
								max_dot = dot
								rc = v.co.copy()
						if reflection_center is not None:
							cur_rc = inv_mat @ reflection_center
							dot = grid_dir_vec_objspc.dot( cur_rc )
							if dot > max_dot:
								rc = cur_rc							

						reflection_center = mat @ rc

				reflection = rmlib.util.ReflectionMatrix( reflection_center, grid_dir_vec )
				for obj in obj_selection:
					mat = mathutils.Matrix( obj.matrix_world )
					new_mat = reflection @ mat

					new_obj = bpy.data.objects.new( obj.name, obj.data )
					obj.users_collection[0].objects.link( new_obj )
					new_obj.matrix_world = new_mat

			else:
				reflection_center = mathutils.Vector( bpy.context.scene.cursor.location )
				reflection = rmlib.util.ReflectionMatrix( reflection_center, grid_dir_vec )

				for obj in obj_selection:
					mat = mathutils.Matrix( obj.matrix_world )
					new_mat = reflection @ mat

					new_obj = bpy.data.objects.new( obj.name, obj.data )
					obj.users_collection[0].objects.link( new_obj )
					new_obj.matrix_world = new_mat

		return { 'FINISHED' }


class VIEW3D_MT_PIE_screenreflect( bpy.types.Menu ):
	"""Quickly mirror the face selection about a plane whose normal is defined by a grid direction relative to viewport camera."""
	bl_idname = 'OBJECT_MT_rm_screenreflect'
	bl_label = 'Screen Reflect'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_l = pie.operator( MESH_OT_screenreflect.bl_idname, text='Left' )
		op_l.str_dir = 'left'
		op_l.mode = context.scene.rmkit_props.screenreflectprops.sr_0
		
		op_r = pie.operator( MESH_OT_screenreflect.bl_idname, text='Right' )
		op_r.str_dir = 'right'
		op_r.mode = context.scene.rmkit_props.screenreflectprops.sr_0
		
		op_d = pie.operator( MESH_OT_screenreflect.bl_idname, text='Down' )
		op_d.str_dir = 'down'
		op_d.mode = context.scene.rmkit_props.screenreflectprops.sr_0
		
		op_u = pie.operator( MESH_OT_screenreflect.bl_idname, text='Up' )
		op_u.str_dir = 'up'
		op_u.mode = context.scene.rmkit_props.screenreflectprops.sr_0
		
		pie.operator( 'view3d.snap_cursor_to_selected', text='Set Cursor' )

		pie.operator( 'wm.call_menu_pie', text='Reflect' ).name = 'VIEW3D_MT_PIE_screenreflect_noslice'
		
		pie.operator( 'view3d.rm_zerocursor', text='Cursor to Origin' )

		pie.operator( 'wm.call_menu_pie', text='Slice' ).name = 'VIEW3D_MT_PIE_screenreflect_slice'
		

class VIEW3D_MT_PIE_screenreflect_slice( bpy.types.Menu ):
	"""Quickly mirror the face selection about a plane whose normal is defined by a grid direction relative to viewport camera."""
	bl_idname = 'VIEW3D_MT_PIE_screenreflect_slice'
	bl_label = 'Screen Reflect - Slice'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_l = pie.operator( MESH_OT_screenreflect.bl_idname, text='Left' )
		op_l.str_dir = 'left'
		op_l.mode = context.scene.rmkit_props.screenreflectprops.sr_1
		
		op_r = pie.operator( MESH_OT_screenreflect.bl_idname, text='Right' )
		op_r.str_dir = 'right'
		op_r.mode = context.scene.rmkit_props.screenreflectprops.sr_1
		
		op_d = pie.operator( MESH_OT_screenreflect.bl_idname, text='Down' )
		op_d.str_dir = 'down'
		op_d.mode = context.scene.rmkit_props.screenreflectprops.sr_1
		
		op_u = pie.operator( MESH_OT_screenreflect.bl_idname, text='Up' )
		op_u.str_dir = 'up'
		op_u.mode = context.scene.rmkit_props.screenreflectprops.sr_1


class VIEW3D_MT_PIE_screenreflect_noslice( bpy.types.Menu ):
	"""Quickly mirror the face selection about a plane whose normal is defined by a grid direction relative to viewport camera."""
	bl_idname = 'VIEW3D_MT_PIE_screenreflect_noslice'
	bl_label = 'Screen Reflect - No Slice'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_l = pie.operator( MESH_OT_screenreflect.bl_idname, text='Left' )
		op_l.str_dir = 'left'
		op_l.mode = context.scene.rmkit_props.screenreflectprops.sr_2
		
		op_r = pie.operator( MESH_OT_screenreflect.bl_idname, text='Right' )
		op_r.str_dir = 'right'
		op_r.mode = context.scene.rmkit_props.screenreflectprops.sr_2
		
		op_d = pie.operator( MESH_OT_screenreflect.bl_idname, text='Down' )
		op_d.str_dir = 'down'
		op_d.mode = context.scene.rmkit_props.screenreflectprops.sr_2
		
		op_u = pie.operator( MESH_OT_screenreflect.bl_idname, text='Up' )
		op_u.str_dir = 'up'
		op_u.mode = context.scene.rmkit_props.screenreflectprops.sr_2
	
	
def register():
	bpy.utils.register_class( MESH_OT_screenreflect )
	bpy.utils.register_class( VIEW3D_MT_PIE_screenreflect )
	bpy.utils.register_class( VIEW3D_MT_PIE_screenreflect_slice )
	bpy.utils.register_class( VIEW3D_MT_PIE_screenreflect_noslice )
	
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_screenreflect )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_screenreflect )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_screenreflect_slice )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_screenreflect_noslice )