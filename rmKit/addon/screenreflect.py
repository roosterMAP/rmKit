import math
import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

REFLECT_CENTER = None

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

	slice: bpy.props.BoolProperty(
		name='Slice',
		description='When True, the geo is slice along the reflection plane and everything in front of it is removed before reflection op.',
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
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }
		
		rm_vp = rmlib.rmViewport( context )
		rm_wp = rmlib.rmCustomOrientation.from_selection( context )

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }
		
		#retrieve active mesh
		rmmesh = rmlib.rmMesh.GetActive( context )

		#transform reflection center into obj space
		global REFLECT_CENTER
		if REFLECT_CENTER is not None:
			reflection_center = rmmesh.world_transform.inverted() @ REFLECT_CENTER @ rmmesh.world_transform

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
			if self.slice and REFLECT_CENTER is not None:
				#slice geo and delete everythin on outer side of slice plane
				d = bmesh.ops.bisect_plane( rmmesh.bmesh, geom=geom, dist=0.00001, plane_co=reflection_center, plane_no=grid_dir_vec, use_snap_center=False, clear_outer=True, clear_inner=False )
				geom = d[ 'geom' ]
			elif REFLECT_CENTER is None:
				#find the farthest point in the direction of the desired axis aligned direction
				reflection_center = active_verts[0].co
				max_dot = -2.0
				for v in active_verts:
					dot = grid_dir_vec.dot( v.co )
					if dot > max_dot:
						max_dot = dot
						reflection_center = v.co
			
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

			if self.slice:
				#merge vertices that are on the slice plane
				epsilon = 0.0001
				merge_verts = rmlib.rmVertexSet()
				for v in rmmesh.bmesh.verts:
					if rmlib.util.PlaneDistance( v.co, reflection_center, grid_dir_vec ) < epsilon:
						merge_verts.append( v )
				bmesh.ops.remove_doubles( rmmesh.bmesh, verts=merge_verts, dist=epsilon )
			
		return { 'FINISHED' }


class MESH_OT_setreflectioncenter( bpy.types.Operator ):
	"""Toggle/Set the worldspace position of the reflection plane."""
	bl_idname = 'mesh.rm_setreflectioncenter'
	bl_label = 'Toggle/Set Reflection Center'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.object.type == 'MESH' and context.object.data.is_editmode )
		
		
	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		global REFLECT_CENTER
		if REFLECT_CENTER is not None:
			REFLECT_CENTER = None
			return { 'FINISHED' }
		
		sel_mode = context.tool_settings.mesh_select_mode[:]
		center = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		if sel_mode[0]:
			rmmesh = rmlib.rmMesh.GetActive( context )
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				verts = rmlib.rmVertexSet.from_selection( rmmesh )				
				for v in verts:
					center += v.co
				center *= 1.0 / len( verts )
		elif sel_mode[1]:
			rmmesh = rmlib.rmMesh.GetActive( context )
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				for e in edges:
					v1, v2 = e.verts
					center += ( v1.co + v2.co ) * 0.5
				center *= 1.0 / len( edges )
		elif sel_mode[2]:
			rmmesh = rmlib.rmMesh.GetActive( context )
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				for p in polys:
					center += p.calc_center_median()
				center *= 1.0 / len( polys )

			center = rmmesh.world_transform @ center
		REFLECT_CENTER = center

		return { 'FINISHED' }


class VIEW3D_MT_PIE_screenreflect( bpy.types.Menu ):
	bl_idname = 'OBJECT_MT_rm_screenreflect'
	bl_label = 'Screen Reflect'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_l = pie.operator( MESH_OT_screenreflect.bl_idname, text='Left' )
		op_l.str_dir = 'left'
		op_l.slice = context.object.sr_slice_false
		
		op_r = pie.operator( MESH_OT_screenreflect.bl_idname, text='Right' )
		op_r.str_dir = 'right'
		op_r.slice = context.object.sr_slice_false
		
		op_d = pie.operator( MESH_OT_screenreflect.bl_idname, text='Down' )
		op_d.str_dir = 'down'
		op_d.slice = context.object.sr_slice_false
		
		op_u = pie.operator( MESH_OT_screenreflect.bl_idname, text='Up' )
		op_u.str_dir = 'up'
		op_u.slice = context.object.sr_slice_false
		
		global REFLECT_CENTER
		if REFLECT_CENTER is None:
			op_c = pie.operator( 'mesh.rm_setreflectioncenter', text='Set' )
		else:
			op_c = pie.operator( 'mesh.rm_setreflectioncenter', text='Clear' )

		pie.operator( 'wm.call_menu_pie', text='Reflect' ).name = 'VIEW3D_MT_PIE_screenreflect_noslice'

		pie.operator( 'wm.call_menu_pie', text='Origin' ).name = 'VIEW3D_MT_PIE_screenreflect_origin'

		pie.operator( 'wm.call_menu_pie', text='Slice' ).name = 'VIEW3D_MT_PIE_screenreflect_slice'
		
		

		

		


