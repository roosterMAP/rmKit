import bpy
import bpy_extras
import rmlib
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
		clipboard_mesh.materials.clear()
			
		temp_bmesh = bmesh.new()
		temp_bmesh = rmmesh.bmesh.copy()
		
		selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
		selected_polygon_indexes = [ p.index for p in selected_polys ]
		
		mat_indexes = []
		delPolys = rmlib.rmPolygonSet()
		for i, p in enumerate( temp_bmesh.faces ):
			if i in selected_polygon_indexes:
				if p.material_index not in mat_indexes:
					mat_indexes.append( p.material_index )
				p.material_index = mat_indexes.index( p.material_index )
			else:
				delPolys.append( p )
		bmesh.ops.delete( temp_bmesh, geom=delPolys, context='FACES' )

		#bring clipboard_mesh into world space
		xfrm = rmmesh.world_transform
		for v in temp_bmesh.verts:
			v.co = xfrm @ v.co.copy()
		
		temp_bmesh.to_mesh( clipboard_mesh )

		if len( rmmesh.mesh.materials ) > 0:
			for old_idx in mat_indexes:
				clipboard_mesh.materials.append( rmmesh.mesh.materials[old_idx] )
		
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
		rmmesh.bmesh.verts.ensure_lookup_table()
		for p in rmmesh.bmesh.faces:
			p.select = False
			
		rmmesh.bmesh.from_mesh( clipboard_mesh )
		rmmesh.bmesh.verts.ensure_lookup_table()

		#map material indexes from clipboard_mesh to rmmesh and add new mats to rmmesh
		mat_lookup = []
		for clip_mat in clipboard_mesh.materials:
			matFound = False
			for i, src_mat in enumerate( rmmesh.mesh.materials ):				
				if clip_mat == src_mat:
					mat_lookup.append( i )
					matFound = True
					break
			if not matFound:
				mat_lookup.append( len( rmmesh.mesh.materials ) )
				rmmesh.mesh.materials.append( clip_mat )				

		paste_faces = rmlib.rmPolygonSet.from_selection( rmmesh )

		#reassign material indexes
		if len( mat_lookup ) > 0:
			for f in paste_faces:
				f.material_index = mat_lookup[ f.material_index ]

		#transform paste verts
		xfrm_inv = rmmesh.world_transform.inverted()
		for v in paste_faces.vertices:
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
	bpy.utils.register_class( MESH_OT_rm_copy )
	bpy.utils.register_class( MESH_OT_rm_paste )	
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_rm_copy )
	bpy.utils.unregister_class( MESH_OT_rm_paste )
	

if __name__ == '__main__':
	register()