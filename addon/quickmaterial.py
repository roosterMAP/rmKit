import bpy, bmesh, mathutils, bpy_extras
import rmKit.rmlib as rmlib

MAT_PROP_UPDATED = False

class MESH_OT_quickmaterial( bpy.types.Operator ):
	"""Utility for quickly sampling, modifying, and creating materials for 3d viewport."""
	bl_idname = 'mesh.rm_quickmaterial'
	bl_label = 'Quick Material'
	bl_options = { 'UNDO' }

	new_name: bpy.props.StringProperty( name='Name' )

	@classmethod
	def poll( cls, context ):
		return context.area.type == 'VIEW_3D'
		
	def execute( self, context ):		
		material = bpy.context.scene.quickmatprops["prop_mat"]
		
		if material is None:
			if self.new_name.strip() == '':
				return { 'CANCELLED' }
			material = bpy.data.materials.new( name=self.new_name.strip() )
		
		global MAT_PROP_UPDATED
		if MAT_PROP_UPDATED:
			material.diffuse_color = bpy.context.scene.quickmatprops["prop_col"]
			material.metallic = bpy.context.scene.quickmatprops["prop_met"]
			material.roughness = bpy.context.scene.quickmatprops["prop_rog"]
			material["WorldMappingWidth"] = bpy.context.scene.quickmatprops["prop_width"]
			material["WorldMappingHeight"] = bpy.context.scene.quickmatprops["prop_height"]
			
		if not context.object.data.is_editmode:
			return { 'FINISHED' }
		
		if context.object is None or context.object.type != 'MESH':
			return { 'FINISHED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[2]:
			rmmesh = rmlib.rmMesh.GetActive( context )
			if rmmesh is None:
				return { 'FINISHED' }
			with rmmesh as rmmesh:
				match_found = False
				for i, mat in enumerate( rmmesh.mesh.materials ):
					if mat is not None  and mat.name_full == material.name_full:
						match_found = True
						break
				if match_found:
					selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
					for p in selected_polys:
						p.material_index = i
				else:
					rmmesh.mesh.materials.append( material )
					selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
					for p in selected_polys:
						p.material_index = len( rmmesh.mesh.materials ) - 1

		return { 'FINISHED' }

	def draw( self, context ):
		layout= self.layout
		layout.prop( context.scene.quickmatprops, "prop_mat" )
		layout.separator( factor=0.1 )
		box = layout.box()
		material = bpy.context.scene.quickmatprops["prop_mat"]
		if material is None:
			box.prop( self, "new_name" )
		box.prop( context.scene.quickmatprops, "prop_col" )
		box.prop( context.scene.quickmatprops, "prop_met" )
		box.prop( context.scene.quickmatprops, "prop_rog" )
		box.prop( context.scene.quickmatprops, "prop_width" )
		box.prop( context.scene.quickmatprops, "prop_height" )
		layout.separator( factor=1 )

	def invoke( self, context, event ):
		m_x, m_y = event.mouse_region_x, event.mouse_region_y
		mouse_pos = mathutils.Vector( ( float( m_x ), float( m_y ) ) )
		
		look_pos = bpy_extras.view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_pos )
		look_vec = bpy_extras.view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_pos )

		depsgraph = context.evaluated_depsgraph_get()
		depsgraph.update()
		hit, loc, nml, idx, obj, mat = context.scene.ray_cast( depsgraph, look_pos, look_vec )
		set_defaults = True
		if hit and len( obj.data.materials ) > 0:
			mat_idx = 0
			rmmesh = rmlib.rmMesh( obj )
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				try:
					source_poly = rmlib.rmPolygonSet.from_mos( rmmesh, context, mouse_pos )[0]
				except IndexError:
					print( 'ERROR :: QuickMat INVOKE :: from_mos failed' )
					return { 'CANCELLED' }
				mat_idx = source_poly.material_index
			try:
				material = obj.data.materials[mat_idx]
			except IndexError:
				material = obj.data.materials[0]
			bpy.context.scene.quickmatprops["prop_mat"] = material
			bpy.context.scene.quickmatprops["prop_col"] = material.diffuse_color
			bpy.context.scene.quickmatprops["prop_met"] = material.metallic
			bpy.context.scene.quickmatprops["prop_rog"] = material.roughness
			try:
				bpy.context.scene.quickmatprops["prop_width"] = material["WorldMappingWidth"]
				bpy.context.scene.quickmatprops["prop_height"] = material["WorldMappingHeight"]
			except KeyError:
				bpy.context.scene.quickmatprops["prop_width"] = 2.0
				bpy.context.scene.quickmatprops["prop_height"] = 2.0
		else:			
			bpy.context.scene.quickmatprops["prop_mat"] = None
			bpy.context.scene.quickmatprops["prop_col"] = ( 0.5, 0.5, 0.5, 1.0 )
			bpy.context.scene.quickmatprops["prop_met"] = 0.0
			bpy.context.scene.quickmatprops["prop_rog"] = 0.4
			bpy.context.scene.quickmatprops["prop_width"] = 2.0
			bpy.context.scene.quickmatprops["prop_height"] = 2.0
		return context.window_manager.invoke_props_dialog( self, width=230 )
	
	
