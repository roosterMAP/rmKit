import bpy

class MESH_OT_hello_world( bpy.types.Operator ):    
	"""This is the tooltip for custom operator"""
	bl_idname = 'mesh.helloworld'
	bl_label = 'Hello World'
	bl_options = { 'REGISTER', 'UNDO' } #tell blender that we support the undo/redo pannel
	
	count_x: bpy.props.IntProperty(
		name='X',
		description='Number of monkeys in X dir.',
		default=3,
		min=1,
		max=10
	)
	count_y: bpy.props.IntProperty(
		name='Y',
		description='Number of monkeys in Y dir.',
		default=2,
		min=1,
		max=10
	)
	size: bpy.props.FloatProperty(
		name='Size',
		description='Size of each monkey.',
		default=0.2,
		min=0.0,
		max=1.0
	)
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return context.area.type == 'VIEW_3D'
		
	def execute( self, context ):
		#Called when operator is run as a cmd/hotkey.
		for i in range( self.count_x * self.count_y ):
			x = i % self.count_x
			y = i // self.count_x
			bpy.ops.mesh.primitive_monkey_add( size=self.size, location=( x, y, 0.0 ) )
		return { 'FINISHED' }
	
	'''
	def invoke( self, context, event ):
		#Called when operator is run from a button or UI element.
		pass
	
	def modal( self, context, event ):
		#Used for live tools where cmd is continuously called and evaluated based on user unput.
		pass
	'''
	
def register():
	bpy.utils.register_class( MESH_OT_hello_world )
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_hello_world )
	
if __name__ == '__main__':
	register()