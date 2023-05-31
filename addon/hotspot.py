from .. import rmlib
import bpy, bmesh, mathutils
import os, random, math, struct, ctypes

MAT_CHUNK = 'MAT'
HOT_CHUNK = 'HOT'

MAX_SHORT = 1 << 15

def clear_tags( rmmesh ):
	for v in rmmesh.bmesh.verts:
		v.tag = False
	for e in rmmesh.bmesh.edges:
		e.tag = False
	for f in rmmesh.bmesh.faces:
		f.tag = False
		for l in f.loops:
			l.tag = False


def GetFaceSelection( context, rmmesh ):
	uvlayer = rmmesh.active_uv
	clear_tags( rmmesh )

	faces = rmlib.rmPolygonSet()
	sel_sync = context.tool_settings.use_uv_select_sync
	if sel_sync or context.area.type == 'VIEW_3D':
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[2]:
			faces = rmlib.rmPolygonSet.from_selection( rmmesh )
		else:
			return faces
	else:
		sel_mode = context.tool_settings.uv_select_mode
		loops = rmlib.rmUVLoopSet.from_selection( rmmesh, uvlayer=uvlayer )
		loop_faces = set()
		for l in loops:
			if not l.face.select and sel_mode != 'EDGE':
				continue
			if not l[uvlayer].select_edge and sel_mode != 'VERT':
				continue
			loop_faces.add( l.face )
			l.tag = True
		for f in loop_faces:
			all_loops_tagged = True
			for l in f.loops:
				if not l.tag:
					all_loops_tagged = False
				else:
					l.tag = False
			if all_loops_tagged:
				faces.append( f )

	clear_tags( rmmesh )

	return faces


def load_mat_subchunk( chunk, offset ):
	'''
	#Chunk layout described below:
	3s(chunkname)
	I(groupcount)
		I(strcount for group)
			I(charcount fror string)
			{}s.format(charcount)(string)
			...
		...
	'''
	chunk_name = struct.unpack_from( '>3s', chunk, offset )[0].decode( 'utf-8' )
	if chunk_name != MAT_CHUNK:
		raise RuntimeError
	offset += 3
	str_list = []
	group_count = struct.unpack_from( '>I', chunk, offset )[0]
	offset += 4
	str_groups = []
	for i in range( group_count ):
		str_count = struct.unpack_from( '>I', chunk, offset )[0]
		offset += 4
		str_list = []
		for j in range( str_count ):
			size = struct.unpack_from( '>I', chunk, offset )[0]
			offset += 4
			s = struct.unpack_from( '>{}s'.format( size ), chunk, offset )[0].decode( 'utf-8' )
			str_list.append( s )
			offset += size
		str_groups.append( str_list )
	return str_groups, offset


def load_hot_chunk( chunk, offset ):
	'''
	#Chunk layout described below:
	3s(chunkname)
	I(hotspotcount)
		hotspot data
		...
	'''
	chunk_name = struct.unpack_from( '>3s', chunk, offset )[0].decode( 'utf-8' )
	if chunk_name != HOT_CHUNK:
		raise RuntimeError
	offset += 3
	hotspots = []
	hotspot_count = struct.unpack_from( '>I', chunk, offset )[0]
	offset += 4
	for i in range( hotspot_count ):
		new_hotspot, offset = Hotspot.unpack( chunk, offset )
		hotspots.append( new_hotspot )
	return hotspots, offset


