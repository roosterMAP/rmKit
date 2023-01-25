import bpy
import bpy_extras
from .. import rmlib
import math
import mathutils
import bmesh

def copy( context, cut=False ):	
	rmmesh = rmlib.rmMesh.GetActive( context )
	if rmmesh is None:
		return
	
	with rmmesh as rmmesh:
		rmmesh.readonly = not cut
		
		clipboard_mesh = None
		for m in bpy.data.meshes:
			if m.name == 'clipboard_mesh':
				clipboard_mesh = m
				break
		if clipboard_mesh is None:
			clipboard_mesh = bpy.data.meshes.new( 'clipboard_mesh' )
		clipboard_mesh.clear_geometry()
			
		temp_bmesh = bmesh.new()
		temp_bmesh = rmmesh.bmesh.copy()
		
		selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
		selected_polygon_indexes = [ p.index for p in selected_polys ]
		
		delPolys = rmlib.rmPolygonSet()
		for i, p in enumerate( temp_bmesh.faces ):
			if i not in selected_polygon_indexes:
				delPolys.append( p )
		bmesh.ops.delete( temp_bmesh, geom=delPolys, context='FACES' )

		#bring clipboard_mesh into world space
		xfrm = rmmesh.world_transform
		for v in temp_bmesh.verts:
			v.co = xfrm @ v.co.copy()
		
		temp_bmesh.to_mesh( clipboard_mesh )
		
		if cut:
			bmesh.ops.delete( rmmesh.bmesh, geom=selected_polys, context='FACES' )
		
		
def paste( context ):
	clipboard_mesh = None
	for m in bpy.data.meshes:
		if m.name == 'clipboard_mesh':
			clipboard_mesh = m
			break
	if clipboard_mesh is None:
		return { 'CANCELLED' }
		
	rmmesh = rmlib.rmMesh.GetActive( context )
	if rmmesh is None:
		return
	with rmmesh as rmmesh:
		for p in rmmesh.bmesh.faces:
			p.select = False
		
		vcount = len( rmmesh.bmesh.verts )
		rmmesh.bmesh.from_mesh( clipboard_mesh )
		rmmesh.bmesh.verts.ensure_lookup_table()
		xfrm_inv = rmmesh.world_transform.inverted()
		for i in range( vcount, len( rmmesh.bmesh.verts ) ):
			v = rmmesh.bmesh.verts[i]
			v.co = xfrm_inv @ mathutils.Vector( v.co )
	
	
class MESH_OT_rm_copy( bpy.types.Operator ):
	"""Runs copybuffer in object mode. In polygon mode is copies/cuts the polygon selection to the clipboard."""
	bl_idname = 'mesh.rm_copy'
	bl_label = 'Copy'

	cut: bpy.props.BoolProperty(
			name='Cut',
			default=False
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and context.object is not None )
		
	def execute( self, context ):
		if context.object.type == 'MESH' and context.object.data.is_editmode:
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if sel_mode[1]:
				bpy.ops.mesh.rm_connectedge('INVOKE_DEFAULT')
			elif sel_mode[2]:
				copy( context, self.cut )
		else:
			bpy.ops.view3d.copybuffer()

		return { 'FINISHED' }
	

class MESH_OT_rm_paste( bpy.types.Operator ):
	"""Runs pastebuffer in object mode. In polygon mode is pastes the polygon selection into the current mesh."""
	bl_idname = 'mesh.rm_paste'
	bl_label = 'Paste'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and context.object is not None )
		
	def execute( self, context ):
		if context.object.type == 'MESH' and context.object.data.is_editmode:
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if sel_mode[2]:
				paste( context )
		else:
			bpy.ops.view3d.pastebuffer()
		return { 'FINISHED' }
	

def register():
	print( 'register :: {}'.format( MESH_OT_rm_copy.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_rm_paste.bl_idname ) )
	bpy.utils.register_class( MESH_OT_rm_copy )
	bpy.utils.register_class( MESH_OT_rm_paste )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_rm_copy.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_rm_paste.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_rm_copy )
	bpy.utils.unregister_class( MESH_OT_rm_paste )
	

if __name__ == '__main__':
	register()