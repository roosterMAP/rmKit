import bpy, rna_keymap_ui

RM_3DVIEW_KEYMAP = []
RM_MESH_KEYMAP = []
RM_GUI_NAMES = set()

#https://docs.blender.org/api/current/bpy.types.KeyMapItems.html#bpy.types.KeyMapItems

def register_keyboard_keymap():
	kc = bpy.context.window_manager.keyconfigs.addon
	if kc:		
		km_3dview = kc.keymaps.new( name='3D View', space_type='VIEW_3D' )
		km_mesh = kc.keymaps.new( name='Mesh', space_type='EMPTY' )

		#3D VIEW KEYMAPS
		RM_3DVIEW_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_dimensions', 'NONE', 'PRESS' ) ) )
		RM_3DVIEW_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_togglegrid', 'NONE', 'PRESS' ) ) )
		RM_3DVIEW_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_workplane', 'NONE', 'PRESS' ) ) )
		RM_3DVIEW_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_cursor_to_selection', 'NONE', 'PRESS' ) ) )
		RM_3DVIEW_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'view3d.rm_unrotate_relative_to_cursor', 'NONE', 'PRESS' ) ) )
		RM_3DVIEW_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'object.rm_origin_to_cursor', 'NONE', 'PRESS' ) ) )
		RM_3DVIEW_KEYMAP.append( ( km_3dview, km_3dview.keymap_items.new( 'mesh.rm_matclearnup', 'NONE', 'PRESS' ) ) )

		kmi = km_3dview.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_PIE_cursor'
		RM_GUI_NAMES.add( 'VIEW3D_MT_PIE_cursor' )
		RM_3DVIEW_KEYMAP.append( ( km_3dview, kmi ) )

		kmi = km_3dview.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'OBJECT_MT_rm_screenreflect'
		RM_GUI_NAMES.add( 'OBJECT_MT_rm_screenreflect' )
		RM_3DVIEW_KEYMAP.append( ( km_3dview, kmi ) )

		kmi = km_3dview.keymap_items.new( 'mesh.rm_changemodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'FACE'
		RM_3DVIEW_KEYMAP.append( ( km_3dview, kmi ) )

		kmi = km_3dview.keymap_items.new( 'mesh.rm_changemodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'EDGE'
		RM_3DVIEW_KEYMAP.append( ( km_3dview, kmi ) )

		kmi = km_3dview.keymap_items.new( 'mesh.rm_changemodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'VERT'
		RM_3DVIEW_KEYMAP.append( ( km_3dview, kmi ) )


		#MESH KEYMAPS		
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_unbevel', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_arcadjust', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_connectedge', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_contextbevel', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_createtube', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_extend', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_grabapplymat', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_grabapplyvcolor', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_quickmaterial', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_radialalign', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_loop', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_ring', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_polypatch', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_invertcontinuous', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_targetweld', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_thicken', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_knifescreenmenu', 'NONE', 'PRESS' ) ) )
		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_extrudealongpath', 'NONE', 'PRESS' ) ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_remove', 'NONE', 'PRESS' )
		kmi.properties.reduce_mode = 'DIS'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_remove', 'NONE', 'PRESS' )
		kmi.properties.reduce_mode = 'COL'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_remove', 'NONE', 'PRESS' )
		kmi.properties.reduce_mode = 'POP'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_remove', 'NONE', 'PRESS' )
		kmi.properties.reduce_mode = 'DEL'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )
		
		kmi = km_mesh.keymap_items.new( 'mesh.rm_copy', 'NONE', 'PRESS' )
		kmi.properties.cut = True
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_copy', 'NONE', 'PRESS' )
		kmi.properties.cut = False
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_paste', 'NONE', 'PRESS' )
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_convertmodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'FACE'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_convertmodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'EDGE'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_convertmodeto', 'NONE', 'PRESS' )
		kmi.properties.mode_to = 'VERT'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_continuous', 'NONE', 'PRESS' )
		kmi.properties.mode = 'remove'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_continuous', 'NONE', 'PRESS' )
		kmi.properties.mode = 'add'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'mesh.rm_continuous', 'NONE', 'PRESS' )
		kmi.properties.mode = 'set'
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_PIE_movetofurthest'
		RM_GUI_NAMES.add( 'VIEW3D_MT_PIE_movetofurthest' )
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_PIE_setedgeweight_crease'
		RM_GUI_NAMES.add( 'VIEW3D_MT_PIE_setedgeweight_crease' )
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu_pie', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_PIE_quicklineardeform'
		RM_GUI_NAMES.add( 'VIEW3D_MT_PIE_quicklineardeform' )
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

		RM_MESH_KEYMAP.append( ( km_mesh, km_mesh.keymap_items.new( 'mesh.rm_falloff', 'NONE', 'PRESS' ) ) )

		kmi = km_mesh.keymap_items.new( 'wm.call_menu', 'NONE', 'PRESS' )
		kmi.properties.name = 'VIEW3D_MT_quickbool'
		RM_GUI_NAMES.add( 'VIEW3D_MT_quickbool' )
		RM_MESH_KEYMAP.append( ( km_mesh, kmi ) )

