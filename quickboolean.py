import bpy
import rmlib

BOOL_COLLECTION_KEY = 'rcl'
BOOL_COLLECTIONTYPE_KEY = 'rct'
BOOL_PARENT_KEY = 'rbp'
BOOL_CHILD_KEY = 'rbc'
BOOL_DUO_KEY = 'rdo'

class BoolCollectionManager():
	def __init__( self, scene ):
		self.__scene = scene
		self.__rootcollection = self.GetRootCollection()
		
	def GetRootCollection( self ):
		for c in self.__scene.collection.children:
			if BOOL_COLLECTION_KEY in c.keys() and c[BOOL_COLLECTION_KEY] == 'root':
				return c
		c = bpy.data.collections.new( 'RM Boolean' )
		c[BOOL_COLLECTION_KEY] = 'root'
		self.__scene.collection.children.link( c )
		return c
		
	def ClearObjectFromCollections( self, obj ):
		for c in obj.users_collection:
			c.objects.unlink( obj )
		self.__scene.collection.objects.link( obj )
		obj.display_type = 'TEXTURED'
					
	def AddObjectToCollection( self, obj, parent, type ):
		for c in obj.users_collection:
			c.objects.unlink( obj )
		for c in parent.users_collection:
			c.objects.link( obj )
		obj.parent = parent
		obj.display_type = 'WIRE'
		for c in self.__rootcollection.children:
			try:
				if c[BOOL_COLLECTION_KEY] == parent.name_full and c[BOOL_COLLECTIONTYPE_KEY] == type:
					c.objects.link( obj )
					obj.display_type = 'WIRE'
					return True
			except KeyError:
				continue

		#fail case
		for c in obj.users_collection:
			c.objects.unlink( obj )
		obj.display_type = 'TEXTURED'
		obj.parent = None
		return False
	
	def CreateCollection( self, obj, parent, type ):
		c = bpy.data.collections.new( '{}_{}_{}'.format( BOOL_COLLECTION_KEY, parent.name, type ) )
		c[BOOL_COLLECTION_KEY] = parent.name_full
		c[BOOL_COLLECTIONTYPE_KEY] = type
		self.__rootcollection.children.link( c )
		
	def GetCollection( self, parent, type ):
		for c in self.__rootcollection.children:
			try:
				if c[BOOL_COLLECTION_KEY] == parent.name_full and c[BOOL_COLLECTIONTYPE_KEY] == type:
					return c
			except KeyError:
				continue
		return None
	
	@property
	def root_collection( self ):
		return self.__rootcollection
	
	
class DUO_Wrapper():
	def __init__( self, obj ):
		self.__duo = obj
		
	@staticmethod
	def CreateDriveUnionObj( parent, type ):		
		mesh = bpy.data.meshes.new( '{}_mesh'.format( BOOL_DUO_KEY ) )
		duo_obj = bpy.data.objects.new( BOOL_DUO_KEY, mesh )
		#duo_obj.parent = parent
		
		collections_mod = BoolCollectionManager( parent.users_scene[0] )
		collections_mod.root_collection.objects.link( duo_obj )		
		#parent.users_collection[0].objects.link( duo_obj )
		
		duo_obj[BOOL_DUO_KEY] = parent.name_full
		m = duo_obj.modifiers.new( name='{}_{}'.format( BOOL_DUO_KEY, type ), type='BOOLEAN' )
		m.operation = 'UNION'
		m.operand_type = 'COLLECTION'
		duo_obj.hide_select = True
		duo_obj.hide_viewport = True
		duo_obj.hide_render = True
		return duo_obj
		
	@classmethod
	def InitDUO( cls, parent, type ):		
		#find boolean obj if available
		for m in parent.modifiers:
			if m.type == 'BOOLEAN' and m.operation == type and m.operand_type == 'COLLECTION' and m.object is None:
				m.object = DUO_Wrapper.CreateDriveUnionObj( parent, type )
				return cls( m.object )
				
		#create drive union object and add to parent
		duo = DUO_Wrapper.CreateDriveUnionObj( parent, type )
		m = parent.modifiers.new( name='{}_{}'.format( BOOL_DUO_KEY, type ), type='BOOLEAN' )
		m.object = duo
		m.operation = type
		
		return cls( duo )
		
	def SetCollection( self, collection, type ):
		for m in self.__duo.modifiers:
			if m.type == 'BOOLEAN' and m.name.startswith( '{}_{}'.format( BOOL_DUO_KEY, type ) ) and m.operand_type == 'COLLECTION':
				m.collection = collection
				return True
		return False
		

def MakeParent( obj ):
	if obj.type != 'MESH':
		raise TypeError
	obj[BOOL_PARENT_KEY] = 'parent'	
	
	
def IsParent( obj ):
	if not obj.type == 'MESH':
		return False
	return BOOL_PARENT_KEY in obj.keys()


def MakeChild( obj, parent ):
	if obj.type != 'MESH':
		raise TypeError
	obj[BOOL_CHILD_KEY] = parent.name_full
	
	
def IsChild( obj ):
	if not obj.type == 'MESH':
		return False
	return BOOL_CHILD_KEY in obj.keys()
		
		
