import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

BACKGROUND_LAYERNAME = 'rm_background'

def GetSelsetPolygons( bm, layername ):
	intlayers = bm.faces.layers.int
	selset = intlayers.get( layername, None )
	if selset is None:
		return rmlib.rmPolygonSet()
	return rmlib.rmPolygonSet( [ f for f in bm.faces if bool( f[selset] ) ] )


class MESH_OT_knifescreen( bpy.types.Operator ):
	"""Slice the background face selection based on the current vert/edge selection."""
	bl_idname = 'mesh.rm_knifescreen'
	bl_label = 'KnifeScreen'
	bl_options = { 'UNDO' }
	
	str_dir: bpy.props.EnumProperty(
		items=[ ( "horizontal", "Horizontal", "", 1 ),
				( "vertical", "Vertical", "", 2 ),
				( "edge", "Edge", "", 3 ) ],
		name="Direction",
		default="horizontal"
	)
	
	alignment: bpy.props.EnumProperty(
		items=[ ( "topology", "Topology", "", 1 ),
				( "grid", "Grid", "", 2 ),
				( "screen", "Screen", "", 3 ) ],
		name="Alignment",
		default="topology"
	)

	mouse_pos: bpy.props.FloatVectorProperty(
		name="Cursor Position",
		size=2,
		default=( 0.0, 0.0 )
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
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }
		
		rm_vp = rmlib.rmViewport( context )
		rm_wp = rmlib.rmCustomOrientation.from_selection( context )

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[2]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			#init geom list for slicing
			active_polys = GetSelsetPolygons( rmmesh.bmesh, BACKGROUND_LAYERNAME )
			if len( active_polys ) < 1:
				return { 'CANCELLED' }

			geom = []
			geom.extend( active_polys.edges )
			geom.extend( active_polys )

			inv_rot_mat = rmmesh.world_transform.to_3x3().inverted()
			
			#in vert mode, slice active polys horizontally or vertically
			if sel_mode[0]:
				selected_vertices = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( selected_vertices ) < 1:
					return { 'CANCELLED' }

				for v in selected_vertices:
					plane_pos = v.co
					if self.alignment == 'topology':
						dir_idx, cam_dir_vec, grid_dir_vec = rm_vp.get_nearest_direction_vector( self.str_dir, rm_wp.matrix )
						vnorm = mathutils.Vector( v.normal )
						grid_dir_vec = inv_rot_mat @ grid_dir_vec
						plane_nml = grid_dir_vec.cross( vnorm )
					elif self.alignment == 'grid':
						strdir = 'horizontal'
						if self.str_dir == 'horizontal':
							strdir = 'vertical'
						dir_idx, cam_dir_vec, plane_nml = rm_vp.get_nearest_direction_vector( strdir, rm_wp.matrix )
						plane_nml = inv_rot_mat @ plane_nml
					else:
						strdir = 'horizontal'
						if self.str_dir == 'horizontal':
							strdir = 'vertical'
						dir_idx, plane_nml, grid_dir_vec = rm_vp.get_nearest_direction_vector( self.str_dir, rm_wp.matrix )
						plane_nml = inv_rot_mat @ plane_nml
						
					#slice op
					d = bmesh.ops.bisect_plane( rmmesh.bmesh, geom=geom, dist=0.00001, plane_co=plane_pos, plane_no=plane_nml, use_snap_center=False, clear_outer=False, clear_inner=False )
					geom = d['geom']

			#in edge mode, slice active polys along edges	
			elif sel_mode[1]:
				selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				if len( selected_edges ) < 1:
					return { 'CANCELLED' }
				
				for e in selected_edges:
					plane_pos = e.verts[0].co
					
					edge_vec = ( e.verts[0].co - e.verts[1].co ).normalized()
					if self.alignment == 'topology':
						edge_nml = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
						for f in e.link_faces:
							edge_nml += f.normal
						edge_nml.normalize()
						plane_nml = edge_vec.cross( edge_nml )
					elif self.alignment == 'grid':
						dir_idx, cam_dir_vec, plane_nml = rm_vp.get_nearest_direction_vector( 'front', rm_wp.matrix )
						plane_nml = inv_rot_mat @ plane_nml
						plane_nml = plane_nml.cross( edge_vec )
					else:
						dir_idx, plane_nml, grid_dir_vec = rm_vp.get_nearest_direction_vector( 'front', rm_wp.matrix )
						plane_nml = inv_rot_mat @ plane_nml
						plane_nml = plane_nml.cross( edge_vec )
						
					#slice op
					d = bmesh.ops.bisect_plane( rmmesh.bmesh, geom=geom, dist=0.00001, plane_co=plane_pos, plane_no=plane_nml, use_snap_center=False, clear_outer=False, clear_inner=False )
					geom = d['geom']
		
		return { 'FINISHED' }


