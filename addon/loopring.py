import bpy, mathutils
from .. import rmlib

def edge_ring( edge, poly, ring ):
	skip_verts = edge.verts
	for p in edge.link_faces:
		if p.tag or len( p.verts ) != 4:
			continue
		p.tag = True
		
		for e in p.edges:
			if e.verts[0] in skip_verts or e.verts[1] in skip_verts:
				continue
			ring.append( e )
			edge_ring( e, p, ring )
			return ring

	return ring


def edge_loop( edge, vert, loop, force_boundary=False ):
	if edge.is_boundary:
		if not force_boundary and len( vert.link_edges ) != 3:
			return loop
	elif len( edge.link_faces ) == 2 and len( vert.link_edges ) != 4:
		return loop

	skip_verts = rmlib.rmPolygonSet( edge.link_faces ).vertices
	
	if force_boundary:
		for e in vert.link_edges:
			if e.is_boundary:
				if e != edge and e in loop:
					return loop
				if e == edge or e in loop:
					continue
				loop.append( e )
				e.tag = False
				v = e.other_vert( vert )
				edge_loop( e, v, loop, force_boundary )
				return loop
				
	for e in vert.link_edges:
		if e == edge or e in loop:
			continue
		v = e.other_vert( vert )
		if v not in skip_verts:
			loop.append( e )
			e.tag = False
			edge_loop( e, v, loop, force_boundary )
			break
		
	return loop


def edge_loop_alt( edge, vert, loop ):
	link_edges = list( vert.link_edges )
	if len( link_edges ) == 1:
		return loop

	for e in link_edges:
		if e.is_boundary:
			e.tag = False
			if e in loop:				
				return loop
			else:
				next_vert = e.other_vert( vert )
				loop.append( e )
				edge_loop_alt( e, next_vert, loop )
				return loop

	try:
		idx = link_edges.index( edge )
	except ValueError:
		return loop
	link_edges = link_edges[idx+1:] + link_edges[:idx]
	next_edge = link_edges[ int( len( link_edges ) / 2 ) ]
	next_edge.tag = False
	loop.append( next_edge )
	if next_edge in loop:
		return loop

	next_vert = next_edge.other_vert( vert )
	edge_loop_alt( next_edge, next_vert, loop )
	return loop


def uvedge_boundary( l, uvlayer ):
	#test if edge loop is a boundary of a uv island
	for f in l.edge.link_faces:
		if f == l.face:
			continue
		if edge_continuous( l.face, f, uvlayer ):
			return False		
	return True


def edge_continuous( f1, f2, uvlayer ):
	#test if two faces are conntected by an edge in uv space
	for l1 in f1.loops:
		for l2 in f2.loops:
			if l1.edge == l2.edge:
				if ( rmlib.util.AlmostEqual_v2( l1.link_loop_next[uvlayer].uv, l2[uvlayer].uv ) and
				rmlib.util.AlmostEqual_v2( l1[uvlayer].uv, l2.link_loop_next[uvlayer].uv ) ):
					return True
	return False

def uvedge_loop_fwd( loop, group, uvlayer, force_boundary=False ):
	nl = loop.link_loop_next
				
	#count uv edges coming out of nl
	uvedgecount = 0
	possible_edges = nl.vert.link_edges
	counted_edges = set()
	for f in nl.vert.link_faces:
		for l in f.loops:
			if l.edge not in possible_edges or l.edge in counted_edges:
				continue
			if l.vert == nl.vert:
				if rmlib.util.AlmostEqual_v2( l[uvlayer].uv, nl[uvlayer].uv ):
					if not uvedge_boundary( l, uvlayer ):
						counted_edges.add( l.edge )
					uvedgecount += 1
			else:
				if rmlib.util.AlmostEqual_v2( l.link_loop_next[uvlayer].uv, nl[uvlayer].uv ):
					if not uvedge_boundary( l, uvlayer ):
						counted_edges.add( l.edge )
					uvedgecount += 1
						
	if uvedgecount == 3 or uvedgecount == 4:
		if uvedge_boundary( nl, uvlayer ):
			return group
		for f in nl.edge.link_faces:
			if f == nl.face:
				continue
			for l in f.loops:

				if l.edge == nl.edge:
					next_loop = l.link_loop_next
					if next_loop.tag:
						continue
					if uvedgecount == 3 and not uvedge_boundary( next_loop, uvlayer ):
						continue
					next_loop.tag = True
					group.append( next_loop )
					uvedge_loop_fwd( next_loop, group, uvlayer, force_boundary )
		
	return group


