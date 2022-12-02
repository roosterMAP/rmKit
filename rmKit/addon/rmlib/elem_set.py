import bpy
from bpy_extras import view3d_utils
from rmKit.rmlib import util
import mathutils

def shared_edge( p1, p2 ):
	for e in p1.edges:
		for np in e.link_faces:
			if np == p2:
				return e
	return None


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
	def from_mos( cls, rmmesh, context, mouse_pos, ignore_backfacing=True ):
		rm_vp = util.rmViewport( context )
		look_idx, look_vec, axis_vec = rm_vp.get_nearest_direction_vector( 'front' )

		xfrm = rmmesh.world_transform
		view_pos = rm_vp.cam_pos
		
		wld_spc_vpos = [None] * len( rmmesh.bmesh.verts )
		active_faces = cls()
		for f in cls( f for f in rmmesh.bmesh.faces if not f.hide ):
			f_normal = xfrm.to_3x3() @ f.normal.copy()
			f_normal.normalize()
			if ignore_backfacing and f_normal.dot( look_vec ) > 0.0:
				continue
			active_faces.append( f )
			for v in f.verts:
				if wld_spc_vpos[v.index] is None:
					wld_spc_vpos[v.index] = xfrm @ v.co.copy()
		if len( active_faces ) < 1:
			return active_faces

		min_dist = 999999999.9
		mos_face = active_faces[0]
		for tri in rmmesh.bmesh.calc_loop_triangles():
			if tri[0].face not in active_faces:
				continue
			sp1 = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=wld_spc_vpos[tri[0].vert.index] )
			sp2 = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=wld_spc_vpos[tri[1].vert.index] )
			sp3 = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=wld_spc_vpos[tri[2].vert.index] )
			if sp1 is None or sp2 is None or sp3 is None:
				continue
			hit = mathutils.geometry.intersect_point_tri_2d( mouse_pos, mathutils.Vector( sp1 ), mathutils.Vector( sp2 ), mathutils.Vector( sp3 ) )
			if hit:
				tri_center = ( wld_spc_vpos[tri[0].vert.index] + wld_spc_vpos[tri[1].vert.index] + wld_spc_vpos[tri[2].vert.index] ) * 0.33333333333
				d = ( tri_center - view_pos ).length
				if d < min_dist:
					min_dist = d
					mos_face = tri[0].face

		return cls( [mos_face] )
	
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
			
	def group( self, element=False, use_seam=False ):
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
			if use_seam:
				for e in p.edges:
					if e.seam:
						v1, v2 = e.verts
						v1.tag = True
						v2.tag = True
				
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
						if use_seam and v.tag:
							e = shared_edge( p, np )
							if e is None or e.seam:
								continue
						if element or np in self:
							outerSet.add( np )
							np.tag = True
							
			continuous_groups.append( innerSet )
			
		for group in continuous_groups:
			for p in group:
				p.tag = False
				if use_seam:
					for v in p.verts:
						v.tag = False
			
		return continuous_groups



	def island( self, uvlayer ):
		"""
		Returns list of rmPolygonSets where each set is an uv island for the uvlayer dataset.

		Args:
			uvlayer (bmesh.types.BMLoopUV): The layer dataset from which to read uv coords.

		Returns:
			[rmPolygonSets,]: List of rmPolygonSets.
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
				for l in p.loops:
					v = l.vert
					for nl in v.link_loops:
						np = nl.face
						if np.tag:
							continue
						if np in self and util.AlmostEqual_v2( l[uvlayer].uv, nl[uvlayer].uv ):
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
		look_idx, look_vec, axis_vec = rm_vp.get_nearest_direction_vector( 'front' )

		xfrm = rmmesh.world_transform

		mos_edges = cls()
		active_edges = cls( e for e in rmmesh.bmesh.edges if not e.hide )
		for e in active_edges:
			ept1, ept2 = e.verts
			enml = ( ept1.normal + ept2.normal ) * 0.5
			enml = xfrm.to_3x3() @ enml
			if ignore_backfacing and enml.dot( look_vec ) > 0.0:
				continue
			pos1_wld = xfrm @ ept1.co
			pos2_wld = xfrm @ ept2.co
			sp1 = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos1_wld )
			sp2 = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos2_wld )
			if sp1 is None or sp2 is None:
				continue
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

		#blender's poly->boundary cmd doesnt clear all edge tags.
		for v in self.vertices:
			for e in v.link_edges:
				e.tag = False
		
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
		look_idx, look_vec, axis_vec = rm_vp.get_nearest_direction_vector( 'front' )

		xfrm = rmmesh.world_transform

		mos_verts = cls()
		active_vertices = cls( v for v in rmmesh.bmesh.verts if not v.hide )
		for v in active_vertices:
			vnorm = xfrm @ xfrm.to_3x3()
			if ignore_backfacing and vnorm.dot( look_vec ) > 0.0:
				continue
			pos_wld = xfrm @ v.co
			sp = view3d_utils.location_3d_to_region_2d( region=context.region, rv3d=context.region_data, coord=pos_wld )
			if sp is None:
				continue
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

	@property
	def loops( self ):
		loops = set()
		for v in self:
			for l in v.link_loops:
				loops.add( l )
		return loops

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


class rmUVLoopSet( list ):
	"""
	Utility class for lists of bmesh.types.BMLoop objects
	"""
	
	def __init__( self, *args, **kwargs ):
		"""
		Constructor for rmUVLoopSet.
		Positional values initializes the super list data.
		Kay value(s) are for the uvlayer dataset.
		"""
		self.uvlayer = None
		list.__init__( self, *args )
		for key, value in kwargs.items():
			if key == 'uvlayer':
				self.uvlayer = value
		
	def __repr__( self ):
		return 'rmUVLoopSet :: {}'.format( [ l.index for l in self ] )
	
	@classmethod
	def from_selection( cls, rmmesh, uvlayer=None ):
		"""
		Class method that returns rmUVLoopSet of current loop selection.

		Args:
			rmmesh (rmMesh): The input mesh whose polygons are selected.
			uvlayer (bmesh.types.BMLoopUV): The uvlayer dataset.

		Returns:
			[rmUVLoopSet,]: List of rmUVLoopSet.
		"""
		
		if uvlayer is None:
			uvlayer = rmmesh.active_uv

		members = cls( [], uvlayer=uvlayer )
		for f in rmmesh.bmesh.faces:
			for l in f.loops:
				if l[uvlayer].select:
					members.append( l )
			
		return members

	@classmethod
	def from_edge_selection( cls, rmmesh, uvlayer=None ):
		"""
		Class method that returns rmUVLoopSet of current loop selection.

		Args:
			rmmesh (rmMesh): The input mesh whose polygons are selected.
			uvlayer (bmesh.types.BMLoopUV): The uvlayer dataset.

		Returns:
			[rmUVLoopSet,]: List of rmUVLoopSet.
		"""
		
		if uvlayer is None:
			uvlayer = rmmesh.active_uv

		members = cls( [], uvlayer=uvlayer )		
		for f in rmmesh.bmesh.faces:
			for l in f.loops:
				if l[uvlayer].select_edge:
					members.append( l )
			
		return members

	@classmethod
	def from_mesh( cls, rmmesh, uvlayer, filter_hidden=True ):
		"""
		Returns a list of all bmesh.types.BMLoop objects that make up a mesh.

		Args:
			rmmesh (rmMesh): The input mesh whose loops are selected.
			uvlayer (bmesh.types.BMLoopUV): The uvlayer dataset.
			filter_hidden (bool): If True, we skip elems hidden in 3d view.

		Returns:
			[rmLoopSet,]: List of rmUVLoopSet.
		"""
		members = cls( [], uvlayer=uvlayer )
		for f in rmmesh.bmesh.faces:
			if filter_hidden and f.hide:
				continue
			for l in f.loops:
				if filter_hidden and l[uvlayer].hide:
					continue
				members.append( l )
		return members
	
	def group_faces( self ):
		continuous_groups = []

		for l in self:
			l.tag = False

		#filter out loops whose faces have loops that are not part of self
		mode_loops = []
		all_loops = set( self )
		for l in all_loops:
			if l.tag:
				continue
			next_l = l.link_loop_next
			while l != next_l:
				next_l.tag = True
				if next_l not in all_loops:
					break
				next_l = next_l.link_loop_next
			if l == next_l:
				mode_loops += list( l.face.loops )
		for l in self:
			l.tag = False

		for loop in mode_loops:
			if loop.tag:
				continue

			innerSet = set()
			outerSet = set( [ loop ] )

			while len( outerSet ) > 0:
				l = outerSet.pop()
				cycleSet = set( [l] )

				#test link_loop adjacency
				for nl in l.vert.link_loops:
					if nl.tag:
						continue
					if nl in mode_loops:
						if util.AlmostEqual_v2( l[self.uvlayer].uv, nl[self.uvlayer].uv ):
							cycleSet.add( nl )

				#test loop_cycle adjacency
				for nl in cycleSet:
					if nl.tag:
						continue
					
					nl_next = nl.link_loop_next
					if not nl_next.tag and nl_next in mode_loops:
						outerSet.add( nl_next )
						
					nl_prev = nl.link_loop_prev
					if not nl_prev.tag and nl_prev in mode_loops:
						outerSet.add( nl_prev )
						
					innerSet.add( nl )
					nl.tag = True

			#add back in the loops that were filtered out at the beginig
			new_members = set()
			for l in innerSet:
				for nl in l.vert.link_loops:
					if nl in self and util.AlmostEqual_v2( l[self.uvlayer].uv, nl[self.uvlayer].uv ):
						new_members.add( nl )
			continuous_groups.append( rmUVLoopSet( list( innerSet.union( new_members ) ), uvlayer=self.uvlayer ) )

		for group in continuous_groups:
			for l in group:
				l.tag = False

		return continuous_groups


	def border_loops( self, invert=False ):
		boader_loops = rmUVLoopSet( [], uvlayer=self.uvlayer )
		continuous_loops = rmUVLoopSet( [], uvlayer=self.uvlayer )
		for l in self:
			if len( l.edge.link_faces ) < 2:
				boader_loops.append( l )
				continue

			next_l = l.link_loop_next
			for nl in next_l.vert.link_loops:
				if nl.edge == l.edge and nl.face != l.face:
					break
			next_nl = nl.link_loop_next
			if util.AlmostEqual_v2( nl[self.uvlayer].uv, next_l[self.uvlayer].uv ) and util.AlmostEqual_v2( next_nl[self.uvlayer].uv, l[self.uvlayer].uv ):
				continuous_loops.append( l )
			else:
				boader_loops.append( l )

		if invert:
			return continuous_loops
		else:
			return boader_loops


	def group_edges( self ):
		continuous_groups = []

		for l in self:
			l.edge.tag = True
			l.tag = False

		for loop in self:
			if loop.tag:
				continue

			innerSet = set()
			outerSet = [ loop ]

			while len( outerSet ) > 0:
				l = outerSet.pop( 0 )
				if l.edge.tag:
					innerSet.add( l )
				l.tag = True

				#test link_loop adjacency
				for el in [ l, l.link_loop_next ]:
					for nl in el.vert.link_loops:
						if not nl.tag and nl.edge.tag and nl in self:
							if util.AlmostEqual_v2( el[self.uvlayer].uv, nl[self.uvlayer].uv ):
								outerSet.append( nl )
								nl.tag = True
						nl_prev = nl.link_loop_prev
						if not nl_prev.tag and nl_prev.edge.tag and nl_prev in self:
							if util.AlmostEqual_v2( el[self.uvlayer].uv, nl[self.uvlayer].uv ):
								outerSet.append( nl_prev )
								nl_prev.tag = True

			continuous_groups.append( rmUVLoopSet( innerSet, uvlayer=self.uvlayer ) )

		for l in self:
			l.edge.tag = False
			l.tag = False

		return continuous_groups


	def add_overlapping_loops( self, include_edge_endpoint=False ):
		for l in self:
			l.tag = True
			
		for i in range( len( self ) ):
			l = self[i]
			for nl in l.vert.link_loops:
				if not nl.tag and util.AlmostEqual_v2( l[self.uvlayer].uv, nl[self.uvlayer].uv ):
					self.append( nl )

			if include_edge_endpoint:
				el = l.link_loop_next
				if not el.tag:
					self.append( el )
					el.tag = True
				for nl in el.vert.link_loops:
					if not nl.tag and util.AlmostEqual_v2( el[self.uvlayer].uv, nl[self.uvlayer].uv ):
						self.append( nl )

		for l in self:
			l.tag = False
	

	def group_vertices( self, element=False ):
		continuous_groups = []

		for l in self:
			l.tag = False

		for loop in self:
			if loop.tag:
				continue

			innerSet = set()
			outerSet = set( [ loop ] )

			while len( outerSet ) > 0:
				l = outerSet.pop()
				cycleSet = set( [l] )

				#test link_loop adjacency
				for nl in l.vert.link_loops:
					if nl.tag or nl == l:
						continue
					if element or nl in self:
						if util.AlmostEqual_v2( l[self.uvlayer].uv, nl[self.uvlayer].uv ):
							cycleSet.add( nl )

				#test loop_cycle adjacency
				for nl in cycleSet:
					if nl.tag:
						continue
					
					nl_next = nl.link_loop_next
					if not nl_next.tag and ( element or nl_next in self ):
						outerSet.add( nl_next )
						
					nl_prev = nl.link_loop_prev
					if not nl_prev.tag and ( element or nl_prev in self ):
						outerSet.add( nl_prev )
						
					innerSet.add( nl )
					nl.tag = True
							
			continuous_groups.append( rmUVLoopSet( innerSet, uvlayer=self.uvlayer ) )

		for group in continuous_groups:
			for l in group:
				l.tag = False

		return continuous_groups