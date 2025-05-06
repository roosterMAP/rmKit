import bpy, bmesh, mathutils
import math
import rmlib

class CEVert( object ):
	def __init__( self, vert ):
		self.vert = vert
		self.index = vert.index
		self.root_indexes = []
		self.__rootverts = []

	def __repr__( self ):
		return 'CEVert :: {}'.format( self.vert.index )

	def __getattr__( self, name ):
		try:
			return super( CEVert, self ).__getattribute__( name )
		except AttributeError:
			return getattr( self.vert, name )

	def __len__( self ):
		return len( self.__rootverts )

	def AddRootVert( self, vert ):
		self.__rootverts.append( vert )
		self.root_indexes.append( vert.vert.index )

	def GetEndVerts( self, p ):
		vlist = list( p.verts )
		idx = vlist.index( self.__rootverts[0].vert )
		if vlist[idx-1] == self.__rootverts[1].vert:
			return self.__rootverts[1], self.__rootverts[0]
		return self.__rootverts[0], self.__rootverts[1]


class CEEdge( object ):
	BMesh = None

	def __init__( self, e, ept1, ept2, active, source_poly ):
		self.edge = e
		self.index = e.index
		self.active = active
		self.slide_switch = False
		self.ept1 = ept1
		self.ept2 = ept2
		self.__subverts = []
		self.source_poly = source_poly

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
		idx = vlist.index( self.ept1.vert )
		if vlist[idx-1].index == self.ept2.vert.index:
			return self.__subverts[::-1]
		return self.__subverts

	def CreateSubverts( self, level, slide, pinch ):
		if not self.active:
			self.__subverts = [ self.ept1, self.ept2 ]
			return
		
		if self.slide_switch:
			slide *= -1.0
		
		pos1 = self.ept1.vert.co
		pos2 = self.ept2.vert.co
			
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
		sv = CEEdge.BMesh.verts.new( p, self.ept1.vert )
		self.__subverts.append( CEVert( sv ) )
		for i in range( level - 1 ):
			p += ( vec * v_step )
			sv = CEEdge.BMesh.verts.new( p, self.ept1.vert )
			self.__subverts.append( CEVert( sv ) )
		self.__subverts.append( self.ept2 )

		for i in range( 1, len( self.__subverts ) - 1 ):
			CEPoly.ALLCEVerts.add( self.__subverts[i] )
			self.__subverts[i].AddRootVert( self.ept1 )
			self.__subverts[i].AddRootVert( self.ept2 )
		

