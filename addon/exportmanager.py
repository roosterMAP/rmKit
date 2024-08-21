import bpy
import random, os, string

HASH_KEY = 'itemexporthash'
EXPORT_OBJECT_NAMES = {}
ENABLE_NAMING_COLLISION = False
ENABLE_INDEX_UPDATE = True
ENABLE_BASEPATH_UPDATE = True


bpy.app.handlers.depsgraph_update_post.clear()


def get_export_object_names( scene ):
	export_object_names = {}
	for obj in scene.objects:
		hash = obj.get( HASH_KEY )
		if hash:
			export_object_names[hash] = obj.name
	return export_object_names
	

def sync_scene_with_export_manager( scene ):
	#ensure all hashes on object are unique
	hash_set = set()
	for obj in scene.objects:
		hash = obj.get( HASH_KEY )
		if hash and hash in hash_set:
			obj[HASH_KEY] = random.getrandbits( 16 )
		hash_set.add( hash )
	
	#get updated dicts of hashes to names
	global EXPORT_OBJECT_NAMES
	current_export_object_names = get_export_object_names( scene )
	
	#build list of export items
	new_export_list = []			
	for export_item in scene.em_propertygroup.export_items:		
		if export_item.hash in current_export_object_names:			
			new_export_list.append( ( current_export_object_names[export_item.hash], export_item.hash, export_item.enabled ) )
			del current_export_object_names[export_item.hash]
			
	#add scene items has hashed but were not already in the export manager list
	for hash, name in current_export_object_names.items():
			new_export_list.append( ( name, hash, True ) )		
			
	#clear export manager list
	scene.em_propertygroup.export_items.clear()
	
	#add to export manager list
	for tuple_data in new_export_list:
		export_item = scene.em_propertygroup.export_items.add()
		export_item.name = tuple_data[0]
		export_item.hash = tuple_data[1]
		export_item.enabled = tuple_data[2]
		
		
def sync_active_selection_with_export_manager( scene ):
	hash = bpy.context.active_object.get( HASH_KEY )
	if hash:	
		for i, export_item in enumerate( scene.em_propertygroup.export_items ):
			if export_item.hash == hash:
				scene.em_propertygroup.active_item_index = i
				return
		
	scene.em_propertygroup.active_item_index = -1


def on_depsgraph_update( scene, depsgraph ):
	global EXPORT_OBJECT_NAMES  

	for update in depsgraph.updates:
		o = update.id
		if type(o) is bpy.types.Object:
			sync_scene_with_export_manager( scene )
		elif type(o) is bpy.types.Scene:	
			sync_active_selection_with_export_manager( scene )
		break


def get_name(self):
	try:
		return self["name"]
	except KeyError:
		return ''


def set_name(self, value):	
	if len( value.strip() ) == 0:
		return

	collision_found = False
	
	name = getattr( self, "name" )
	if name != '':
		#check for collision
		try:
			object = bpy.data.objects[value]
			collision_found = True
		except KeyError:		
			object = bpy.data.objects[name]
			object.name = value
	
	global ENABLE_NAMING_COLLISION
	if not collision_found or ENABLE_NAMING_COLLISION:
		self["name"] = value
		
		
def index_update( self, context ):
	global ENABLE_INDEX_UPDATE
	if not ENABLE_INDEX_UPDATE:
		return
	
	active_item_index = getattr( self, "active_item_index" )
	export_item_count = len( getattr( self, "export_items" ) )
	if context.mode == 'OBJECT' and active_item_index >= 0 and active_item_index < export_item_count:
		obj_name = self['export_items'][active_item_index]["name"]
		obj = context.scene.objects[obj_name]
		view_layer = context.view_layer
		for o in view_layer.objects:
			o.select_set( False )
		obj.select_set(True)
		view_layer.objects.active = obj
		
	
# this is where we store all the item properties
class EM_PropertyGroupItem(bpy.types.PropertyGroup):
	enabled : bpy.props.BoolProperty( name = "Enabled", default=True )    
	name : bpy.props.StringProperty( name="Name", get=get_name, set=set_name )
	hash : bpy.props.IntProperty( name='Hash', default=0 )


class EM_PropertyGroup(bpy.types.PropertyGroup):
	export_items : bpy.props.CollectionProperty(type=EM_PropertyGroupItem, name="ExportItems" )
	active_item_index : bpy.props.IntProperty(name="Active Item", default=-1, update=lambda self, context : index_update( self, context ) )


class EXPORTMANAGER_UL_item_list( bpy.types.UIList ):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index ):
		column_enabled = layout.column()
		column_enabled.prop(item, "enabled",  text = "")

		column_name = layout.column()
		column_name.prop(item, "name",  text = "")
		column_name.scale_x = 100

		column_export = layout.column()
		column_export.operator("object.em_export_object", text="Export").item_index = index
		if index < len( context.scene.em_core.export_items ):
			column_export.enabled = context.scene.em_core.export_items[index].enabled
			column_export.scale_x = 20


