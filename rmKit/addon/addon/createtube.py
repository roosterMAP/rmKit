from operator import inv
from re import T
import bpy
import bmesh
import rmKit.rmlib as rmlib
import mathutils
import math

class Tube():
	index = -1

	def __init__( self ):
		self.centers = []
		self.normals = []
		self.vec = mathutils.Vector( ( 0.0, 0.0, 1.0 ) )
		self.closed = False
		self.poly = None
		self.__length = -1.0

		self.idx = Tube.index
		Tube.index += 1

	@property
	def length( self ):
		if self.__length < 0.0:
			self.__length = 0.0
			for i in range( int( not self.closed ), len( self.centers ) ):
				self.__length += ( self.centers[i-1] - self.centers[i] ).length
				
		return self.__length


class MESH_OT_createtube( bpy.types.Operator ):
	"""Creates a generalized cylinder abound the edge selection. If a generalized cylinder is selected in polygon mode, then a new ones is recreated."""
	bl_idname = 'mesh.rm_createtube'
	bl_label = 'Create Tube'
	bl_options = { 'REGISTER', 'UNDO' }
	
	level: bpy.props.IntProperty(
		name='Level',
		default=8,
		min=3
	)
	radius: bpy.props.FloatProperty(
		name='Radius',
		default=0.1
	)

	degrees: bpy.props.FloatProperty(
		name='Angle',
		default=0.0,
		min=-180.0,
		max=180.0
	)

	def __init__( self ):
		self.bmesh = None
		self._tubes = []
		self.bbox_dist = 0.0

	def __del__( self ):
		if self.bmesh is not None:
			self.bmesh.free()
			self.bmesh = None
		self._tubes.clear()
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def LocalizeNewBMesh( self ):
		bm = self.bmesh.copy()
		bm.verts.ensure_lookup_table()
		bm.edges.ensure_lookup_table()
		bm.faces.ensure_lookup_table()
		for v in bm.verts:
			v.tag = False
		for p in bm.faces:
			p.tag = False
		return bm
		
	def execute( self, context ):
		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )

		#localize writable mesh
		bm = self.LocalizeNewBMesh()

		#get/create uv layer
		uv_layer = bm.loops.layers.uv.verify()

		#create tubes
		for tube in self._tubes:
			use_tube_normals = len( tube.normals ) == len( tube.centers )

			#create new vertices
			rings = []
			nml = tube.vec
			for i in range( len( tube.centers ) ):
				currPos = tube.centers[i]
				if tube.closed or ( i != 0 and i != len( tube.centers ) - 1 ):
					prevPos = tube.centers[i-1]
					try:
						nextPos = tube.centers[i+1]
					except IndexError:
						nextPos = tube.centers[0]
					A = ( currPos - prevPos ).normalized()
					B = ( nextPos - currPos ).normalized()
					tan = ( A + B ).normalized()
				else:
					if i == 0:
						nextPos = tube.centers[i+1]
						tan = ( nextPos - currPos ).normalized()
					else:
						prevPos = tube.centers[i-1]
						tan = ( currPos - prevPos ).normalized()
				if use_tube_normals:
					bitan = tan.cross( tube.normals[i] ).normalized()
				else:
					bitan = tan.cross( nml ).normalized()
					nml = bitan.cross( tan ).normalized()

				verts = []
				offset_quat = mathutils.Quaternion( tan, math.radians( self.degrees ) )
				rot_quat = mathutils.Quaternion( tan, math.pi * 2.0 / self.level )
				bitan.rotate( offset_quat )
				for j in range( self.level ):
					new_vert = bm.verts.new( currPos + ( bitan * self.radius ) )
					verts.append( new_vert )
					bitan.rotate( rot_quat )
				rings.append( verts )
				
			#create faces and set uv data
			current_length = 0.0
			u_step = 1.0 / float( self.level )
			for i in range( int( not tube.closed ), len( rings ) ):
				next_length = current_length + ( tube.centers[i] - tube.centers[i-1] ).length
				for j in range( self.level ):
					verts = ( rings[i-1][j-1], rings[i-1][j], rings[i][j], rings[i][j-1] )
					face = bm.faces.new( verts )
					face.loops[0][uv_layer].uv = ( u_step * j, current_length / tube.length )
					face.loops[1][uv_layer].uv = ( u_step * ( j + 1 ), current_length / tube.length )
					face.loops[2][uv_layer].uv = ( u_step * ( j + 1 ), next_length / tube.length )
					face.loops[3][uv_layer].uv = ( u_step * j, next_length / tube.length )
				current_length = next_length
				
		targetMesh = context.active_object.data
		bm.to_mesh( targetMesh )
		bm.calc_loop_triangles()
		targetMesh.update()
		bm.free()
		
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )
		
		return { 'FINISHED' }

	def modal( self, context, event ):
		if event.type == 'LEFTMOUSE':
			return { 'FINISHED' }
		elif event.type == 'MOUSEMOVE':
			delta_x = float( event.mouse_prev_press_x - event.mouse_x ) / context.region.width
			self.radius = 0.1 + ( delta_x * self.bbox_dist * 10.0 )
			self.execute( context )
		elif event.type == 'WHEELUPMOUSE':
			self.level = min( self.level + 1, 128 )
		elif event.type == 'WHEELDOWNMOUSE':
			self.level = max( self.level - 1, 3 )	
		elif event.type == 'ESC':
			return { 'CANCELLED' }

		return { 'RUNNING_MODAL' }
	
	def invoke( self, context, event ):
		#ensure a mesh is selected and in edit mode
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		#ensure user is in edge or face mode
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not ( sel_mode[1] or sel_mode[2] ):
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is not None:
			with rmmesh as rmmesh:
				rmmesh.readme = True

				for v in rmmesh.bmesh.verts:
					v.tag = False
				for p in rmmesh.bmesh.faces:
					p.tag = False

				self.bmesh = rmmesh.bmesh.copy()

				#cache Tube objects for edge selection
				if sel_mode[1]:
					edges = rmlib.rmEdgeSet.from_selection( rmmesh )
					
					#init bbox_dist for haul sensitivity
					verts = edges.vertices
					min = verts[0].co.copy()
					max = verts[0].co.copy()
					for v in verts:
						for i in range( 3 ):
							if v.co[i] < min[i]:
								min[i] = v.co[i]
							if v.co[i] > max[i]:
								max[i] = v.co[i]
					self.bbox_dist = ( max - min ).length
					
					chains = edges.chain()
					for i, chain in enumerate( chains ):
						tube = Tube()

						tube.closed = chain[0][0] == chain[-1][-1]
						
						for pair in chain:
							tube.centers.append( pair[0].co.copy() )
							tube.normals.append( pair[0].normal.copy() )
						if not tube.closed:
							tube.centers.append( chain[-1][-1].co.copy() )
							tube.normals.append( chain[-1][-1].normal.copy() )
							
						first_edge = rmlib.rmEdgeSet.from_endpoints( chain[0][0], chain[0][1] )
						try:
							tube.poly = first_edge.link_faces[0].index
						except IndexError:
							pass
							
						self._tubes.append( tube )

				#cache Tube objs from face selection
				elif sel_mode[2]:
					faces = rmlib.rmPolygonSet.from_selection( rmmesh )

					#init bbox_dist for haul sensitivity
					verts = faces.vertices
					min = verts[0].co.copy()
					max = verts[0].co.copy()
					for v in verts:
						for i in range( 3 ):
							if v.co[i] < min[i]:
								min[i] = v.co[i]
							if v.co[i] > max[i]:
								max[i] = v.co[i]
					self.bbox_dist = ( max - min ).length

					groups = faces.group()
					for group in groups:
						#ensure group is all quads
						allQuads = True
						for p in group:
							if len( p.verts ) != 4:
								allQuads = False
								break
						if not allQuads:
							continue

						#ensure exactly two continuous closed loops of open edges (no caps)
						chains = rmlib.rmEdgeSet( [ e for e in group.edges if e.is_boundary ] ).chain()
						if len( chains ) != 2:
							continue
						if len( chains[0] ) < 3:
							continue
						if chains[0][0][0] != chains[0][-1][-1] or chains[1][0][0] != chains[1][-1][-1]:
							continue

						#ensure each vert either boardered 4 manifold edges or 1 manifold and 2 boundary edges
						invalidTopo = False
						for v in group.vertices:
							boundary_count = 0
							contiguous_count = 0
							for e in v.link_edges:
								if e.is_boundary:
									boundary_count += 1
								if e.is_contiguous:
									contiguous_count += 1
							if not ( boundary_count == 2 and contiguous_count == 1 ):
								invalidTopo = True
								break
							if not ( boundary_count == 4 and contiguous_count == 0 ):
								invalidTopo = True
								break
						if not invalidTopo:
							continue

						#break up group into list of verts each of same size (rings of tube)
						rings = [ rmlib.rmVertexSet( [ pair[0] for pair in chains[0] ] ) ]
						for v in rings[-1]:
							v.tag = True
						while( True ):
							new_ring = set()
							for p in rings[-1].polygons:
								if p.tag:
									continue
								p.tag = True
								for v in p.verts:
									if v.tag:
										continue
									v.tag = True
									new_ring.add( v )
							if len( new_ring ) < 3:
								break
							rings.append( rmlib.rmVertexSet( new_ring ) )
						if len( rings ) < 2:
							continue

						#cache Tube obj
						tube = Tube()
						for ring in rings:
							avg = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
							for v in ring:
								avg += v.co
							avg *= 1.0 / len( ring )
							tube.centers.append( avg )
						
						tube.vec = groups[0][0].normal.copy()
						tube.poly = groups[0][0].index

						self._tubes.append( tube )

		if len( self._tubes ) < 1:
			return { 'CANCELLED' }
			
		context.window_manager.modal_handler_add( self )
		return { 'RUNNING_MODAL' }


def register():
	bpy.utils.register_class( MESH_OT_createtube )
	
def unregister():
	bpy.utils.unregister_class( MESH_OT_createtube )