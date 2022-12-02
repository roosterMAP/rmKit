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
				for f in island:
					f.tag = True

				island_uvarea = 0.0
				for tri in tri_loops:
					if not tri[0].face.tag:
						continue
					uv1 = mathutils.Vector( tri[0][uvlayer].uv )
					uv2 = mathutils.Vector( tri[1][uvlayer].uv )
					uv3 = mathutils.Vector( tri[2][uvlayer].uv )
					uvarea = mathutils.geometry.area_tri( uv1, uv2, uv3 )
					island_uvarea += uvarea

				island_3darea = 0.0
				for f in island:
					island_3darea += f.calc_area()

				densities.append( island_uvarea / island_3darea )

				for f in island:
					f.tag = False

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
				
			print( densities )
			print( target_density )
			print( '\n' )

			#set the density of all islands to the target
			for i, island in enumerate( islands ):
				scale_factor = math.sqrt( target_density / densities[i] )
				print( scale_factor )

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

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_scaleislandrelative )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_scaleislandrelative )