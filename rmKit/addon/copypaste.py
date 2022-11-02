import bpy
import bpy_extras
import rmKit.rmlib as rmlib
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
		
		rmmesh.bmesh.from_mesh( clipboard_mesh )
	
	
class MESH_OT_rm_copy( bpy.types.Operator ):
	bl_idname = 'mesh.rm_copy'
	bl_label = 'Copy'

	cut: bpy.props.BoolProperty(
			name='Cut',
			default=False
	)
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[1]:
			bpy.ops.mesh.rm_connectedge('INVOKE_DEFAULT')
		elif sel_mode[2]:
			copy( context, self.cut )
		return { 'FINISHED' }
	

class MESH_OT_rm_paste( bpy.types.Operator ):
	bl_idname = 'mesh.rm_paste'
	bl_label = 'Paste'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		paste( context )
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