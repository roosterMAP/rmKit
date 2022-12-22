import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib
import math

def clear_tags( rmmesh ):
	for v in rmmesh.bmesh.verts:
		v.tag = False
	for e in rmmesh.bmesh.edges:
		e.tag = False
	for f in rmmesh.bmesh.faces:
		f.tag = False
		for l in f.loops:
			l.tag = False

class MESH_OT_scaleislandrelative( bpy.types.Operator ):
	"""Scale Selected UV Islands Relative to Onanother"""
	bl_idname = 'mesh.rm_relativeislands'
	bl_label = 'Relative Islands'
	bl_options = { 'UNDO' }

	relative: bpy.props.EnumProperty(
		items=[ ( "avg", "Average", "", 1 ),
				( "min", "Minimum", "", 2 ),
				( "max", "Maximum", "", 3 ) ],
		name="Mode",
		default="avg"
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def draw( self, context ):
		layout= self.layout
		layout.prop( self, 'relative' )

	def invoke( self, context, event ):
		wm = context.window_manager
		return wm.invoke_props_dialog( self )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			clear_tags( rmmesh )

			#get face selection from uv loop selection
			faces = rmlib.rmPolygonSet()
			sel_sync = context.tool_settings.use_uv_select_sync
			if sel_sync:
				sel_mode = context.tool_settings.mesh_select_mode[:]
				if sel_mode[2]:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
				else:
					return { 'CANCELLED' }
			else:
				sel_mode = context.tool_settings.uv_select_mode
				if sel_mode == 'FACE':
					loops = rmlib.rmUVLoopSet.from_selection( rmmesh, uvlayer=uvlayer )
					loop_faces = set()
					for l in loops:
						loop_faces.add( l.face )
						l.tag = True
					for f in loop_faces:
						all_loops_tagged = True
						for l in f.loops:
							if not l.tag:
								all_loops_tagged = False
							else:
								l.tag = False
						if all_loops_tagged:
							faces.append( f )
				else:
					return { 'CANCELLED' }

			if len( faces ) < 1:
				return { 'CANCELLED' }

			#create list of uvislands and compute a density ( 3darea/uvarea ) for each
			tri_loops = rmmesh.bmesh.calc_loop_triangles()
			islands = faces.island( uvlayer )
			densities = []
			for island in islands:
				island_uvarea = 0.0
				for tri in tri_loops:
					uv1 = mathutils.Vector( tri[0][uvlayer].uv )
					uv2 = mathutils.Vector( tri[1][uvlayer].uv )
					uv3 = mathutils.Vector( tri[2][uvlayer].uv )
					uvarea = mathutils.geometry.area_tri( uv1, uv2, uv3 )
					island_uvarea += uvarea

				island_3darea = 0.0
				for f in island:
					island_3darea += f.calc_area()

				densities.append( island_uvarea / island_3darea )

			#compute a target density from self.relative mode
			target_density = densities[0]
			for d in densities:
				if self.relative == 'min':
					target_density = min( d, target_density )
				elif self.relative == 'max':
					target_density = max( d, target_density )
				else:
					target_density += d
			if self.relative == 'avg':
				target_density -= densities[0]
				target_density /= len( densities )

			#set the density of all islands to the target
			for i, island in enumerate( islands ):
				scale_factor = math.sqrt( target_density / densities[i] )

				island_center = mathutils.Vector( ( 0.0, 0.0 ) )
				lcount = 0
				for f in island:
					for l in f.loops:
						island_center += mathutils.Vector( l[uvlayer].uv )
						lcount += 1
				island_center = island_center * ( 1.0 / lcount )

				for f in island:
					for l in f.loops:
						uv = mathutils.Vector( l[uvlayer].uv )
						uv -= island_center
						uv *= scale_factor
						uv += island_center
						l[uvlayer].uv = uv

			clear_tags( rmmesh )

		return { 'FINISHED' }


class MESH_OT_scaletotexeldensity( bpy.types.Operator ):
	"""Scale Selected UV Islands to target Texel Density"""
	bl_idname = 'mesh.rm_scaletotexeldensity'
	bl_label = 'Scale to Texel Density'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( ( context.area.type == 'VIEW_3D' or context.area.type == 'IMAGE_EDITOR' ) and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			clear_tags( rmmesh )

			#get face selection from uv loop selection
			faces = rmlib.rmPolygonSet()
			sel_sync = context.tool_settings.use_uv_select_sync
			if sel_sync or context.area.type == 'VIEW_3D':
				sel_mode = context.tool_settings.mesh_select_mode[:]
				if sel_mode[2]:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )
				else:
					return { 'CANCELLED' }
			else:
				sel_mode = context.tool_settings.uv_select_mode
				if sel_mode == 'FACE':
					loops = rmlib.rmUVLoopSet.from_selection( rmmesh, uvlayer=uvlayer )
					loop_faces = set()
					for l in loops:
						loop_faces.add( l.face )
						l.tag = True
					for f in loop_faces:
						all_loops_tagged = True
						for l in f.loops:
							if not l.tag:
								all_loops_tagged = False
							else:
								l.tag = False
						if all_loops_tagged:
							faces.append( f )
				else:
					return { 'CANCELLED' }

			if len( faces ) < 1:
				return { 'CANCELLED' }


			meters_per_1024 = context.scene.target_texel_density
			target_texel_density = 1024.0 / meters_per_1024
			
			print( 'meters_per_1024 :: {}'.format( meters_per_1024 ) )
			print( 'target_texel_density :: {}'.format( target_texel_density ) )

			#create list of uvislands and compute a density ( 3darea/uvarea ) for each
			tri_loops = rmmesh.bmesh.calc_loop_triangles()
			islands = faces.island( uvlayer )
			for island in islands:

				#get the world space size of the material on the first poly of this island
				material_size = [ 6.5, 6.5 ]
				try:
					material = rmmesh.mesh.materials[island[0].material_index]
				except IndexError:
					pass
				try:
					material_size[0] = material["WorldMappingWidth_inches"] * 0.0254
					material_size[1] = material["WorldMappingHeight_inches"] * 0.0254
				except KeyError:
					pass

				#compute uv island area
				island_uvarea = 0.0
				for tri in tri_loops:
					uv1 = mathutils.Vector( tri[0][uvlayer].uv )
					uv2 = mathutils.Vector( tri[1][uvlayer].uv )
					uv3 = mathutils.Vector( tri[2][uvlayer].uv )
					uvarea = mathutils.geometry.area_tri( uv1, uv2, uv3 )
					island_uvarea += uvarea

				#compute island 3d surface area
				island_3darea = 0.0
				for f in island:
					island_3darea += f.calc_area()

				#compute island center in uv space
				island_center = mathutils.Vector( ( 0.0, 0.0 ) )
				lcount = 0
				for f in island:
					for l in f.loops:
						island_center += mathutils.Vector( l[uvlayer].uv )
						lcount += 1
				island_center = island_center * ( 1.0 / lcount )
				
				#scale uv islands to target texel density
				current_texel_density = island_uvarea * material_size[0] * material_size[1] / island_3darea
				scale_factor = target_texel_density / current_texel_density
				print( 'current_texel_density :: {}'.format( current_texel_density ) )
				print( 'target_texel_density :: {}'.format( target_texel_density ) )
				for f in island:
					for l in f.loops:
						uv = mathutils.Vector( l[uvlayer].uv )
						uv -= island_center
						uv *= scale_factor
						uv += island_center
						l[uvlayer].uv = uv

			clear_tags( rmmesh )

		return { 'FINISHED' }


class UV_PT_UVDensityTools( bpy.types.Panel ):
	bl_parent_id = 'UV_PT_RMKIT_PARENT'
	bl_idname = 'UV_PT_UVDensityTools'
	bl_label = 'Island Texel Scale'
	bl_region_type = 'UI'
	bl_space_type = 'IMAGE_EDITOR'
	bl_options = { 'DEFAULT_CLOSED' }

	def draw( self, context ):
		layout = self.layout
		r = layout.row()
		r.alignment = 'EXPAND'
		r.label( text='Target Density' )
		r.prop( context.scene, 'target_texel_density', text='' )
		layout.operator( MESH_OT_scaletotexeldensity.bl_idname, text='Texel Density' )
		layout.operator( MESH_OT_scaleislandrelative.bl_idname )
		


def register():
	print( 'register :: {}'.format( MESH_OT_scaleislandrelative.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_scaletotexeldensity.bl_idname ) )
	bpy.utils.register_class( MESH_OT_scaleislandrelative )
	bpy.utils.register_class( MESH_OT_scaletotexeldensity )
	bpy.utils.register_class( UV_PT_UVDensityTools )
	bpy.types.Scene.target_texel_density = bpy.props.FloatProperty( name='Target Texel Density', default=0.6096, unit='LENGTH', subtype='DISTANCE' )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_scaleislandrelative.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_scaletotexeldensity.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_scaleislandrelative )
	bpy.utils.register_class( MESH_OT_scaletotexeldensity )
	bpy.utils.unregister_class( UV_PT_UVDensityTools )
	del bpy.types.Scene.target_texel_density