class Bounds2d():
	def __init__( self, points, **kwargs ):
		self.__min = mathutils.Vector( ( 0.0, 0.0 ) )
		self.__max = mathutils.Vector( ( 1.0, 1.0 ) )
		if len( points ) > 0:
			self.__min = points[0].copy()
			self.__max = points[0].copy()
		#self.__inset = mathutils.Vector( ( 0.0, 0.0 ) )
		#self.__properties = {}
		for p in points:
			for i in range( 2 ):
				self.__min[i] = min( p[i], self.__min[i] )
				self.__max[i] = max( p[i], self.__max[i] )

		'''
		for key, value in kwargs.items():
			if key == 'inset':
				self.__inset = value
			elif key == 'properties':
				self.__properties = value
		'''

	def __repr__( self ):
		return 'min:Vec2( {}, {} )  max:Vec2( {}, {} )'.format( self.__min[0], self.__min[1], self.__max[0], self.max[1] )

	def __eq__( self, __o ):
		return rmlib.util.AlmostEqual_v2( self.__min, __o.__min ) and rmlib.util.AlmostEqual_v2( self.__max, __o.__max )

	def __bytes__( self ):
		return struct.pack( '>HHHH', ctypes.c_ushort( int( self.__min[0] * MAX_SHORT ) ).value,
									ctypes.c_ushort( int( self.__min[1] * MAX_SHORT ) ).value,
									ctypes.c_ushort( int( self.__max[0] * MAX_SHORT ) ).value,
									ctypes.c_ushort( int( self.__max[1] * MAX_SHORT ) ).value )

	@classmethod
	def from_verts( cls, verts ):
		#build bounds from list of BMVerts
		poslist = [ v.co.to_2d() for v in verts ]
		return cls( poslist )

	@classmethod
	def from_loops( cls, loops, uvlayer ):
		#build bounds from list of BMVerts
		uvlist = [ l[uvlayer].uv.copy() for l in loops ]
		return cls( uvlist )

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
		return self.__max[1] - self.__min[1]

	@property
	def aspect( self ):
		return self.width / self.height
	
	@property
	def area( self ):
		return self.width * self.height

	@property
	def center( self ):
		return ( self.__min + self.__max ) * 0.5

	@property
	def horizontal( self ):
		#returns true if self is wider than it is tall
		return self.width > self.height

	@property
	def tiling( self ):
		if self.__max[0] - self.__min[0] == 1.0:
			return 1
		if self.__max[1] - self.__min[1] == 1.0:
			return 2
		return 0

	@property
	def corners( self ):
		#return corner coords of self in (u,v) domain
		return [ self.__min, mathutils.Vector( ( self.__max[0], self.__min[1] ) ), self.__max, mathutils.Vector( ( self.__min[0], self.__max[1] ) ) ]

	def clamp( self ):
		new_bounds = Bounds2d( [ self.__min, self.__max ] )

		#move into unit square
		center = ( new_bounds.__min + new_bounds.__max ) / 2.0
		center.x = math.floor( center.x )
		center.y = math.floor( center.y )
		new_bounds.__min -= center
		new_bounds.__max -= center

		#clamp to 0.0-1.0 range
		new_bounds.__min.x = max( new_bounds.__min.x, 0.0 )
		new_bounds.__min.y = max( new_bounds.__min.y, 0.0 )
		new_bounds.__max.x = min( new_bounds.__max.x, 1.0 )
		new_bounds.__max.y = min( new_bounds.__max.y, 1.0 )

		return new_bounds

	def normalized( self ):
		#ensure bounds overlapps the 0-1 region
		center = self.center
		new_bounds = Bounds2d( [ self.__min, self.__max ] )
		new_bounds.__min[0] -= float( math.floor( center[0] ) )
		new_bounds.__min[1] -= float( math.floor( center[1] ) )
		new_bounds.__max[0] -= float( math.floor( center[0] ) )
		new_bounds.__max[1] -= float( math.floor( center[1] ) )
		return new_bounds

	def inside( self, point ):
		#test if point is inside self
		return ( point[0] > self.min[0] and point[1] > self.min[1] and point[0] < self.max[0] and point[1] < self.max[1] )

	def overlapping( self, bounds ):
		#test if bounds overlapps self
		return not ( self.__max[0] < bounds.__min[0] or self.__min[0] > bounds.max[0] or self.__max[1] < bounds.__min[1] or self.__min[1] > bounds.max[1] )
	
	def overlapping_area( self, bounds ):
		#does not test if bounds actually overlapp
		min_x = max( self.__min[0], bounds.min[0] )
		min_y = max( self.__min[1], bounds.min[1] )
		max_x = min( self.__max[0], bounds.max[0] )
		max_y = min( self.__max[1], bounds.max[1] )
		return ( max_x - min_x ) * ( max_y - min_y )

	def transform( self, other, skip_rot=False, trim=False ):
		#compute the 3x3 matrix that transforms bound 'other' to self
		trans_mat = mathutils.Matrix.Identity( 3 )
		trans_mat[0][2] = self.center[0] * -1.0
		trans_mat[1][2] = self.center[1] * -1.0
		
		trans_mat_inverse = mathutils.Matrix.Identity( 3 )
		trans_mat_inverse[0][2] = other.center[0]
		trans_mat_inverse[1][2] = other.center[1]

		rot_mat = mathutils.Matrix.Identity( 3 )
		scl_mat = mathutils.Matrix.Identity( 3 )
		if trim and ( other.width >= 1.0 or other.height >= 1.0 ):
			if self.horizontal != other.horizontal and not skip_rot:
				rot_mat[0][0] = math.cos( math.pi  / 2.0 )
				rot_mat[1][0] = math.sin( math.pi  / 2.0 ) * -1.0
				rot_mat[0][1] = math.sin( math.pi  / 2.0 )
				rot_mat[1][1] = math.cos( math.pi  / 2.0 )
				if other.width >= 1.0:
					scl_mat[1][1] = other.width / self.height
					scl_mat[0][0] = scl_mat[1][1]
				else:
					scl_mat[0][0] = other.height / self.width
					scl_mat[1][1] = scl_mat[0][0]
			else:
				if other.width >= 1.0:
					scl_mat[1][1] = other.height / self.height
					scl_mat[0][0] = scl_mat[1][1]
				else:
					scl_mat[0][0] = other.width / self.width
					scl_mat[1][1] = scl_mat[0][0]
		else:
			if self.horizontal != other.horizontal and not skip_rot:
				rot_mat[0][0] = math.cos( math.pi  / 2.0 )
				rot_mat[1][0] = math.sin( math.pi  / 2.0 ) * -1.0
				rot_mat[0][1] = math.sin( math.pi  / 2.0 )
				rot_mat[1][1] = math.cos( math.pi  / 2.0 )
				scl_mat[0][0] = other.width / self.height
				scl_mat[1][1] = other.height / self.width
			else:
				scl_mat[0][0] = other.width / self.width
				scl_mat[1][1] = other.height / self.height

		return trans_mat_inverse @ scl_mat @ rot_mat @ trans_mat
	
	def copy( self ):
		return Bounds2d( [ self.__min, self.__max ] )

	def inset( self, f ):
		self.__min[0] += f
		self.__min[1] += f
		self.__max[0] -= f
		self.__max[1] -= f


