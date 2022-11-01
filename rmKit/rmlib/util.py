import bpy
import mathutils
import bpy_extras
import math

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
		self.__space = context.area.spaces.active

	@property
	def cam_pos( self ):
		return self.__space.region_3d.view_matrix.inverted().translation

	@property
	def look_dir( self ):
		return self.__space.region_3d.view_rotation @ mathutils.Vector( ( 0.0, 0.0, -1.0 ) )

	def cursor_to_ray( self, context, mouse_pos ):
		ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_pos )
		ray_dir = bpy_extras.view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_pos )
		return ( ray_origin, ray_dir )

	def is_view3d( self ):
		return self.__space.type == 'VIEW_3D'

	def is_uvview( self ):
		return self.__space.type == 'IMAGE_EDITOR'

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
	a = abs( pN.dot( p ) + d )
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