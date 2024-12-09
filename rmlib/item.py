import bpy
import bmesh
import mathutils
from bpy_extras import view3d_utils

def iter_edit_meshes( context, mode_filter=True ):
	#when mode_filter is False, then meshes get yielded even if they're not in editmode
	meshes = set()

	#add active mesh
	ao = context.active_object
	if ao.type == 'MESH':
		meshes.add( ao.data )
		yield rmMesh( ao )
	
	#selected mesh objects
	for o in context.selected_objects:
		if o.type == 'MESH' and ( o.data.is_editmode or not mode_filter ) and o.data not in meshes:
			meshes.add( o.data )
			yield rmMesh( o )

	#editable mesh objects
	for o in context.editable_objects:
		if o.type == 'MESH' and ( o.data.is_editmode or not mode_filter ) and o.data not in meshes:
			meshes.add( o.data )			
			yield rmMesh( o )


def iter_selected_meshes( context, mode_filter=True ):
	#when mode_filter is False, then meshes get yielded even if they're not in editmode
	meshes = set()

	#add active mesh
	ao = context.active_object
	if ao.type == 'MESH':
		meshes.add( ao.data )
		yield rmMesh( ao )
	
	#selected mesh objects
	for o in context.selected_objects:
		if o.type == 'MESH' and ( o.data.is_editmode or not mode_filter ) and o.data not in meshes:
			meshes.add( o.data )
			yield rmMesh( o )


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

	@classmethod
	def from_bmesh( cls, obj, bmesh ):
		rmmesh = cls( obj )
		rmmesh.__bmesh = bmesh
		return rmmesh

	@classmethod
	def from_mos( cls, context, mouse_pos ):
		look_pos = view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_pos )
		look_vec = view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_pos )

		depsgraph = context.evaluated_depsgraph_get()
		depsgraph.update()
		hit, loc, nml, idx, obj, mat = context.scene.ray_cast( depsgraph, look_pos, look_vec )
		if not hit:
			return None

		return cls( obj )

	def GetEvaluated( self, context ):
		#returns read only instance of rmmesh  post modifier and animation and such.
		#returned data is temp and use causes crashes. so be carfull!!!
		depsgraph = context.evaluated_depsgraph_get()
		depsgraph.update()
		eval_obj = self.__object.evaluated_get( depsgraph )
		eval_rmmesh = rmMesh( eval_obj )
		eval_rmmesh.readonly = True
		return eval_rmmesh
	
	def __enter__( self ):
		if self.__bmesh is not None:
			raise RuntimeError( 'bmesh already accessable!!!' )
		if self.__mesh.is_editmode:
			self.__bmesh = bmesh.from_edit_mesh( self.__mesh )
		else:
			self.__bmesh = bmesh.new()
			self.__bmesh.from_mesh( self.__mesh )
		return self
			
	def __exit__( self, type, value, traceback ):
		if self.__bmesh.is_wrapped: #True when this mesh is owned by blender (typically the editmode BMesh).
			bmesh.update_edit_mesh( self.__mesh, loop_triangles=( not self.__readonly ), destructive=( not self.__readonly ) )
			self.__bmesh.select_flush_mode()
		else:
			self.__bmesh.to_mesh( self.__mesh )
			if not self.__readonly:
				self.__bmesh.calc_loop_triangles()   	
				self.__mesh.update()
			self.__bmesh.free()

		self.__bmesh = None
		self.__mesh = self.__object.data

	def iter_uvs( self ):
		if self.__bmesh is None:
			raise RuntimeError( 'bmesh cannot be accessed outside of a "with" context!!!' )
		for uvlayer in self.bmesh.loops.layers.uv.values():
			yield uvlayer

	def clear_selection( self, mode='NONE' ):
		if self.__bmesh is None:
			raise RuntimeError( 'bmesh cannot be accessed outside of a "with" context!!!' )
		if mode == 'NONE':
			for v in self.__bmesh.verts:
				v.select = False
			for e in self.__bmesh.edges:
				e.select = False
			for f in self.__bmesh.faces:
				f.select = False
		elif mode == 'VERT':
			for v in self.__bmesh.verts:
				v.select = False
		elif mode == 'EDGE':
			for e in self.__bmesh.edges:
				e.select = False
		elif mode == 'FACE':
			for f in self.__bmesh.faces:
				f.select = False

	@property
	def active_uv( self ):
		if self.__bmesh is None:
			raise RuntimeError( 'bmesh cannot be accessed outside of a "with" context!!!' )
		return self.bmesh.loops.layers.uv.verify()

	@property
	def object( self ):
		return self.__object

	@property
	def mesh( self ):
		if self.__mesh is None:
			return self.__object.data
		return self.__mesh

	@property
	def bmesh( self ):
		if self.__bmesh is None:
			raise RuntimeError( 'bmesh cannot be accessed outside of a "with" context!!!' )
		return self.__bmesh

	@bmesh.setter
	def bmesh( self, bm ):
		self.__bmesh = bm

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
