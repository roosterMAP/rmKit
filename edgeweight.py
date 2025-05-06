import bpy, bmesh
import rmlib

def GetEdges( bmesh, sel_mode ):
	if sel_mode[1]:
		return rmlib.rmEdgeSet( [ e for e in bmesh.edges if e.select ] )
	elif sel_mode[2]:
		edges = set()
		polys = rmlib.rmPolygonSet( [ f for f in bmesh.faces if f.select ] )
		for e in polys.edges:
			for p in e.link_faces:
				if p not in polys:
					edges.add( e )
					break
		return rmlib.rmEdgeSet( edges )
	return rmlib.rmEdgeSet()

def SetEdgeCrease( context, weight ):
	sel_mode = context.tool_settings.mesh_select_mode[:]
	rmmesh = rmlib.rmMesh.GetActive( context )	
	with rmmesh as rmmesh:
		rmmesh.skipchecks = True
		clyr = None
		if bpy.app.version < (4,0,0):
			c_layers = rmmesh.bmesh.edges.layers.crease
			clyr = c_layers.verify()
		else:
			clyr = rmmesh.bmesh.edges.layers.float.get( 'crease_edge', None )
			if clyr is None:
				clyr = rmmesh.bmesh.edges.layers.float.new( 'crease_edge' )
		for e in GetEdges( rmmesh.bmesh, sel_mode ):
			e[clyr] = weight


def SetEdgeBevelWeight( context, weight ):
	sel_mode = context.tool_settings.mesh_select_mode[:]
	rmmesh = rmlib.rmMesh.GetActive( context )	
	with rmmesh as rmmesh:
		rmmesh.skipchecks = True
		blyr = None
		if bpy.app.version < (4,0,0):
			b_layers = rmmesh.bmesh.edges.layers.bevel_weight
			blyr = b_layers.verify()
		else:
			blyr = rmmesh.bmesh.edges.layers.float.get( 'bevel_weight_edge', None )
			if blyr is None:
				blyr = rmmesh.bmesh.edges.layers.float.new( 'bevel_weight_edge' )
		for e in GetEdges( rmmesh.bmesh, sel_mode ):
			e[blyr] = weight


def SetEdgeSharp( context, weight ):
	sel_mode = context.tool_settings.mesh_select_mode[:]
	rmmesh = rmlib.rmMesh.GetActive( context )	
	with rmmesh as rmmesh:
		rmmesh.skipchecks = True
		for e in GetEdges( rmmesh.bmesh, sel_mode ):
			e.smooth = not bool( round( weight ) )
			