class VIEW3D_MT_PIE_screenreflect_slice( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_screenreflect_slice'
	bl_label = 'Screen Reflect - Slice'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_l = pie.operator( MESH_OT_screenreflect.bl_idname, text='Left' )
		op_l.str_dir = 'left'
		op_l.slice = context.object.sr_slice_true
		
		op_r = pie.operator( MESH_OT_screenreflect.bl_idname, text='Right' )
		op_r.str_dir = 'right'
		op_r.slice = context.object.sr_slice_true
		
		op_d = pie.operator( MESH_OT_screenreflect.bl_idname, text='Down' )
		op_d.str_dir = 'down'
		op_d.slice = context.object.sr_slice_true
		
		op_u = pie.operator( MESH_OT_screenreflect.bl_idname, text='Up' )
		op_u.str_dir = 'up'
		op_u.slice = context.object.sr_slice_true


class VIEW3D_MT_PIE_screenreflect_origin( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_screenreflect_origin'
	bl_label = 'Screen Reflect - Origin'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()

		global REFLECT_CENTER
		REFLECT_CENTER = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		
		op_l = pie.operator( MESH_OT_screenreflect.bl_idname, text='Left' )
		op_l.str_dir = 'left'
		op_l.slice = context.object.sr_slice_true
		
		op_r = pie.operator( MESH_OT_screenreflect.bl_idname, text='Right' )
		op_r.str_dir = 'right'
		op_r.slice = context.object.sr_slice_true
		
		op_d = pie.operator( MESH_OT_screenreflect.bl_idname, text='Down' )
		op_d.str_dir = 'down'
		op_d.slice = context.object.sr_slice_true
		
		op_u = pie.operator( MESH_OT_screenreflect.bl_idname, text='Up' )
		op_u.str_dir = 'up'
		op_u.slice = context.object.sr_slice_true
		
		pie.separator()

		pie.operator( 'wm.call_menu_pie', text='Reflect' ).name = 'VIEW3D_MT_PIE_screenreflect_noslice'


class VIEW3D_MT_PIE_screenreflect_noslice( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_screenreflect_noslice'
	bl_label = 'Screen Reflect - No Slice'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_l = pie.operator( MESH_OT_screenreflect.bl_idname, text='Left' )
		op_l.str_dir = 'left'
		op_l.slice = context.object.sr_slice_false
		
		op_r = pie.operator( MESH_OT_screenreflect.bl_idname, text='Right' )
		op_r.str_dir = 'right'
		op_r.slice = context.object.sr_slice_false
		
		op_d = pie.operator( MESH_OT_screenreflect.bl_idname, text='Down' )
		op_d.str_dir = 'down'
		op_d.slice = context.object.sr_slice_false
		
		op_u = pie.operator( MESH_OT_screenreflect.bl_idname, text='Up' )
		op_u.str_dir = 'up'
		op_u.slice = context.object.sr_slice_false
	
	
def register():
	print( 'register :: {}'.format( MESH_OT_screenreflect.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_setreflectioncenter.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_screenreflect.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_screenreflect_slice.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_screenreflect_origin.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_screenreflect_noslice.bl_idname ) )
	bpy.utils.register_class( MESH_OT_screenreflect )
	bpy.utils.register_class( MESH_OT_setreflectioncenter )
	bpy.utils.register_class( VIEW3D_MT_PIE_screenreflect )
	bpy.utils.register_class( VIEW3D_MT_PIE_screenreflect_slice )
	bpy.utils.register_class( VIEW3D_MT_PIE_screenreflect_origin )
	bpy.utils.register_class( VIEW3D_MT_PIE_screenreflect_noslice )
	bpy.types.Object.sr_slice_true = bpy.props.BoolProperty(
		name='Slice',
		default=True
	)
	bpy.types.Object.sr_slice_false = bpy.props.BoolProperty(
		name='No Slice',
		default=False
	)
	
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_screenreflect.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_setreflectioncenter.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_screenreflect.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_screenreflect_slice.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_screenreflect_origin.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_screenreflect_noslice.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_screenreflect )
	bpy.utils.unregister_class( MESH_OT_setreflectioncenter )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_screenreflect )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_screenreflect_slice )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_screenreflect_origin )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_screenreflect_noslice )
	del bpy.types.Object.sr_slice_true
	del bpy.types.Object.sr_slice_false