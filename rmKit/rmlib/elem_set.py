import bpy
from bpy_extras import view3d_utils
from rmKit.rmlib import util
import mathutils


#MOS :: https://blender.stackexchange.com/questions/9222/how-to-get-intersection-of-a-specific-object-and-the-mouse-in-the-bge


class rmPolygonSet( list ):
	"""
	Utility class for lists of bmesh.types.BMFace objects
	"""
	
	def __init__( self, *args ):
		list.__init__( self, *args )
		
	def __repr__( self ):
		return 'PolygonSet :: {}'.format( [ p.index for p in self ] )
	
	@classmethod
	def from_selection( cls, rmmesh ):
		"""
		Class method that returns PolygonSet of current face selection.

		Args:
			rmmesh (rmMesh): The input mesh whose polygons are selected.


		Returns:
			[PolygonSet,]: List of PolygonSets.
		"""
		return cls( p for p in rmmesh.bmesh.faces if p.select )

	@classmethod
	def from_mesh( cls, rmmesh, filter_hidden=False ):
		"""
		Returns a list of 3d continuous PolygonSets.

		Args:
			rmmesh (rmMesh): The input mesh whose polygons are selected.
			filter_hidden (bool): When True, all hidden polys are omitted from the return list.

		Returns:
			[PolygonSet,]: List of PolygonSets.
		"""
		
		if filter_hidden:
			return cls( p for p in rmmesh.bmesh.faces )
		else:
			return cls( p for p in rmmesh.bmesh.faces if not p.hide )

	@classmethod
	def from_mos( cls, rmmesh, context, event, ignore_backfacing=True ):
		m_x, m_y = event.mouse_region_x, event.mouse_region_y
		mouse_pos = mathutils.Vector( ( float( m_x ), float( m_y ) ) )

		look_pos = view3d_utils.region_2d_to_origin_3d( context.region, context.region_data, mouse_pos )
		look_vec = view3d_utils.region_2d_to_vector_3d( context.region, context.region_data, mouse_pos )

		mos_polygons = cls()
		world_transform_inv = rmmesh.world_transform.inverted()
		cam_pos_obj = look_pos @ world_transform_inv					
		look_vec_obj = look_vec @ world_transform_inv.to_3x3()
		bvh = mathutils.bvhtree.BVHTree.FromBMesh( rmmesh.bmesh )
		location, normal, index, distance = bvh.ray_cast( cam_pos_obj, look_vec_obj )
		if location is not None:
			p = rmmesh.bmesh.faces[index]
			if ignore_backfacing and p.normal.dot( look_vec ) < 0.0:
				mos_polygons.append( p )

		return mos_polygons
	
	@property
	def vertices( self ):
		"""
		Returns rmVertexSet of member vertices of self.

		Returns:
			[rmVertexSet,]: List of vertices
		"""
		verts = set()		
		for p in self:
			for v in p.verts:
				verts.add( v )
		return rmVertexSet( verts )
	
	@property
	def edges( self ):
		"""
		Returns rmEdgeSet of member edge of self.

		Returns:
			[rmEdgeSet,]: List of edges
		"""
		edges = set()
		for p in self:
			for e in p.edges:
				if e not in edges:
					edges.add( e )
		return rmEdgeSet( edges )

	def tag( self, b ):
		"""
		Set tag for all member face.

		Args:
			b (bool): Value to which all member tags are set.
		"""
		for p in self:
			p.tag = b

	def select( self, replace=False ):
		"""
		Select member polygons

		Args:
			replace (bool): When true, current selection is first cleared.
		"""
		if replace:
			bpy.ops.mesh.select_all( action ='DESELECT' )
		for p in self:
			p.select = True
			
	def group( self, element=False ):
		"""
		Returns a list of 3d continuous PolygonSets.

		Args:
			element (bool): When True, all polys 3d continuouse to self are visited.

		Returns:
			[PolygonSet,]: List of PolygonSets.
		"""
		
		continuous_groups = []
		
		for p in self:
			p.tag = False
				
		for poly in self:
			if poly.tag:
				continue
				
			innerSet = rmPolygonSet()
			poly.tag = True
			outerSet = set( [ poly ] )
			
			while len( outerSet ) > 0:
				p = outerSet.pop()
				innerSet.append( p )
				for v in p.verts:
					for np in v.link_faces:
						if np.tag:
							continue							
						if element or np in self:
							outerSet.add( np )
							np.tag = True
							
			continuous_groups.append( innerSet )
			
		for group in continuous_groups:
			for p in group:
				p.tag = False
			
		return continuous_groups
	
	
