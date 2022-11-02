import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

class MESH_OT_knifescreeninternal( bpy.types.Operator ):
	"""Slice visible geo based on current selection and selection mode."""
	bl_idname = 'mesh.rm_knifescreeninternal'
	bl_label = 'KnifeScreen'
	bl_options = { 'UNDO', 'INTERNAL' }
	
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

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:

			#init geom list for slicing
			if sel_mode[2]:
				active_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
			else:
				active_polys = rmlib.rmPolygonSet.from_mesh( rmmesh )
			if len( active_polys ) < 1:
				return { 'CANCELLED' }
			geom = []
			geom.extend( active_polys.edges )
			geom.extend( active_polys )
			
			#in vert mode, slice active polys horizontally or vertically
			if sel_mode[0]:
				selected_vertices = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( selected_vertices ) < 1:
					return { 'CANCELLED' }

				for v in selected_vertices:
					plane_pos = v.co
					if self.alignment == 'topology':
						dir_idx, cam_dir_vec, grid_dir_vec = rm_vp.get_nearest_direction_vector( self.str_dir, rm_wp.matrix )
						plane_nml = grid_dir_vec.cross( v.normal )
					elif self.alignment == 'grid':
						dir_idx, cam_dir_vec, plane_nml = rm_vp.get_nearest_direction_vector( 'up', rm_wp.matrix )
					else:
						dir_idx, plane_nml, grid_dir_vec = rm_vp.get_nearest_direction_vector( 'up', rm_wp.matrix )
						
					#slice op
					d = bmesh.ops.bisect_plane( rmmesh.bmesh, geom=geom, dist=0.00001, plane_co=plane_pos, plane_no=plane_nml, use_snap_center=False, clear_outer=False, clear_inner=False )
					
					#set resulting selection
					for v in d['geom_cut']:
						if isinstance( v, bmesh.types.BMVert ):
							v.select = True

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
						plane_nml = plane_nml.cross( edge_vec )
					else:
						dir_idx, plane_nml, grid_dir_vec = rm_vp.get_nearest_direction_vector( 'front', rm_wp.matrix )
						plane_nml = plane_nml.cross( edge_vec )
						
					#slice op
					d = bmesh.ops.bisect_plane( rmmesh.bmesh, geom=geom, dist=0.00001, plane_co=plane_pos, plane_no=plane_nml, use_snap_center=False, clear_outer=False, clear_inner=False )
					
					#set resulting selection
					for e in d['geom_cut']:
						if isinstance( e, bmesh.types.BMEdge ):
							e.select = True

			#in poly mode, mos a vert or edge and slice accordingly	
			else:
				if self.str_dir == 'edge':
					mos_edges = rmlib.rmEdgeSet.from_mos( rmmesh, context, mathutils.Vector( ( self.mouse_pos[0], self.mouse_pos[1] ) ) )
					for e in mos_edges:
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
							plane_nml = plane_nml.cross( edge_vec )
						else:
							dir_idx, plane_nml, grid_dir_vec = rm_vp.get_nearest_direction_vector( 'front', rm_wp.matrix )
							plane_nml = plane_nml.cross( edge_vec )
							
						#slice op
						d = bmesh.ops.bisect_plane( rmmesh.bmesh, geom=geom, dist=0.00001, plane_co=plane_pos, plane_no=plane_nml, use_snap_center=False, clear_outer=False, clear_inner=False )
						
						#set resulting selection
						for p in d['geom_cut']:
							if isinstance( p, bmesh.types.BMFace ):
								p.select = True

				else:
					mos_verts = rmlib.rmVertexSet.from_mos( rmmesh, context, mathutils.Vector( ( self.mouse_pos[0], self.mouse_pos[1] ) ) )
					for v in mos_verts:
						plane_pos = v.co
						if self.alignment == 'topology':
							plane_nml = grid_dir_vec.cross( v.normal )
						elif self.alignment == 'grid':
							dir_idx, cam_dir_vec, plane_nml = rm_vp.get_nearest_direction_vector( 'up', rm_wp.matrix )
						else:
							dir_idx, plane_nml, grid_dir_vec = rm_vp.get_nearest_direction_vector( 'up', rm_wp.matrix )
							
						#slice op
						d = bmesh.ops.bisect_plane( rmmesh.bmesh, geom=geom, dist=0.00001, plane_co=plane_pos, plane_no=plane_nml, use_snap_center=False, clear_outer=False, clear_inner=False )
						
						#set resulting selection
						for p in d['geom_cut']:
							if isinstance( p, bmesh.types.BMFace ):
								p.select = True
		
		return { 'FINISHED' }


class VIEW3D_MT_knifescreen( bpy.types.Menu ):
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
			op_vht = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Vertex :: Topo :: Horizontal' )
			op_vht.str_dir = 'horizontal'
			op_vht.alignment = context.object.ks_alignment_topo
			
			op_vhg = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Vertex :: Grid :: Horizontal' )
			op_vhg.str_dir = 'horizontal'
			op_vhg.alignment = context.object.ks_alignment_grid
			
			layout.separator()
			
			op_vvt = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Vertex :: Topo :: Vertical' )
			op_vvt.str_dir = 'vertical'
			op_vvt.alignment = context.object.ks_alignment_topo
			
			op_vvg = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Vertex :: Grid :: Vertical' )
			op_vvg.str_dir = 'vertical'
			op_vvg.alignment = context.object.ks_alignment_grid
					
		elif sel_mode[1]:
			op_et = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Edge :: Topo' )
			op_et.alignment = context.object.ks_alignment_topo
			
			op_eg = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Edge :: Grid' )
			op_eg.alignment = context.object.ks_alignment_grid
			
			op_eg = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Edge :: Screen' )
			op_eg.alignment = context.object.ks_alignment_screen
			
		elif sel_mode[2]:
			op_vht = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Vertex :: Topo :: Horizontal' )
			op_vht.str_dir = 'horizontal'
			op_vht.alignment = context.object.ks_alignment_topo
			op_vht.mouse_pos = context.object.ks_mouse_pos
			
			op_vhg = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Vertex :: Grid :: Horizontal' )
			op_vhg.str_dir = 'horizontal'
			op_vhg.alignment = context.object.ks_alignment_grid
			op_vhg.mouse_pos = context.object.ks_mouse_pos
			
			layout.separator()
			
			op_vvt = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Vertex :: Topo :: Vertical' )
			op_vvt.str_dir = 'vertical'
			op_vvt.alignment = context.object.ks_alignment_topo
			op_vvt.mouse_pos = context.object.ks_mouse_pos
			
			op_vvg = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Vertex :: Grid :: Vertical' )
			op_vvg.str_dir = 'vertical'
			op_vvg.alignment = context.object.ks_alignment_grid
			op_vvg.mouse_pos = context.object.ks_mouse_pos
		
			layout.separator()

			op_et = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Edge :: Topo' )
			op_et.str_dir = 'edge'
			op_et.alignment = context.object.ks_alignment_topo
			op_et.mouse_pos = context.object.ks_mouse_pos
			
			op_eg = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Edge :: Grid' )
			op_eg.str_dir = 'edge'
			op_eg.alignment = context.object.ks_alignment_grid
			op_eg.mouse_pos = context.object.ks_mouse_pos
			
			op_eg = layout.operator( MESH_OT_knifescreeninternal.bl_idname, text='Edge :: Screen' )
			op_eg.str_dir = 'edge'
			op_eg.alignment = context.object.ks_alignment_screen
			op_eg.mouse_pos = context.object.ks_mouse_pos
			

class MESH_OT_knifescreen( bpy.types.Operator ):
	"""Knife Screen Dispatch Operator"""
	bl_idname = 'mesh.rm_knifescreen'
	bl_label = 'Knife Screen'

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		context.object.ks_mouse_pos = self.mouse_pos
		bpy.ops.wm.call_menu( name=VIEW3D_MT_knifescreen.bl_idname )
		return { 'FINISHED' }

	def invoke( self, context, event ):
		x, y = event.mouse_region_x, event.mouse_region_y
		self.mouse_pos = ( float( x ), float( y ) )
		return self.execute( context )	

	
def register():
	print( 'register :: {}'.format( MESH_OT_knifescreeninternal.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_knifescreen.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_knifescreen.bl_idname ) )
	bpy.utils.register_class( MESH_OT_knifescreeninternal )
	bpy.utils.register_class( VIEW3D_MT_knifescreen )
	bpy.utils.register_class( MESH_OT_knifescreen )
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
	bpy.types.Object.ks_mouse_pos = bpy.props.FloatVectorProperty(
		name="Cursor Position",
		size=2,
		default=( 0.0, 0.0 )
	)
	
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_knifescreen.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_knifescreen.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_knifescreen.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_knifescreeninternal )
	bpy.utils.unregister_class( VIEW3D_MT_knifescreen )
	bpy.utils.unregister_class( MESH_OT_knifescreen )
	del bpy.types.Object.ks_alignment_topo
	del bpy.types.Object.ks_alignment_grid
	del bpy.types.Object.ks_alignment_screen
	del bpy.types.Object.ks_mouse_pos