class Hotspot():
	def __init__( self, bounds2d_list, **kwargs ):
		self.__name = ''
		self.__properties = None
		self.__data = []
		for b in bounds2d_list:
			if b.area > 0.0:
				self.__data.append( b )
		for key, value in kwargs.items():
			if key == 'name':
				self.__name = value
			elif key == 'properties':
				self.__properties = None

	def __repr__( self ):
		s = 'HOTSPOT :: \"{}\" \n'.format( self.__name )
		#s += '\tproperties :: {}\n'.format( self.__properties )
		for i, r in enumerate( self.__data ):
			s += '\t{} :: {}\n'.format( i, r )
		return s

	def __eq__( self, __o ):
		if len( self.__data ) != len( __o.__data ):
			return False
		
		for b in self.__data:
			if b not in __o.__data:
				return False
			
		return True

	def __bytes__( self ):
		bounds_data = struct.pack( '>I', len( self.__data ) )
		for b in self.__data:
			bounds_data += bytes( b )		
		return bounds_data
	
	@property
	def data( self ):
		return self.__data

	@staticmethod
	def unpack( bytearray, offset ):
		bounds_count = struct.unpack_from( '>I', bytearray, offset )[0]
		offset += 4
		data = []
		for i in range( bounds_count ):
			bmin_x, bmin_y, bmax_x, bmax_y = struct.unpack_from( '>HHHH', bytearray, offset )
			min_pos = mathutils.Vector( ( bmin_x / MAX_SHORT, bmin_y / MAX_SHORT ) )
			max_pos = mathutils.Vector( ( bmax_x / MAX_SHORT, bmax_y / MAX_SHORT ) )
			data.append( Bounds2d( [ min_pos, max_pos ] ) )
			offset += 8
		return Hotspot( data ), offset

	@classmethod
	def from_bmesh( cls, rmmesh ):
		#load hotspot from subrect_atlas		
		boundslist = []
		with rmmesh as rmmesh:
			rmmesh.readonly = True
			uv_layer = rmmesh.bmesh.loops.layers.uv.verify()
			for f in rmmesh.bmesh.faces:
				boundslist.append( Bounds2d.from_loops( f.loops, uv_layer ) )
		return cls( boundslist )

	@property
	def name( self ):
		return self.__name

	def save_bmesh( self, rmmesh ):
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			del_faces = list( rmmesh.bmesh.faces )
			
			for bounds in self.__data:
				verts = []
				corners = bounds.corners
				for c in corners:
					verts.append( rmmesh.bmesh.verts.new( c.to_3d() ) )
				f = rmmesh.bmesh.faces.new( verts )
				for i, l in enumerate( f.loops ):
					l[uvlayer].uv = corners[i]

			bmesh.ops.delete( rmmesh.bmesh, geom=del_faces, context='FACES' )

	def match( self, source_bounds, tollerance=0.01, random_orient=True ):
		#find the bound in this hotspot that best matches source
		sb_aspect = min( source_bounds.aspect, 1.0 / source_bounds.aspect )
		source_coord = mathutils.Vector( ( math.sqrt( source_bounds.area ), sb_aspect ) )

		min_dist = 9999999.9
		best_bounds = self.__data[0]
		for tb in self.__data:
			aspect = min( tb.aspect, 1.0 / tb.aspect )
			target_coord = mathutils.Vector( ( math.sqrt( tb.area ), aspect ) )
			dist = ( target_coord - source_coord ).length
			if dist < min_dist:
				min_dist = dist
				best_bounds = tb
		best_aspect = min( best_bounds.aspect, 1.0 / best_bounds.aspect )
		best_coord = mathutils.Vector( ( math.sqrt( best_bounds.area ), best_aspect ) )

		target_list = []
		for tb in self.__data:
			aspect = min( tb.aspect, 1.0 / tb.aspect )
			target_coord = mathutils.Vector( ( math.sqrt( tb.area ), aspect ) )
			if ( target_coord - best_coord ).length <= tollerance:
				if not random_orient and tb.horizontal == best_bounds.hotizontal:
						target_list.append( tb )
				else:
					target_list.append( tb )
					
		return random.choice( target_list )

	def nearest( self, u, v ):
		#normalize u and v
		u -= math.floor( u )
		v -= math.floor( v )

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
		b_in = bounds2d.normalized()

		#find the bounds that most overlapps bounds2d
		max_overlap_area = -1.0
		overlap_bounds = self.__data[0]
		for b in self.__data:
			if b.overlapping( b_in ):
				overlap_area = b.overlapping_area( b_in )
				if overlap_area > max_overlap_area:
					max_overlap_area = overlap_area
					overlap_bounds = b
		return overlap_bounds


