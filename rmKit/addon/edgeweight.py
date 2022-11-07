import bpy, bmesh
import rmKit.rmlib as rmlib

def SetEdgeCrease( rmmesh, weight ):
	clyr = None
	with rmmesh as rmmesh:
		c_layers = rmmesh.bmesh.edges.layers.crease
		clyr = c_layers.verify()
	with rmmesh as rmmesh:
		for e in rmlib.rmEdgeSet.from_selection( rmmesh ):
			e[clyr] = weight


def SetEdgeBevelWeight( rmmesh, weight ):
	blyr = None
	with rmmesh as rmmesh:
		b_layers = rmmesh.bmesh.edges.layers.bevel_weight
		blyr = b_layers.verify()
	with rmmesh as rmmesh:
		for e in rmlib.rmEdgeSet.from_selection( rmmesh ):
			e[blyr] = weight
			

class MESH_OT_setedgeweight( bpy.types.Operator ):
	bl_idname = 'mesh.rm_setedgeweight'
	bl_label = 'Set Edge Weight'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	weight_type: bpy.props.EnumProperty(
		items=[ ( "crease", "Crease", "", 1 ),
				( "bevel_weight", "Bevel Weight", "", 2 ) ],
		name="Weight Type",
		default="crease"
	)

	weight: bpy.props.FloatProperty(
		name='Weight',
		default=0.0
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

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }

		if self.weight_type == 'crease':
			SetEdgeCrease( rmmesh, self.weight )
		else:
			SetEdgeBevelWeight( rmmesh, self.weight )

		return { 'FINISHED' }


class VIEW3D_MT_PIE_setedgeweight_crease( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_setedgeweight_crease'
	bl_label = 'Edge Weight'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_w = pie.operator( MESH_OT_setedgeweight.bl_idname, text='99%' )
		op_w.weight = 0.99
		op_w.weight_type = context.object.ew_weight_type_crease
		
		op_e = pie.operator( MESH_OT_setedgeweight.bl_idname, text='40%' )
		op_e.weight = 0.4
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

		op_se = pie.operator( MESH_OT_setedgeweight.bl_idname, text='50%' )
		op_se.weight = 0.5
		op_se.weight_type = context.object.ew_weight_type_crease	


class VIEW3D_MT_PIE_setedgeweight_bevel( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_PIE_setedgeweight_bevel'
	bl_label = 'Edge Weight'

	def draw( self, context ):
		layout = self.layout

		pie = layout.menu_pie()
		
		op_w = pie.operator( MESH_OT_setedgeweight.bl_idname, text='99%' )
		op_w.weight = 0.99
		op_w.weight_type = context.object.ew_weight_type_bevel_weight
		
		op_e = pie.operator( MESH_OT_setedgeweight.bl_idname, text='40%' )
		op_e.weight = 0.4
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

		op_se = pie.operator( MESH_OT_setedgeweight.bl_idname, text='50%' )
		op_se.weight = 0.5
		op_se.weight_type = context.object.ew_weight_type_bevel_weight


def register():
	print( 'register :: {}'.format( MESH_OT_setedgeweight.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_setedgeweight_crease.bl_idname ) )
	print( 'register :: {}'.format( VIEW3D_MT_PIE_setedgeweight_bevel.bl_idname ) )
	bpy.utils.register_class( MESH_OT_setedgeweight )
	bpy.utils.register_class( VIEW3D_MT_PIE_setedgeweight_crease )
	bpy.utils.register_class( VIEW3D_MT_PIE_setedgeweight_bevel )
	bpy.types.Object.ew_weight_type_crease = bpy.props.EnumProperty(
		items=[ ( "crease", "Crease", "", 1 ),
				( "bevel_weight", "Bevel Weight", "", 2 ) ],
		name="Weight Type",
		default="crease"
	)
	bpy.types.Object.ew_weight_type_bevel_weight = bpy.props.EnumProperty(
		items=[ ( "crease", "Crease", "", 1 ),
				( "bevel_weight", "Bevel Weight", "", 2 ) ],
		name="Weight Type",
		default="bevel_weight"
	)


def unregister():
	print( 'unregister :: {}'.format( MESH_OT_setedgeweight.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_setedgeweight_crease.bl_idname ) )
	print( 'unregister :: {}'.format( VIEW3D_MT_PIE_setedgeweight_bevel.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_setedgeweight )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_setedgeweight_crease )
	bpy.utils.unregister_class( VIEW3D_MT_PIE_setedgeweight_bevel )
	del bpy.types.Object.ew_weight_type_crease
	del bpy.types.Object.ew_weight_type_bevel_weight