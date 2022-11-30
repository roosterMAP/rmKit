import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

def clear_tags( rmmesh ):
	for v in rmmesh.bmesh.verts:
		v.tag = False
	for e in rmmesh.bmesh.edges:
		e.tag = False
	for f in rmmesh.bmesh.faces:
		f.tag = False
		for l in f.loops:
			l.tag = False

class MESH_OT_uvmaptogrid( bpy.types.Operator ):
	"""Map the uv verts of the selected UV Islands to a Grid"""
	bl_idname = 'mesh.rm_uvgridify'
	bl_label = 'Gridify'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode and
				context.tool_settings.use_uv_select_sync )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			clear_tags( rmmesh )
			
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if not sel_mode[2]:
				return { 'CANCELLED' }

			uvlayer = rmmesh.active_uv

			faces = rmlib.rmPolygonSet.from_selection( rmmesh )
			for group in faces.group():

				#validate topology of group
				valid_topo = True
				for v in group.vertices:
					fcount = len( v.link_faces )
					if fcount == 3 or fcount > 4:
						valid_topo = False
						break
				if not valid_topo:
					continue
				for f in group:
					if len( f.verts ) != 4:
						valid_topo = False
						break
				if not valid_topo:
					continue

				#initialize start_loop	
				start_loop = f.loops[0]
				for f in group:
					outer_edge_count = 0
					for l in f.loops:
						if l.edge.seam or l.edge.is_boundary :
							start_loop = l							
							outer_edge_count += 1
						else:
							for nf in l.edge.link_faces:
								if nf != f and nf not in group:
									start_loop = l
									outer_edge_count += 1
									break
					if outer_edge_count == 2:
						break

				#build lists of ring loops
				loop_rings = []
				while( start_loop is not None ):
					ring = [ start_loop ]
					next_loop = start_loop.link_loop_next.link_loop_next
					final_loop = None
					while( next_loop is not None ):
						next_loop.face.tag = True
						loop = next_loop
						next_loop = None
						for f in loop.edge.link_faces:
							if f.tag:
								continue
							if f != loop.face:
								for l in f.loops:
									if l.edge == loop.edge:
										ring.append( l )
										next_loop = l.link_loop_next.link_loop_next
										break
								if next_loop is not None:
									break
						if next_loop is None:
							final_loop = loop
							final_loop.face.tag = True
							ring.append( loop )

					loop_rings.append( ring )
					
					use_next = len( loop_rings ) % 2 == 0
					if use_next:
						bridge_loop = final_loop.link_loop_next
					else:
						bridge_loop = final_loop.link_loop_prev
						
					start_loop = None
					for f in bridge_loop.edge.link_faces:
						if f.tag:
							continue
						if f != final_loop.face:
							for l in f.loops:
								if l.edge == bridge_loop.edge:
									if use_next:
										start_loop = l.link_loop_next
									else:
										start_loop = l.link_loop_prev
									break
						if start_loop is not None:
							break

				#convert ring loops into ring verts
				rings = []
				loop_rings.append( loop_rings[-1] )
				for i in range( len( loop_rings ) ):
					ring = []
					if i % 2 == 0:
						for l in loop_rings[i][:-1]:
							ring.append( l.vert )
						ring.append( loop_rings[i][-1].link_loop_next.vert )
					else:
						ring.append( loop_rings[i][-1].vert )
						for l in loop_rings[i][:-1][::-1]:
							ring.append( l.link_loop_next.vert )						
					rings.append( ring )
				rings[-1] = rings[-1][::-1]
						
				#compute aspect ratio of grid
				avg_ring_len = 0.0
				avg_loop_len = 0.0
				for r in rings:
					for i in range( 1, len( r ) ):
						avg_ring_len += ( r[i].co - r[i-1].co ).length
				for i in range( len( rings[0] ) ):
					for j in range( 1, len( rings ) ):
						avg_loop_len += ( rings[j][i].co - rings[j-1][i].co ).length
				avg_ring_len /= len( rings )
				avg_loop_len /= len( rings[0] )
				aspect_ratio = avg_ring_len / avg_loop_len
				
				#build lists of faces
				last_ring_faces = set( [ l.face for l in loop_rings[-1] ] )
				last_loop_faces = set()
				for i, r in enumerate( loop_rings[:-1] ):
					if i % 2 == 0:
						last_loop_faces.add( r[-1].face )
					else:
						last_loop_faces.add( r[0].face )						
					
				#set uv values
				u_step = 1.0 / ( len( rings ) - 1 )
				v_step = 1.0 / ( len( rings[0] ) - 1 )
				for i, r in enumerate( rings ):
					for j, vert in enumerate( r ):
						for l in vert.link_loops:
							if i == len( rings ) - 1 and l.face not in last_ring_faces:
								continue
							if j == len( r ) - 1 and l.face not in last_loop_faces:
								continue
							if l.face in faces:
								if aspect_ratio < 1.0:
									l[uvlayer].uv = ( u_step * i , v_step * j * aspect_ratio )
								else:
									l[uvlayer].uv = ( u_step * i / aspect_ratio , v_step * j )
								
				clear_tags( rmmesh )
			
		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvmaptogrid )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvmaptogrid )