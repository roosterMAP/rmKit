import bpy, bmesh, mathutils, bpy_extras
import rmKit.rmlib as rmlib


def GrabApplyEdgeWeight( target_rmmesh, context, mouse_pos ):
	look_pos = bpy_extras.view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_pos )
	look_vec = bpy_extras.view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_pos )

	depsgraph = context.evaluated_depsgraph_get()
	depsgraph.update()
	hit, loc, nml, idx, obj, mat = context.scene.ray_cast( depsgraph, look_pos, look_vec )
	if not hit:
		return { 'CANCELLED' }

	bevel_weight = None
	crease_weight = None
	mos_rmmesh = rmlib.rmMesh( obj )
	with mos_rmmesh as mos_rmmesh:
		mos_rmmesh.readonly = True

		mos_edges = rmlib.rmEdgeSet.from_mos( mos_rmmesh, context, mouse_pos, pixel_radius=8 )
		if len( mos_edges ) < 1:
			return { 'CANCELLED' }

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

	blyr = None
	clyr = None
	with target_rmmesh as rmmesh:
		if bevel_weight is not None:
			b_layers = rmmesh.bmesh.edges.layers.bevel_weight
			blyr = b_layers.verify()

		if crease_weight is not None:
			c_layers = rmmesh.bmesh.edges.layers.crease
			clyr = c_layers.verify()

	with target_rmmesh as rmmesh:
		edges = rmlib.rmEdgeSet.from_selection( rmmesh )
		for e in edges:
			if blyr is not None:
				e[blyr] = bevel_weight
			if clyr is not None:
				e[clyr] = crease_weight


def GrabApplyMat( target_rmmesh, context, mouse_pos ):
	with target_rmmesh as rmmesh:
		faces = rmlib.rmPolygonSet.from_selection( rmmesh )
		if len( faces ) < 1:
			return { 'CANCELLED' }

		look_pos = bpy_extras.view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_pos )
		look_vec = bpy_extras.view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_pos )

		depsgraph = context.evaluated_depsgraph_get()
		depsgraph.update()
		hit, loc, nml, idx, obj, mat = context.scene.ray_cast( depsgraph, look_pos, look_vec )
		if not hit:
			return { 'CANCELLED' }

		if obj == rmmesh.object:
			try:
				source_poly = rmlib.rmPolygonSet.from_mos( rmmesh, context, mouse_pos )[0]
			except IndexError:
				print( 'ERROR :: GrabApplyMat :: from_mos failed' )
				return { 'CANCELLED' }				
			source_mat_idx = source_poly.material_index
			for f in faces:
				f.material_index = source_mat_idx
		else:
			other_rmmesh = rmlib.rmMesh( obj )
			with other_rmmesh as other_rmmesh:
				other_rmmesh.readonly = True
				try:
					source_poly = rmlib.rmPolygonSet.from_mos( rmmesh, context, mouse_pos )[0]
				except IndexError:
					print( 'ERROR :: GrabApplyMat :: from_mos failed' )
					return { 'CANCELLED' }
				source_mat_idx = source_poly.material_index
				match_found = False
				for i, mat in enumerate( rmmesh.object.data.materials ):
					if mat.name_full == obj.data.materials[source_mat_idx].name_full:
						match_found = True
						for f in faces:
							f.material_index = i	
						break
				if not match_found:
					rmmesh.object.data.materials.append( obj.data.materials[source_mat_idx] )
					for f in faces:
						f.material_index = len( rmmesh.object.data.materials ) - 1


class MESH_OT_grabapplymat( bpy.types.Operator ):
	bl_idname = 'mesh.rm_grabapplymat'
	bl_label = 'GrabApplyMat (MOS)'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel

	def __init__( self ):
		self.m_x = 0
		self.m_y = 0
	
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

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }

		mouse_pos = mathutils.Vector( ( float( self.m_x ), float( self.m_y ) ) )

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			return { 'CANCELLED' }
		elif sel_mode[1]:
			GrabApplyEdgeWeight( rmmesh, context, mouse_pos )
		elif sel_mode[2]:
			GrabApplyMat( rmmesh, context, mouse_pos )
		else:
			return { 'CANCELLED' }

		return { 'FINISHED' }

	def invoke( self, context, event ):
		self.m_x, self.m_y = event.mouse_region_x, event.mouse_region_y
		return self.execute( context )


def register():
	print( 'register :: {}'.format( MESH_OT_grabapplymat.bl_idname ) )
	bpy.utils.register_class( MESH_OT_grabapplymat )

	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_grabapplymat.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_grabapplymat )