import bpy, rna_keymap_ui

RM_KEYMAP = []

#https://docs.blender.org/api/current/bpy.types.KeyMapItems.html#bpy.types.KeyMapItems

def register_keyboard_keymap():
	kc = bpy.context.window_manager.keyconfigs.addon
	if kc:
		km_3dview = kc.keymaps.new( name='3D View', space_type='EMPTY' )
		km_mesh = kc.keymaps.new( name='Mesh', space_type='EMPTY' )
		km_uv = kc.keymaps.new( name='UV Editor', space_type='EMPTY' )

		RM_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_togglegrid', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_workplane', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_cursor_to_selection', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_unrotate_relative_to_cursor', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_origin_to_cursor', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_arcadjust', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_connectedge', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_contextbevel', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_createtube', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_extend', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_grabapplymat', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_quickmaterial', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'messh.rm_radialalign', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.grabapplyuvbounds', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.moshotspot', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.nrsthotspot', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.matchhotspot', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_loop', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_ring', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.rm_uvloop', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.rm_uvring', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_polypatch', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.rm_uvrectangularize', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.rm_uvgridify', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_remove', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.rm_relativeislands', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_invertcontinuous', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.rm_stitch', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_targetweld', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_thicken', 'NONE', 'PRESS' ) ) )
		RM_KEYMAP.append( ( km_uv, km_uv.keymap_items.new( 'mesh.rm_uvunrotate', 'NONE', 'PRESS' ) ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_copy', 'NONE', 'PRESS' )
		kmi.properties.cut = True
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_copy', 'NONE', 'PRESS' )
		kmi.properties.cut = False
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_paste', 'NONE', 'PRESS' )
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_changemodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'VERT'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_changemodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'EDGE'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_changemodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'FACE'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_convertmodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'VERT'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_convertmodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'EDGE'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_convertmodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'FACE'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_continuous', 'NONE', 'PRESS' )
		kmi.properties.add = False
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_continuous', 'NONE', 'PRESS' )
		kmi.properties.add = True
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_PIE_movetofurthest'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_PIE_cursor'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_PIE_setedgeweight_crease'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu', 'NONE', 'PRESS' )
		kmi.properties.name = 'OBJECT_MT_rm_knifescreen'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_uv.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'IMAGE_EDITOR_MT_PIE_uvmovetofurthest'
		RM_KEYMAP.append( ( km_uv, kmi ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'OBJECT_MT_rm_screenreflect'
		RM_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_3dview.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_PIE_cursor'
		RM_KEYMAP.append( ( km_3dview, kmi ) )


def unregister_keyboard_keymap():
	for km, kmi in RM_KEYMAP:
		km.keymap_items.remove( kmi )
	RM_KEYMAP.clear()


class RMKITPreferences( bpy.types.AddonPreferences ):
	bl_idname = 'rmKit'

	v3d_checkbox: bpy.props.BoolProperty( name="3D View", default=False )
	mesh_checkbox: bpy.props.BoolProperty( name="Mesh", default=False )
	uv_checkbox: bpy.props.BoolProperty( name="UV Editor", default=False )

	def draw( self, context ):
		layout = self.layout
		box = layout.box()

		row_view3d = box.row()
		row_view3d.prop( self, 'v3d_checkbox', icon='TRIA_DOWN' if self.v3d_checkbox else 'TRIA_RIGHT', icon_only=True, emboss=False )
		row_view3d.label( text='3D View' )
		if self.v3d_checkbox:
			col = box.column( align=True )
			self.draw_keymap_items( col, '3D View', RM_KEYMAP, {'KEYBOARD'}, False )

		row_mesh = box.row()
		row_mesh.prop( self, 'mesh_checkbox', icon='TRIA_DOWN' if self.mesh_checkbox else 'TRIA_RIGHT', icon_only=True, emboss=False )
		row_mesh.label( text='Mesh' )
		if self.mesh_checkbox:
			col = box.column( align=True )
			self.draw_keymap_items( col, 'Mesh', RM_KEYMAP, {'KEYBOARD'}, False )

		row_uv = box.row()
		row_uv.prop( self, 'uv_checkbox', icon='TRIA_DOWN' if self.uv_checkbox else 'TRIA_RIGHT', icon_only=True, emboss=False )
		row_uv.label( text='UV Editor' )
		if self.uv_checkbox:
			col = box.column( align=True )
			self.draw_keymap_items( col, 'UV Editor', RM_KEYMAP, {'KEYBOARD'}, False )

	@staticmethod
	def draw_keymap_items( col, km_name, keymap, map_type, allow_remove=False ):
		kc = bpy.context.window_manager.keyconfigs.user
		km = kc.keymaps.get( km_name )
		kmi_idnames = [ km_tuple[1].idname for km_tuple in keymap ]
		if allow_remove:
			col.context_pointer_set( 'keymap', km )

		kmis = [ kmi for kmi in km.keymap_items if kmi.idname in kmi_idnames and kmi.map_type in map_type ]
		for kmi in kmis:
			rna_keymap_ui.draw_kmi( [], kc, km, kmi, col, 0 )
		

def register():
	bpy.utils.register_class( RMKITPreferences )
	register_keyboard_keymap()


def unregister():
	bpy.utils.unregister_class( RMKITPreferences )
	unregister_keyboard_keymap()