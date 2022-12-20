import bpy
import rmKit.rmlib as rmlib


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

		r3 = layout.row()
		r3.alignment = 'EXPAND'
		r3.operator( 'wm.call_menu_pie', text='3D Cursor Pie' ).name = 'VIEW3D_MT_PIE_cursor'


class UV_PT_UVTOOLS( bpy.types.Panel ):
	bl_parent_id = 'UV_PT_RMKIT_PARENT'
	bl_idname = 'UV_PT_UVTOOLS'
	bl_label = 'UV Operations'
	bl_region_type = 'UI'
	bl_space_type = 'IMAGE_EDITOR'
	bl_options = { 'HIDE_HEADER' }

	def draw( self, context ):
		layout = self.layout

		r1 = layout.row()
		r1.alignment = 'EXPAND'
		r1.operator( 'mesh.rm_uvloop', text='UV Loop' )
		r1.operator( 'mesh.rm_uvring', text='UV Ring' )
		
		layout.operator( 'wm.call_menu_pie', text='UV Move To Furthest' ).name = 'IMAGE_EDITOR_MT_PIE_uvmovetofurthest'
		layout.operator( 'mesh.rm_uvgridify', text='Gridify' )
		layout.operator( 'mesh.rm_uvrectangularize', text='Rectangularize' )
		layout.operator( 'mesh.rm_relativeislands', text='Relative Islands' )
		layout.operator( 'mesh.rm_stitch', text='Stitch' )
		layout.operator( 'mesh.rm_uvunrotate', text='Unrotate' )


class VIEW3D_PT_SELECTION( bpy.types.Panel ):
	bl_parent_id = 'VIEW3D_PT_RMKIT_PARENT'
	bl_label = 'Selection'
	bl_region_type = 'UI'
	bl_space_type = 'VIEW_3D'
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout

		box1 = layout.box()

		r1 = box1.row()
		r1.alignment = 'EXPAND'
		r1.operator( 'mesh.rm_changemodeto', text='Vert Mode' ).mode_to = 'VERT'
		r1.operator( 'mesh.rm_convertmodeto', text='Convert to Vert' ).mode_to = 'VERT'

		r2 = box1.row()
		r2.alignment = 'EXPAND'
		r2.operator( 'mesh.rm_changemodeto', text='Edge Mode' ).mode_to = 'EDGE'
		r2.operator( 'mesh.rm_convertmodeto', text='Convert to Edge' ).mode_to = 'EDGE'

		r3 = box1.row()
		r3.alignment = 'EXPAND'
		r3.operator( 'mesh.rm_changemodeto', text='Face Mode' ).mode_to = 'FACE'
		r3.operator( 'mesh.rm_convertmodeto', text='Convert to Face' ).mode_to = 'FACE'

		layout.operator( 'mesh.rm_loop', text='Loop' ).force_boundary = False
		layout.operator( 'mesh.rm_loop', text='Loop Alt' ).force_boundary = True	
		layout.operator( 'mesh.rm_ring', text='Ring' )
		layout.operator( 'mesh.rm_continuous', text='Set Continuous' ).add = False
		layout.operator( 'mesh.rm_continuous', text='Add Continuous' ).add = True
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
		c1.operator( 'wm.call_menu', text='Knife Screen' ).name = 'OBJECT_MT_rm_knifescreen'
		c1.operator( 'wm.call_menu_pie', text='Move To Furthest' ).name = 'VIEW3D_MT_PIE_movetofurthest'
		c1.operator( 'wm.call_menu_pie', text='Screen Reflect' ).name = 'OBJECT_MT_rm_screenreflect'

		r2 = layout.row()
		r2.operator( 'mesh.rm_contextbevel', text='Bevel' )
		r2.operator( 'mesh.rm_extend', text='Extend' )
		r2.operator( 'mesh.rm_slide', text='Slide' )

		c2 = layout.column()
		c2.operator( 'mesh.rm_connectedge', text='Connect Edges' )
		c2.operator( 'mesh.rm_push', text='Push' )
		c2.operator( 'mesh.rm_thicken', text='Thicken' )
		c2.operator( 'mesh.rm_createtube', text='Create Tube' )
		c2.operator( 'mesh.rm_arcadjust', text='Arc Adjust' )

		c3 = layout.column()
		c3.operator( 'mesh.rm_unbevel', text='Unbevel' )
		c3.operator( 'mesh.rm_radialalign', text='Radial Align' )
		c3.operator( 'mesh.rm_targetweld', text='Target Weld' )


class VIEW3D_PT_MATERIALS( bpy.types.Panel ):
	bl_parent_id = 'VIEW3D_PT_RMKIT_PARENT'
	bl_label = 'Materials'
	bl_region_type = 'UI'
	bl_space_type = 'VIEW_3D'
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout

		r1 = layout.column()
		r1.alignment = 'EXPAND'
		r1.operator( 'mesh.rm_grabapplymat', text='GrabApplyMat (MOS)' )
		r1.operator( 'mesh.rm_quickmaterial', text='QuickMaterial (MOS)' )


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
		layout.operator( 'mesh.rm_uvgridify', text='UV Gridify' )
		layout.operator( 'mesh.rm_uvrectangularize', text='UV Rectangularize' )
	
	
def register():
	bpy.utils.register_class( VIEW3D_PT_UTILS )
	bpy.utils.register_class( VIEW3D_PT_SELECTION )
	bpy.utils.register_class( VIEW3D_PT_MESHEDIT )
	bpy.utils.register_class( VIEW3D_PT_LAYERS )
	bpy.utils.register_class( VIEW3D_PT_MATERIALS )
	bpy.utils.register_class( UV_PT_UVTOOLS )
	

def unregister():
	bpy.utils.unregister_class( VIEW3D_PT_UTILS )
	bpy.utils.unregister_class( VIEW3D_PT_SELECTION )
	bpy.utils.unregister_class( VIEW3D_PT_MESHEDIT )
	bpy.utils.unregister_class( VIEW3D_PT_LAYERS )
	bpy.utils.unregister_class( VIEW3D_PT_MATERIALS )
	bpy.utils.unregister_class( UV_PT_UVTOOLS )