class CEPoly( object ):
	BMesh = None
	level = 0
	ALLCEVerts = set()
	AllCEEdges = set()
	AllCEPolygons = set()

	def __init__( self, p ):
		"""
		CEPoly constructor
		"""
		self.polygon = p
		self.ceVerts = []
		self.eidx_list = []
		self.ceEdges = []
		self.seed_polygons = []
		self.index = p.index

		#add to static list
		CEPoly.AllCEPolygons.add( self )

		#create first ConnectEdgeVert and add to static list
		prev_vert = CEVert( self.verts[-1] )
		prev_vert.AddRootVert( prev_vert )
		CEPoly.ALLCEVerts.add( prev_vert )

		#iterate through all verts of polygon and create ConnectEdge elems
		vcount = len( self.verts )
		for i in range( vcount ):
			#the nth edge of poly has the same starting vert as the nth vert in said poly
			v1 = self.verts[i]
			v2 = self.verts[(i+1)%vcount]
			e = rmlib.rmEdgeSet.from_endpoints( v1, v2 )

			#create new ConnectEdgeVerts if they dont already exist in static list.
			cev1 = None
			cev2 = None
			for cev in CEPoly.ALLCEVerts:
				if cev.index == v1.index:
					cev1 = cev
				elif cev.index == v2.index:
					cev2 = cev
				if cev1 is not None and cev2 is not None:
					break
			if cev1 is None:
				cev1 = CEVert( v1 )
				cev1.AddRootVert( cev1 )
				CEPoly.ALLCEVerts.add( cev1 )
			if cev2 is None:
				cev2 = CEVert( v2 )
				cev2.AddRootVert( cev2 )
				CEPoly.ALLCEVerts.add( cev2 )
			self.ceVerts.append( cev1 )
			prev_vert.AddRootVert( cev1 )
			prev_vert = cev1			

			#add idx of edge if selected to keep track of active edges on this poly
			if e.select:
				self.eidx_list.append( i )
				
			#create new ConnectEdgeEdges if they dont already exist in static list.
			ceeAlreadyExists = False
			for cee in CEPoly.AllCEEdges:
				if cee.index == e.index:
					self.ceEdges.append( cee )
					ceeAlreadyExists = True
					break
			if not ceeAlreadyExists:
				cee = CEEdge( e, cev1, cev2, e.select, self )
				self.ceEdges.append( cee )
				CEPoly.AllCEEdges.add( cee )

	@classmethod
	def AccumulateCEElem( cls, seed_poly, seed_edge=None ):
		"""
		Recursive function that builds CE data structure.
		"""

		#ensure we only visit seed_poly once
		if seed_poly.tag:
			return
		seed_poly.tag = True

		#create ConnectEdgePolygon
		cep = cls( seed_poly )

		#build list of ceEdges where the first edge is the seed_edge.
		#If seed_edge arg is None, then settle for first active edge encountered.
		ceEdges = cep.ceEdges
		prev_active_edge_idx = 0
		if seed_edge is None:
			#if seed_edge is None, it means that this is the start of a AccumulateCEElem recusion.
			for i, cee in enumerate( ceEdges ):
				if cee.select:
					cee.edge.tag = True #avoids tricky bug where start of recursion is dependant on prev edge whose swich value is the default (and not dictated by topo).
					prev_active_edge_idx = i
					break
			if len( cep.eidx_list ) == 1:
				#if there's only one active edge on this poly, just kickoff a recursive call and return early.
				#there's nothing we more need from this poly.
				cee.edge.tag = True
				for p in cee.edge.link_faces:
					if p.tag:
						continue
					cls.AccumulateCEElem( p, cee )
					return
		else:
			for i, cee in enumerate( ceEdges ):
				if cee.index == seed_edge.index:
					prev_active_edge_idx = i
					break			
		prev_active_edge = ceEdges[prev_active_edge_idx]

		#get current active edge and sort ceEdges to start with that edge
		cur_active_edge_idx = 0
		for i in range( prev_active_edge_idx, len( ceEdges ) ):
			idx = ( i + i ) % len( ceEdges )
			if ceEdges[idx].select:
				cur_active_edge_idx = idx
				break
		ceEdges = ceEdges[cur_active_edge_idx:] + ceEdges[:cur_active_edge_idx]
		
		#iterate through active edges in poly and dispatch recursive calls
		for i in range( len( ceEdges ) ):
			cee = ceEdges[i]

			if cee.edge.tag:
				if cee.edge.select:
					prev_active_edge = cee
				continue
			cee.edge.tag = True

			if cee.edge.select:
				#manage slice_switch
				if cee.source_poly == prev_active_edge.source_poly:
					cee.slide_switch = not prev_active_edge.slide_switch
				else:
					cee.slide_switch = prev_active_edge.slide_switch
				prev_active_edge = cee
				
				for p in cee.edge.link_faces:
					if p.tag:
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


	def TransferLayerData( self, verts, new_poly ):
		"""
		Sets the uv corrd of a vert on a poly. This is done by interpolating
		between the endpoints of the edge on which the subvert resides.
		"""
		for i, vert in enumerate( verts ):
			start_vert, end_vert = vert.GetEndVerts( self.polygon )

			if vert.index != -1:
				#if vert is not subvert, then just copy existing loop uv coord
				for loop in self.loops:
					if loop.vert == vert.vert:
						break

				for subvert_loop in new_poly.loops:
					if subvert_loop.vert == vert.vert:
						break

				if CEPoly.BMesh.loops.layers.uv is not None:
					for uvlayer in CEPoly.BMesh.loops.layers.uv.values():
						subvert_loop[uvlayer].uv = loop[uvlayer].uv.copy()

				if CEPoly.BMesh.loops.layers.color is not None:
					for colorlayer in CEPoly.BMesh.loops.layers.color:
						subvert_loop[colorlayer] = loop[colorlayer]
						
			else:
				#if vert is a subvert, then coompute interpolated uvcoord				
				start_3d = start_vert.co
				end_3d = end_vert.co
				length_3d = ( end_3d - start_3d ).length
				weight = ( vert.co - start_3d ).length / length_3d

				loop = self.loops[-1]
				for end_loop in self.loops:
					if end_loop.vert == end_vert.vert:
						break
					loop = end_loop

				for subvert_loop in new_poly.loops:
					if subvert_loop.vert == vert.vert:
						break
					
				#asigne uv data
				if CEPoly.BMesh.loops.layers.uv is not None:
					#generate interpolated uv coord
					for uvlayer in CEPoly.BMesh.loops.layers.uv.values():
						start_uv = loop[uvlayer].uv
						end_uv = end_loop[uvlayer].uv
						vec_uv = end_uv - start_uv
						interp_uv = start_uv + ( vec_uv * weight )
						subvert_loop[uvlayer].uv = interp_uv

				#asigne color data
				if CEPoly.BMesh.loops.layers.color is not None:
					#generate interpolated color coord
					for colorlayer in CEPoly.BMesh.loops.layers.color:
						start_color = loop[colorlayer]
						end_color = end_loop[colorlayer]
						vec_color = end_color - start_color
						interp_color = start_color + ( vec_color * weight )
						subvert_loop[colorlayer] = interp_color
			
			#assign edge layer data
			if subvert_loop.edge.tag:
				continue

			#edge data processing
			next_vert = verts[ ( i + 1 ) % len( verts ) ]
			if next_vert.GetEndVerts( self.polygon )[1] == end_vert or end_vert == next_vert:
				#transfer crease weight
				if bpy.app.version < (4,0,0) and CEPoly.BMesh.edges.layers.crease is not None:
					for layer in CEPoly.BMesh.edges.layers.crease.values():
						subvert_loop.edge[layer] = loop.edge[layer]
						subvert_loop.edge.tag = True
				else:
					clyr = CEPoly.BMesh.edges.layers.float.get( 'crease_edge', None )
					if clyr is None:
						clyr = CEPoly.BMesh.edges.layers.float.get( 'crease_edge' )
					if clyr is not None:
						subvert_loop.edge[clyr] = loop.edge[clyr]
					subvert_loop.edge.tag = True

				#transfer sharp and seam
				subvert_loop.edge.smooth = loop.edge.smooth
				subvert_loop.edge.seam = loop.edge.seam
				subvert_loop.edge.tag = True
			


	def __createOuterPolygon( self, vlist ):
		"""
		Case for all faces that link the outermost subverts to the inactive edges.
		"""
		if len( set( vlist ) ) < 3:
			return None
					
		new_poly = CEPoly.BMesh.faces.new( [ v.vert for v in vlist ], self.polygon )
		self.TransferLayerData( vlist, new_poly )

	def __createInnerPolygons( self, ceedge1_idx, ceedge2_idx ):
		"""
		Case for all faces that connect subverts of one active edge to that of the next.
		"""
		vlist1 = self.ceEdges[ceedge1_idx].GetSubverts( self )[1:-1]
		vlist1 = vlist1[ int( CEPoly.level / 2 ): ][::-1]

		vlist2 = self.ceEdges[ceedge2_idx].GetSubverts( self )[1:-1]
		vlist2 = vlist2[ :int( CEPoly.level / 2 ) + int( CEPoly.level % 2 ) ]
	
		for i in range( 1, len( vlist1 ) ):
			quad = ( vlist1[i], vlist1[i-1], vlist2[i-1], vlist2[i] )
			new_poly = CEPoly.BMesh.faces.new( [ v.vert for v in quad ], self.polygon )			
			self.TransferLayerData( quad, new_poly )

	def __createCenterPolygon( self, vlist ):
		"""
		Case for when face at center of joint CEPoly.
		"""
		if len( vlist ) >= 3:
			new_poly = CEPoly.BMesh.faces.new( [ v.vert for v in vlist ], self.polygon )			
			self.TransferLayerData( vlist, new_poly )

	def __createCapPolygon( self ):
		"""
		Case for when exactly one active edge in CEPoly.
		"""
		
		vlist = rmlib.rmVertexSet()
		for i, e in enumerate( self.edges ):
			if i in self.eidx_list:
				subverts = self.ceEdges[i].GetSubverts( self )
				vlist += subverts[:-1]
			else:
				vlist.append( self.ceVerts[i] )

		new_poly = CEPoly.BMesh.faces.new( [ v.vert for v in vlist ], self.polygon )		
		self.TransferLayerData( vlist, new_poly )

	def ConnectEdges( self ):
		"""
		Use subverts to create the new topology for this face.
		"""

		if len( self.eidx_list ) == 1:
			return self.__createCapPolygon()

		#init previous_idx such that it is on an active edge
		vcount = len( self.verts )
		for previous_idx in range( vcount ):
			if previous_idx in self.eidx_list:          
				break
		current_idx = ( previous_idx + 1 ) % vcount

		centerPoly_verts = rmlib.rmVertexSet()
		outerPoly_verts = [ self.ceEdges[previous_idx].GetSubverts( self )[-2] ]
		for i in range( vcount ):
			active = current_idx in self.eidx_list
			subverts = self.ceEdges[current_idx].GetSubverts( self )			

			#handles outer polygons
			if active:
				self.__createOuterPolygon( outerPoly_verts + subverts[:2] )
				outerPoly_verts = [ subverts[-2] ]
			else:
				outerPoly_verts.append( subverts[0] )

			#handles inner polygons
			if active and CEPoly.level > 1:
				next_idx = ( current_idx + 1 ) % vcount		
				while( next_idx not in self.eidx_list ):
					next_idx = ( next_idx + 1 ) % vcount
				self.__createInnerPolygons( current_idx, next_idx )

			#handles center polygom
			if active:
				if CEPoly.level % 2 == 0:
					centerPoly_verts.append( subverts[ int( len( subverts ) / 2 ) - 1 ] )
				centerPoly_verts.append( subverts[ int( len( subverts ) / 2 ) ] )

			#increment
			current_idx = ( current_idx + 1 ) % vcount
			
		self.__createCenterPolygon( centerPoly_verts )


	@staticmethod
	def Cleanup():
		"""
		Delete old topology and clear tags.
		"""
		for cep in CEPoly.AllCEPolygons:
			CEPoly.BMesh.faces.remove( cep.polygon )
		for cee in CEPoly.AllCEEdges:
			if cee.active:
				CEPoly.BMesh.edges.remove( cee.edge )
		for e in CEPoly.BMesh.edges:
			e.tag = False
				
	@staticmethod
	def ClearStaticMembers():
		"""
		ClearStaticMembers
		"""
		CEPoly.AllCEPolygons.clear()
		CEPoly.AllCEEdges.clear()
		CEPoly.ALLCEVerts.clear()