class UIListPanelExportManager(bpy.types.Panel):
	"""Creates a Panel in the Object properties window"""
	bl_parent_id = "VIEW3D_PT_RMKIT_PARENT"
	bl_label = "Export Manager"
	bl_idname = "OBJECT_PT_ui_export_manager"
	bl_region_type = "UI"
	bl_space_type = "VIEW_3D"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, context):
		basedir = bpy.data.filepath
		if not basedir:
			row = self.layout.row()
			row.label(text="Unsaved Scene")
			row.operator('view.em_export_settings', text='', icon='SETTINGS')
			return

		row = self.layout.row()
		row.operator( "object.em_export_enabled_object" )
		row.operator('view.em_export_settings', text='', icon='SETTINGS')
		self.layout.template_list(
				"EXPORTMANAGER_UL_item_list", 
				"", 
				context.scene.em_propertygroup,
				"export_items",
				context.scene.em_propertygroup,
				"active_item_index",
				type='DEFAULT'      
			)
		
		row = self.layout.row()
		row.operator( "object.em_add_export_object" )
		row.operator( "object.em_remove_export_object" )
		
		
def already_exists( export_items, name ):
	for item in export_items:
		if name.strip() == item.name:
			return True
	return False
		

class OBJECT_OT_AddExportObject(bpy.types.Operator):
	bl_idname = "object.em_add_export_object"
	bl_label = "Add"
	bl_options = set()

	def execute(self, context):
		export_items = context.scene.em_propertygroup.export_items

		objects = bpy.context.selected_objects					
		if not len( objects ):   
			self.report({'ERROR'},  "No Objects Selected" )
			return {'FINISHED'}
		
		for obj in objects:
			export_item_name = obj.name
			if already_exists( export_items, export_item_name ):
				self.report({'ERROR'},  "Export Item {} already listed in Export List!!!".format( export_item_name ) )  
				return {'FINISHED'}
			export_item = export_items.add()
			export_item.name = export_item_name
			obj[HASH_KEY] = random.getrandbits( 16 )
			export_item.hash = obj[HASH_KEY]
			
		sync_scene_with_export_manager( context.scene )
				
		context.scene.em_propertygroup.active_item_index = len(export_items) - 1
		return {'FINISHED'}
	

class OBJECT_OT_RemoveExportObject(bpy.types.Operator):
	bl_idname = "object.em_remove_export_object"
	bl_label = "Remove"
	bl_options = set()

	@classmethod
	def poll(cls, context):
		active_index = context.scene.em_propertygroup.active_item_index
		item_count = len( context.scene.em_propertygroup.export_items )
		return active_index >= 0 and item_count > 0 and active_index < item_count

	def execute(self, context):
		current_index = context.scene.em_propertygroup.active_item_index
		export_items = context.scene.em_propertygroup.export_items
		remove_item = context.scene.objects[export_items[current_index].name]
		if remove_item.get( HASH_KEY ):
			del remove_item[HASH_KEY]
		export_items.remove(current_index)
		context.scene.em_propertygroup.active_item_index -= 1
		if context.scene.em_propertygroup.active_item_index < 0:
			context.scene.em_propertygroup.active_item_index = 0
		if len( context.scene.em_propertygroup.export_items ) == 0:
			context.scene.em_propertygroup.active_item_index = -1
			
		sync_scene_with_export_manager( context.scene )
			
		return {'FINISHED'}  
	
	
EXPORT_ERROR_CODE  = {
	0 : 'Success',
	1 : 'Invalid Dir',
	2 : 'File(\'s) not Writable',
	3 : 'Invalid character is export filename',
}
	

def export_path( context, object ):
	basePath = bpy.context.preferences.addons[__name__].preferences.export_manager_basepath
	
	filepath = bpy.data.filepath
	filename = os.path.basename( filepath )
	
	directory = os.path.dirname( filepath )
	
	exportpath = basePath.replace( '$SceneDir', directory )
	exportpath = exportpath.replace( '$SceneName', os.path.splitext( filename )[0] )
	exportpath = exportpath.replace( '$ObjectName', object.name )
		
	directory = os.path.dirname( exportpath )
	
	if not os.path.exists(directory):
		os.makedirs(directory)
	if not os.path.isdir(directory):
		return ( 1, '' )
	
	if os.path.isfile( exportpath ):
		if not os.access(exportpath, os.W_OK):
			return ( 2, '' )
		
	filename = os.path.basename( exportpath )
	
	valid_chars = "-_(){}{}".format( string.ascii_letters, string.digits )
	for c in filename.lower():
		if c not in valid_chars:
			return ( 3, '' )
	
	return ( 0, exportpath.replace( '/', '\\' ) + '.fbx' )
	

