import bpy
import bmesh
import mathutils

class rmMesh():
	def __init__( self, object ):
		self.__object = None
		self.__mesh = None
		self.__bmesh = None
		self.__readonly = False
	
		if object.type != 'MESH':
			raise TypeError( 'object arg must be of type MESH!!!' )
		self.__object = object
		self.__mesh = object.data 
	
	@classmethod
	def GetActive( cls, context ):
		ao = context.active_object
		if ao is None:
			return None
		return( cls( ao ) )
	
	def __enter__( self ):
		if self.__mesh.is_editmode:
			self.__bmesh = bmesh.from_edit_mesh( self.__mesh )
		else:
			self.__bmesh = bmesh.new()
			self.__bmesh.from_mesh( self.__mesh )
		return self
			
	def __exit__( self ,type, value, traceback ):
		if self.__bmesh.is_wrapped:
			bmesh.update_edit_mesh( self.__mesh, loop_triangles=( not self.__readonly ), destructive=( not self.__readonly ) )
			self.__bmesh.select_flush_mode()
			print( 'update_edit_mesh :: loop_triangles={} destructive={}'.format( not self.__readonly, not self.__readonly ) )
		else:
			self.__bmesh.to_mesh( self.__mesh )
			if not self.__readonly:
				self.__bmesh.calc_loop_triangles()   	
				self.__mesh.update()
			self.__bmesh.free()		
		self.__bmesh = None

	@property
	def object( self ):
		return self.__object

	@property
	def mesh( self ):
		if self.__mesh is None:
			raise RuntimeError( 'mesh cannot be accessed outside of a "with" context!!!' )
		return self.__mesh

	@property
	def bmesh( self ):
		if self.__bmesh is None:
			raise RuntimeError( 'bmesh cannot be accessed outside of a "with" context!!!' )
		return self.__bmesh

	@property
	def readonly( self ):
		return self.__readonly
	
	@readonly.setter
	def readonly( self, b ):
		if not isinstance( b, bool ):
			raise ValueError( 'readonly property must be typr Boolean!!!' )
		self.__readonly = b

	@property
	def world_transform( self ):
		return mathutils.Matrix( self.__object.matrix_world )