class MESH_OT_setedgeweight( bpy.types.Operator ):
	"""Set create/bevelweight amount on selected edges."""
	bl_idname = 'mesh.rm_setedgeweight'
	bl_label = 'Set Edge Weight'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	weight_type: bpy.props.EnumProperty(
		items=[ ( "crease", "Crease", "", 1 ),
				( "bevel_weight", "Bevel Weight", "", 2 ),
				( "sharp", "Sharp", "", 3 ) ],
		name="Weight Type",
		default="crease"
	)

	weight: bpy.props.FloatProperty(
		name='Weight',
		default=0.0
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

		if self.weight_type == 'crease':
			SetEdgeCrease( context, self.weight )
		elif self.weight_type == 'bevel_weight':
			SetEdgeBevelWeight( context, self.weight )
		else:
			SetEdgeSharp( context, self.weight )

		return { 'FINISHED' }


class VIEW3D_MT_PIE_setedgeweight_crease( bpy.types.Menu ):
	"""Set create/bevelweight amount on selected edges."""
	bl_idname = 'VIEW3D_MT_PIE_setedgeweight_crease'
	bl_label = 'Edge Weight'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_w = pie.operator( MESH_OT_setedgeweight.bl_idname, text='100%' )
		op_w.weight = 1.0
		op_w.weight_type = context.object.ew_weight_type_crease
		
		op_e = pie.operator( MESH_OT_setedgeweight.bl_idname, text='30%' )
		op_e.weight = 0.3
		op_e.weight_type = context.object.ew_weight_type_crease
		
		op_s = pie.operator( MESH_OT_setedgeweight.bl_idname, text='60%' )
		op_s.weight = 0.6
		op_s.weight_type = context.object.ew_weight_type_crease
		
		op_n = pie.operator( MESH_OT_setedgeweight.bl_idname, text='0%' )
		op_n.weight = 0.0
		op_n.weight_type = context.object.ew_weight_type_crease

		pie.operator( 'wm.call_menu_pie', text='Bevel Weight' ).name = 'VIEW3D_MT_PIE_setedgeweight_bevel'

		op_ne = pie.operator( MESH_OT_setedgeweight.bl_idname, text='20%' )
		op_ne.weight = 0.2
		op_ne.weight_type = context.object.ew_weight_type_crease

		op_sw = pie.operator( MESH_OT_setedgeweight.bl_idname, text='80%' )
		op_sw.weight = 0.8
		op_sw.weight_type = context.object.ew_weight_type_crease

		op_se = pie.operator( MESH_OT_setedgeweight.bl_idname, text='40%' )
		op_se.weight = 0.4
		op_se.weight_type = context.object.ew_weight_type_crease	


class VIEW3D_MT_PIE_setedgeweight_bevel( bpy.types.Menu ):
	"""Set create/bevelweight amount on selected edges."""
	bl_idname = 'VIEW3D_MT_PIE_setedgeweight_bevel'
	bl_label = 'Edge Weight'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_w = pie.operator( MESH_OT_setedgeweight.bl_idname, text='100%' )
		op_w.weight = 1.0
		op_w.weight_type = context.object.ew_weight_type_bevel_weight
		
		op_e = pie.operator( MESH_OT_setedgeweight.bl_idname, text='30%' )
		op_e.weight = 0.3
		op_e.weight_type = context.object.ew_weight_type_bevel_weight
		
		op_s = pie.operator( MESH_OT_setedgeweight.bl_idname, text='60%' )
		op_s.weight = 0.6
		op_s.weight_type = context.object.ew_weight_type_bevel_weight
		
		op_n = pie.operator( MESH_OT_setedgeweight.bl_idname, text='0%' )
		op_n.weight = 0.0
		op_n.weight_type = context.object.ew_weight_type_bevel_weight

		pie.operator( 'wm.call_menu_pie', text='Crease' ).name = 'VIEW3D_MT_PIE_setedgeweight_crease'

		op_ne = pie.operator( MESH_OT_setedgeweight.bl_idname, text='20%' )
		op_ne.weight = 0.2
		op_ne.weight_type = context.object.ew_weight_type_bevel_weight

		op_sw = pie.operator( MESH_OT_setedgeweight.bl_idname, text='80%' )
		op_sw.weight = 0.8
		op_sw.weight_type = context.object.ew_weight_type_bevel_weight

		op_se = pie.operator( MESH_OT_setedgeweight.bl_idname, text='40%' )
		op_se.weight = 0.4
		op_se.weight_type = context.object.ew_weight_type_bevel_weight


def register():
	bpy.utils.register_class( MESH_OT_setedgeweight )
	bpy.utils.register_class( VIEW3D_MT_PIE_setedgeweight_crease )
	bpy.utils.register_class( VIEW3D_MT_PIE_setedgeweight_bevel )
	bpy.types.Object.ew_weight_type_crease = bpy.props.EnumProperty(
		items=[ ( "crease", "Crease", "", 1 ),
				( "bevel_weight", "Bevel Weight", "", 2 ),
				( "sharp", "Sharp", "", 3 ) ],
		name="Weight Type",
		default="crease"
	)
	bpy.types.Object.ew_weight_type_bevel_weight = bpy.props.EnumProperty(
		items=[ ( "crease", "Crease", "", 1 ),
				( "bevel_weight", "Bevel Weight", "", 2 ),
				( "sharp", "Sharp", "", 3 ) ],
		name="Weight Type",
		default="bevel_weight"
	)


def unregister():
	bpy.utils.unregister_class( MESH_OT_setedgeweight )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_setedgeweight_crease )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_setedgeweight_bevel )
	del bpy.types.Object.ew_weight_type_crease
	del bpy.types.Object.ew_weight_type_bevel_weight