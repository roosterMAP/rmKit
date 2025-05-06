import bpy, bmesh, mathutils
import rmlib

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


def edge_loops( edge, force_boundary=False ):		
	next_edges = []
	skip_verts = rmlib.rmPolygonSet( edge.link_faces ).vertices
	for vert in edge.verts:
		if edge.is_boundary:
			if not force_boundary and len( vert.link_edges ) != 3:
				continue
		elif len( edge.link_faces ) == 2 and len( vert.link_edges ) != 4:
			continue

		for e in vert.link_edges:
			if e == edge or e.tag:
				continue
			if force_boundary and edge.is_boundary:
				if e.is_boundary:
					next_edges.append( e )
					e.tag = True
					break
			else:
				if e.other_vert( vert ) not in skip_verts:
					next_edges.append( e )
					e.tag = True
					break

	return next_edges


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


class MESH_OT_ring( bpy.types.Operator ):
	"""Extend current element selection by ring."""
	bl_idname = 'mesh.rm_ring'
	bl_label = 'Ring Select'
	bl_options = { 'UNDO' }

	unsel: bpy.props.BoolProperty(
		name='Deselect',
		description='Deselect loop edges.',
		default=False
	)

	@classmethod
	def poll( cls, context ):
		return ( len( context.editable_objects ) > 0 and context.mode == 'EDIT_MESH' )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]

		emptyselection = True

		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			with rmmesh as rmmesh:
				rmmesh.readonly = True
				for e in rmmesh.bmesh.edges:
					e.tag = False
				for p in rmmesh.bmesh.faces:
					p.tag = False					

				if sel_mode[0] or sel_mode[1]:
					if self.unsel:
						selected_edges = rmlib.rmEdgeSet( [rmmesh.bmesh.select_history.active] )
					else:
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
				
				if len( selected_edges ) > 0:
					emptyselection = False
				
				for e in selected_edges:
					if e.tag:
						continue
					
					ring = rmlib.rmEdgeSet( [e] )		
					try:
						ring = edge_ring( e, e.link_faces[0], ring )
						ring += edge_ring( e, e.link_faces[1], ring )
					except IndexError:
						pass

					#set selection state
					if sel_mode[1]:
						for e in ring:
							e.select = not self.unsel
					else:
						ring.polygons.select( replace=False )
					
				for e in rmmesh.bmesh.edges:
					e.tag = False
				for p in rmmesh.bmesh.faces:
					p.tag = False

		if emptyselection:
			self.report( { 'ERROR' }, 'Selection is empty!' )
			return { 'CANCELLED' }

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
	
	mode: bpy.props.EnumProperty(
		name='Mode',
		description='Set/Add/Remove to/from selection.',
		items=[ ( "set", "Set", "", 1 ),
				( "add", "Add", "", 2 ),
				( "remove", "Remove", "", 3 ) ],
		default='set'
	)

	evaluate_all_selected: bpy.props.BoolProperty(
		name='Evaluate All Selected',
		description='When True, all selected edges are loop extended.',
		default=False,
		options={ 'HIDDEN' }
	)

	@classmethod
	def poll( cls, context ):
		return ( len( context.editable_objects ) > 0 and context.mode == 'EDIT_MESH' )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			try:
				bpy.ops.mesh.rm_ring()
			except Exception as e:
				self.report( { 'ERROR' }, str( e ) )
				return { 'CANCELLED' }
			return { 'FINISHED' }
		
		emptyselection = True
				
		for rmmesh in rmlib.iter_edit_meshes( context, mode_filter=True ):
			with rmmesh as rmmesh:
				for e in rmmesh.bmesh.edges:
					e.tag = False
				
				rmmesh.readonly = True

				if self.mode != 'set' and rmmesh.bmesh.select_history.active is not None and isinstance( rmmesh.bmesh.select_history.active, bmesh.types.BMEdge ) and not self.evaluate_all_selected:
					selected_edges = rmlib.rmEdgeSet( [rmmesh.bmesh.select_history.active] )
				else:
					selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )

				if len( selected_edges ) < 1:
					continue
				emptyselection = False

				#selected_edges.tag( True )
				while( len( selected_edges ) > 0 ):
					e = selected_edges.pop()
					for e in edge_loops( e, self.force_boundary ):
						e.select = self.mode != 'remove'
						selected_edges.append( e )
					
				for e in rmmesh.bmesh.edges:
					e.tag = False

		if emptyselection:
			self.report( { 'ERROR' }, 'Selection is empty!' )
			return { 'CANCELLED' }

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_loop )
	bpy.utils.register_class( MESH_OT_ring )
	
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_loop )
	bpy.utils.unregister_class( MESH_OT_ring )