class rmEdgeSet( list ):
	"""
	Utility class for lists of bmesh.types.BMEdge objects
	"""	
	
	def __init__( self, *args ):
		list.__init__( self, *args )
		
	def __repr__( self ):
		return 'EdgeSet :: {}'.format( [ v.index for v in self ] )
	
	@classmethod
	def from_selection( cls, rmmesh ):
		return cls( e for e in rmmesh.bmesh.edges if e.select )

	@classmethod
	def from_mesh( cls, rmmesh, filter_hidden=False ):
		if filter_hidden:
			return cls( e for e in rmmesh.bmesh.edges )
		else:
			return cls( e for e in rmmesh.bmesh.edges if not e.hide )

	@classmethod
	def from_mos( cls, rmmesh, context, mouse_pos, pixel_radius=8, ignore_backfacing=True ):
		rm_vp = util.rmViewport( context )
		look_idx, abs_look_vec, look_vec = rm_vp.get_nearest_direction_vector( 'front' )

		mos_edges = cls()
		active_edges = cls( e for e in rmmesh.bmesh.edges if not e.hide )
		for e in active_edges:
			ept1, ept2 = e.verts
			if ignore_backfacing and ept1.normal.dot( look_vec ) > 0.0 and ept2.normal.dot( look_vec ) > 0.0:
				continue
			pos1_wld = ept1.co @ rmmesh.world_transform
			pos2_wld = ept2.co @ rmmesh.world_transform
			sp1 = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos1_wld )
			sp2 = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos2_wld )
			if util.line2_dist( mathutils.Vector( sp1 ), mathutils.Vector( sp2 ), mathutils.Vector( mouse_pos ) ) <= float( pixel_radius ):
				mos_edges.append( e )

		return mos_edges

	@staticmethod
	def from_endpoints( v1, v2 ):
		for e in v1.link_edges:
			if e.other_vert( v1 ) == v2:
				return e
		raise LookupError( 'Edge with endpoints {} {} could not be found!!!'.format( v1.index, v2.index ) )
	
	@property
	def vertices( self ):
		verts = set()
		for e in self:
			for v in e.verts:
				if v not in verts:
					verts.add( v )
		return rmVertexSet( verts )
	
	@property
	def polygons( self ):
		polys = set()
		for e in self:
			for p in e.link_faces:
				if p not in polys:
					polys.add( p )
		return rmPolygonSet( polys )

	def tag( self, b ):
		for e in self:
			e.tag = b

	def select( self, replace=False ):
		if replace:
			bpy.ops.mesh.select_all( action ='DESELECT' )
		for e in self:
			e.select = True
				
	def group( self, element=False ):
		"""
		Returns a list of 3d continuous EdgeSets.

		Args:
			element (bool): When True, all edges 3d continuouse to self are visited.

		Returns:
			[EdgeSet,]: List of EdgeSet.
		"""
		
		continuous_groups = []
		
		for e in self:
			e.tag = False
				
		for edge in self:
			if edge.tag:
				continue
				
			innerSet = rmEdgeSet()
			edge.tag = True
			outerSet = set( [ edge ] )
			
			while len( outerSet ) > 0:
				e = outerSet.pop()
				innerSet.append( e )
				for v in e.verts:
					for ne in v.link_edges:
						if ne == e or ne.tag:
							continue
						if element or ne in self:
							outerSet.add( ne )
							ne.tag = True
							
			continuous_groups.append( innerSet )
			
		for group in continuous_groups:
			for e in group:
				e.tag = False
			
		return continuous_groups
				
	
	def vert_chain( self ):
		vert_chains = []
		
		#tag all member edges
		for e in self:
			e.tag = True
				
		for e in self:
			#skip if edge has been untagged				
			if not e.tag:
				continue

			#extend the chain in the direction of both endpoints.
			#new verts in fwd dir get appended to the list.
			#new verts in rev dir get inserted at the front of the list.
			vchain = []
			for b, nv in enumerate( list( e.verts )	 ):
				if nv in vchain: #break if loop is closed
					break
				e.tag = True
				ne = e
				while ne.tag: #keep extending until along unprocessed member edges
					ne.tag = False #mark ne as processed

					#extend chain
					if b:
						vchain.append( nv )
					else:
						vchain.insert( 0, nv )
						
					#get next edge
					next_edge_found = False
					for ne in nv.link_edges: #find unprocessed link edge
						if ne.tag:
							next_edge_found = True
							break
					if not next_edge_found:
						break
						
					#get next vert
					nv = ne.other_vert( nv )
				
			e.tag = False

			vert_chains.append( vchain )
			
		for e in self:
			e.tag = False
			
		return vert_chains
	
	def chain( self ):
		"""
		Returns a list of sorted BMVert pairs. Each pair represents the endpoints of an edge.
		The list is sorted such that each edge is touching the edge after and before it like a chain.

		Returns:
			[(BMVert,BMVert),]: List of sorted tuple pairs of BMVerts.
		"""
		
		chains = []
		for ch in self.vert_chain():
			chains.append( [ ( ch[i], ch[i+1] ) for i in range( len( ch ) - 1 ) ] )
			try:
				e = rmEdgeSet.from_endpoints( ch[0], ch[-1] )
				if e in self:
					chains[-1].append( ( ch[-1], ch[0] ) )
			except LookupError:
				pass

		return chains
		
		
class rmVertexSet( list ):
	"""
	Utility class for lists of bmesh.types.BMVert objects
	"""	
	
	def __init__( self, *args ):
		list.__init__( self, *args )
		
	def __repr__( self ):
		return 'VertexSet :: {}'.format( [ v.index for v in self ] )
	
	@classmethod
	def from_selection( cls, rmmesh ):
		return cls( v for v in rmmesh.bmesh.verts if v.select )

	@classmethod
	def from_mesh( cls, rmmesh, filter_hidden=False ):
		if filter_hidden:
			return cls( v for v in rmmesh.bmesh.verts )
		else:
			return cls( v for v in rmmesh.bmesh.verts if not v.hide )

	@classmethod
	def from_mos( cls, rmmesh, context, mouse_pos, pixel_radius=8, ignore_backfacing=True ):
		rm_vp = util.rmViewport( context )
		look_idx, abs_look_vec, look_vec = rm_vp.get_nearest_direction_vector( 'front' )

		mos_verts = cls()
		active_vertices = cls( v for v in rmmesh.bmesh.verts if not v.hide )
		for v in active_vertices:
			if ignore_backfacing and v.normal.dot( look_vec ) > 0.0:
				continue
			pos_wld = v.co @ rmmesh.world_transform
			sp = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos_wld )
			if ( sp - mouse_pos ).length <= float( pixel_radius ):
				mos_verts.append( v )

		return mos_verts

	@property
	def edges( self ):
		edges = set()
		for v in self:
			for e in v.link_edges:
				if e not in edges:
					edges.add( e )
		return rmEdgeSet( edges )
	
	@property
	def polygons( self ):
		polys = set()
		for v in self:
			for p in v.link_faces:
				if p not in polys:
					polys.add( p )
		return rmPolygonSet( polys )

	def tag( self, b ):
		for v in self:
			v.tag = b

	def select( self, replace=False ):
		if replace:
			bpy.ops.mesh.select_all( action ='DESELECT' )
		for v in self:
			v.select = True
				
	def group( self, element=False ):
		"""
		Returns a list of 3d continuous VertexSets.

		Args:
			element (bool): When True, all verts 3d continuouse to self are visited.

		Returns:
			[VertexSet,]: List of VertexSets.
		"""		
		continuous_groups = []
		
		for v in self:
			v.tag = False
				
		for vert in self:
			if vert.tag:
				continue
				
			innerSet = rmVertexSet()
			vert.tag = True
			outerSet = set( [ vert ] )
			
			while len( outerSet ) > 0:
				v = outerSet.pop()
				innerSet.append( v )
				for e in v.link_edges:
					nv = e.other_vert( v )
					if nv.tag:
						continue							
					if element or nv in self:
						outerSet.add( nv )
						nv.tag = True
							
			continuous_groups.append( innerSet )
			
		for group in continuous_groups:
			for v in group:
				v.tag = False
			
		return continuous_groups