def write_default_file( file ):
	bounds = []
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.5, 0.0 ) ), mathutils.Vector( ( 0.75, 0.5 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.9375, 0.0 ) ), mathutils.Vector( ( 0.96875, 0.5 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.75, 0.0 ) ), mathutils.Vector( ( 0.875, 0.5 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.0, 0.0 ) ), mathutils.Vector( ( 0.5, 0.5 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.875, 0.0 ) ), mathutils.Vector( ( 0.9375, 0.5 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.75, 0.5 ) ), mathutils.Vector( ( 0.875, 0.75 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.875, 0.5 ) ), mathutils.Vector( ( 0.9375, 0.75 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.0, 0.5 ) ), mathutils.Vector( ( 0.5, 0.75 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.5, 0.5 ) ), mathutils.Vector( ( 0.75, 0.75 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.9375, 0.5 ) ), mathutils.Vector( ( 0.96875, 0.75 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.875, 0.75 ) ), mathutils.Vector( ( 0.9375, 0.875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.5, 0.75 ) ), mathutils.Vector( ( 0.75, 0.875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.9375, 0.75 ) ), mathutils.Vector( ( 0.96875, 0.875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.75, 0.75 ) ), mathutils.Vector( ( 0.875, 0.875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.0, 0.75 ) ), mathutils.Vector( ( 0.5, 0.875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.0, 0.875 ) ), mathutils.Vector( ( 0.5, 0.9375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.5, 0.875 ) ), mathutils.Vector( ( 0.75, 0.9375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.9375, 0.875 ) ), mathutils.Vector( ( 0.96875, 0.9375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.875, 0.875 ) ), mathutils.Vector( ( 0.9375, 0.9375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.75, 0.875 ) ), mathutils.Vector( ( 0.875, 0.9375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.875, 0.9375 ) ), mathutils.Vector( ( 0.9375, 0.96875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.9375, 0.9375 ) ), mathutils.Vector( ( 0.96875, 0.96875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.75, 0.9375 ) ), mathutils.Vector( ( 0.875, 0.96875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.0, 0.9375 ) ), mathutils.Vector( ( 0.5, 0.96875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.5, 0.9375 ) ), mathutils.Vector( ( 0.75, 0.96875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.984375, 0.9375 ) ), mathutils.Vector( ( 1.0, 0.96875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.96875, 0.9375 ) ), mathutils.Vector( ( 0.984375, 0.96875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.984375, 0.875 ) ), mathutils.Vector( ( 1.0, 0.9375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.96875, 0.875 ) ), mathutils.Vector( ( 0.984375, 0.9375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.984375, 0.75 ) ), mathutils.Vector( ( 1.0, 0.875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.96875, 0.75 ) ), mathutils.Vector( ( 0.984375, 0.875 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.984375, 0.0 ) ), mathutils.Vector( ( 1.0, 0.5 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.96875, 0.0 ) ), mathutils.Vector( ( 0.984375, 0.5 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.984375, 0.5 ) ), mathutils.Vector( ( 1.0, 0.75 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.96875, 0.5 ) ), mathutils.Vector( ( 0.984375, 0.75 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.0, 0.984375 ) ), mathutils.Vector( ( 0.5, 1.0 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.0, 0.96875 ) ), mathutils.Vector( ( 0.5, 0.984375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.96875, 0.96875 ) ), mathutils.Vector( ( 0.984375, 0.984375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.96875, 0.984375 ) ), mathutils.Vector( ( 0.984375, 1.0 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.9375, 0.984375 ) ), mathutils.Vector( ( 0.96875, 1.0 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.9375, 0.96875 ) ), mathutils.Vector( ( 0.96875, 0.984375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.984375, 0.984375 ) ), mathutils.Vector( ( 1.0, 1.0 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.984375, 0.96875 ) ), mathutils.Vector( ( 1.0, 0.984375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.5, 0.984375 ) ), mathutils.Vector( ( 0.75, 1.0 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.5, 0.96875 ) ), mathutils.Vector( ( 0.75, 0.984375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.75, 0.984375 ) ), mathutils.Vector( ( 0.875, 1.0 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.75, 0.96875 ) ), mathutils.Vector( ( 0.875, 0.984375 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.875, 0.984375 ) ), mathutils.Vector( ( 0.9375, 1.0 ) ) ] ) )
	bounds.append( Bounds2d( [ mathutils.Vector( ( 0.875, 0.96875 ) ), mathutils.Vector( ( 0.9375, 0.984375 ) ) ] ) )
	hotspot = Hotspot( bounds, name='default' )

	with open( file, 'wb' ) as f:
		#write material chunk
		f.write( struct.pack( '>3s', bytes( MAT_CHUNK, 'utf-8' ) ) )
		f.write( struct.pack( '>I', 1 ) )
		for matgroup in [ [ 'default' ] ]:
			f.write( struct.pack( '>I', len( matgroup ) ) )
			for mat in matgroup:
				size = len( mat )
				f.write( struct.pack( '>I', size ) )
				f.write( struct.pack( '>{}s'.format( size ), bytes( mat, 'utf-8' ) ) )

		#write hotspot chunk
		f.write( struct.pack( '>3s', bytes( HOT_CHUNK, 'utf-8' ) ) )
		f.write( struct.pack( '>I', 1 ) )
		f.write( bytes( hotspot ) )


def write_hot_file( file, materials, hotspots ):
	if len( hotspots ) != len( materials ):
		raise RuntimeError

	with open( file, 'wb' ) as f:
		#write material chunk
		f.write( struct.pack( '>3s', bytes( MAT_CHUNK, 'utf-8' ) ) )
		f.write( struct.pack( '>I', len( materials ) ) )
		for matgroup in materials:
			f.write( struct.pack( '>I', len( matgroup ) ) )
			for mat in matgroup:
				size = len( mat )
				f.write( struct.pack( '>I', size ) )
				f.write( struct.pack( '>{}s'.format( size ), bytes( mat, 'utf-8' ) ) )

		#write hotspot chunk
		f.write( struct.pack( '>3s', bytes( HOT_CHUNK, 'utf-8' ) ) )
		f.write( struct.pack( '>I', len( hotspots ) ) )
		for h in hotspots:
			f.write( bytes( h ) )


def read_hot_file( file ):
	materials = []
	hotspots = []
	with open( file, 'rb' ) as f:
		data = f.read()

		offset = 0
		chunkname = struct.unpack_from( '>3s', data, offset )[0].decode( 'utf-8' )
		if chunkname == MAT_CHUNK:
			materials, offset = load_mat_subchunk( data, offset )
		
		chunkname = struct.unpack_from( '>3s', data, offset )[0].decode( 'utf-8' )
		if chunkname == HOT_CHUNK:
			hotspots, offset = load_hot_chunk( data, offset )

	return materials, hotspots


def get_hotfile_path():
	filepath = os.path.dirname( os.path.dirname( rmlib.__file__ ) ) + '\\atlas_repo.hot'
	if not os.path.isfile( filepath ):
		write_default_file( filepath )
	return filepath


def load_hotspot_from_repo( material_name ):
	#load hotspot repo file
	hotfile = get_hotfile_path()
	existing_materials, existing_hotspots = read_hot_file( hotfile )

	hotspot_idx = -1
	for i in range( len( existing_materials ) ):
		if material_name in existing_materials[i]:
			hotspot_idx = i
			break
	if hotspot_idx < 0:
		return None

	return existing_hotspots[hotspot_idx]


