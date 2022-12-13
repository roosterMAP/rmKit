import rmKit.rmlib as rmlib
import bpy, bmesh, mathutils
import os, random, math

MAX_SHORT = 32768.0


class Bounds2d():
	def __init__( self, points, **kwargs ):
		self.__min = mathutils.Vector( ( 0.0, 0.0 ) )
		self.__max = mathutils.Vector( ( 1.0, 1.0 ) )
		if len( points ) > 0:
			self.__min = points[0].copy()
			self.__max = points[0].copy()
		self.__inset = mathutils.Vector( ( 0.0, 0.0 ) )
		self.__properties = {}
		for p in points:
			for i in range( 2 ):
				if p[i] <= self.__min[i]:
					self.__min[i] = p[i]
				if p[i] >= self.__max[i]:
					self.__max[i] = p[i]

		for key, value in kwargs.items():
			if key == 'inset':
				self.__inset = value
			elif key == 'properties':
				self.__properties = value

	def __repr__( self ):
		return 'min:{}  max:{}'.format( self.__min, self.__max )

	@classmethod
	def from_verts( cls, verts ):
		#build bounds from list of BMVerts
		poslist = [ v.co.to_2d() for v in verts ]
		return cls( poslist )

	@classmethod
	def from_loops( cls, loops, uvlayer ):
		#build bounds from list of BMVerts
		uvlist = [ l[uvlayer].uv for l in loops ]
		return cls( uvlist )

	@property
	def min( self ):
		return self.__min

	@property
	def max( self ):
		return self.__max

	@property
	def width( self ):
		return self.__max[0] - self.__min[0]

	@property
	def height( self ):
		return self.__max[1] - self.__min[0]

	@property
	def aspect( self ):
		return self.width / self.height

	@property
	def center( self ):
		return ( self.__min + self.__max ) * 0.5

	@property
	def horizontal( self ):
		#returns true if self is wider than it is tall
		return self.width > self.height

	@property
	def corners( self ):
		#return corner coords of self in (u,v) domain
		return [ self.__min, mathutils.Vector( ( self.__max[0], self.__min[1] ) ), self.__max, mathutils.Vector( ( self.__min[0], self.__max[1] ) ) ]

	def normalize( self ):
		#ensure bounds overlapps the 0-1 region
		center = self.center
		offset_u = center[0] - float( floor( center[0] ) )
		offset_v = center[1] - float( floor( center[1] ) )
		self.__min[0] -= offset_u
		self.__min[1] -= offset_v
		self.__max[0] -= offset_u
		self.__max[1] -= offset_v

	def inside( self, point ):
		#test if point is inside self
		return ( point[0] > self.min[0] and point[1] > self.min[1] and point[0] < self.max[0] and point[1] < self.max[1] )

	def overlapping( self, bounds ):
		#test if bounds overlapps self
		return not ( self.__max[0] < bounds.__min[0] or self.__min[0] > bounds.max[0] or self.__max[1] < bounds.__min[1] or self.__min[1] > bounds.max[1] )

	def transform( self, other ):
		#compute the 3x3 matrix that transforms bound 'other' to self
		trans_mat = mathutils.Matrix.Identity( 3 )
		trans_mat[2] = self.center - other.center
		
		trans_mat_inverse = mathutils.Matrix.Identity( 3 )
		trans_mat_inverse[2] = other.center - self.center

		rot_mat = mathutils.Matrix.Identity( 3 )
		if self.horizontal != other.horizontal:
			rot_mat[0][0] = math.cos( math.pi  / 2.0 )
			rot_mat[1][0] = math.sin( math.pi  / 2.0 ) * -1.0
			rot_mat[0][1] = math.cos( math.pi  / 2.0 )
			rot_mat[1][1] = math.sin( math.pi  / 2.0 )

		return trans_mat_inverse @ rot_mat @ trans_mat


def add_to_chunk( chunk, key, value ):
	if isinstance( chunk, dict ):
		chunk[key] = value
	elif isinstance( chunk, list ):
		chunk.append( { key : value } )


