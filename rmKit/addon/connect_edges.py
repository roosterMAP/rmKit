import bpy, bmesh, mathutils
import math
import rmKit.rmlib as rmlib

class CEEdge( object ):
	BMesh = None

	def __init__( self, e, ept1, ept2, active ):
		self.edge = e
		self.index = e.index
		self.active = active
		self.slide_switch = False
		self.ept1 = ept1
		self.ept2 = ept2
		self.ept1_idx = ept1.index
		self.ept2_idx = ept2.index
		self.__subverts = []

	def __getattr__( self, name ):
		try:
			return super( CEEdge, self ).__getattribute__( name )
		except AttributeError:
			return getattr( self.edge, name )

	def __repr__( self ):
		if self.active:
			return 'CEEdge:{} ACTIVE'.format( self.index )
		else:
			return 'CEEdge:{} INACTIVE'.format( self.index )

	def GetSubverts( self, p ):
		vlist = list( p.verts )
		idx = vlist.index( self.ept1 )
		if vlist[idx-1].index == self.ept2.index:
			return self.__subverts[::-1]
		return self.__subverts

	def CreateSubverts( self, level, slide, pinch ):
		if not self.active:
			self.__subverts = list( self.verts )
			return
		
		if not self.slide_switch:
			slide *= -1.0
			
		pos1 = self.ept1.co
		pos2 = self.ept2.co
			
		d = min( 1.0, float( level - 1 ) / float( level + 1 ) * pinch )
		e = ( 1.0 - d ) * 0.5
		v_min = max( 0.0, e + slide )
		v_max = min( 1.0, 1.0 - e + slide )
		if v_min == 0.0:
			v_max = d
		if v_max == 1.0:
			v_min = 1.0 - d
		try:
			v_step = d / float( level - 1 )
		except ZeroDivisionError:
			v_step = 0.0

		self.__subverts = [ self.ept1 ]
		vec = pos2 - pos1
		p = pos1 + ( vec * v_min )
		sv = CEEdge.BMesh.verts.new( p, self.ept1 )
		self.__subverts.append( sv )
		for i in range( level - 1 ):
			p += ( vec * v_step )
			sv = CEEdge.BMesh.verts.new( p, self.ept1 )
			self.__subverts.append( sv )
		self.__subverts.append( self.ept2 )
		

class CEPoly( object ):
	BMesh = None
	level = 0
	AllCEEdges = set()
	AllCEPolygons = set()
	JointCEPolygonIndexes = set()
	UVLayers = None

	def __init__( self, p ):
		self.polygon = p
		self.eidx_list = []
		self.ceEdges = []
		self.seed_polygons = []
		self.index = p.index
		self.uvdata = []

		CEPoly.AllCEPolygons.add( self )

		vcount = len( self.verts )
		for i in range( vcount ):
			v1 = self.verts[i]
			try:
				v2 = self.verts[i+1]
			except IndexError:
				v2 = self.verts[0]
			e = rmlib.rmEdgeSet.from_endpoints( v1, v2 )

			if e.select:
				self.eidx_list.append( i )
				
			ceeAlreadyExists = False
			for cee in CEPoly.AllCEEdges:
				if cee.index == e.index:
					self.ceEdges.append( cee )
					ceeAlreadyExists = True
					break
			if not ceeAlreadyExists:
				cee = CEEdge( e, v1, v2, e.select )
				self.ceEdges.append( cee )
				CEPoly.AllCEEdges.add( cee )

		#cache uv data
		if CEPoly.UVLayers is not None:
			for uvlayer in CEPoly.UVLayers.values():
				self.uvdata.append( [ self.polygon.loops[i][uvlayer].uv.copy() for i in range( vcount ) ] )

	@classmethod
	def AccumulateCEElem( cls, seed_poly, seed_edge=None ):
		if seed_poly.tag:
			return
		seed_poly.tag = True
		cep = cls( seed_poly )
		
		if seed_edge is not None:
			for i, cee in enumerate( cep.ceEdges ):
				if cee.index == seed_edge.index:
					break
			ceEdges = cep.ceEdges[i:] + cep.ceEdges[:i]
			switch = not seed_edge.slide_switch
		else:
			ceEdges = cep.ceEdges
			switch = cep.ceEdges[0].slide_switch
		
		for i, cee in enumerate( ceEdges ):
			if cee.edge.tag:
				if cee.edge.select:
					switch = cee.slide_switch
				continue
			cee.edge.tag = True
			if cee.edge.select:
				cee.slide_switch = switch
				for p in cee.edge.link_faces:
					if p.tag or p.index in CEPoly.JointCEPolygonIndexes:
						continue
					cls.AccumulateCEElem( p, cee )

	def __getattr__( self, name ):
		try:
			return super( CEPoly, self ).__getattribute__( name )
		except AttributeError:
			return getattr( self.polygon, name )

	def __repr__( self ):
		s = 'CEPoly {}\n'.format( self.index )
		for i, e in enumerate( self.ceEdges ):			
			s += '\tvidx:{} -> {}\n'.format( self.verts[i].index, e )
		return s

	def ComputeUVCoord( self, subvert_vidx, start_vidx, new_poly ):
		"""
		Sets the uv corrd of a vert on a poly. This is done by interpolating
		between the endpoints of the edge on which the subvert resides.

		Args:
			subvert_vidx (int): The index of the vert in new_poly. This is the vert that gets its uv set.
			start_vidx (int): The index of the start endpoint in self.polygon of the edge where the subvert exists.
			new_poly ( bmesh.types.BFace ): The polygon whose vert is getting the uv coord.

		"""
		start_3d = self.polygon.verts[start_vidx].co
		try:
			end_3d = self.polygon.verts[start_vidx+1].co
		except IndexError:
			end_3d = self.polygon.verts[0].co
		length_3d = ( end_3d - start_3d ).length
		weight = ( new_poly.verts[subvert_vidx].co - start_3d ).length / length_3d


		for uvlayer in CEPoly.UVLayers.values():
			start_uv = self.polygon.loops[start_vidx][uvlayer].uv
			try:
				end_uv = self.polygon.loops[start_vidx+1][uvlayer].uv
			except IndexError:
				end_uv = self.polygon.loops[0][uvlayer].uv
			vec_uv = end_uv - start_uv
			interp_uv = start_uv + ( vec_uv * weight )
			new_poly.loops[subvert_vidx][uvlayer].uv = interp_uv

	def __createOuterPolygon( self, vlist, vidxs ):
		if len( set( vlist ) ) < 3:
			return None
			
		verts = [ vlist[0] ]
		startvert_idxlist = [vidxs[0] ]
		for i in range( 1, len( vlist ) ):
			if vlist[i] == verts[-1]:
				continue
			verts.append( vlist[i] )
			startvert_idxlist.append( vidxs[i] )

		new_poly = CEPoly.BMesh.faces.new( verts, self.polygon )

		if CEPoly.UVLayers is not None:
			for i in range( len( verts ) ):
				self.ComputeUVCoord( i, startvert_idxlist[i], new_poly )
					
		return new_poly

	def __createInnerPolygons( self, ceedge1_idx, ceedge2_idx ):
		new_polygons = rmlib.rmPolygonSet()

		vlist1 = self.ceEdges[ceedge1_idx].GetSubverts( self )[1:-1]
		vlist1 = vlist1[ int( CEPoly.level / 2 ): ][::-1]

		vlist2 = self.ceEdges[ceedge2_idx].GetSubverts( self )[1:-1]
		vlist2 = vlist2[ :int( CEPoly.level / 2 ) + int( CEPoly.level % 2 ) ]
	
		for i in range( 1, len( vlist1 ) ):
			quad = ( vlist1[i], vlist1[i-1], vlist2[i-1], vlist2[i] )
			new_poly = CEPoly.BMesh.faces.new( quad, self.polygon )

			if CEPoly.UVLayers is not None:
				self.ComputeUVCoord( 0, ceedge1_idx, new_poly )
				self.ComputeUVCoord( 1, ceedge1_idx, new_poly )
				self.ComputeUVCoord( 2, ceedge2_idx, new_poly )
				self.ComputeUVCoord( 3, ceedge2_idx, new_poly )
				
			new_polygons.append( new_poly )

		return new_polygons

	def __createCenterPolygon( self, vlist, start_vidxs ):
		if len( vlist ) >= 3:
			new_poly = CEPoly.BMesh.faces.new( vlist, self.polygon )

			if CEPoly.UVLayers is not None:
				for i in range( len( vlist ) ):
					self.ComputeUVCoord( i, start_vidxs[i], new_poly )

			return new_poly

	def __createCapPolygon( self ):
		"""
		Case for when exactly one active edge in CEPoly.
		"""
		
		vertlist = rmlib.rmVertexSet()
		startvert_idxlist = []

		for i, e in enumerate( self.edges ):
			if i in self.eidx_list:
				subverts = self.ceEdges[i].GetSubverts( self )
				vertlist += subverts[:-1]
				startvert_idxlist += [ i ] * ( len( subverts ) - 1 )
			else:
				vertlist.append( self.verts[i] )
				startvert_idxlist.append( i )

		new_poly = CEPoly.BMesh.faces.new( vertlist, self.polygon )

		if CEPoly.UVLayers is not None:
			for i in range( len( vertlist ) ):
				self.ComputeUVCoord( i, startvert_idxlist[i], new_poly )
	
		return new_poly

	def ConnectEdges( self ):
		if len( self.eidx_list ) == 1:
			return self.__createCapPolygon()

		#init previous_idx such that it is on an active edge
		for previous_idx in range( len( self.verts ) ):
			if previous_idx in self.eidx_list:          
				break
		current_idx = ( previous_idx + 1 ) % len( self.verts )	

		centerPoly_verts = rmlib.rmVertexSet()
		centerPoly_vidxs = []
		outerPoly_verts = self.ceEdges[previous_idx].GetSubverts( self )[-2:]
		outerPoly_vidxs = [previous_idx] * len( outerPoly_verts )
		for i in range( len( self.verts ) ):
			active = current_idx in self.eidx_list
			subverts = self.ceEdges[current_idx].GetSubverts( self )

			#handles outer polygons
			if active:
				self.__createOuterPolygon( outerPoly_verts + subverts[:2], outerPoly_vidxs + [current_idx] * len( subverts[:2] ) )
				outerPoly_verts = subverts[-2:]
				outerPoly_vidxs = [ current_idx, current_idx ]
			else:
				outerPoly_verts.append( self.verts[current_idx] )
				outerPoly_vidxs.append( current_idx )

			#handles inner polygons
			if active and CEPoly.level > 1:
				next_idx = ( current_idx + 1 ) % len( self.verts )
				while( next_idx not in self.eidx_list ):
					next_idx = ( next_idx + 1 ) % len( self.verts )
				self.__createInnerPolygons( current_idx, next_idx )

			#handles center polygom
			if active:
				if CEPoly.level % 2 == 0:
					centerPoly_verts.append( subverts[ int( len( subverts ) / 2 ) - 1 ] )
					centerPoly_vidxs.append( current_idx )
				centerPoly_verts.append( subverts[ int( len( subverts ) / 2 ) ] )
				centerPoly_vidxs.append( current_idx )

			#increment
			previous_idx = current_idx
			current_idx = ( current_idx + 1 ) % len( self.verts )
			
		self.__createCenterPolygon( centerPoly_verts, centerPoly_vidxs )


	@staticmethod
	def Cleanup():
		for cep in CEPoly.AllCEPolygons:
			CEPoly.BMesh.faces.remove( cep.polygon )
		for cee in CEPoly.AllCEEdges:
			if cee.active:
				CEPoly.BMesh.edges.remove( cee.edge )
			else:
				cee.edge.tag = False
				
	@staticmethod
	def ClearStaticMembers():
		CEPoly.AllCEPolygons.clear()
		CEPoly.AllCEEdges.clear()
		CEPoly.JointCEPolygonIndexes.clear()
		CEPoly.UVLayers = None


