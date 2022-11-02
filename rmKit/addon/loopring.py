import bpy
import rmKit.rmlib as rmlib

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
	if len( edge.link_faces ) == 2 and len( vert.link_edges ) != 4:
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


class MESH_OT_ring( bpy.types.Operator ):    
	"""Extend current element selection by ring."""
	bl_idname = 'mesh.rm_ring'
	bl_label = 'Ring Select'
	#bl_options = { 'REGISTER', 'UNDO' } #tell blender that we support the undo/redo pannel
	bl_options = { 'UNDO' }

	extend_last: bpy.props.BoolProperty(
			name='Extend Last',
			description='Only extend loop selection for most recently selected edge',
			default=False
	)

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]

		rmmesh = rmlib.rmMesh.GetActive( context )
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
					ring.select( False )
				else:
					ring.polygons.select( True )

				if self.extend_last:
					break
				
			for e in rmmesh.bmesh.edges:
				e.tag = False
			for p in rmmesh.bmesh.faces:
				p.tag = False

		return { 'FINISHED' }


class MESH_OT_loop( bpy.types.Operator ):    
	"""Extend current element selection by loop."""
	bl_idname = 'mesh.rm_loop'
	bl_label = 'Loop Select'
	#bl_options = { 'REGISTER', 'UNDO' } #tell blender that we support the undo/redo pannel
	bl_options = { 'UNDO' }
	
	force_boundary: bpy.props.BoolProperty(
		name='Force Boundary',
		description='When True, all loop edges extend along bounary edges.',
		default=False
	)

	modo_algorithm: bpy.props.BoolProperty(
			name='Modo Loop',
			description='Uses an alternative algorithm to match modo\' loop selection behavior.',
			default=False
	)

	extend_last: bpy.props.BoolProperty(
			name='Extend Last',
			description='Only extend loop selection for most recently selected edge',
			default=False
	)

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			bpy.ops.mesh.rm_ring( extend_last=self.extend_last )
			return { 'FINISHED' }
		
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			for e in rmmesh.bmesh.edges:
				e.tag = False
			
			rmmesh.readonly = True
			selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
			selected_edges.tag( True )
			for e in selected_edges:
				if not e.tag:
					continue
				
				if self.modo_algorithm:
					loop = edge_loop_alt( e, e.verts[0], rmlib.rmEdgeSet( [e] ) )
					loop = edge_loop_alt( e, e.verts[1], loop )
				else:
					loop = edge_loop( e, e.verts[0], rmlib.rmEdgeSet( [e] ), self.force_boundary )
					loop = edge_loop( e, e.verts[1], loop, self.force_boundary )
				
				loop.select( False )

				if self.extend_last:
					break
				
			for e in rmmesh.bmesh.edges:
				e.tag = False

		return { 'FINISHED' }


class MESH_OT_continuous( bpy.types.Operator ):    
	"""Extend current element selection by ring."""
	bl_idname = 'mesh.rm_continuouse'
	bl_label = 'Select Continuouse'
	bl_options = { 'UNDO' }

	extend: bpy.props.BoolProperty(
			name='Extend',
			description='Add to existing selection.',
			default=False
	)

	modo_algorithm: bpy.props.BoolProperty(
			name='Modo Loop',
			description='Uses an alternative algorithm to match modo\' loop selection behavior.',
			default=False
	)

	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			rmmesh.readonly = True
			sel_mode = context.tool_settings.mesh_select_mode[:]
			if sel_mode[0]:
				selected_verts = rmlib.rmVertexSet.from_selection( rmmesh )				
				bpy.ops.mesh.select_linked( delimit={ 'SEAM' } )
				if self.extend:
					selected_verts.select( False )
			elif sel_mode[1]:
				bpy.ops.mesh.rm_loop( force_boundary=True, modo_algorithm=self.modo_algorithm )
			else:
				selected_polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				bpy.ops.mesh.select_linked( delimit={ 'SEAM' } )
				if self.extend:
					selected_polys.select( False )
		return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_loop.bl_idname ) )
	bpy.utils.register_class( MESH_OT_loop )
	print( 'register :: {}'.format( MESH_OT_ring.bl_idname ) )
	bpy.utils.register_class( MESH_OT_ring )
	print( 'register :: {}'.format( MESH_OT_continuous.bl_idname ) )
	bpy.utils.register_class( MESH_OT_continuous )
	
	
def unregister():
	print( 'unregister :: {}'.format( MESH_OT_loop.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_loop )
	print( 'unregister :: {}'.format( MESH_OT_ring.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_ring )
	print( 'unregister :: {}'.format( MESH_OT_continuous.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_continuous )