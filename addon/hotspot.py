import rmKit.rmlib as rmlib
import bpy, bmesh, mathutils
import os, random, math

class Bounds2d():
	def __init__( self, points ):
		self.__min = mathutils.Vector( ( 0.0, 0.0 ) )
		self.__max = mathutils.Vector( ( 1.0, 1.0 ) )
		for p in points:
			for i in range( 2 ):
				if p[i] <= self.__min[i]:
					self.__min[i] = p[i]
				if p[i] >= self.__max[i]:
					self.__max[i] = p[i]

	@classmethod
	def from_verts( cls, verts ):
		#build bounds from list of BMVerts
		poslist = [ v.co.copy() for v in verts ]
		return cls( poslist )

	@property
	def min( self ):
		return self.__min

	@property
	def max( self ):
		return self.__max

	@property
	def width( self ):
		return self.__max[0] - self.__min[0]

	@property
	def height( self ):
		return self.__max[1] - self.__min[0]

	@property
	def aspect( self ):
		return self.width / self.height

	@property
	def center( self ):
		return ( self.__min + self.__max ) * 0.5

	@property
	def horizontal( self ):
		#returns true if self is wider than it is tall
		return self.width > self.height

	@property
	def corners( self ):
		#return corner coords of self in (u,v) domain
		return [ self.__min, mathutils.Vector( ( self.__min[1], self.__max[0] ) ), self.__max, mathutils.Vector( ( self.__max[1], self.__min[0] ) ) ]

	def inside( self, point ):
		#test if point is inside self
		return ( point[0] > self.min[0] and point[1] > self.min[1] and point[0] < self.max[0] and point[1] < self.max[1] )

	def overlapping( self, bounds ):
		#test if bounds overlapps self
		return not ( self.__max[0] < bounds.__min[0] or self.__min[0] > bounds.max[0] or self.__max[1] < bounds.__min[1] or self.__min[1] > bounds.max[1] )

	def transform( self, other ):
		#compute the 3x3 matrix that transforms bound 'other' to self
		trans_mat = mathutils.Matrix.Identity( 3 )
		trans_mat[2] = self.center - other.center
		
		trans_mat_inverse = mathutils.Matrix.Identity( 3 )
		trans_mat_inverse[2] = other.center - self.center

		rot_mat = mathutils.Matrix.Identity( 3 )
		if self.horizontal != other.horizontal:
			rot_mat[0][0] = math.cos( math.pi  / 2.0 )
			rot_mat[1][0] = math.sin( math.pi  / 2.0 ) * -1.0
			rot_mat[0][1] = math.cos( math.pi  / 2.0 )
			rot_mat[1][1] = math.sin( math.pi  / 2.0 )

		return trans_mat_inverse @ rot_mat @ trans_mat


class Hotspot():
	def __init__( self, bounds2d_list, **kwargs ):
		self.__name = ''
		self.__td = 512.0 #texels per meter
		self.__data = [ bounds for bounds in bounds2d_list ]
		for key, value in kwargs.items():
			if key == 'name':
				self.__name = value
			elif key == 'texel_density':
				self.__td = value

	@classmethod
	def from_bmesh( cls, context ):
		#load hotspot from subrect_atlas
		obj = context.scene.subrect_atlas
		me = obj.data
		bm = bmesh.new()
		bm.from_mesh( me )
		
		boundslist = []
		uv_layer = bm.loops.layers.uv.verify()
		for f in bm.faces:
			uvs = [ mathutils.Vector( l[uv_layer].uv ) for l in f.loops ]
			boundslist.append( Bounds2d( uvs ) )
		mat_name = obj.data.materials[bm.faces[0].material_index].name_full

		return cls( boundslist, name=mat_name )

	@classmethod
	def from_file( cls ):
		#load hotspot from .rect file
		return cls

	def save_bmesh( self, context ):
		#save hotspot to subrect_atlas object
		obj = context.scene.subrect_atlas
		rmmesh = rmlib.rmMesh( obj )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			del_faces = list( rmmesh.bmesh.faces )
			
			for bounds in self.__data:
				verts = []
				corners = bounds.corners
				for c in corners:
					verts.append( rmmesh.bmesh.verts.new( c.to_3d() ) )
				f = rmmesh.bmesh.faces.new( verts, example=del_faces[0] )
				for i, l in enumerate( f.loops ):
					l[uvlayer].uv = corners[i]
					
				#MATERIAL HANDLING HERE

			bmesh.ops.delete( rmmesh.bmesh, geom=del_faces, context='FACES' )			
			

	def save_file( self, file ):
		#save hotspot to new .rect file
		pass

	def match( self, source, tollerance=0.01, random_orient=True ):
		#find the bound in this hotspot that best matches source
		source_bounds = Bounds2d.from_verts( source.vertices )
		surface_area = 0.0
		for p in source:
			surface_area += p.calc_area()
		source_coord = mathutils.Vector( ( surface_area / self.__td, source_bounds.aspect ) )

		min_dist = 9999999.9
		target_bounds = None
		for tb in self.__data:
			aspect = min( tb.aspect, 1.0 / tb.aspect )
			target_coord = mathutils.Vector( ( tb.width * tb.height, aspect ) )
			dist = ( target_coord - source_coord )
			if dist < min_dist:
				min_dist = dist
				target_bounds = tb

		target_list = []
		for tb in self.__data:
			aspect = min( tb.aspect, 1.0 / tb.aspect )
			target_coord = mathutils.Vector( ( tb.width * tb.height, aspect ) )
			dist = ( target_coord - source_coord )
			if abs( dist - min_dist ) <= tollerance:
				if not random_orient:
					if tb.horizontal == source.hotizontal:
						target_list.append( tb )
				else:
					target_list.append( tb )

		return random.choice( target_list )


	def nearest( self, u, v ):
		#find the bounds nearest to (u,v) coord
		point = mathutils.Vector( ( u, v ) )
		nearest_rect = self.__data[0]
		nearest_rect_dist = 999999999.9
		for b in self.__data:
			if b.inside( point ):
				return b
			min_dist = 999999999.9
			for c in b.corners:
				dist = ( c - point ).length
				if dist < min_dist:
					min_dist = dist
			if min_dist < nearest_rect_dist:
				nearest_rect_dist = min_dist
				nearest_rect = b
		return nearest_rect

	def overlapping( self, bounds2d ):
		#find the bounds that most overlapps bounds2d
		max_overlap_area = -1.0
		overlap_bounds = self.__data[0]
		for b in self.__data:
			if b.overlapping( bounds2d ):
				#compute overlapping area between two bounds
				overlap = 0.0
				if overlap > max_overlap_area:
					max_overlap_area = overlap
					overlap_bounds = b
		return overlap_bounds




def register():
	bpy.utils.register_class( MESH_OT_autohotspot )
	bpy.utils.register_class( MESH_OT_nrsthotspot )
	bpy.utils.register_class( MESH_OT_moshotspot )
	bpy.types.Scene.subrect_atlas = bpy.props.PointerProperty( name='atlas',type=bpy.types.Object,description='atlas object' )
	

def unregister():
	bpy.utils.uregister_class( MESH_OT_autohotspot )
	bpy.utils.uregister_class( MESH_OT_nrsthotspot )
	bpy.utils.uregister_class( MESH_OT_moshotspot )
	del bpy.types.Scene.subrect_atlas