def uvedge_loop_rev( loop, group, uvlayer, force_boundary=False ):	
	#count uv edges coming out of nl
	uvedgecount = 0
	possible_edges = loop.vert.link_edges
	counted_edges = set()
	for f in loop.vert.link_faces:
		for l in f.loops:
			if l.edge not in possible_edges or l.edge in counted_edges:
				continue
			if l.vert == loop.vert:
				if rmlib.util.AlmostEqual_v2( l[uvlayer].uv, loop[uvlayer].uv ):
					if not uvedge_boundary( l, uvlayer ):
						counted_edges.add( l.edge )
					uvedgecount += 1
			else:
				if rmlib.util.AlmostEqual_v2( l.link_loop_next[uvlayer].uv, loop[uvlayer].uv ):
					if not uvedge_boundary( l, uvlayer ):
						counted_edges.add( l.edge )
					uvedgecount += 1
										
	nl = loop.link_loop_prev
	if uvedgecount == 3 or uvedgecount == 4:
		if uvedge_boundary( nl, uvlayer ):
			return group
		for f in nl.edge.link_faces:
			if f == nl.face:
				continue
			for l in f.loops:
				if l.edge == nl.edge:
					prev_loop = l.link_loop_prev
					if prev_loop.tag:
						continue
					if uvedgecount == 3 and not uvedge_boundary( prev_loop, uvlayer ):
						continue
					prev_loop.tag = True
					group.append( prev_loop )
					uvedge_loop_rev( prev_loop, group, uvlayer, force_boundary )
		
	return group


def uvedge_ring( loop, group, uvlayer ):
	if len( loop.face.verts ) != 4:
		return group
	
	next_loop = loop.link_loop_next.link_loop_next
	if next_loop.tag:
		return group
	next_loop.tag = True
	group.append( next_loop )
	
	for f in next_loop.edge.link_faces:
		if f == next_loop.face:
			continue
		for l in f.loops:
			if l.edge == next_loop.edge and edge_continuous( f, next_loop.face, uvlayer ):
				next_loop = l
				if next_loop.tag:
					return group
				next_loop.tag = True
				group.append( next_loop )
				uvedge_ring( next_loop, group, uvlayer )
				
	return group


class MESH_OT_ring( bpy.types.Operator ):
	"""Extend current element selection by ring."""
	bl_idname = 'mesh.rm_ring'
	bl_label = 'Ring Select'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and len( context.editable_objects ) > 0 )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]

		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				for e in rmmesh.bmesh.edges:
					e.tag = False
				for p in rmmesh.bmesh.faces:
					p.tag = False
					

				if sel_mode[1]:
					selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				elif sel_mode[2]:
					selected_polygons = rmlib.rmPolygonSet.from_selection( rmmesh )
					shared_edges = set()

					allEdges = []
					for p in selected_polygons:
						allEdges += p.edges

					while( len( allEdges ) > 0 ):
						e = allEdges.pop( 0 )
						if e in allEdges:
							shared_edges.add( e )

					selected_edges = rmlib.rmEdgeSet( shared_edges )
				else:
					return { 'CANCELLED' }
				
				for e in selected_edges:
					if e.tag:
						continue
					
					ring = rmlib.rmEdgeSet( [e] )		
					try:
						ring = edge_ring( e, e.link_faces[0], ring )
						ring += edge_ring( e, e.link_faces[1], ring )
					except IndexError:
						pass

					if sel_mode[1]:
						ring.select( replace=False )
					else:
						ring.polygons.select( replace=False )
					
				for e in rmmesh.bmesh.edges:
					e.tag = False
				for p in rmmesh.bmesh.faces:
					p.tag = False

		return { 'FINISHED' }