def load_rect_chunk( current_idx, lines, chunk=None, prev_key=None ):
	active_key = prev_key
	while current_idx < len( lines ):
		line = lines[current_idx].strip()
		if len( line ) == 0 or line.startswith( '<!--' ):
			current_idx += 1
			continue

		if line == '[' or line == '{':			
			if line == '[':
				current_idx, subchunk = load_rect_chunk( current_idx+1, lines, list() )
			elif line == '{':
				current_idx, subchunk = load_rect_chunk( current_idx+1, lines, dict() )				
			if isinstance( chunk, dict ):
				chunk[active_key] = subchunk
			elif isinstance( chunk, list ):
				chunk.append( subchunk )
			else:
				chunk = subchunk
			current_idx += 1
			continue

		if line == ']' or line == '],':
			return ( current_idx, chunk )
		elif line == '}' or line == '},':
			return ( current_idx, chunk )

		slist = line.split( '=' )
		key = slist[0].strip()
		value = slist[1].strip()
		if len( value ) == 0:
			if isinstance( chunk, dict ):
				active_key = key

		elif '\"' in value:
			add_to_chunk( chunk, key, value[1:-1] )

		elif value == 'null':
			add_to_chunk( chunk, key, None )

		elif value == 'false':
			add_to_chunk( chunk, key, False )

		elif value == 'true':
			add_to_chunk( chunk, key, True )

		elif '[' in value and ']' in value:
			flist = value[1:-1].split( ',' )
			uv = mathutils.Vector( ( float( flist[0] ) / MAX_SHORT, float( flist[1] ) / MAX_SHORT ) )
			add_to_chunk( chunk, key, uv )

		current_idx += 1

	return ( current_idx, chunk )



class Hotspot():
	def __init__( self, bounds2d_list, **kwargs ):
		self.__name = ''
		self.__properties = None
		self.__td = 512.0 #texels per meter
		self.__data = [ bounds for bounds in bounds2d_list ]
		for key, value in kwargs.items():
			if key == 'name':
				self.__name = value
			elif key == 'properties':
				self.__properties = None
			elif key == 'texel_density':
				self.__td = value

	def __repr__( self ):
		s = 'HOTSPOT {}\n'.format( self.__name )
		s += 'properties :: {}\n'.format( self.__properties )
		s += 'texel density :: {}\n'.format( self.__td )
		for i, r in enumerate( self.__data ):
			s += '\t{} :: {}\n'.format( i, r )
		return s

	@classmethod
	def from_bmesh( cls, rmmesh ):
		#load hotspot from subrect_atlas		
		boundslist = []
		with rmmesh as rmmesh:
			rmmesh.readonly = True
			uv_layer = rmmesh.bmesh.loops.layers.uv.verify()
			for f in rmmesh.bnmesh.faces:
				uvs = [ mathutils.Vector( l[uv_layer].uv ) for l in f.loops ]
				boundslist.append( Bounds2d( uvs ) )
		return cls( boundslist )

	@classmethod
	def from_file( cls, file ):
		#load hotspot from .rect file
		with open( file, 'r' ) as f:
			lines = f.readlines()
			current_idx = 0
			while current_idx < len( lines ) and not lines[current_idx].strip().startswith( '{' ):
				current_idx += 1
			current_idx, data = load_rect_chunk( current_idx, lines, None )
			
			rect_name = data['RectangleSets'][0]['name']
			rect_properties = data['RectangleSets'][0]['properties']
			hotspot = cls( [], name=rect_name, properties=rect_properties )
			for rectangle in data['RectangleSets'][0]['rectangles']:
				bbox = Bounds2d( [ rectangle['min'], rectangle['max'] ], inset=rectangle['inset'], properties=rectangle['properties'] )
				hotspot.__data.append( bbox )

			return hotspot

	def save_bmesh( self, rmmesh ):
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			del_faces = list( rmmesh.bmesh.faces )
			
			for bounds in self.__data:
				verts = []
				corners = bounds.corners
				for c in corners:
					verts.append( rmmesh.bmesh.verts.new( c.to_3d() ) )
				f = rmmesh.bmesh.faces.new( verts )
				for i, l in enumerate( f.loops ):
					l[uvlayer].uv = corners[i]

			bmesh.ops.delete( rmmesh.bmesh, geom=del_faces, context='FACES' )			
			
	def save_file( self, file ):
		#save hotspot to new .rect file
		pass

	def match( self, source, tollerance=0.01, random_orient=True ):
		#find the bound in this hotspot that best matches source
		source_bounds = Bounds2d.from_verts( source.vertices )
		surface_area = 0.0
		for p in source:
			surface_area += p.calc_area()
		source_coord = mathutils.Vector( ( surface_area / self.__td, source_bounds.aspect ) )

		min_dist = 9999999.9
		target_bounds = None
		for tb in self.__data:
			aspect = min( tb.aspect, 1.0 / tb.aspect )
			target_coord = mathutils.Vector( ( tb.width * tb.height, aspect ) )
			dist = ( target_coord - source_coord )
			if dist < min_dist:
				min_dist = dist
				target_bounds = tb

		target_list = []
		for tb in self.__data:
			aspect = min( tb.aspect, 1.0 / tb.aspect )
			target_coord = mathutils.Vector( ( tb.width * tb.height, aspect ) )
			dist = ( target_coord - source_coord )
			if abs( dist - min_dist ) <= tollerance:
				if not random_orient:
					if tb.horizontal == source.hotizontal:
						target_list.append( tb )
				else:
					target_list.append( tb )

		return random.choice( target_list )

	def nearest( self, u, v ):
		#find the bounds nearest to (u,v) coord
		point = mathutils.Vector( ( u, v ) )
		nearest_rect = self.__data[0]
		nearest_rect_dist = 999999999.9
		for b in self.__data:
			if b.inside( point ):
				return b
			min_dist = 999999999.9
			for c in b.corners:
				dist = ( c - point ).length
				if dist < min_dist:
					min_dist = dist
			if min_dist < nearest_rect_dist:
				nearest_rect_dist = min_dist
				nearest_rect = b
		return nearest_rect

	def overlapping( self, bounds2d ):
		#find the bounds that most overlapps bounds2d
		max_overlap_area = -1.0
		overlap_bounds = self.__data[0]
		for b in self.__data:
			if b.overlapping( bounds2d ):
				#compute overlapping area between two bounds
				overlap = 0.0
				if overlap > max_overlap_area:
					max_overlap_area = overlap
					overlap_bounds = b
		return overlap_bounds


class OBJECT_OT_loadrect( bpy.types.Operator ):
	bl_idname = 'object.load_rect'
	bl_label = 'Load .rect'
	bl_options = { 'UNDO' }
	
	filter_glob: bpy.props.StringProperty( default='*.rect', options={ 'HIDDEN' } )
	filepath: bpy.props.StringProperty( name="File Path", description="Filepath used for importing txt files", maxlen= 1024, default= "" )
	files: bpy.props.CollectionProperty( name = 'File Path', type = bpy.types.OperatorFileListElement )

	def execute( self, context ):
		hotspot = Hotspot.from_file( file=self.filepath )
		
		mesh = bpy.data.meshes.new( 'mesh' )
		obj = bpy.data.objects.new( 'atlas', mesh )			
		hotspot.save_bmesh( rmlib.rmMesh( obj ) )

		context.scene.subrect_atlas = obj
		context.view_layer.active_layer_collection.collection.objects.link( obj )
		context.view_layer.objects.active = obj
		obj.select_set( True )

		return  {'FINISHED' }

	def draw( self, context ):
		self.layout.operator( 'file.select_all_toggle' )

	def invoke( self, context, event ):
		wm = context.window_manager
		wm.fileselect_add( self )
		return { 'RUNNING_MODAL' }


