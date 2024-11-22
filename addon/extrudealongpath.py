import bpy, bmesh, mathutils
from .. import rmlib

BACKGROUND_LAYERNAME = 'rm_background'

def GetSelsetEdges( bm, layername ):
	intlayers = bm.edges.layers.int
	selset = intlayers.get( layername, None )
	if selset is None:
		return rmlib.rmEdgeSet()
	return rmlib.rmEdgeSet( [ e for e in bm.edges if bool( e[selset] ) ] )


class MESH_OT_extrudealongpath( bpy.types.Operator ):
	"""Extrude the face selection along the path defined by the background edge selection."""
	bl_idname = 'mesh.rm_extrudealongpath'
	bl_label = 'Extrude Along Path'
	bl_options = { 'UNDO' }

	offsetonly: bpy.props.BoolProperty(
		name='Offset Only',
		default=False
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
			
	def execute( self, context ):	
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }
		
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			self.report( { 'WARNING' }, 'Must be in face mode.' )
			return { 'CANCELLED' }
		
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			selset_edges = GetSelsetEdges( rmmesh.bmesh, BACKGROUND_LAYERNAME )
			if len( selset_edges ) < 1:
				self.report( { 'WARNING' }, 'Must have at least one background edge selected.' )
				return { 'CANCELLED' }
			path_edges = selset_edges.chain()[0]
			
			selected_faces = rmlib.rmPolygonSet.from_selection( rmmesh )
			new_faces = rmlib.rmPolygonSet()
			for group in selected_faces.group():
				boundary_edges = rmlib.rmEdgeSet()
				for e in group.edges:
					linkfaces = list( e.link_faces )
					if len( linkfaces ) <= 1:
						boundary_edges.append( e )
						continue
									
					selfacecount = 0
					for f in e.link_faces:
						if f.select:
							selfacecount += 1
					if selfacecount == 1:
						boundary_edges.append( e )
					continue
				
				vchain = boundary_edges.vert_chain()[0]
				
				profile = [ v.co.copy() for v in vchain ]	
				
				profile_center = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
				for p in profile:
					profile_center += p
				profile_center /= len( profile )
				
				#reverse path_edges if profile is close to endpoint than startpoint
				if ( profile_center - path_edges[0][0].co ).length > ( profile_center - path_edges[-1][-1].co ).length:
					path_edges = path_edges[::-1]
					for i, t in enumerate( path_edges ):
						path_edges[i] = ( t[1], t[0] )
				
				#project the profile onto the plane defined by the first path
				first_path_v1, first_path_v2 = path_edges[0]
				first_path_p1 = first_path_v1.co.copy()
				plane_nml = ( first_path_v2.co.copy() - first_path_p1 ).normalized()			
				for i in range( len( profile ) ):
					p = profile[i]
					dist = rmlib.util.PlaneDistance( p, profile_center, plane_nml )
					profile[i] = p - plane_nml * dist
					
				profile_verts = vchain
				
				for n, path_edge in enumerate( path_edges ):
					v1, v2 = path_edge
					pos1 = v1.co.copy()
					pos2 = v2.co.copy()
					offset = pos2 - pos1
					
					profile_center += offset

					plane_nml = mathutils.Vector( ( 1.0, 0.0, 0.0 ) )
					if not self.offsetonly:
						try:
							v1, v2 = path_edges[n+1]
						except IndexError:
							pass
						pos1 = v1.co.copy()
						pos2 = v2.co.copy()
					
						vec_a = offset.normalized()
						vec_b = ( pos2 - pos1 ).normalized()
						plane_nml = vec_a + vec_b
						if plane_nml.length < rmlib.util.FLOAT_EPSILON:
							plane_nml = vec_a
						plane_nml.normalize()
					
					new_profile = [None] * len( profile )
					new_profile_verts = [None] * len( profile )
					for i in range( len( profile ) ):
						if self.offsetonly:
							new_profile[i] = profile[i] + offset
						else:
							new_profile[i] = mathutils.geometry.intersect_line_plane( profile[i], profile[i] + offset * 10.0, profile_center, plane_nml )
							if new_profile[i] is None:
								new_profile[i] = profile[i] + offset
						new_profile_verts[i] = rmmesh.bmesh.verts.new( new_profile[i] )
						
					for i in range( len( profile ) ):
						vlist = [ profile_verts[i-1], profile_verts[i], new_profile_verts[i], new_profile_verts[i-1] ]
						face = rmmesh.bmesh.faces.new( vlist, group[0] )
						new_faces.append( face )
						
					profile_verts = new_profile_verts
					profile = new_profile
					
				bmesh.ops.delete( rmmesh.bmesh, geom=group, context='FACES' )
				
			new_faces.select( replace=True )
		bpy.ops.mesh.rm_uvgridify()

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_extrudealongpath )
	
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_extrudealongpath )