def get_hotspot( context ):
	if context.scene.use_subrect_atlas:
		if context.scene.subrect_atlas is None:
			return None
		return Hotspot.from_bmesh( rmlib.rmMesh( context.scene.subrect_atlas ) )
	
	rmmesh = rmlib.rmMesh.GetActive( context )
	if rmmesh is None:
		return None

	with rmmesh as rmmesh:
		rmmesh.readonly = True
		faces = rmlib.rmPolygonSet.from_selection( rmmesh )
		if len( faces ) <= 0:
			return None
		try:
			material_name = rmmesh.mesh.materials[ faces[0].material_index ].name
		except IndexError:
			return None
		return load_hotspot_from_repo( material_name )


class OBJECT_OT_savehotspot( bpy.types.Operator ):
	bl_idname = 'mesh.savehotspot'
	bl_label = 'Create Hotspot'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.mode == 'OBJECT' and
				context.active_object.type == 'MESH' )

	def execute( self, context ):
		#generate new hotspot obj from face selection
		hotspot = None
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			rmmesh.readonly = True

			if len( rmmesh.bmesh.loops.layers.uv.values() ) == 0:
				return { 'CANCELLED' }
			uvlayer = rmmesh.active_uv
			
			polys = rmlib.rmPolygonSet.from_mesh( rmmesh, filter_hidden=False )
			if len( polys ) == 0:
				return { 'CANCELLED' }

			bounds = []
			for f in polys:
				uvlist = [ mathutils.Vector( l[uvlayer].uv.copy() ) for l in f.loops ]
				pmin = mathutils.Vector( uvlist[0] )
				pmax = mathutils.Vector( uvlist[0] )
				for p in uvlist:
					for i in range( 2 ):
						pmin[i] = min( pmin[i], p[i] )
						pmax[i] = max( pmax[i], p[i] )
				bounds.append( Bounds2d( [ pmin, pmax ] ).clamp() )

			try:
				mat_name = rmmesh.mesh.materials[ polys[0].material_index ].name
			except IndexError:
				self.report( { 'WARNING' }, 'Material lookup failed!!!' )
				return { 'CANCELLED' }
			hotspot = Hotspot( bounds, name=mat_name )

		#load hotspot repo file
		hotfile = get_hotfile_path()
		existing_materials, existing_hotspots = read_hot_file( hotfile )

		#remove matname from matgroup if it exists. it'll be added in later
		for i, matgrp in enumerate( existing_materials ):
			if mat_name in matgrp:
				existing_materials[i].remove( mat_name )
				if len( existing_materials[i] ) == 0:
					existing_materials.pop( i )
					existing_hotspots.pop( i )
				break

		'''
		#update hotspot database
		hotspot_already_exists = False
		for i, exhot in enumerate( existing_hotspots ):
			if exhot == hotspot:
				existing_materials[i].append( mat_name )
				hotspot_already_exists = True
				break
		if not hotspot_already_exists:
			existing_materials.append( [ mat_name ] )
			existing_hotspots.append( hotspot )
		'''

		#update hotspot database
		existing_materials.append( [ mat_name ] )
		existing_hotspots.append( hotspot )
		

		#write updated database
		write_hot_file( hotfile, existing_materials, existing_hotspots )
		self.report( { 'WARNING' }, 'Hotspot Repo Updated!!!' )

		return  {'FINISHED' }


class OBJECT_OT_repotoascii( bpy.types.Operator ):
	bl_idname = 'mesh.repotoascii'
	bl_label = 'Hotspot Repo to Ascii'
	
	filter_glob: bpy.props.StringProperty( default='*.txt', options={ 'HIDDEN' } )
	filepath: bpy.props.StringProperty( name="File Path", description="", maxlen= 1024, default= "" )
	files: bpy.props.CollectionProperty( name = 'File Path', type = bpy.types.OperatorFileListElement )

	@classmethod
	def poll( cls, context ):
		return True

	def execute( self, context ):
		#load hotspot repo file
		hotfile = get_hotfile_path()
		existing_materials, existing_hotspots = read_hot_file( hotfile )

		if not self.filepath.endswith( '.txt' ):
			self.filepath += '.txt'

		#write ascii file
		with open( self.filepath, 'w' ) as f:
			f.write( MAT_CHUNK + '\n' )
			for i, matgroup in enumerate( existing_materials ):
				f.write( '\t{}\n'.format( i ) )
				for mat in matgroup:
					f.write( '\t\t{}\n'.format( mat ) )

			f.write( '\n' + HOT_CHUNK + '\n' )
			for hotspot in existing_hotspots:
				f.write( str( hotspot ) )
				f.write( '\n\n' )

		return  {'FINISHED' }

	def invoke( self, context, event ):
		wm = context.window_manager
		wm.fileselect_add( self )
		return { 'RUNNING_MODAL' }


class MESH_OT_grabapplyuvbounds( bpy.types.Operator ):
	bl_idname = 'mesh.grabapplyuvbounds'
	bl_label = 'GrabApplyUVBounds (MOS)'
	bl_options = { 'UNDO' }

	def __init__( self ):
		self.mos = ( 0.0, 0.0 )

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		#get target_bounds from MOS
		mouse_pos = mathutils.Vector( ( float( self.mos[0] ), float( self.mos[1] ) ) )
		mos_rmmesh = rmlib.rmMesh.from_mos( context, mouse_pos )
		if mos_rmmesh is None:
			return { 'CANCELLED' }
		with mos_rmmesh as rmmesh:
			rmmesh.readonly = True
			if len( rmmesh.bmesh.loops.layers.uv ) < 1:
				return { 'CANCELLED' }
			uvlayer = rmmesh.active_uv
		
			faces = rmlib.rmPolygonSet.from_mos( rmmesh, context, mouse_pos )
			if len( faces ) < 1:
				return { 'CANCELLED' }
			
			target_faces = faces.island( uvlayer, element=True )[0]
			target_loops = set()
			for f in target_faces:
				for l in f.loops:
					target_loops.add( l )
			target_bounds = Bounds2d.from_loops( target_loops, uvlayer )

		#move selection to target_bounds
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			source_faces = rmlib.rmPolygonSet.from_selection( rmmesh )
			for source_island in source_faces.island( uvlayer ):
				loops = set()
				for f in source_island:
					for l in f.loops:
						loops.add( l )
				source_bounds = Bounds2d.from_loops( loops, uvlayer )

				mat = source_bounds.transform( target_bounds )		
				for l in loops:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()

		return { 'FINISHED' }

	def invoke( self, context, event ):
		self.mos = ( event.mouse_region_x, event.mouse_region_y )
		return self.execute( context )


