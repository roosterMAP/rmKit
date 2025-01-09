import mathutils
from bpy_extras import view3d_utils
import math

FLOAT_EPSILON = 0.000001

class rmCustomOrientation():
	def __init__( self, context ):
		self.__scene = context.scene
		self.__co = None

	@classmethod
	def from_selection( cls, context ):
		co = cls( context )
		co.__co = co.__scene.transform_orientation_slots[0].custom_orientation
		return co

	@property
	def name( self ):
		if self.__co is not None:
			return self.__co.name
		return None

	@property
	def matrix( self ):
		if self.__co is not None:
			return mathutils.Matrix( self.__co.matrix )
		return mathutils.Matrix.Identity( 3 )


class rmViewport():
	def __init__( self, context ):
		a = context.area
		if a is None:
			return None
		self.__space = a.spaces.active

	@property
	def cam_pos( self ):
		return self.__space.region_3d.view_matrix.inverted().translation

	@property
	def look_dir( self ):
		return self.__space.region_3d.view_rotation @ mathutils.Vector( ( 0.0, 0.0, -1.0 ) )

	def cursor_to_ray( self, context, mouse_pos ):
		ray_origin = view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_pos )
		ray_dir = view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_pos )
		return ( ray_origin, ray_dir )

	def is_view3d( self ):
		return self.__space.type == 'VIEW_3D'

	def is_uvview( self ):
		return self.__space.type == 'IMAGE_EDITOR'

	def get_mouse_on_plane( self, context, plane_pos, plane_dir, mouse_coords ):
		if not self.is_view3d():
			raise TypeError( 'get_nearest_direction_vector() only valid for VIEW_3D spaces' )

		if plane_dir is None:
			plane_dir = self.__space.region_3d.view_rotation @ mathutils.Vector( ( 0.0, 0.0, -1.0 ) )

		mouse_pos = view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_coords )
		mouse_dir = view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_coords )
		new_pos = mathutils.geometry.intersect_line_plane( mouse_pos, mouse_pos + ( mouse_dir * 10000.0 ), plane_pos, plane_dir, False )
		if new_pos:
			return new_pos

		return None

	def get_nearest_direction_vector( self, dir_string, input_rot=mathutils.Matrix.Identity( 3 ) ):
		"""
		Returns directional data relative to viewport camera.

		Args:
			dir_string (string): The relative direction from viewport camera perspective.
			input_rot (mathutils.Matrix(4)): Additional transform. Usefull for fetching relative direction on a custom orientation.

		Returns:
			[int,mathUtils.Vector(3), mathUtils.Vector(3)]:
				-Index of the orientation matrix row that best aligns with the relative dir.
				-Vec3 row at the index described above.
				-Vec3 row of the world/grid orientation that best aligns with the relative dir.
		"""

		if not self.is_view3d():
			raise TypeError( 'get_nearest_direction_vector() only valid for VIEW_3D spaces' )

		r3d = self.__space.region_3d
		view_matrix = r3d.view_matrix.to_3x3()
		
		dir = [ 'right', 'up', 'back' ]
		inv_dir = [ 'left', 'down', 'front' ]
		avg_dir = [ 'horizontal', 'vertical', 'depth' ]
		if dir_string in dir:
			dir_vec = view_matrix[ dir.index( dir_string ) ]
		elif dir_string in inv_dir:
			dir_vec = view_matrix[ inv_dir.index( dir_string ) ] * -1.0
		elif dir_string in avg_dir:
			dir_vec = view_matrix[ avg_dir.index( dir_string ) ] * -1.0
		else:
			raise ValueError( 'Invalid input direction string!!!' )
			
		maxDot = 0.0
		maxDot_neg = False
		row_idx = 0
		input_rot.transpose()
		for i in range( 3 ):
			dot = dir_vec.dot( input_rot[i] )
			if abs( dot ) > maxDot:
				maxDot = abs( dot )
				maxDot_neg = dot < 0.0
				row_idx = i
		n = 1.0
		if maxDot_neg:
			n = -1.0
				
		return ( row_idx, dir_vec, input_rot[row_idx] * n )

	def get_nearest_direction_vector_from_mouse( self, context, mouse_start, mouse_end, offset, input_rot=mathutils.Matrix.Identity( 3 ) ):
		region = context.region
		rv3d = context.region_data
		
		x2d = view3d_utils.location_3d_to_region_2d( region, rv3d, offset + input_rot[0] )
		y2d = view3d_utils.location_3d_to_region_2d( region, rv3d, offset + input_rot[1] )
		z2d = view3d_utils.location_3d_to_region_2d( region, rv3d, offset + input_rot[2] )
		c2d = view3d_utils.location_3d_to_region_2d( region, rv3d, offset )
		x2d = ( x2d - c2d ).normalized()
		y2d = ( y2d - c2d ).normalized()
		z2d = ( z2d - c2d ).normalized()
		
		mv = ( mouse_start - mouse_end ).normalized()	
		x_dot = abs( mv.dot( x2d ) )
		y_dot = abs( mv.dot( y2d ) )
		z_dot = abs( mv.dot( z2d ) )

		if x_dot > y_dot and x_dot > z_dot:
			return 0
		elif y_dot > x_dot and y_dot > z_dot:
			return 1
		elif z_dot > x_dot and z_dot > y_dot:
			return 2
		else:
			return -1


