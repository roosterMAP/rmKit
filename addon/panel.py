import bpy
from .. import rmlib


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
		layout.prop( context.scene, 'dimensions_use_background_face_selection' )

		layout.separator()

		layout.operator( 'mesh.rm_itemnametomeshname' )

		layout.operator( 'mesh.rm_matclearnup', text='Material Cleanup' )
		

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
		if bpy.app.version < ( 4, 0, 0 ):
			layout.operator( 'mesh.rm_uvboundstransform', text='Bounds Transform' )
		layout.operator( 'mesh.rm_uvfalloff', text='Falloff UV Transform' )
		layout.operator( 'mesh.rm_uvaspectscale', text='Inset Scale UVs' )
		layout.operator( 'mesh.rm_uvgridify', text='Gridify' )
		layout.operator( 'mesh.rm_uvrectangularize', text='Boxify' )
		layout.operator( 'mesh.rm_stitch', text='Stitch' )
		layout.operator( 'mesh.rm_uvunrotate', text='Unrotate' )
		layout.operator( 'mesh.rm_relativeislands' )
		layout.operator( 'mesh.rm_worldspaceproject' )
		layout.operator( 'mesh.rm_scaletomaterialsize' )
		r3 = layout.row()
		r3.operator( 'mesh.rm_uvgrowshrink', text='UV Grow' ).mode = 'GROW'
		r3.operator( 'mesh.rm_uvgrowshrink', text='UV Shrink' ).mode = 'SHRINK'

		r2 = layout.row()
		r2.alignment = 'EXPAND'
		r2.operator( 'mesh.rm_normalizetexels', text='NmlTex U' ).horizontal = True
		r2.operator( 'mesh.rm_normalizetexels', text='NmlTex V' ).horizontal = False


class VIEW3D_PT_SELECTION( bpy.types.Panel ):
	bl_parent_id = 'VIEW3D_PT_RMKIT_PARENT'
	bl_label = 'Selection'
	bl_region_type = 'UI'
	bl_space_type = 'VIEW_3D'
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout

		'''
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
		'''

		r4 = layout.row()
		r4.alignment = 'EXPAND'

		r4.operator( 'mesh.rm_loop', text='Loop' ).force_boundary = False
		r4.operator( 'mesh.rm_loop', text='Loop Alt' ).force_boundary = True

		layout.operator( 'mesh.rm_ring', text='Ring' )

		r5 = layout.row()
		r5.alignment = 'EXPAND'

		r5.operator( 'mesh.rm_continuous', text='Set Continuous' ).add = False
		r5.operator( 'mesh.rm_continuous', text='Add Continuous' ).add = True

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


class VIEW3D_PT_VIEW3D_UV( bpy.types.Panel ):
	bl_idname = 'VIEW3D_PT_VIEW3D_UV'
	bl_parent_id = 'VIEW3D_PT_RMKIT_PARENT'
	bl_label = 'View3D UV Tools'
	bl_region_type = 'UI'
	bl_space_type = 'VIEW_3D'
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout

		layout.operator( 'mesh.rm_worldspaceproject' )
		layout.operator( 'mesh.rm_uvgridify', text='UV Gridify' )
		layout.operator( 'mesh.rm_uvrectangularize', text='UV Boxify' )
		layout.separator()
		layout.operator( 'object.savehotspot', text='New Hotspot' )
		layout.operator( 'mesh.refhotspot', text='Ref Hotspot' )
		layout.separator()
		r1 = layout.row()
		r1.prop( context.scene, 'use_multiUV' )
		r2 = layout.row()
		r2.prop( context.scene, 'hotspot_uv1' )
		r2.prop( context.scene, 'hotspot_uv2' )
		r2.enabled = context.scene.use_multiUV
		layout.operator( 'mesh.matchhotspot' )
	
	
def register():
	bpy.utils.register_class( VIEW3D_PT_UTILS )
	bpy.utils.register_class( VIEW3D_PT_SELECTION )
	bpy.utils.register_class( VIEW3D_PT_MESHEDIT )
	bpy.utils.register_class( VIEW3D_PT_LAYERS )
	bpy.utils.register_class( UV_PT_UVTOOLS )
	bpy.utils.register_class( VIEW3D_PT_VIEW3D_UV )
	

def unregister():
	bpy.utils.unregister_class( VIEW3D_PT_UTILS )
	bpy.utils.unregister_class( VIEW3D_PT_SELECTION )
	bpy.utils.unregister_class( VIEW3D_PT_MESHEDIT )
	bpy.utils.unregister_class( VIEW3D_PT_LAYERS )
	bpy.utils.unregister_class( UV_PT_UVTOOLS )
	bpy.utils.unregister_class( VIEW3D_PT_VIEW3D_UV )