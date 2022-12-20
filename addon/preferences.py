import bpy, rna_keymap_ui

UTILS_KEYMAP = []
SELECTION_KEYMAP = []

#https://docs.blender.org/api/current/bpy.types.KeyMapItems.html#bpy.types.KeyMapItems

def register_keyboard_keymap():
	kc = bpy.context.window_manager.keyconfigs.addon
	if kc:
		km = kc.keymaps.new( name='Mesh', space_type='EMPTY' )
		UTILS_KEYMAP.append( ( km, km.keymap_items.new( 'mesh.rm_copy', 'NONE', 'PRESS' ) ) )
		UTILS_KEYMAP.append( ( km, km.keymap_items.new( 'mesh.rm_paste', 'NONE', 'PRESS' ) ) )
		UTILS_KEYMAP.append( ( km, km.keymap_items.new( 'view3d.rm_togglegrid', 'NONE', 'PRESS' ) ) )
		UTILS_KEYMAP.append( ( km, km.keymap_items.new( 'view3d.rm_workplane', 'NONE', 'PRESS' ) ) )
		UTILS_KEYMAP.append( ( km, km.keymap_items.new( 'view3d.rm_cursor_to_selection', 'NONE', 'PRESS' ) ) )
		UTILS_KEYMAP.append( ( km, km.keymap_items.new( 'view3d.rm_unrotate_relative_to_cursor', 'NONE', 'PRESS' ) ) )
		UTILS_KEYMAP.append( ( km, km.keymap_items.new( 'view3d.rm_origin_to_cursor', 'NONE', 'PRESS' ) ) )


def unregister_keyboard_keymap():
	for km, kmi in UTILS_KEYMAP:
		km.keymap_items.remove( kmi )
	UTILS_KEYMAP.clear()

	for km, kmi in SELECTION_KEYMAP:
		km.keymap_items.remove( kmi )
	SELECTION_KEYMAP.clear()


class RMKITPreferences( bpy.types.AddonPreferences ):
	bl_idname = 'rmKit'

	utils_checkbox: bpy.props.BoolProperty( name="Utilities", default=True )
	sel_checkbox: bpy.props.BoolProperty( name="Selection", default=True )

	def draw( self, context ):
		layout = self.layout
		box = layout.box()
		
		row_utils = box.row()
		row_utils.prop( self, 'utils_checkbox', icon='TRIA_DOWN' if self.utils_checkbox else 'TRIA_RIGHT', icon_only=True, emboss=False )
		row_utils.label( text='Utilities' )
		if self.utils_checkbox:
			col = box.column( align=True )
			self.draw_keymap_items( col, 'Mesh', UTILS_KEYMAP, {'KEYBOARD'}, False )

		'''
		sel_utils = box.row()
		sel_utils.prop( self, 'sel_checkbox', icon='TRIA_DOWN' if self.sel_checkbox else 'TRIA_RIGHT', icon_only=True, emboss=False )
		sel_utils.label( text='Selection' )
		if self.sel_checkbox:
			col = box.column( align=True )
			self.draw_keymap_items( col, 'Mesh', SELECTION_KEYMAP, {'KEYBOARD'}, False )
		'''

	@staticmethod
	def draw_keymap_items( col, km_name, keymap, map_type, allow_remove=False ):
		kc = bpy.context.window_manager.keyconfigs.user
		km = kc.keymaps.get( km_name )
		kmi_idnames = [ km_tuple[1].idname for km_tuple in keymap ]
		if allow_remove:
			col.context_pointer_set( 'keymap', km )

		kmis = [ kmi for kmi in km.keymap_items if kmi.idname in kmi_idnames and kmi.map_type in map_type ]
		for kmi in kmis:
			rna_keymap_ui.draw_kmi( ['ADDON'], kc, km, kmi, col, 0 )
		

def register():
	bpy.utils.register_class( RMKITPreferences )
	register_keyboard_keymap()


def unregister():
	bpy.utils.unregister_class( RMKITPreferences )
	unregister_keyboard_keymap()