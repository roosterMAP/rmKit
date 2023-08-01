import bpy, mathutils, bpy_extras

class MESH_OT_quicknavigate( bpy.types.Operator ):
	'''Passes a navigation if cursor is over empty space. Otherwise passes a click'''
	bl_idname = 'mesh.rm_quicknav'
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
		m_x, m_y = event.mouse_region_x, event.mouse_region_y
		mouse_pos = mathutils.Vector( ( float( m_x ), float( m_y ) ) )
		
		look_pos = bpy_extras.view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_pos )
		look_vec = bpy_extras.view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_pos )

		depsgraph = context.evaluated_depsgraph_get()
		depsgraph.update()
		hit, loc, nml, idx, obj, mat = context.scene.ray_cast( depsgraph, look_pos, look_vec )
		if hit:
			if self.nav == 'rot':
				bpy.ops.sculpt.brush_stroke( 'INVOKE_DEFAULT', mode='NORMAL' )
			elif self.nav == 'scl':
				bpy.ops.sculpt.brush_stroke( 'INVOKE_DEFAULT', mode='SMOOTH' )
			else:
				bpy.ops.sculpt.brush_stroke( 'INVOKE_DEFAULT', mode='NORMAL' )
		else:
			if self.nav == 'rot':
				print( self.nav )
				bpy.ops.view3d.rotate( 'INVOKE_DEFAULT' )
			elif self.nav == 'scl':
				bpy.ops.view3d.zoom( 'INVOKE_DEFAULT' )
			else:
				print( 'pan' )
				bpy.ops.view3d.move( 'INVOKE_DEFAULT' )
		self.nav = 'rot'
		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_quicknavigate.bl_idname ) )
	bpy.utils.register_class( MESH_OT_quicknavigate )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_quicknavigate.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_quicknavigate )