def line2_dist( a, b, x ):
	d_ab = ( a - b ).length
	d_ax = ( a - x ).length
	d_bx = ( b - x ).length

	if ( a - b ).dot( x - b ) * ( b - a ).dot( x - a ) >= 0:
		A = mathutils.Matrix([ [ a[0], a[1], 1.0 ], [ b[0], b[1], 1.0 ], [ x[0], x[1], 1.0 ] ] )
		d = abs( A.determinant() ) / d_ab
	else:
		d = min( d_ax, d_bx )
	
	return d

def PlaneDistance( p, pP, pN ):
	pN.normalize()
	d = pN.dot( pP ) * -1.0
	a = pN.dot( p ) + d
	b = math.sqrt( pN.dot( pN ) )
	return a / b

def ReflectionMatrix( p, n ):
	n.normalize()
	a = n.x
	b = n.y
	c = n.z
	d = n.dot( p ) * -1.0
	
	M = mathutils.Matrix.Identity( 4 )
	M[0][0] = 1.0 - 2.0 * a * a
	M[0][1] = -2.0 * a * b
	M[0][2] = -2.0 * a * c
	M[0][3] = -2.0 * a * d
	M[1][0] = -2.0 * a * b
	M[1][1] = 1.0 - 2.0 * b * b
	M[1][2] = -2.0 * b * c
	M[1][3] = -2.0 * b * d
	M[2][0] = -2.0 * a * c
	M[2][1] = -2.0 * b * c
	M[2][2] = 1.0 - 2.0 * c * c
	M[2][3] = -2.0 * c * d

	return M

def LookAt( look, up, pos ):
	d = look.normalized()
	u = up.normalized()
	r = d.cross( u ).normalized()

	R = mathutils.Matrix( ( r, u, -d ) )
	R.transpose()
	
	return mathutils.Matrix.LocRotScale( pos, R, None )

def Angle2( v1, v2, up ):
	cross = up.cross( v1 ).normalized()
	if v2.dot( cross ) < 0.0:
		return v1.angle( v2 ) * -1.0
	return v1.angle( v2 )

def AlmostEqual( f1, f2 ):
	return abs( f1 - f2 ) <= FLOAT_EPSILON

def AlmostEqual_v2( v1, v2 ):
	return AlmostEqual( v1[0], v2[0] ) and AlmostEqual( v1[1], v2[1] )

def ProjectVector( a, b ):
	#returns vector produced by projecting a onto b.
	return b * ( a.dot( b ) / b.dot( b ) )

def CCW_Angle2D( a, b ):
	det = a[0] * b[1] - a[1] * b[0] #determinant
	return math.atan2( det, a.dot( b ) )

def HSV_to_RGB( h, s, v ):
	#input and outputs in ranges 0.0 - 1.0
	if s == 0.0:
		return ( v, v, v )
	
	i = int( h * 6.0 ) #assume int() truncates!
	f = ( h * 6.0 ) - i
	p = v * ( 1.0 - s )
	q = v * ( 1.0 - s * f )
	t = v * ( 1.0 - s * ( 1.0 - f ) )
	i %= 6

	if i == 0:
		return ( v, t, p )
	if i == 1:
		return ( q, v, p )
	if i == 2:
		return ( p, v, t )
	if i == 3:
		return ( p, q, v )
	if i == 4:
		return ( t, p, v )
	if i == 5:
		return ( v, p, q )


def EaseOutCircular( t ):
	return math.sqrt( 1.0 - math.pow( t - 1.0, 2.0 ) )


def EaseInCircular( t ):
	return 1.0 - math.sqrt( 1.0 - math.pow( t, 2.0 ) )

def TriangleArea( a, b, c ):
	u = b - a
	v = c - a

	i = u.y * v.z - u.z * v.y
	j = u.z * v.x - u.x * v.z
	k = u.x * v.y - u.y * v.x

	return math.sqrt( i * i + j * j + k * k ) * 0.5