class MESH_OT_loop( bpy.types.Operator ):
	"""Extend current element selection by loop. Utilizes 3DSMax edge loop algorithm."""
	bl_idname = 'mesh.rm_loop'
	bl_label = 'Loop Select'
	bl_options = { 'UNDO' }
	
	force_boundary: bpy.props.BoolProperty(
		name='Force Boundary',
		description='When True, all loop edges extend along bounary edges.',
		default=False
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and len( context.editable_objects ) > 0 )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			bpy.ops.mesh.rm_ring()
			return { 'FINISHED' }
		
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			with rmmesh as rmmesh:
				for e in rmmesh.bmesh.edges:
					e.tag = False
				
				rmmesh.readonly = True
				selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				selected_edges.tag( True )
				for e in selected_edges:
					if not e.tag:
						continue
					
					loop = edge_loop( e, e.verts[0], rmlib.rmEdgeSet( [e] ), self.force_boundary )
					loop = edge_loop( e, e.verts[1], loop, self.force_boundary )
					
					loop.select( False )
					
				for e in rmmesh.bmesh.edges:
					e.tag = False

		return { 'FINISHED' }


class MESH_OT_uvloop( bpy.types.Operator ):
	"""Extend current edge selection by loop. Utilizes 3DS Max algorithm."""
	bl_idname = 'mesh.rm_uvloop'
	bl_label = 'UV Loop Select'
	bl_options = { 'UNDO' }
	
	force_boundary: bpy.props.BoolProperty(
		name='Force Boundary',
		description='When True, all loop edges extend along bounary edges.',
		default=False
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):		
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			
			sel_sync = context.tool_settings.use_uv_select_sync
			if sel_sync:
				bpy.ops.mesh.rm_loop( force_boundary=self.force_boundary )
				
			else:				
				sel_mode = context.tool_settings.uv_select_mode
				if sel_mode != 'EDGE':
					bpy.ops.mesh.rm_uvring()
					return { 'FINISHED' }
				
				uvlayer = rmmesh.active_uv
			
				#clear loopm tags
				for f in rmmesh.bmesh.faces:
					for l in f.loops:
						l.tag = False
						
				#tag loop selection
				loop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh=rmmesh, uvlayer=uvlayer )
				for l in loop_selection:
					l.tag = True
					l[uvlayer].select_edge = False
				
				for l in loop_selection:					
					group = uvedge_loop_fwd( l, [ l ], uvlayer, self.force_boundary )
					group = uvedge_loop_rev( l, group, uvlayer, self.force_boundary )
					
					for l in group:
						l[uvlayer].select_edge = True
						uvcoord = mathutils.Vector( l[uvlayer].uv )
						for n_l in l.vert.link_loops:
							n_uvcoord = mathutils.Vector( n_l[uvlayer].uv )
							if rmlib.util.AlmostEqual_v2( uvcoord, n_uvcoord ):
								n_l[uvlayer].select = True
						uvcoord = mathutils.Vector( l.link_loop_next[uvlayer].uv )
						for n_l in l.link_loop_next.vert.link_loops:
							n_uvcoord = mathutils.Vector( n_l[uvlayer].uv )
							if rmlib.util.AlmostEqual_v2( uvcoord, n_uvcoord ):
								n_l[uvlayer].select = True
				
				for f in rmmesh.bmesh.faces:
					for l in f.loops:
						l.tag = False

		return { 'FINISHED' }