class MESH_OT_moshotspot( bpy.types.Operator ):
	bl_idname = 'mesh.moshotspot'
	bl_label = 'Hotspot (MOS)'
	bl_options = { 'UNDO' }

	def __init__( self ):
		self.mos_uv = ( 0.0, 0.0 )

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		hotspot = get_hotspot( context )
		if hotspot is None:
			return { 'CANCELLED' }

		use_trim = context.scene.use_trim

		target_bounds = hotspot.nearest( self.mos_uv[0], self.mos_uv[1] ).copy()
		target_bounds.inset( context.scene.hotspot_inset / 1024.0 )

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			
			faces = GetFaceSelection( context, rmmesh )
			if len( faces ) < 1:
				return { 'CANCELLED' }

			for island in faces.island( uvlayer ):
				loops = set()
				for f in island:
					for l in f.loops:
						loops.add( l )
				source_bounds = Bounds2d.from_loops( loops, uvlayer )

				mat = source_bounds.transform( target_bounds, skip_rot=True, trim=use_trim )		
				for l in loops:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()

		return { 'FINISHED' }

	def invoke( self, context, event ):
		self.mos_uv = context.region.view2d.region_to_view( event.mouse_region_x, event.mouse_region_y )
		return self.execute( context )


class MESH_OT_nrsthotspot( bpy.types.Operator ):
	bl_idname = 'mesh.nrsthotspot'
	bl_label = 'Hotspot Nrst'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		hotspot = get_hotspot( context )
		if hotspot is None:
			return { 'CANCELLED' }

		use_trim = context.scene.use_trim

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			
			faces = GetFaceSelection( context, rmmesh )
			if len( faces ) < 1:
				return { 'CANCELLED' }

			for island in faces.island( uvlayer ):
				loops = set()
				for f in island:
					for l in f.loops:
						loops.add( l )
				source_bounds = Bounds2d.from_loops( loops, uvlayer )
				#target_bounds = hotspot.overlapping( source_bounds ).copy()
				target_bounds = hotspot.nearest( source_bounds.center.x, source_bounds.center.y ).copy()
				target_bounds.inset( context.scene.hotspot_inset / 1024.0 )				
				mat = source_bounds.transform( target_bounds, skip_rot=True, trim=use_trim )
				for l in loops:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()

		return { 'FINISHED' }
	

