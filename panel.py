import bpy
import rmlib


class VIEW3D_PT_UTILS( bpy.types.Panel ):
	bl_parent_id = 'VIEW3D_PT_RMKIT_PARENT'
	bl_label = 'Utilities'
	bl_region_type = 'UI'
	bl_space_type = 'VIEW_3D'
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout

		r1 = layout.row()
		r1.alignment = 'EXPAND'
		r1.operator( 'mesh.rm_copy', text='Copy' ).cut = False
		r1.operator( 'mesh.rm_copy', text='Cut' ).cut = True
		r1.operator( 'mesh.rm_paste', text='Paste' )

		r2 = layout.row()
		r2.alignment = 'EXPAND'
		r2.operator( 'view3d.rm_togglegrid', text='Grid Toggle' )
		r2.operator( 'view3d.rm_workplane', text='Toggle Workplane' )		

		layout.operator( 'wm.call_menu_pie', text='3D Cursor Pie' ).name = 'VIEW3D_MT_PIE_cursor'

		layout.separator()
		
		layout.operator( 'view3d.rm_dimensions', text='Toggle Dimensions' )
		layout.prop( context.scene.rmkit_props, 'dimensions_use_background_face_selection' )

		layout.separator()

		layout.operator( 'mesh.rm_itemnametomeshname' )

		layout.operator( 'mesh.rm_matclearnup', text='Material Cleanup' )


class VIEW3D_PT_SELECTION( bpy.types.Panel ):
	bl_parent_id = 'VIEW3D_PT_RMKIT_PARENT'
	bl_label = 'Selection'
	bl_region_type = 'UI'
	bl_space_type = 'VIEW_3D'
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout
		
		r4 = layout.row()
		r4.alignment = 'EXPAND'

		r4.operator( 'mesh.rm_loop', text='Loop' ).force_boundary = False
		r4.operator( 'mesh.rm_loop', text='Loop Alt' ).force_boundary = True

		layout.operator( 'mesh.rm_ring', text='Ring' )

		layout.operator( 'mesh.rm_continuous', text='Set Continuous' ).mode = 'set'
		layout.operator( 'mesh.rm_invertcontinuous', text='Invert Continuous' )


class VIEW3D_PT_MESHEDIT( bpy.types.Panel ):
	bl_parent_id = 'VIEW3D_PT_RMKIT_PARENT'
	bl_label = 'Mesh Edit'
	bl_region_type = 'UI'
	bl_space_type = 'VIEW_3D'
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout
		
		layout.operator( 'mesh.rm_polypatch', text='PolyPatch' )

		box1 = layout.box()
		r2 = box1.row()
		r2.alignment = 'EXPAND'
		r2.operator( 'mesh.rm_remove', text='Delete' ).reduce_mode = 'DEL'
		r2.operator( 'mesh.rm_remove', text='Collapse' ).reduce_mode = 'COL'
		r2.operator( 'mesh.rm_remove', text='Dissolve' ).reduce_mode = 'DIS'
		r2.operator( 'mesh.rm_remove', text='Pop' ).reduce_mode = 'POP'

		c1 = layout.column()
		c1.operator( 'mesh.rm_knifescreenmenu', text='Knife Screen' )
		c1.operator( 'wm.call_menu_pie', text='Move To Furthest' ).name = 'VIEW3D_MT_PIE_movetofurthest'
		c1.operator( 'wm.call_menu_pie', text='Screen Reflect' ).name = 'OBJECT_MT_rm_screenreflect'
		c1.operator( 'mesh.rm_falloff', text='Falloff Transform' )

		r2 = layout.row()
		r2.operator( 'mesh.rm_contextbevel', text='Bevel' )
		r2.operator( 'mesh.rm_extend', text='Extend' )

		c2 = layout.column()
		c2.operator( 'mesh.rm_connectedge', text='Connect Edges' )
		c2.operator( 'mesh.rm_thicken', text='Thicken' )
		c2.operator( 'mesh.rm_createtube', text='Create Tube' )
		c2.operator( 'mesh.rm_arcadjust', text='Arc Adjust' )
		c2.operator( 'mesh.rm_extrudealongpath', text='Extrude Along Path' )

		c3 = layout.column()
		c3.operator( 'mesh.rm_unbevel', text='Unbevel' )
		c3.operator( 'mesh.rm_radialalign', text='Radial Align' )
		c3.operator( 'mesh.rm_targetweld', text='Target Weld' )


class VIEW3D_PT_LAYERS( bpy.types.Panel ):
	bl_idname = 'VIEW3D_PT_LAYERS'
	bl_parent_id = 'VIEW3D_PT_RMKIT_PARENT'
	bl_label = 'Mesh Layers'
	bl_region_type = 'UI'
	bl_space_type = 'VIEW_3D'
	bl_options = {'DEFAULT_CLOSED'}	

	def draw( self, context ):
		layout = self.layout
		
		layout.operator( 'wm.call_menu_pie', text='Edge Weight Pie' ).name = 'VIEW3D_MT_PIE_setedgeweight_crease'
	
	
def register():
	bpy.utils.register_class( VIEW3D_PT_UTILS )
	bpy.utils.register_class( VIEW3D_PT_SELECTION )
	bpy.utils.register_class( VIEW3D_PT_MESHEDIT )
	bpy.utils.register_class( VIEW3D_PT_LAYERS )
	

def unregister():
	bpy.utils.unregister_class( VIEW3D_PT_UTILS )
	bpy.utils.unregister_class( VIEW3D_PT_SELECTION )
	bpy.utils.unregister_class( VIEW3D_PT_MESHEDIT )
	bpy.utils.unregister_class( VIEW3D_PT_LAYERS )