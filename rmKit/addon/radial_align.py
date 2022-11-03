import bpy
import bmesh
import rmKit.rmlib as rmlib
import mathutils
import math

def circularize( vert_loop ):
	pass

class MESH_OT_radialalign( bpy.types.Operator ):
	bl_idname = 'mesh.rm_radialalign'
	bl_label = 'Radial Align'

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[0]:
			return { 'CANCELLED' }
			
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			if sel_mode[1]:
				edges = rmlib.rmEdgeSet.from_selection( rmmesh )
			elif sel_mode[2]:
				polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				edges = rmlib.rmEdgeSet()
				for p in polys:
					for e in p.edges:
						if e.is_boundary:
							edges.append( e )
							continue
						has_unselected_neigh = False
						for n_p in e.other_face( p ):
							if not n_p.select:
								has_unselected_neigh = True
								break
						if has_unselected_neigh and e not in edges:
							edges.append( e )
							
				for chain in edges.chains():
					if chain[0][0] != chain[-1][-1]:
						continue

					vert_loop = [ pair[0] for pair in chain ]
					circularize( vert_loop )

		return { 'FINISHED' }
	
def register():
	print( 'register :: {}'.format( MESH_OT_contextbevel.bl_idname ) )
	bpy.utils.register_class( MESH_OT_contextbevel )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_contextbevel.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_contextbevel )