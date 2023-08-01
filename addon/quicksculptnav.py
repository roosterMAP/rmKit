import bpy, mathutils, bpy_extras


def visible_objects_and_duplis( context ):
	"""Loop over (object, matrix) pairs (mesh only)"""

	depsgraph = context.evaluated_depsgraph_get()
	for dup in depsgraph.object_instances:
		if dup.is_instance:  # Real dupli instance
			obj = dup.instance_object
			yield (obj, dup.matrix_world.copy())
		else:  # Usual object
			obj = dup.object
			yield (obj, obj.matrix_world.copy())
		

def obj_ray_cast(obj, matrix, ray_origin, ray_target):
	"""Wrapper for ray casting that moves the ray into object space"""

	# get the ray relative to the object
	matrix_inv = matrix.inverted()
	ray_origin_obj = matrix_inv @ ray_origin
	ray_target_obj = matrix_inv @ ray_target
	ray_direction_obj = ray_target_obj - ray_origin_obj

	# cast the ray
	success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)

	if success:
		return location, normal, face_index
	else:
		return None, None, None


class VIEW3D_OT_quicknavigate( bpy.types.Operator ):
	'''Passes a navigation if cursor is over empty space. Otherwise passes a click'''
	bl_idname = 'view3d.rm_quicknav'
	bl_label = 'Quick SculptNav'

	nav: bpy.props.EnumProperty(
		items=[ ( "rot", "Rotate", "", 1 ),
				( "scl", "Scale", "", 2 ),
				( "pan", "Pan", "", 3 ) ],
		name="NavAction",
		default="rot"
	)

	@classmethod
	def poll( cls, context ):
		return context.area.type == 'VIEW_3D'
		
	def execute( self, context ):
		return { 'FINISHED' }

	def invoke( self, context, event ):
		# get the context arguments
		scene = context.scene
		region = context.region
		rv3d = context.region_data
		coord = event.mouse_region_x, event.mouse_region_y

		# get the ray from the viewport and mouse
		view_vector = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
		ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
		ray_target = ray_origin + view_vector
		
		# determine if a hit occired
		hit = False
		for obj, matrix in visible_objects_and_duplis( context ):
			if obj.type == 'MESH':
				success, normal, face_index = obj_ray_cast(obj, matrix, ray_origin, ray_target)
				if success is not None:
					hit = True

		#dispatch brush stroke or nav ops
		if hit:
			if self.nav == 'rot':
				bpy.ops.sculpt.brush_stroke( 'INVOKE_DEFAULT', mode='NORMAL' )
			elif self.nav == 'scl':
				bpy.ops.sculpt.brush_stroke( 'INVOKE_DEFAULT', mode='SMOOTH' )
			else:
				bpy.ops.sculpt.brush_stroke( 'INVOKE_DEFAULT', mode='NORMAL' )
		else:
			if self.nav == 'rot':
				bpy.ops.view3d.rotate( 'INVOKE_DEFAULT' )
			elif self.nav == 'scl':
				bpy.ops.view3d.zoom( 'INVOKE_DEFAULT' )
			else:
				bpy.ops.view3d.move( 'INVOKE_DEFAULT' )

		#reset to default (modkeyless nav op)
		self.nav = 'rot'
		
		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( VIEW3D_OT_quicknavigate.bl_idname ) )
	bpy.utils.register_class( VIEW3D_OT_quicknavigate )
	
def unregister():
	print( 'unregister :: {}'.format( VIEW3D_OT_quicknavigate.bl_idname ) )
	bpy.utils.unregister_class( VIEW3D_OT_quicknavigate )