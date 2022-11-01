import bpy
import bpy_extras
import rmKit.rmlib as rmlib
import math
import mathutils
import bmesh

def v2_dist( v1, v2 ):
	a = abs( v1[0] - v2[0] )
	b = abs( v1[1] - v2[1] )
	return math.sqrt( float( a * a + b * b ) )

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

class MESH_OT_test( bpy.types.Operator ):
	"""Mesh editing operator that modifies topology based off selection and context."""
	bl_idname = 'mesh.test'
	bl_label = 'PolyPatch'
	bl_options = { 'UNDO' }
	
	mouse_pos: bpy.props.FloatVectorProperty(
		name='Mouse Pos',
		size=2,
		default=( 0.0, 0.0 )
	)

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }

		look_pos = bpy_extras.view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, self.mouse_pos )
		look_vec = bpy_extras.view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, self.mouse_pos )
		
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }		
		item_transform = rmmesh.world_transform
		
		ignore_backfacing = True
		pixel_radius = 16

		with rmmesh as rmmesh:
			rmmesh.readonly = True
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if sel_mode[0]:
				verts = rmlib.rmVertexSet()
				selected_verts = rmlib.rmVertexSet.from_mesh( rmmesh=rmmesh, filter_hidden=True )
				for v in selected_verts:
					if ignore_backfacing and v.normal.dot( look_vec ) > 0.0:
						continue
					pos_wld = v.co @ rmmesh.world_transform
					sp = bpy_extras.view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos_wld )
					if v2_dist( sp, self.mouse_pos ) <= float( pixel_radius ):
						verts.append( v )
						
				for v in verts:
					v.select = True
						
			if sel_mode[1]:
				edges = rmlib.rmEdgeSet()
				selected_edges = rmlib.rmEdgeSet.from_mesh( rmmesh=rmmesh, filter_hidden=True )
				for e in selected_edges:
					ept1, ept2 = e.verts
					if ignore_backfacing and ept1.normal.dot( look_vec ) > 0.0 and ept2.normal.dot( look_vec ) > 0.0:
						continue
					pos1_wld = ept1.co @ rmmesh.world_transform
					pos2_wld = ept2.co @ rmmesh.world_transform
					sp1 = bpy_extras.view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos1_wld )
					sp2 = bpy_extras.view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos2_wld )
					if line2_dist( mathutils.Vector( sp1 ), mathutils.Vector( sp2 ), mathutils.Vector( self.mouse_pos ) ) <= float( pixel_radius ):
						edges.append( e )
						
				for e in edges:
					e.select = True
					
			if sel_mode[2]:
				bvh = mathutils.bvhtree.BVHTree.FromBMesh( rmmesh.bmesh )
				polys = rmlib.rmPolygonSet()
				world_transform_inv = rmmesh.world_transform.inverted()
				cam_pos_obj = look_pos @ world_transform_inv					
				look_vec_obj = look_vec @ world_transform_inv.to_3x3()
				print( cam_pos_obj, look_vec_obj )
				location, normal, index, distance = bvh.ray_cast( cam_pos_obj, look_vec_obj )
				if location is not None:
					p = rmmesh.bmesh.faces[index]
					if ignore_backfacing and p.normal.dot( look_vec ) < 0.0:
						polys.append( p )
						
				for p in polys:
					p.select = True
					
		return { 'FINISHED' }
	
	def invoke(self, context, event):
		x, y = event.mouse_region_x, event.mouse_region_y
		self.mouse_pos = ( x, y )
		return self.execute(context)

def register():
	bpy.utils.register_class( MESH_OT_test )
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_test )
	
if __name__ == '__main__':
	register()