def mat_search_changed( self, context ):
	global MAT_PROP_UPDATED
	MAT_PROP_UPDATED = False
	material = self["prop_mat"]
	if material is not None:
		self["prop_col"] = material.diffuse_color
		self["prop_met"] = material.metallic
		self["prop_rog"] = material.roughness
		try:
			self["prop_width"] = material["WorldMappingWidth"]
			self["prop_height"] = material["WorldMappingHeight"]
		except KeyError:
			self["prop_width"] = 2.0
			self["prop_height"] = 2.0
	else:
		self["prop_col"] = ( 0.5, 0.5, 0.5, 1.0 )
		self["prop_met"] = 0.0
		self["prop_rog"] = 0.4
		self["prop_width"] = 2.0
		self["prop_height"] = 2.0
		
		
def mat_prop_changed( self, context ):
	global MAT_PROP_UPDATED
	MAT_PROP_UPDATED = True
	
	
class QuickMatProps( bpy.types.PropertyGroup ):
	prop_mat: bpy.props.PointerProperty( name="Material", type=bpy.types.Material, update=lambda self, context : mat_search_changed( self, context ) )
	prop_col: bpy.props.FloatVectorProperty( name="Color", subtype= 'COLOR_GAMMA', size=4, default=( 0.5, 0.5, 0.5, 1.0 ), update=lambda self, context : mat_prop_changed( self, context ) )
	prop_met: bpy.props.FloatProperty( name='Metallic', default=0.0, min=0.0, max=1.0, update=lambda self, context : mat_prop_changed( self, context ) )
	prop_rog: bpy.props.FloatProperty( name='Roughness', default=0.4, min=0.0, max=1.0, update=lambda self, context : mat_prop_changed( self, context ) )
	prop_width: bpy.props.FloatProperty( name='World Width', default=2.0, min=0.0, subtype='DISTANCE', unit='LENGTH', update=lambda self, context : mat_prop_changed( self, context ) )
	prop_height: bpy.props.FloatProperty( name='World Height', default=2.0, min=0.0, subtype='DISTANCE', unit='LENGTH', update=lambda self, context : mat_prop_changed( self, context ) )

	
def register():
	print( 'register :: {}'.format( MESH_OT_quickmaterial.bl_idname ) )
	bpy.utils.register_class( MESH_OT_quickmaterial )
	bpy.utils.register_class( QuickMatProps )
	bpy.types.Scene.quickmatprops = bpy.props.PointerProperty( type=QuickMatProps )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_quickmaterial.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_quickmaterial )
	bpy.utils.unregister_class( QuickMatProps )
	del bpy.types.Scene.quickmatprops