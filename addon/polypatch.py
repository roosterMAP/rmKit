import bpy
import bmesh
import rmKit.rmlib as rmlib

def select_vchain( vchain, replace=False ):
	if replace:
		bpy.ops.mesh.select_all( action = 'DESELECT' )
	for vp in vchain:
		be = rmlib.rmEdgeSet.from_endpoints( vp[0], vp[1] )
		if be is None:
			continue
		be.select = True

class MESH_OT_polypatch( bpy.types.Operator ):
	"""Mesh editing operator that modifies topology based off selection and context."""
	bl_idname = 'mesh.rm_polypatch'
	bl_label = 'PolyPatch'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
						
	def execute( self, context ):
		#get the selection mode
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		#get the current object type
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }		

		if sel_mode[0]:
			with rmmesh as rmmesh:
				sel_verts = rmlib.rmVertexSet.from_selection( rmmesh )
				if len( sel_verts ) < 2:
					return { 'CANCELLED' }							
				slice_edges = bmesh.ops.connect_verts( rmmesh.bmesh, verts=sel_verts, check_degenerate=False )

		elif sel_mode[1]:
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				sel_edges = rmlib.rmEdgeSet.from_selection( rmmesh )				
				open_edges = rmlib.rmEdgeSet()
				closed_edges = rmlib.rmEdgeSet()
				for e in sel_edges:
					if e.is_boundary:
						open_edges.append( e )
					elif e.is_contiguous:
						closed_edges.append( e )
				
				if len( open_edges ) > 0:				
					vchains = open_edges.chain()

					#break up vchains into edge sets of open and closed loops
					closed_loops = []
					open_loops = []
					for vchain in vchains:
						elist = rmlib.rmEdgeSet()
						for vp in vchain:
							elist.append( rmlib.rmEdgeSet.from_endpoints( vp[0], vp[1] ) )

						if vchain[0][0] == vchain[-1][-1]:
							closed_loops.append( elist )
						else:
							open_loops.append( elist )

					#close loops get capped
					if len( closed_loops ) > 0:
						bpy.ops.mesh.select_all( action = 'DESELECT' )
						for loop in closed_loops:
							loop.select( False )
						bpy.ops.mesh.edge_face_add()

					#if there are two open loops, then bridge
					if len( open_loops ) == 2:
						bpy.ops.mesh.select_all( action = 'DESELECT' )
						for loop in open_loops:
							loop.select( False )
						bpy.ops.mesh.bridge_edge_loops()

					#otherwise just face_add
					elif len( open_loops ) > 0:
						bpy.ops.mesh.select_all( action = 'DESELECT' )
						for loop in open_loops:
							loop.select( False )
						bpy.ops.mesh.edge_face_add()
						
				#closed edges get rotated
				if len( closed_edges ) > 0:
					closed_edges.select( True )
					bpy.ops.mesh.edge_rotate( use_ccw=True )
	
		elif sel_mode[2]:
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				sel_polys = rmlib.rmPolygonSet.from_selection( rmmesh )				
				groups = sel_polys.group()
				if len( groups ) == 2:
					bpy.ops.mesh.bridge_edge_loops()
				else:
					bpy.ops.mesh.duplicate_move()

		return { 'FINISHED' }
	
def register():
	print( 'register :: {}'.format( MESH_OT_polypatch.bl_idname ) )
	bpy.utils.register_class( MESH_OT_polypatch )
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_polypatch.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_polypatch )