def AddBoolean( obj, parent, type ):
	if IsParent( obj ):
		return False

	collections_mod = BoolCollectionManager( obj.users_scene[0] )
	
	if IsChild( obj ):
		collections_mod.ClearObjectFromCollections( obj )
	else:
		MakeChild( obj, parent )
		
	if not collections_mod.AddObjectToCollection( obj, parent, type ):
		collections_mod.CreateCollection( obj, parent, type )
		collections_mod.AddObjectToCollection( obj, parent, type )
		
	c = collections_mod.GetCollection( parent, type )
	duo = DUO_Wrapper.InitDUO( parent, type )
	duo.SetCollection( c, type )

	return True
	

def CleanupQuickBool( context ):
	collections_mod = BoolCollectionManager( context.scene )
	#remove empty collections
	for c in collections_mod.root_collection.children:
		for o in list( c.objects ):
			if len( o.data.polygons ) < 1:
				bpy.data.objects.remove( o, do_unlink=True )
		if len( c.objects ) == 0:
			bpy.data.collections.remove( c )

	#remove duo objects with missing collections or missing parents
	for o in list( collections_mod.root_collection.objects ):
		#missing parent
		try:
			bpy.data.objects[o[BOOL_DUO_KEY]] #get parent by name
		except LookupError:
			print( 'failed to get parent by name {}'.format( o[BOOL_DUO_KEY] ) )
			bpy.data.objects.remove( o, do_unlink=True )
			continue

		#missing collection
		for m in list( o.modifiers ):
			if m.type == 'BOOLEAN':
				if m.collection is None:
					o.modifiers.remove( m )

		#duo has no mods
		if len( o.modifiers ) < 1:
			bpy.data.objects.remove( o, do_unlink=True )

		
class MESH_OT_quickbooladd( bpy.types.Operator ):
	bl_idname = 'view3d.rm_quickbooladd'
	bl_label = 'Add'
	bl_options = { 'UNDO' }

	operation: bpy.props.EnumProperty(
		items=[ ( 'UNION', "Union", "", 1 ),
				( 'DIFFERENCE', "Subtract", "", 2 ),
				( 'INTERSECT', "Intersect", "", 3 ) ],
		name="Boolean Type",
		default='UNION'
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.mode == 'OBJECT' )
		
	def execute( self, context ):
		#make active object a parrent
		obj_active = context.active_object
		if not IsParent( obj_active ):
			MakeParent( obj_active )
			
		#all other selected objects are drive meshes
		for o in context.selected_objects:
			if o.type != 'MESH' or o == obj_active:
				continue
			AddBoolean( o, obj_active, self.operation )

		CleanupQuickBool( context )
				
		return { 'FINISHED' }


class MESH_OT_quickboolclear( bpy.types.Operator ):
	bl_idname = 'view3d.rm_quickboolclear'
	bl_label = 'Remove'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.mode == 'OBJECT' )
		
	def execute( self, context ):
		#make active object a parent
		obj_active = context.active_object
		if IsParent( obj_active ):
			for m in list( obj_active.modifiers ):
				if m.type == 'BOOLEAN' and m.name.startswith( BOOL_DUO_KEY ) and m.object is not None:
					duo = DUO_Wrapper( m.object )
					for o in list( duo.collection.objects ):
						duo.collection.objects.unlink( o )
						context.scene.collection.objects.link( o )
						o.display_type = 'TEXTURED'
						del o[BOOL_CHILD_KEY]
					bpy.data.objects.remove( m.object, do_unlink=True )
				obj_active.modifiers.remove( m )
			del obj_active[BOOL_PARENT_KEY]
		elif IsChild( obj_active ):
			collections_mod = BoolCollectionManager( context.scene )
			collections_mod.ClearObjectFromCollections( obj_active )
			del obj_active[BOOL_CHILD_KEY]
		else:
			return { 'FINISHED' }

		CleanupQuickBool( context )
				
		return { 'FINISHED' }


class VIEW3D_MT_quickbool( bpy.types.Menu ):
	bl_idname = 'VIEW3D_MT_quickbool'
	bl_label = 'Quick Boolean GUI'

	def draw( self, context ):
		layout = self.layout

		if context.active_object.type == 'MESH' and context.mode == 'EDIT_MESH':
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if sel_mode[2]:
				layout.operator( 'mesh.intersect_boolean', text='Union', icon="SELECT_EXTEND" ).operation = 'UNION'
				layout.operator( 'mesh.intersect_boolean', text='Difference', icon="SELECT_SUBTRACT" ).operation = 'DIFFERENCE'
				layout.operator( 'mesh.intersect_boolean', text='Intersect', icon="SELECT_INTERSECT" ).operation = 'INTERSECT'
				layout.operator( 'mesh.intersect', text='Slice', icon="SELECT_DIFFERENCE" ).mode = 'SELECT_UNSELECT'


def register():
	bpy.utils.register_class( VIEW3D_MT_quickbool )
	
	
def unregister():
	bpy.utils.unregister_class( VIEW3D_MT_quickbool )