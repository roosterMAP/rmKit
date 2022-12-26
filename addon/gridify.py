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
			
def is_boundary( l ):
	if l.edge.seam or l.edge.is_boundary:
		return True
	else:
		for nf in l.edge.link_faces:
			if nf != l.face and not nf.tag:
				return True
	return False

class MESH_OT_uvmaptogrid( bpy.types.Operator ):
	"""Map the uv verts of the selected UV Islands to a Grid"""
	bl_idname = 'mesh.rm_uvgridify'
	bl_label = 'Gridify'
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

			complete_failure = True
			for group in faces.group( use_seam=True ):
				#set tags
				for f in group:
					f.tag = True
				
				#validate topology of group
				valid_topo = True
				for v in group.vertices:
					fcount = 0
					for f in v.link_faces:
						if f.tag:
							fcount += 1
					if fcount == 3 or fcount > 4:
						valid_topo = False
						break
				for f in group:
					if len( f.verts ) != 4:
						valid_topo = False
						break
				if not valid_topo:
					for f in group:
						f.tag = False
					continue
				
				#initialize start_loop
				start_loop = None
				for f in group:
					for l in f.loops:
						if is_boundary( l ) and is_boundary( l.link_loop_prev ):
							start_loop = l
							break
					if start_loop is not None:
						break
				if start_loop is None:
					start_loop = group[0].loops[0]
									
				#mark boundary edges
				for f in group:
					for e in f.edges:
						if e.seam or e.is_boundary:
							e.tag = True
						for nf in e.link_faces:
							if nf != f and not nf.tag:
								e.tag = True
								break
							
				#clear tags	
				for f in group:
					f.tag = False

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
							if f.tag or loop.edge.tag:
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
						if f.tag or bridge_loop.edge.tag:
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
							if l.face in group:
								if aspect_ratio < 1.0:
									l[uvlayer].uv = ( u_step * i , v_step * j * aspect_ratio )
								else:
									l[uvlayer].uv = ( u_step * i / aspect_ratio , v_step * j )
								
				clear_tags( rmmesh )

				complete_failure = False

		#return failed if all poly groups failed to be gridified
		if complete_failure:
			return { 'CANCELLED' }
			
		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvmaptogrid )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_uvmaptogrid )