class MESH_OT_connect_edge( bpy.types.Operator ):
	bl_idname = 'mesh.rm_connectedge'
	bl_label = 'Connect Edges'
	bl_options = { 'REGISTER', 'UNDO' }
	
	level: bpy.props.IntProperty(
		name='Level',
		default=5,
		min=1,
		max=64
	)
	slide: bpy.props.FloatProperty(
		name='Slide',
		default=0.0,
		min=-1.0,
		max=1.0
	)
	pinch: bpy.props.FloatProperty(
		name='Pinch',
		default=1.0,
		min=0.0,
		max=2.0
	)

	def __init__( self ):
		self.bmesh = None

	def __del__( self ):
		CEPoly.ClearStaticMembers()
		if self.bmesh is not None:
			self.bmesh.free()
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )

	def LocalizeNewBMesh( self ):
		bm = self.bmesh.copy()
		bm.verts.ensure_lookup_table()
		bm.edges.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		CEEdge.BMesh = bm
		CEPoly.BMesh = bm
		CEPoly.level = self.level
		for p in CEPoly.AllCEPolygons:
			p.polygon = bm.faces[p.index]
		for e in CEPoly.AllCEEdges:
			e.edge = bm.edges[e.index]
			e.ept1 = bm.verts[e.ept1_idx]
			e.ept2 = bm.verts[e.ept2_idx]
		return bm
		
	def execute( self, context ):
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )

		bm = self.LocalizeNewBMesh()

		CEPoly.UVLayers = bm.loops.layers.uv

		for cee in CEPoly.AllCEEdges:
			cee.CreateSubverts( self.level, self.slide, self.pinch )

		for cep in CEPoly.AllCEPolygons:
			cep.ConnectEdges()

		CEPoly.Cleanup()

		targetMesh = context.active_object.data
		bm.to_mesh( targetMesh )
		bm.calc_loop_triangles()
		targetMesh.update()
		bm.free()
		
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )

		return { 'FINISHED' }

	def invoke( self, context, event ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			return { 'CANCELLED' }
		
		CEPoly.ClearStaticMembers()

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readonly = True

				CEEdge.BMesh = rmmesh.bmesh
				CEPoly.BMesh = rmmesh.bmesh
				
				for e in rmmesh.bmesh.edges:
					e.tag = False
				for p in rmmesh.bmesh.faces:
					p.tag = False
					
				selected_edges = rmlib.rmEdgeSet.from_selection( rmmesh )
				if len( selected_edges ) < 1:
					return { 'CANCELLED' }

				active_polygons = rmlib.rmPolygonSet()
				for p in selected_edges.polygons:
					count = 0
					for i in range( len( p.verts ) ):
						v1 = p.verts[i-1]
						v2 = p.verts[i]
						e = rmlib.rmEdgeSet.from_endpoints( v1, v2 )
						if e.select:
							count += 1
					if count > 2:
						active_polygons.insert( 0, p )
						CEPoly.JointCEPolygonIndexes.add( p.index )
					else:
						active_polygons.append( p )
					
				for p in active_polygons:
					CEPoly.AccumulateCEElem( p )
				if len( CEPoly.AllCEPolygons ) < 1:
					return { 'CANCELLED' }

				self.bmesh = rmmesh.bmesh.copy()
				
		return self.execute( context )

def register():
	bpy.utils.register_class( MESH_OT_connect_edge )
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_connect_edge )