def unregister_keyboard_keymap():
	for km, kmi in RM_3DVIEW_KEYMAP:
		km.keymap_items.remove( kmi )
	for km, kmi in RM_MESH_KEYMAP:
		km.keymap_items.remove( kmi )
	RM_3DVIEW_KEYMAP.clear()
	RM_MESH_KEYMAP.clear()
	RM_GUI_NAMES.clear()


def set_basepath(self, value):	
	if '$ObjectName' not in value:
		return
	self["em_basepath"] = value
	

def get_basepath(self):
	try:
		return self["em_basepath"]
	except KeyError:
		return '$SceneDir\\$SceneName_$ObjectName'


class RMKITPreferences( bpy.types.AddonPreferences ):
	bl_idname = __package__

	export_manager_basepath: bpy.props.StringProperty(name='BasePath', default='$SceneDir\\$SceneName_$ObjectName', get=get_basepath, set=set_basepath)

	v3d_checkbox: bpy.props.BoolProperty( name="3D View", default=False )
	mesh_checkbox: bpy.props.BoolProperty( name="Mesh", default=False )

	def draw( self, context ):
		layout = self.layout

		box = layout.box()

		row_view3d = box.row()
		row_view3d.prop( self, 'v3d_checkbox', icon='TRIA_DOWN' if self.v3d_checkbox else 'TRIA_RIGHT', icon_only=True, emboss=False )
		row_view3d.label( text='3D View' )
		if self.v3d_checkbox:
			col = box.column( align=True )
			self.draw_keymap_items( col, '3D View', RM_3DVIEW_KEYMAP, {'ACTIONZONE', 'KEYBOARD', 'MOUSE', 'NDOF'}, False )

		row_mesh = box.row()
		row_mesh.prop( self, 'mesh_checkbox', icon='TRIA_DOWN' if self.mesh_checkbox else 'TRIA_RIGHT', icon_only=True, emboss=False )
		row_mesh.label( text='Mesh' )
		if self.mesh_checkbox:
			col = box.column( align=True )
			self.draw_keymap_items( col, 'Mesh', RM_MESH_KEYMAP, {'ACTIONZONE', 'KEYBOARD', 'MOUSE', 'NDOF'}, False )


	@staticmethod
	def draw_keymap_items( col, km_name, keymap, map_type, allow_remove=False ):
		kc = bpy.context.window_manager.keyconfigs.user
		km = kc.keymaps.get( km_name )
		kmi_idnames = [ km_tuple[1].idname for km_tuple in keymap ]
		if allow_remove:
			col.context_pointer_set( 'keymap', km )

		for kmi in km.keymap_items:
			if kmi.idname in kmi_idnames and kmi.map_type in map_type:
				if kmi.idname == 'wm.call_menu_pie' or kmi.idname == 'wm.call_menu':
					if kmi.properties.name not in RM_GUI_NAMES:
						continue
				rna_keymap_ui.draw_kmi( ['ADDON', 'USER', 'DEFAULT'], kc, km, kmi, col, 0 )
		

def register():
	bpy.utils.register_class( RMKITPreferences )
	register_keyboard_keymap()


def unregister():
	bpy.utils.unregister_class( RMKITPreferences )
	unregister_keyboard_keymap()