def export_object( context, export_object, exportpath ):
	selected_objects = bpy.context.selected_objects

	for obj in selected_objects:
		obj.select_set( False )

	for obj in export_object.children_recursive:
		obj.select_set( True )

	bpy.ops.export_scene.fbx( filepath=exportpath, use_selection=True )

	for obj in bpy.context.selected_objects:
		obj.select_set( False )
	for obj in selected_objects:
		obj.select_set( True )


class OBJECT_OT_ExportObject(bpy.types.Operator):
	bl_idname = "object.em_export_object"
	bl_label = "Export"
	bl_options = set()

	item_index : bpy.props.IntProperty( name="Index", default=0 )

	@classmethod
	def poll(cls, context):
		return True

	def execute(self, context):
		export_items = context.scene.em_propertygroup.export_items
		target_hash = export_items[self.item_index].hash
		for object in context.scene.objects:
			object_hash = object.get( HASH_KEY )
			if not object_hash:
				continue
			if target_hash == object_hash:
				error_code, exportpath = export_path( context, object )
				if error_code > 0:
					self.report({'ERROR'},  EXPORT_ERROR_CODE[error_code] )
					break
				export_object( context, object, exportpath )					
				return {'FINISHED'}
				
		return {'FINISHED'}
	
	
class OBJECT_OT_ExportEnabledObject(bpy.types.Operator):
	bl_idname = "object.em_export_enabled_object"
	bl_label = "Export Checked"
	bl_options = set()

	@classmethod
	def poll(cls, context):
		return True

	def execute(self, context):
		for i, export_item in enumerate( context.scene.em_propertygroup.export_items ):
			if not export_item.enabled:
				continue
			bpy.ops.object.em_export_object( item_index=i )

		return {'FINISHED'}
	
	
class OBJECT_OT_ExportManagerSettings(bpy.types.Operator):
	bl_idname = "view.em_export_settings"
	bl_label = "Export Manager Settings"
	bl_options = { 'UNDO' }

	@classmethod
	def poll(cls, context):
		return True

	def invoke(self, context, event):
		return context.window_manager.invoke_popup(self, width=512)
		
	def draw(self, context):
		packagename = __package__[:__package__.index( '.' )]
		self.layout.prop( context.preferences.addons[packagename].preferences, 'export_manager_basepath' )
				
		box = self.layout.box()
		box.label( text='PathStrings: ' )
		row = box.row()
		row.separator( factor=3.0 )
		col = row.column()
		col.label( text='$SceneDir' )
		col.label( text='$SceneName' )
		col.label( text='$ObjectName' )

	def execute(self, context):
		return {'FINISHED'}


def register():
	bpy.utils.register_class( EM_PropertyGroupItem )
	bpy.utils.register_class( EM_PropertyGroup )
	bpy.utils.register_class( OBJECT_OT_AddExportObject )
	bpy.utils.register_class( OBJECT_OT_RemoveExportObject )
	bpy.utils.register_class(UIListPanelExportManager)
	bpy.utils.register_class(EXPORTMANAGER_UL_item_list)
	bpy.utils.register_class(OBJECT_OT_ExportObject)
	bpy.utils.register_class(OBJECT_OT_ExportEnabledObject)
	bpy.utils.register_class(OBJECT_OT_ExportManagerSettings)
	
	bpy.types.Scene.em_propertygroup = bpy.props.PointerProperty(type=EM_PropertyGroup)
	bpy.types.Object.itemexporthash = bpy.props.IntProperty( name='ExportHash' )

	bpy.app.handlers.depsgraph_update_post.append( on_depsgraph_update )


def unregister():	
	bpy.utils.unregister_class( EM_PropertyGroupItem )
	bpy.utils.unregister_class( EM_PropertyGroup )
	bpy.utils.unregister_class( OBJECT_OT_AddExportObject )
	bpy.utils.unregister_class( OBJECT_OT_RemoveExportObject )
	bpy.utils.unregister_class(UIListPanelExportManager)
	bpy.utils.unregister_class(EXPORTMANAGER_UL_item_list)
	bpy.utils.unregister_class(OBJECT_OT_ExportObject)
	bpy.utils.unregister_class(OBJECT_OT_ExportEnabledObject)
	bpy.utils.unregister_class(OBJECT_OT_ExportManagerSettings)

	del bpy.types.Scene.em_propertygroup
	del bpy.types.Scene.itemexporthash

	bpy.app.handlers.depsgraph_update_post.clear()