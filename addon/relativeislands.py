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
					if tri[0].face in island:
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


class MESH_OT_scaletomaterialsize( bpy.types.Operator ):
	"""Scale Selected UV Islands to the material size."""
	bl_idname = 'mesh.rm_scaletomaterialsize'
	bl_label = 'Scale to Material Size'
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

			#create list of uvislands and compute a density ( 3darea/uvarea ) for each
			tri_loops = rmmesh.bmesh.calc_loop_triangles()
			islands = faces.island( uvlayer )
			for island in islands:

				#get the world space size of the material on the first poly of this island
				material_size = [ 2.0, 2.0 ]
				try:
					material = rmmesh.mesh.materials[island[0].material_index]
				except IndexError:
					pass
				try:
					material_size[0] = material["WorldMappingWidth"]
					material_size[1] = material["WorldMappingHeight"]
				except KeyError:
					pass

				#compute uv island area
				island_uvarea = 0.0
				for tri in tri_loops:
					if tri[0].face in island:
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
				
				target_uvarea = island_3darea / ( material_size[0] * material_size[1] )
				scale_factor = math.sqrt( target_uvarea ) / math.sqrt( island_uvarea )

				#scale uv islands to target texel density				
				for f in island:
					for l in f.loops:
						uv = mathutils.Vector( l[uvlayer].uv )
						uv -= island_center
						uv *= scale_factor
						uv += island_center
						l[uvlayer].uv = uv

			clear_tags( rmmesh )

		return { 'FINISHED' }


class MESH_OT_normalizetexels( bpy.types.Operator ):
	"""Scale UV Islands such that the texels are as square as possible."""
	bl_idname = 'mesh.rm_normalizetexels'
	bl_label ='Normalize Texels'
	bl_options = { 'UNDO' }

	horizontal: bpy.props.BoolProperty(
			name='Horizontal',
			default=True
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
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

			#create list of uvislands and compute a density ( 3darea/uvarea ) for each
			tri_loops = rmmesh.bmesh.calc_loop_triangles()
			islands = faces.island( uvlayer )
			for island in islands:

				#compute uv island area
				for tri in tri_loops:
					if tri[0].face in island:
						break

				#compute tangent and bitangent vectors
				v1 = mathutils.Vector( tri[0].vert.co.copy() )
				v2 = mathutils.Vector( tri[1].vert.co.copy() )
				v3 = mathutils.Vector( tri[2].vert.co.copy() )

				w1 = mathutils.Vector( tri[0][uvlayer].uv )
				w2 = mathutils.Vector( tri[1][uvlayer].uv )
				w3 = mathutils.Vector( tri[2][uvlayer].uv )

				x1 = v2.x - v1.x
				x2 = v3.x - v1.x
				y1 = v2.y - v1.y
				y2 = v3.y - v1.y
				z1 = v2.z - v1.z
				z2 = v3.z - v1.z

				s1 = w2.x - w1.x
				s2 = w3.x - w1.x
				t1 = w2.y - w1.y
				t2 = w3.y - w1.y

				r = 1.0 / ( s1 * t2 - s2 * t1 )
				tangent = mathutils.Vector( ( ( t2 * x1 - t1 * x2 ) * r, ( t2 * y1 - t1 * y2 ) * r, ( t2 * z1 - t1 * z2 ) * r ) )
				bitangent = mathutils.Vector( ( ( s1 * x2 - s2 * x1 ) * r, ( s1 * y2 - s2 * y1 ) * r, ( s1 * z2 - s2 * z1 ) * r ) )
				
				#compute scale factor based on scaling axis
				axis_idx = 0
				scale_factor = 1.0
				if self.horizontal:
					scale_factor = tangent.length / bitangent.length
				else:
					axis_idx = 1
					scale_factor = bitangent.length / tangent.length

				#compute island center in uv space
				island_center = mathutils.Vector( ( 0.0, 0.0 ) )
				lcount = 0
				for f in island:
					for l in f.loops:
						island_center += mathutils.Vector( l[uvlayer].uv )
						lcount += 1
				island_center = island_center * ( 1.0 / lcount )
				
				#scale uv islands to target texel density				
				for f in island:
					for l in f.loops:
						uv = mathutils.Vector( l[uvlayer].uv )
						uv -= island_center
						uv[axis_idx] *= scale_factor
						uv += island_center
						l[uvlayer].uv = uv

			clear_tags( rmmesh )

		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_scaleislandrelative.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_scaletomaterialsize.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_normalizetexels.bl_idname ) )
	bpy.utils.register_class( MESH_OT_scaleislandrelative )
	bpy.utils.register_class( MESH_OT_scaletomaterialsize )
	bpy.utils.register_class( MESH_OT_normalizetexels )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_scaleislandrelative.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_scaletomaterialsize.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_normalizetexels.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_scaleislandrelative )
	bpy.utils.unregister_class( MESH_OT_scaletomaterialsize )
	bpy.utils.unregister_class( MESH_OT_normalizetexels )