class MESH_OT_matchhotspot( bpy.types.Operator ):
	bl_idname = 'mesh.matchhotspot'
	bl_label = 'Hotspot Match'
	bl_options = { 'UNDO' }

	tollerance: bpy.props.FloatProperty(
		name='Tollerance',
		default=0.01
	)

	@classmethod
	def poll( cls, context ):
		return ( ( context.area.type == 'VIEW_3D' or context.area.type == 'IMAGE_EDITOR' ) and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		hotspot = get_hotspot( context )
		if hotspot is None:
			return { 'CANCELLED' }

		use_trim = context.scene.use_trim

		#preprocess uvs
		islands_as_indexes = []
		if context.area.type == 'VIEW_3D': #if in 3dvp, scale to mat size then rectangularize/gridify uv islands
			rmmesh = rmlib.rmMesh.GetActive( context )
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				if len( rmmesh.bmesh.loops.layers.uv.values() ) == 0:
					return { 'CANCELLED' }

				uvlayer = rmmesh.active_uv

				faces = rmlib.rmPolygonSet.from_selection( rmmesh )
				if len( faces ) < 1:
					return { 'CANCELLED' }

				auto_smooth_angle = math.pi
				if rmmesh.mesh.use_auto_smooth:
					auto_smooth_angle = rmmesh.mesh.auto_smooth_angle

				for island in faces.group( element=False, use_seam=True, use_material=True, use_sharp=True, use_angle=auto_smooth_angle ):
					islands_as_indexes.append( [ f.index for f in island ] )					
					island.select( replace=True )
					result = bpy.ops.mesh.rm_uvgridify() #gridify
					if result == { 'CANCELLED' }:
						bpy.ops.uv.unwrap( 'INVOKE_DEFAULT', method='CONFORMAL' )
						bpy.ops.mesh.rm_uvunrotate() #unrotate uv by longest edge in island
						#bpy.ops.mesh.rm_uvrectangularize() #rectangularize
					bpy.ops.mesh.rm_scaletomaterialsize() #scale to mat size

		elif context.area.type == 'IMAGE_EDITOR': #iv in uvvp, scale to mat sizecomplete_failure
			rmmesh = rmlib.rmMesh.GetActive( context )
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				if len( rmmesh.bmesh.loops.layers.uv.values() ) == 0:
					return { 'CANCELLED' }

				uvlayer = rmmesh.active_uv

				faces = GetFaceSelection( context, rmmesh )
				if len( faces ) < 1:
					return { 'CANCELLED' }
				for island in faces.island( uvlayer, use_seam=True ):
					islands_as_indexes.append( [ f.index for f in island ] )
					#island.select( replace=True )
					#bpy.ops.mesh.rm_scaletomaterialsize() #scale to mat size
					
		#hotspot
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			if context.area.type == 'VIEW_3D':
				initial_selection = []
				for pidx_list in islands_as_indexes:
					island = [ rmmesh.bmesh.faces[pidx] for pidx in pidx_list ]
					initial_selection += set( island )
					loops = set()
					for f in island:
						for l in f.loops:
							loops.add( l )
					source_bounds = Bounds2d.from_loops( loops, uvlayer )
					target_bounds = hotspot.match( source_bounds, tollerance=self.tollerance ).copy()
					target_bounds.inset( context.scene.hotspot_inset / 1024.0 )

					mat = source_bounds.transform( target_bounds, skip_rot=False, trim=use_trim )		
					for l in loops:
						uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
						uv[2] = 1.0
						uv = mat @ uv
						l[uvlayer].uv = uv.to_2d()

				for f in initial_selection:
					f.select = True

			elif context.area.type == 'IMAGE_EDITOR':
				initial_selection = []
				for pidx_list in islands_as_indexes:					
					island = [ rmmesh.bmesh.faces[pidx] for pidx in pidx_list ]
					initial_selection += set( island )
					loops = set()
					for f in island:
						for l in f.loops:
							loops.add( l )
					source_bounds = Bounds2d.from_loops( loops, uvlayer )
					target_bounds = hotspot.match( source_bounds, tollerance=self.tollerance ).copy()
					target_bounds.inset( context.scene.hotspot_inset / 1024.0 )

					mat = source_bounds.transform( target_bounds, skip_rot=False, trim=use_trim )		
					for l in loops:
						uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
						uv[2] = 1.0
						uv = mat @ uv
						l[uvlayer].uv = uv.to_2d()

				for f in initial_selection:
					f.select = True

		return { 'FINISHED' }


class MESH_OT_uvaspectscale( bpy.types.Operator ):
	"""Inset Selected UV Islands"""
	bl_idname = 'mesh.rm_uvaspectscale'
	bl_label = 'UV Aspect Scale'
	bl_options = { 'REGISTER', 'UNDO' }
	
	scale: bpy.props.FloatProperty(
		name='Inset',
		default=0.0
	)

	def __init__( self ):
		self.bmesh = None
		self.prev_delta = 0
		self.shift_sensitivity = False

	def __del__( self ):
		try:
			if self.bmesh is not None:
				self.bmesh.free()
		except AttributeError:
			pass
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		offset = self.scale / 10.0
		if self.shift_sensitivity:
			offset /= 10.0

		targetObj = context.active_object
		targetMesh = targetObj.data

		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )
		
		bm = self.bmesh.copy()
		
		uvlayer = bm.loops.layers.uv.verify()
		
		rmmesh = rmlib.rmMesh.from_bmesh( targetObj, bm )
		faces = GetFaceSelection( context, rmmesh )
		if len( faces ) < 1:
			bpy.ops.object.mode_set( mode='EDIT', toggle=False )
			return { 'CANCELLED' }

		for island in faces.island( uvlayer ):
			loops = set()
			for f in island:
				for l in f.loops:
					loops.add( l )
			source_bounds = Bounds2d.from_loops( loops, uvlayer )

			new_min = source_bounds.min.copy()
			new_min[0] += offset
			new_min[1] += offset

			new_max = source_bounds.max.copy()
			new_max[0] -= offset
			new_max[1] -= offset

			target_bounds = Bounds2d( [ new_min, new_max ] )

			mat = source_bounds.transform( target_bounds, skip_rot=True, trim=False )		
			for l in loops:
				uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
				uv[2] = 1.0
				uv = mat @ uv
				l[uvlayer].uv = uv.to_2d()

		
		bm.to_mesh( targetMesh )
		bm.calc_loop_triangles()
		targetMesh.update()
		bm.free()
		
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )
		
		return { 'FINISHED' }

	def modal( self, context, event ):
		if event.type == 'LEFTMOUSE':
			return { 'FINISHED' }
		elif event.type == 'MOUSEMOVE':
			self.shift_sensitivity = event.shift
			delta_x = float( event.mouse_x - event.mouse_prev_press_x ) / context.region.width
			if delta_x != self.prev_delta:
				self.prev_delta = delta_x
				self.scale = delta_x * 4.0
				self.execute( context )			
		elif event.type == 'ESC':
			return { 'CANCELLED' }

		return { 'RUNNING_MODAL' }
	
	def invoke( self, context, event ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readme = True
				self.bmesh = rmmesh.bmesh.copy()
				
		context.window_manager.modal_handler_add( self )
		return { 'RUNNING_MODAL' }
	

def enum_previews_from_directory_items(self, context):
	enum_items = []

	if context is None:
		return enum_items
	

	hotfile = get_hotfile_path()
	existing_materials, existing_hotspots = read_hot_file( hotfile )
	
	pcoll = preview_collections["main"]
	for i in range( len( existing_hotspots ) ):
		name = str( i )
		icon = pcoll.get( name )
		if not icon:
			size = 64
			thumb = pcoll.new( name )
			thumb.image_size = [ size, size ]
			raw_data = [ 0.1 ] * 4 * size * size

			hotspot = existing_hotspots[i]
			for b in hotspot.data:
				color = rmlib.util.HSV_to_RGB( random.random(), random.random(), random.random() * 0.5 + 0.5 )
				w = int( b.width * size )
				h = int( b.height * size )
				min_x = int( b.min[0] * size )
				min_y = int( b.min[1] * size )
				for m in range( h ):					
					y = min_y + m
					for n in range( w ):
						x = min_x + n
						idx = ( y * size + x ) * 4
						raw_data[ idx ] = color[0]
						raw_data[ idx + 1 ] = color[1]
						raw_data[ idx + 2 ] = color[2]
			thumb.image_pixels_float = raw_data
			thumb.is_icon_custom = True			
		else:
			thumb = pcoll[name]
		enum_items.append( ( name, name, "", thumb.icon_id, i ) )

	pcoll.my_previews = enum_items
	return pcoll.my_previews


class MESH_OT_refhostpot( bpy.types.Operator ):
	bl_idname = 'mesh.refhotspot'
	bl_label = 'Ref Hotspot'
	bl_options = { 'UNDO' }

	my_previews: bpy.props.EnumProperty( items=enum_previews_from_directory_items )

	@classmethod
	def poll( cls, context ):
		return ( ( context.area.type == 'VIEW_3D' or context.area.type == 'IMAGE_EDITOR' ) and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):		
		img_name = self.my_previews

		#get material name
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			rmmesh.readonly = True
			
			polys = rmlib.rmPolygonSet.from_selection( rmmesh )
			if len( polys ) == 0:
				return { 'CANCELLED' }
			try:
				mat_name = rmmesh.mesh.materials[ polys[0].material_index ].name
			except KeyError:
				return { 'CANCELLED' }

		#load hotspot repo file
		hotfile = get_hotfile_path()
		existing_materials, existing_hotspots = read_hot_file( hotfile )

		#remove matname from matgroup if it exists. it'll be added in later
		for i, matgrp in enumerate( existing_materials ):
			if mat_name in matgrp:
				existing_materials[i].remove( mat_name )

		#update hotspot database
		hotspot_idx = int( img_name )
		if hotspot_idx < len( existing_materials ):
			existing_materials[hotspot_idx].append( mat_name )		

		#write updated database
		write_hot_file( hotfile, existing_materials, existing_hotspots )
		self.report( { 'WARNING' }, 'Hotspot Repo Updated!!!' )

		return  {'FINISHED' }

	def draw(self, context):
		layout = self.layout
		layout.template_icon_view( self, "my_previews" )

	def invoke( self, context, event ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		random.seed( 0 )
		return context.window_manager.invoke_props_dialog( self, width=128 )


preview_collections = {}


class UV_PT_UVHotspotTools( bpy.types.Panel ):
	bl_parent_id = 'UV_PT_RMKIT_PARENT'
	bl_idname = 'UV_PT_UVHotspotTools'
	bl_label = 'Hotspot'
	bl_region_type = 'UI'
	bl_space_type = 'IMAGE_EDITOR'
	bl_options = { 'DEFAULT_CLOSED' }

	def draw( self, context ):
		layout = self.layout
		layout.prop( context.scene, 'use_subrect_atlas' )
		r1 = layout.row()
		r1.label( text="Atlas: ")
		r1.prop_search( context.scene, "subrect_atlas", context.scene, "objects", text="", icon="MOD_MULTIRES" )
		r1.enabled = context.scene.use_subrect_atlas
		r2 = layout.row()
		r2.prop( context.scene, 'use_trim' )
		r2.prop( context.scene, 'hotspot_inset' )
		layout.operator( 'mesh.savehotspot', text='New Hotspot' )
		layout.operator( 'mesh.refhotspot', text='Ref Hotspot' )
		layout.operator( 'mesh.matchhotspot', text='Hotspot Match' )
		layout.operator( 'mesh.nrsthotspot', text='Hotspot Nearest' )
		#layout.operator( 'mesh.moshotspot', text='Hotspot MOS' )

def register():
	bpy.utils.register_class( OBJECT_OT_savehotspot )
	bpy.utils.register_class( MESH_OT_matchhotspot )
	bpy.utils.register_class( MESH_OT_nrsthotspot )
	bpy.utils.register_class( MESH_OT_moshotspot )
	bpy.utils.register_class( MESH_OT_grabapplyuvbounds )
	bpy.types.Scene.use_subrect_atlas = bpy.props.BoolProperty( name='Use Override Atlas' )
	bpy.types.Scene.hotspot_inset = bpy.props.FloatProperty( name='Inset', default=0.0 )
	bpy.types.Scene.use_trim = bpy.props.BoolProperty( name='Use Trims' )
	bpy.types.Scene.subrect_atlas = bpy.props.PointerProperty( name='Atlas', type=bpy.types.Object, description='atlas object' )
	bpy.utils.register_class( UV_PT_UVHotspotTools )
	bpy.utils.register_class( OBJECT_OT_repotoascii )
	bpy.utils.register_class( MESH_OT_uvaspectscale )

	pcoll = bpy.utils.previews.new()
	pcoll.my_previews = ()
	preview_collections["main"] = pcoll
	bpy.utils.register_class( MESH_OT_refhostpot )


def unregister():
	bpy.utils.unregister_class( OBJECT_OT_savehotspot )
	bpy.utils.unregister_class( MESH_OT_matchhotspot )
	bpy.utils.unregister_class( MESH_OT_nrsthotspot )
	bpy.utils.unregister_class( MESH_OT_moshotspot )
	bpy.utils.unregister_class( MESH_OT_grabapplyuvbounds )
	del bpy.types.Scene.use_subrect_atlas
	del bpy.types.Scene.subrect_atlas
	del bpy.types.Scene.hotspot_inset
	del bpy.types.Scene.use_trim
	bpy.utils.unregister_class( UV_PT_UVHotspotTools )
	bpy.utils.unregister_class( OBJECT_OT_repotoascii )
	bpy.utils.unregister_class( MESH_OT_uvaspectscale )

	for pcoll in preview_collections.values():
		bpy.utils.previews.remove(pcoll)
	preview_collections.clear()
	bpy.utils.unregister_class( MESH_OT_refhostpot )