class VIEW3D_MT_knifescreen( bpy.types.Menu ):
	"""Slice the background face selection based on the current vert/edge selection."""
	bl_idname = 'OBJECT_MT_rm_knifescreen'
	bl_label = 'Knife Screen GUI'

	def draw( self, context ):
		layout = self.layout
		
		if context.object is None or context.mode == 'OBJECT':
			return layout
		
		if context.object.type != 'MESH':
			return layout
		
		sel_mode = context.tool_settings.mesh_select_mode[:]
		
		if sel_mode[0]:
			op_vhg = layout.operator( MESH_OT_knifescreen.bl_idname, text='Vertex :: Grid :: Horizontal' )
			op_vhg.str_dir = 'horizontal'
			op_vhg.alignment = context.object.ks_alignment_grid

			op_vht = layout.operator( MESH_OT_knifescreen.bl_idname, text='Vertex :: Screen :: Horizontal' )
			op_vht.str_dir = 'horizontal'
			op_vht.alignment = context.object.ks_alignment_screen
			
			layout.separator()

			op_vvg = layout.operator( MESH_OT_knifescreen.bl_idname, text='Vertex :: Grid :: Vertical' )
			op_vvg.str_dir = 'vertical'
			op_vvg.alignment = context.object.ks_alignment_grid
			
			op_vvt = layout.operator( MESH_OT_knifescreen.bl_idname, text='Vertex :: Screen :: Vertical' )
			op_vvt.str_dir = 'vertical'
			op_vvt.alignment = context.object.ks_alignment_screen
					
		elif sel_mode[1]:
			op_et = layout.operator( MESH_OT_knifescreen.bl_idname, text='Edge :: Topo' )
			op_et.alignment = context.object.ks_alignment_topo
			
			op_eg = layout.operator( MESH_OT_knifescreen.bl_idname, text='Edge :: Grid' )
			op_eg.alignment = context.object.ks_alignment_grid
			
			op_eg = layout.operator( MESH_OT_knifescreen.bl_idname, text='Edge :: Screen' )
			op_eg.alignment = context.object.ks_alignment_screen
			

def register():
	print( 'register :: {}'.format( MESH_OT_knifescreen.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_knifescreen.bl_idname ) )
	bpy.utils.register_class( MESH_OT_knifescreen )
	bpy.utils.register_class( VIEW3D_MT_knifescreen )
	bpy.types.Object.ks_alignment_topo = bpy.props.EnumProperty(
		items=[ ( "topology", "Topology", "", 1 ),
				( "grid", "Grid", "", 2 ),
				( "screen", "Screen", "", 3 ) ],
		name="Alignment",
		default="topology"
	)
	bpy.types.Object.ks_alignment_grid = bpy.props.EnumProperty(
		items=[ ( "topology", "Topology", "", 1 ),
				( "grid", "Grid", "", 2 ),
				( "screen", "Screen", "", 3 ) ],
		name="Alignment",
		default="grid"
	)
	bpy.types.Object.ks_alignment_screen = bpy.props.EnumProperty(
		items=[ ( "topology", "Topology", "", 1 ),
				( "grid", "Grid", "", 2 ),
				( "screen", "Screen", "", 3 ) ],
		name="Alignment",
		default="screen"
	)
	
	
def unregister():
	print( 'unregister :: {}'.format( VIEW3D_MT_knifescreen.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_knifescreen.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_knifescreen )
	bpy.utils.unregister_class( VIEW3D_MT_knifescreen )
	del bpy.types.Object.ks_alignment_topo
	del bpy.types.Object.ks_alignment_grid
	del bpy.types.Object.ks_alignment_screen