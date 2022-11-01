import bpy
import bmesh
import rmKit.rmlib as rmlib
import mathutils
import math

def ScaleLine( p0, p1, scale ):
	v = p1 - p0
	m = v.length
	v.normalize()
	p0 -= v * m * 0.5 * scale
	p1 += v * m * 0.5 * scale
	return ( p0, p1 )

class MESH_OT_arcadjust( bpy.types.Operator ):
	bl_idname = 'mesh.rm_arcadjust'
	bl_label = 'Arc Adjust'
	bl_options = { 'REGISTER', 'UNDO' }
	
	scale: bpy.props.FloatProperty(
		name='Scale',
		description='Scale applied to selected arc',
		default=1.0
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
		
		edges = rmlib.rmEdgeSet( [ e for e in bm.edges if e.select ] )
		chains = edges.chain()
		for chain in chains:
			if len( chain ) < 3:
				continue

			a, b = ScaleLine( chain[0][0].co.copy(), chain[0][1].co.copy(), 10000.0 )
			c, d = ScaleLine( chain[-1][0].co.copy(), chain[-1][1].co.copy() , 10000.0 )
			p0, p1 = mathutils.geometry.intersect_line_line( a, b, c, d )
			c = ( p0 + p1 ) * 0.5
			s = mathutils.Matrix.Identity( 3 )
			s[0][0] = self.scale
			s[1][1] = self.scale
			s[2][2] = self.scale

			verts = rmlib.rmVertexSet( [ pair[0] for pair in chain[1:] ] )
			for v in verts:
				print( v.co )
				pos = v.co - c
				pos = s @ pos
				v.co = pos + c
				print( pos )

			if abs( self.scale ) <= 0.0000001:
				bmesh.ops.remove_doubles( bm, verts=verts, dist=0.00001 )

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

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readme = True
				self.bmesh = rmmesh.bmesh.copy()
				
		return self.execute( context )


def register():
	bpy.utils.register_class( MESH_OT_arcadjust )
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_arcadjust )