class MESH_OT_moshotspot( bpy.types.Operator ):
	bl_idname = 'mesh.moshotspot'
	bl_label = 'Hotspot MOS'
	bl_options = { 'UNDO' }

	def __init__( self ):
		self.mos_uv = ( 0.0, 0.0 )

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode and
				not context.tool_settings.use_uv_select_sync )

	def execute( self, context ):
		if context.scene.subrect_atlas is None:
			self.report( { 'WARNING' }, 'No valid atlas selected!' )
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		hotspot = Hotspot.from_bmesh( rmmlib.rmMesh( context.scene.subrect_atlas ) )
		target_bounds = hotspot.nearest( self.mos_uv[0], self.mos_uv[1] )

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			loops = set()
			for f in rmlib.rmPolygonSet.from_selection( rmmesh ):
				for l in f.loops:
					loops.add( l )
			source_bounds = Bounds2d.from_loops( loops, uvlayer )

			mat = source_bounds.transform( target_bounds )
			for l in loops:
				uv = mathutils.Vector( l[uvlayer].uv.copy() )
				l[uvlayer].uv = mat @ uv

		return { 'FINISHED' }

	def invoke( self, context, event ):
		self.mos_uv = context.region.view2d.region_to_view( event.mouse_region_x, event.mouse_region_y )
		return self.execute( context )


class MESH_OT_nrsthotspot( bpy.types.Operator ):
	bl_idname = 'mesh.nrsthotspot'
	bl_label = 'Hotspot Nrst'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode and
				not context.tool_settings.use_uv_select_sync )

	def execute( self, context ):
		if context.scene.subrect_atlas is None:
			self.report( { 'WARNING' }, 'No valid atlas selected!' )
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		hotspot = Hotspot.from_bmesh( rmmlib.rmMesh( context.scene.subrect_atlas ) )

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			loops = set()
			for f in rmlib.rmPolygonSet.from_selection( rmmesh ):
				for l in f.loops:
					loops.add( l )
			source_bounds = Bounds2d.from_loops( loops, uvlayer )
			source_bounds.normalize()

			target_bounds = hotspot.overlapping( source_bounds )

			mat = source_bounds.transform( target_bounds )
			for l in loops:
				uv = mathutils.Vector( l[uvlayer].uv.copy() )
				l[uvlayer].uv = mat @ uv

		return { 'FINISHED' }


class MESH_OT_matchhotspot( bpy.types.Operator ):
	bl_idname = 'mesh.mathhotspot'
	bl_label = 'Hotspot Match'
	bl_options = { 'UNDO' }

	tollerance: bpy.props.FloatProperty(
		name='Tollerance',
		default=0.01
	)

	@classmethod
	def poll( cls, context ):
		return ( ( context.area.type == 'VIEW_3D' or context.area.type == 'IMAGE_EDITOR' ) and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		if context.scene.subrect_atlas is None:
			self.report( { 'WARNING' }, 'No valid atlas selected!' )
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		hotspot = Hotspot.from_bmesh( rmmlib.rmMesh( context.scene.subrect_atlas ) )

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			loops = set()
			for f in rmlib.rmPolygonSet.from_selection( rmmesh ):
				for l in f.loops:
					loops.add( l )
			source_bounds = Bounds2d.from_loops( loops, uvlayer )

			target_bounds = hotspot.match( source_bounds, tollerance=self.tollerance )

			mat = source_bounds.transform( target_bounds )
			for l in loops:
				uv = mathutils.Vector( l[uvlayer].uv.copy() )
				l[uvlayer].uv = mat @ uv

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( OBJECT_OT_loadrect )
	bpy.utils.register_class( MESH_OT_matchhotspot )
	bpy.utils.register_class( MESH_OT_nrsthotspot )
	bpy.utils.register_class( MESH_OT_moshotspot )
	bpy.types.Scene.subrect_atlas = bpy.props.PointerProperty( name='atlas',type=bpy.types.Object,description='atlas object' )
	

def unregister():
	bpy.utils.unregister_class( OBJECT_OT_loadrect )
	bpy.utils.uregister_class( MESH_OT_matchhotspot )
	bpy.utils.uregister_class( MESH_OT_nrsthotspot )
	bpy.utils.uregister_class( MESH_OT_moshotspot )
	del bpy.types.Scene.subrect_atlas
	
register()