class MESH_OT_uvring( bpy.types.Operator ):
	"""Extend current edge selection by ring. Utilizes 3DS Max algorithm."""
	bl_idname = 'mesh.rm_uvring'
	bl_label = 'UV Ring Select'
	bl_options = { 'UNDO' }
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):		
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			
			sel_sync = context.tool_settings.use_uv_select_sync
			if sel_sync:
				bpy.ops.mesh.rm_ring()
			else:				
				sel_mode = context.tool_settings.uv_select_mode
				if sel_mode == 'EDGE':				
					uvlayer = rmmesh.active_uv
				
					#clear tags
					for f in rmmesh.bmesh.faces:
						for l in f.loops:
							l.tag = False
							
					#tag selection
					loop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh=rmmesh, uvlayer=uvlayer )
					for l in loop_selection:
						l.tag = True
						l[uvlayer].select_edge = False
					
					for l in loop_selection:								
						group = uvedge_ring( l, [ l ], uvlayer )
						
						for l in group:
							l[uvlayer].select_edge = True
							uvcoord = mathutils.Vector( l[uvlayer].uv )
							for n_l in l.vert.link_loops:
								n_uvcoord = mathutils.Vector( n_l[uvlayer].uv )
								if rmlib.util.AlmostEqual_v2( uvcoord, n_uvcoord ):
									n_l[uvlayer].select = True
							uvcoord = mathutils.Vector( l.link_loop_next[uvlayer].uv )
							for n_l in l.link_loop_next.vert.link_loops:
								n_uvcoord = mathutils.Vector( n_l[uvlayer].uv )
								if rmlib.util.AlmostEqual_v2( uvcoord, n_uvcoord ):
									n_l[uvlayer].select = True
					
					for f in rmmesh.bmesh.faces:
						for l in f.loops:
							l.tag = False


				elif sel_mode == 'FACE':					
					uvlayer = rmmesh.active_uv

					#clear tags
					for f in rmmesh.bmesh.faces:
						for l in f.loops:
							l.tag = False
							
					#tag selection
					loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
					faces = set()
					for l in loop_selection:
						l.tag = True
						l[uvlayer].select = False
						faces.add( l.face )

					#get face selection
					face_selection = rmlib.rmPolygonSet()
					for f in faces:
						all_loops_tagged = True
						for l in f.loops:
							if not l.tag:
								all_loops_tagged = False
								break
						if all_loops_tagged:
							f.tag = True
							face_selection.append( f )

					loop_selection = rmlib.rmUVLoopSet( [], uvlayer=uvlayer )
					for f in face_selection:
						for l in f.loops:
							for nf in l.edge.link_faces:
								if nf != f and nf.tag:
									loop_selection.append( l )
									break

					#clear tags
					for f in rmmesh.bmesh.faces:
						for l in f.loops:
							l.tag = False

					#set tags
					for l in loop_selection:
						l.tag = True

					#gather ring selection			
					all_loops = set()
					for l in loop_selection:								
						all_loops |= set( uvedge_ring( l, [ l ], uvlayer ) )
						
					#select resulting face loops
					for l in all_loops:
						for nl in l.face.loops:
							nl[uvlayer].select = True
							nl[uvlayer].select_edge = True
							
					for l in all_loops:
						for nl in l.vert.link_loops:
							if nl[uvlayer].select:
								continue
							if rmlib.util.AlmostEqual_v2( l[uvlayer].uv, nl[uvlayer].uv ):
								nl[uvlayer].select = True
								
					for f in rmmesh.bmesh.faces:
						f.tag = False
						for l in f.loops:
							l.tag = False

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_loop )
	bpy.utils.register_class( MESH_OT_ring )
	bpy.utils.register_class( MESH_OT_uvloop )
	bpy.utils.register_class( MESH_OT_uvring )
	
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_loop )
	bpy.utils.unregister_class( MESH_OT_ring )
	bpy.utils.unregister_class( MESH_OT_uvloop )
	bpy.utils.unregister_class( MESH_OT_uvring )