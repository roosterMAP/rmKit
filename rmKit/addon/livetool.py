import bpy
import bmesh
import rmKit.rmlib as rmlib
import mathutils
import math

class MESH_OT_livetool( bpy.types.Operator ):    
	"""This is the tooltip for lilve tool operator"""
	bl_idname = 'mesh.livetool'
	bl_label = 'Live Tool'
	bl_options = { 'REGISTER', 'UNDO' }
	
	level: bpy.props.IntProperty(
		name='Level',
		description='Number of radial steps.',
		default=6,
		min=3,
		max=64
	)
	radius: bpy.props.FloatProperty(
		name='Radius',
		description='Radus of disk',
		default=1.0,
		min=0.0
	)

	def __init__( self ):
		self.bmesh = None

	def __del__( self ):
		if self.bmesh is not None:
			self.bmesh.free()
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )
		
		bm = self.bmesh.copy()
		
		origin = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
		v0 = bm.verts.new( origin )
		vertList = []
		for i in range( self.level ):
			theta = math.pi * 2.0 / self.level * i
			vec = mathutils.Vector( ( math.cos( theta ), math.sin( theta ), 0.0 ) )
			pos = vec * self.radius
			vertList.append( bm.verts.new( pos ) )

		for i in range( self.level ):
			bm.faces.new( ( v0, vertList[i-1], vertList[i] ) )

		targetMesh = context.active_object.data
		bm.to_mesh( targetMesh )
		bm.calc_loop_triangles()
		targetMesh.update()
		bm.free()
		
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )
		
		return { 'FINISHED' }
	
	def invoke( self, context, event ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readme = True
				self.bmesh = rmmesh.bmesh.copy()
				
		return self.execute( context )


def register():
	bpy.utils.register_class( MESH_OT_livetool )
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_livetool )
	
if __name__ == '__main__':
	register()