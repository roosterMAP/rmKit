from logging import exception
from re import T
import bpy, bmesh
import rmKit.rmlib as rmlib

def chain_is_sorted( chain ):
	e = rmlib.rmEdgeSet.from_endpoints( chain[0], chain[1] )
	verts = list( e.link_faces[0].verts )
	idx = verts.index( chain[1] )
	return verts[ idx - 1 ] == chain[0]


def chain_is_boundary( chain ):
	for i in range( 1, len( chain ) ):
		e = rmlib.rmEdgeSet.from_endpoints( chain[i-1], chain[i] )
		if e.is_contiguous:
			return False
	return True


class MESH_OT_targetweld( bpy.types.Operator ):
	bl_idname = 'mesh.rm_targetweld'
	bl_label = 'Target Weld'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[2]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			if sel_mode[0]:
				verts = rmlib.rmVertexSet.from_selection( rmmesh )
				active_vert = rmmesh.bmesh.select_history.active
				if not isinstance( active_vert, bmesh.types.BMVert ):
					active_vert = verts[0]
				if len( verts ) < 2:
					return { 'CANCELLED' }
				target_vert = verts.pop( verts.index( active_vert ) )
				for v in verts:
					v.co = target_vert.co
				verts.append( active_vert )
				bmesh.ops.remove_doubles( rmmesh.bmesh, verts=verts, dist=0.00001 )
			
			elif sel_mode[1]:
				#get verts of current active edge
				edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				if len( edges ) < 2:
					return { 'CANCELLED' }
				active_edge = rmmesh.bmesh.select_history.active
				if active_edge is None or not isinstance( active_edge, bmesh.types.BMEdge ):
					active_edge = edges[0]
				active_verts = list( active_edge.verts )
				
				#clear tags
				for v in edges.vertices:
					v.tag = False
				
				#break up edges into chains and set the one that includes the active verts to be the weld target
				chains = edges.vert_chain()
				if len( chains ) < 2:
					return { 'CANCELLED' }
				for i, chain in enumerate( chains ):
					if active_verts[0] in chain and active_verts[1] in chain:
						break
				target_chain = chains.pop( i )
				for v in target_chain:
					v.tag = True

				#weld open edges
				target_chain_is_sorted = chain_is_sorted( target_chain )
				if chain_is_boundary( target_chain ):
					print( 'source is open' )
					for i, chain in enumerate( chains ):
						if chain_is_boundary( chain ):
							if target_chain_is_sorted and chain_is_sorted( chain ):
								print( 'target is open' )
								chain = chain[::-1]
							for i in range( len( target_chain ) ):
								try:
									chain[i].co = target_chain[i].co
									chain[i].tag = True
								except IndexError:
									break
				
				#weld closed edges
				verts_welded = True
				skip_idxs = set()
				while( verts_welded ):
					verts_welded = False
					for i, chain in enumerate( chains ):
						if i in skip_idxs:
							continue
						for v in chain:
							if v.tag:
								continue
							for e in v.link_edges:
								l_v = e.other_vert( v )
								if l_v.tag:
									v.co = l_v.co
									verts_welded = True
									skip_idxs.add( i )
									break
						for v in chain:
							v.tag = True

				bmesh.ops.remove_doubles( rmmesh.bmesh, verts=edges.vertices, dist=0.0001 )


		return { 'FINISHED' }

	
def register():
	print( 'register :: {}'.format( MESH_OT_targetweld.bl_idname ) )
	bpy.utils.register_class( MESH_OT_targetweld )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_targetweld.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_targetweld )