import bpy, bmesh, mathutils, bpy_extras
from .. import rmlib

def ResetSubdivModLevels( mods ):
	for mod, level in mods.items():
		mod.levels = level

class MESH_OT_grabapplymat( bpy.types.Operator ):
	"""Sample the material of the face under the cursor and apply it to the selected faces."""
	bl_idname = 'mesh.rm_grabapplymat'
	bl_label = 'GrabApplyMat (MOS)'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel

	def __init__( self ):
		self.m_x = 0
		self.m_y = 0
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def GrabApplyEdgeWeight( self, context ):
		mouse_pos = mathutils.Vector( ( float( self.m_x ), float( self.m_y ) ) )
		
		target_rmmesh_list = []
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			target_rmmesh_list.append( rmmesh )

		mos_rmmesh = rmlib.rmMesh.from_mos( context, mouse_pos ) #used to get mat data. using eval mat data causes crash
		if mos_rmmesh is None:
			return { 'CANCELLED' }

		mos_edge_seam = None
		mos_edge_smooth = None
		bevel_weight = None
		crease_weight = None
		with mos_rmmesh as mos_rmmesh:
			mos_rmmesh.readonly = True

			mos_edges = rmlib.rmEdgeSet.from_mos( mos_rmmesh, context, mouse_pos, pixel_radius=8 )
			if len( mos_edges ) < 1:
				return { 'CANCELLED' }
		
			mos_edge_seam = mos_edges[0].seam
			mos_edge_smooth = mos_edges[0].smooth

			if bpy.app.version < (4,0,0):
				bevlayers = mos_rmmesh.bmesh.edges.layers.bevel_weight
				try:
					bev_layer = bevlayers.items()[0]
					bevel_weight = mos_edges[0][bev_layer[1]]
				except IndexError:
					pass

				crslayers = mos_rmmesh.bmesh.edges.layers.crease
				try:
					crs_layer = crslayers.items()[0]
					crease_weight = mos_edges[0][crs_layer[1]]
				except IndexError:
					pass
			else:
				bev_layer = mos_rmmesh.bmesh.edges.layers.float.get( 'bevel_weight_edge', None )
				if bev_layer is not None:
					bevel_weight = mos_edges[0][bev_layer]

				crs_layer = mos_rmmesh.bmesh.edges.layers.float.get( 'crease_edge', None )
				if crs_layer is not None:
					crease_weight = mos_edges[0][crs_layer]

		blyr = None
		clyr = None
		for rmmesh in target_rmmesh_list:
			bm = bmesh.from_edit_mesh( rmmesh.mesh )
			rmmesh.bmesh = bm
			
			if bpy.app.version < (4,0,0):
				if bevel_weight is not None:
					b_layers = rmmesh.bmesh.edges.layers.bevel_weight
					blyr = b_layers.verify()

				if crease_weight is not None:
					c_layers = rmmesh.bmesh.edges.layers.crease
					clyr = c_layers.verify()
			else:
				blyr = rmmesh.bmesh.edges.layers.float.get( 'bevel_weight_edge', None )
				if blyr is None:
					blyr = rmmesh.bmesh.edges.layers.float.new( 'bevel_weight_edge' )

				clyr = rmmesh.bmesh.edges.layers.float.get( 'crease_edge', None )
				if clyr is None:
					clyr = rmmesh.bmesh.edges.layers.float.new( 'crease_edge' )

			edges = rmlib.rmEdgeSet.from_selection( rmmesh )
			for e in edges:
				if mos_edge_seam is not None:
					e.seam = mos_edge_seam
				if mos_edge_smooth is not None:
					e.smooth = mos_edge_smooth
				if blyr is not None and bevel_weight is not None:
					e[blyr] = bevel_weight
				if clyr is not None and crease_weight is not None:
					e[clyr] = crease_weight

			bmesh.update_edit_mesh( rmmesh.mesh, loop_triangles=False, destructive=False )	

		return { 'FINISHED' }

	def GrabApplyMat( self, context ):
		mouse_pos = mathutils.Vector( ( float( self.m_x ), float( self.m_y ) ) )

		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):			
			bm = bmesh.from_edit_mesh( rmmesh.mesh )
			rmmesh.bmesh = bm

			faces = rmlib.rmPolygonSet.from_selection( rmmesh )
			if len( faces ) < 1:
				return { 'CANCELLED' }

			#get obj
			mos_rmmesh = rmlib.rmMesh.from_mos( context, mouse_pos ) #used to get mat data. using eval mat data causes crash
			if mos_rmmesh is None:
				return { 'CANCELLED' }

			#cache the levels of each subdiv mod for the mos_rmmesh and set their levels to 0
			subdiv_mods = {}
			for mod in mos_rmmesh.object.modifiers:
				if mod.type == 'SUBSURF':
					subdiv_mods[mod] = mod.levels
					mod.levels = 0

			eval_rmmesh = mos_rmmesh.GetEvaluated( context ) #used to get mos polygon after modifiers and anims

			#get the material index from the evaluated mesh under the mouse
			with eval_rmmesh as eval_rmmesh:
				eval_rmmesh.readonly = True
				try:
					source_poly = rmlib.rmPolygonSet.from_mos( eval_rmmesh, context, mouse_pos, ignore_hidden=eval_rmmesh.mesh.is_editmode )[0]
				except IndexError:
					ResetSubdivModLevels( subdiv_mods )
					print( 'ERROR :: GrabApplyMat :: from_mos failed' )
					return { 'CANCELLED' }				
				source_mat_idx = source_poly.material_index

			if len( mos_rmmesh.mesh.materials ) < 1:
				ResetSubdivModLevels( subdiv_mods )
				self.report( { 'WARNING' }, 'Material under cursor is emply!!!' )
				return { 'CANCELLED' }			

			#apply material
			match_found = False
			for i, mat in enumerate( rmmesh.object.data.materials ):
				if mat == mos_rmmesh.mesh.materials[source_mat_idx]:
					match_found = True
					for f in faces:
						f.material_index = i
					break
			if not match_found:
				rmmesh.object.data.materials.append( mos_rmmesh.mesh.materials[source_mat_idx] )
				for f in faces:
					f.material_index = len( rmmesh.object.data.materials ) - 1		

			bmesh.update_edit_mesh( rmmesh.mesh, loop_triangles=False, destructive=False )			

			ResetSubdivModLevels( subdiv_mods )

		return { 'FINISHED' }
		
	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }		

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[1]:
			return self.GrabApplyEdgeWeight( context )
		elif sel_mode[2]:
			return self.GrabApplyMat( context )
		
		return { 'CANCELLED' }

	def invoke( self, context, event ):
		self.m_x, self.m_y = event.mouse_region_x, event.mouse_region_y
		return self.execute( context )


def register():
	print( 'register :: {}'.format( MESH_OT_grabapplymat.bl_idname ) )
	bpy.utils.register_class( MESH_OT_grabapplymat )

	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_grabapplymat.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_grabapplymat )