class MESH_OT_connect_edge( bpy.types.Operator ):
	"""Creates new edges between adjacent pairs of selected edges."""
	bl_idname = 'mesh.rm_connectedge'
	bl_label = 'Connect Edges'
	bl_options = { 'REGISTER', 'UNDO' }
	
	level: bpy.props.IntProperty(
		name='Level',
		default=1,
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
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def LocalizeNewBMesh( self ):
		"""
		Copy the cached bmesh, and transfer all stale cached verts/edges/faces to use active ones of the 
		copy bmesh.
		"""
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
		for v in CEPoly.ALLCEVerts:
			v.vert = bm.verts[v.index]
		return bm

	def cancel( self, context ):
		"""
		Clear static members and free memory of cached bmesh
		"""
		CEPoly.ClearStaticMembers()
		if hasattr(self, "bmesh"):
			self.bmesh.free()
		
	def execute( self, context ):
		"""
		Actually modifies the geometry and connects edges using the cached data structure.
		Also manages undo bmesh process.

		Args:
			context (bpy.types.context): Blender context for operation
		"""

		if self.bmesh is None:
			return { 'CANCELLED' }

		#bmesh undo funcs only work in object mode
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )

		#update the cached data structure to use non-stale data
		bm = self.LocalizeNewBMesh()

		#add new verts
		for cee in CEPoly.AllCEEdges:
			cee.CreateSubverts( self.level, self.slide, self.pinch )

		#create new topology that adds edges between all new verts
		for cep in CEPoly.AllCEPolygons:
			cep.ConnectEdges()

		#delete old geo
		CEPoly.Cleanup()

		#merge cached bmesh into scene mesh
		targetMesh = context.active_object.data
		bm.to_mesh( targetMesh )
		bm.calc_loop_triangles()
		targetMesh.update()
		bm.free()
		
		#switch back to edit mode
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )

		return { 'FINISHED' }

	def modal( self, context, event ):
		"""
		Called every time Blender recieves an input from user. This function increments tool attributes like level,
		slide, and pinch. It also handles applying and cancelling the tool.

		Args:
			context (bpy.types.context): Blender context for operation
			event (bpy.types.event): Event input for operation
		"""

		if event.type == 'LEFTMOUSE':
			return { 'FINISHED' }

		elif event.type == 'MOUSEMOVE':
			delta_x = float( event.mouse_x - event.mouse_prev_press_x ) / context.region.width
			delta_y = float( event.mouse_y - event.mouse_prev_press_y ) / context.region.height
			if event.ctrl and event.shift:
				self.pinch = 1.0 + ( delta_x * 2.0 )
				self.slide = delta_y * 2.0
			elif event.ctrl:
				self.pinch = 1.0 + ( delta_x * 2.0 )
			elif event.shift:
				self.slide = delta_x * 2.0
			else:
				return { 'RUNNING_MODAL' }
			self.execute( context )

		elif event.type == 'WHEELUPMOUSE':
			self.level = min( self.level + 1, 64 )
			self.execute( context )

		elif event.type == 'WHEELDOWNMOUSE':
			self.level = max( self.level - 1, 1 )
			self.execute( context )

		elif event.type == 'ESC':
			return { 'CANCELLED' }

		return { 'RUNNING_MODAL' }

	def invoke( self, context, event ):
		"""
		First function called when op is run. It ensures blender is in correct state and clears data from preveious
		op evaluation. Then it builds the CE data structure, and caches the bmesh for the execute function.

		Args:
			context (bpy.types.context): Blender context for operation
			event (bpy.types.event): Event input for operation
		"""

		self.bmesh = None

		#ensure correct state
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[1]:
			return { 'CANCELLED' }
		
		#clear members from previous time op was run
		CEPoly.ClearStaticMembers()
		if self.bmesh is not None:
			self.bmesh.free()

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			#localize a readonly bmesh
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

				#build list of active polygons. These are polys that neighbor selected edges. A poly with more than
				#two selected edges is considered a joint polygons. These need to be operated on first to allow for
				#slide feature.
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
					else:
						active_polygons.append( p )
					
				#build the CE data structure.
				for p in active_polygons:
					CEPoly.AccumulateCEElem( p )
				if len( CEPoly.AllCEPolygons ) < 1:
					return { 'CANCELLED' }

				#cache a copy of the current bmesh
				self.bmesh = rmmesh.bmesh.copy()
				
		context.window_manager.modal_handler_add( self ) #required for modal to run
		self.execute( context )
		return { 'RUNNING_MODAL' }

def register():
	bpy.utils.register_class( MESH_OT_connect_edge )
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_connect_edge )