import rmKit.rmlib as rmlib
import bpy, bmesh, mathutils
import os, random, math
from bpy_extras import view3d_utils

MAX_SHORT = 32768.0


def clear_tags( rmmesh ):
	for v in rmmesh.bmesh.verts:
		v.tag = False
	for e in rmmesh.bmesh.edges:
		e.tag = False
	for f in rmmesh.bmesh.faces:
		f.tag = False
		for l in f.loops:
			l.tag = False


def GetFaceSelection( context, rmmesh ):
	uvlayer = rmmesh.active_uv
	clear_tags( rmmesh )

	faces = rmlib.rmPolygonSet()
	sel_sync = context.tool_settings.use_uv_select_sync
	if sel_sync or context.area.type == 'VIEW_3D':
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if sel_mode[2]:
			faces = rmlib.rmPolygonSet.from_selection( rmmesh )
		else:
			return faces
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
			return faces

	clear_tags( rmmesh )

	return faces


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
				self.__min[i] = min( p[i], self.__min[i] )
				self.__max[i] = max( p[i], self.__max[i] )

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
		uvlist = [ l[uvlayer].uv.copy() for l in loops ]
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
		return self.__max[1] - self.__min[1]

	@property
	def aspect( self ):
		return self.width / self.height
	
	@property
	def area( self ):
		return self.width * self.height

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
	
	def overlapping_area( self, bounds ):
		#does not test if bounds actually overlapp
		min_x = max( self.__min[0], bounds.min[0] )
		min_y = max( self.__min[1], bounds.min[1] )
		max_x = min( self.__max[0], bounds.max[0] )
		max_y = min( self.__max[1], bounds.max[1] )
		return ( max_x - min_x ) * ( max_y - min_y )

	def transform( self, other ):
		#compute the 3x3 matrix that transforms bound 'other' to self
		trans_mat = mathutils.Matrix.Identity( 3 )
		trans_mat[0][2] = self.center[0] * -1.0
		trans_mat[1][2] = self.center[1] * -1.0
		
		trans_mat_inverse = mathutils.Matrix.Identity( 3 )
		trans_mat_inverse[0][2] = other.center[0]
		trans_mat_inverse[1][2] = other.center[1]

		rot_mat = mathutils.Matrix.Identity( 3 )
		scl_mat = mathutils.Matrix.Identity( 3 )
		if self.horizontal != other.horizontal:
			rot_mat[0][0] = math.cos( math.pi  / 2.0 )
			rot_mat[1][0] = math.sin( math.pi  / 2.0 ) * -1.0
			rot_mat[0][1] = math.sin( math.pi  / 2.0 )
			rot_mat[1][1] = math.cos( math.pi  / 2.0 )	
			scl_mat[0][0] = other.width / self.height
			scl_mat[1][1] = other.height / self.width
		else:
			scl_mat[0][0] = other.width / self.width
			scl_mat[1][1] = other.height / self.height

		return trans_mat_inverse @ scl_mat @ rot_mat @ trans_mat


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
		self.__data = []
		for b in bounds2d_list:
			if b.area > 0.0:
				self.__data.append( b )
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
			for f in rmmesh.bmesh.faces:
				boundslist.append( Bounds2d.from_loops( f.loops, uv_layer ) )
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

	def match( self, source_bounds, tollerance=0.01, random_orient=True ):
		#find the bound in this hotspot that best matches source
		sb_aspect = min( source_bounds.aspect, 1.0 / source_bounds.aspect )
		source_coord = mathutils.Vector( ( math.sqrt( source_bounds.area ), sb_aspect ) )

		min_dist = 9999999.9
		best_bounds = self.__data[0]
		for tb in self.__data:
			aspect = min( tb.aspect, 1.0 / tb.aspect )
			target_coord = mathutils.Vector( ( math.sqrt( tb.area ), aspect ) )
			dist = ( target_coord - source_coord ).length
			if dist < min_dist:
				min_dist = dist
				best_bounds = tb
		best_aspect = min( best_bounds.aspect, 1.0 / best_bounds.aspect )
		best_coord = mathutils.Vector( ( math.sqrt( best_bounds.area ), best_aspect ) )

		target_list = []
		for tb in self.__data:
			aspect = min( tb.aspect, 1.0 / tb.aspect )
			target_coord = mathutils.Vector( ( math.sqrt( tb.area ), aspect ) )
			dist = ( target_coord - best_coord ).length
			if abs( dist - min_dist ) <= tollerance:
				if not random_orient and tb.horizontal == best_bounds.hotizontal:
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
				overlap_area = b.overlapping_area( bounds2d )
				if overlap_area > max_overlap_area:
					max_overlap_area = overlap_area
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


class MESH_OT_grabapplyuvbounds( bpy.types.Operator ):
	bl_idname = 'mesh.grabapplyuvbounds'
	bl_label = 'GrabApply UVBounds MOS'
	bl_options = { 'UNDO' }

	def __init__( self ):
		self.mos = ( 0.0, 0.0 )

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' )

	def execute( self, context ):
		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		#get target_bounds from MOS
		mouse_pos = mathutils.Vector( ( float( self.mos[0] ), float( self.mos[1] ) ) )
		mos_rmmesh = rmlib.rmMesh.from_mos( context, mouse_pos )
		if mos_rmmesh is None:
			return { 'CANCELLED' }
		with mos_rmmesh as rmmesh:
			rmmesh.readonly = True
			if len( rmmesh.bmesh.loops.layers.uv ) < 1:
				return { 'CANCELLED' }
			uvlayer = rmmesh.active_uv
		
			faces = rmlib.rmPolygonSet.from_mos( rmmesh, context, mouse_pos )
			if len( faces ) < 1:
				return { 'CANCELLED' }
			
			target_faces = faces.island( uvlayer, element=True )[0]
			target_loops = set()
			for f in target_faces:
				for l in f.loops:
					target_loops.add( l )
			target_bounds = Bounds2d.from_loops( target_loops, uvlayer )

		#move selection to target_bounds
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			source_faces = rmlib.rmPolygonSet.from_selection( rmmesh )
			for source_island in source_faces.island( uvlayer ):
				loops = set()
				for f in source_island:
					for l in f.loops:
						loops.add( l )
				source_bounds = Bounds2d.from_loops( loops, uvlayer )

				mat = source_bounds.transform( target_bounds )		
				for l in loops:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()

		return { 'FINISHED' }

	def invoke( self, context, event ):
		self.mos = ( event.mouse_region_x, event.mouse_region_y )
		return self.execute( context )



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
				context.object.data.is_editmode )

	def execute( self, context ):
		if context.scene.subrect_atlas is None:
			self.report( { 'WARNING' }, 'No valid atlas selected!' )
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		hotspot = Hotspot.from_bmesh( rmlib.rmMesh( context.scene.subrect_atlas ) )
		target_bounds = hotspot.nearest( self.mos_uv[0], self.mos_uv[1] )

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			
			faces = GetFaceSelection( context, rmmesh )
			if len( faces ) < 1:
				return { 'CANCELLED' }

			for island in faces.island( uvlayer ):
				loops = set()
				for f in island:
					for l in f.loops:
						loops.add( l )
				source_bounds = Bounds2d.from_loops( loops, uvlayer )

				mat = source_bounds.transform( target_bounds )		
				for l in loops:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()

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
				context.object.data.is_editmode )

	def execute( self, context ):
		if context.scene.subrect_atlas is None:
			self.report( { 'WARNING' }, 'No valid atlas selected!' )
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		hotspot = Hotspot.from_bmesh( rmlib.rmMesh( context.scene.subrect_atlas ) )

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			
			faces = GetFaceSelection( context, rmmesh )
			if len( faces ) < 1:
				return { 'CANCELLED' }

			for island in faces.island( uvlayer ):
				loops = set()
				for f in island:
					for l in f.loops:
						loops.add( l )
				source_bounds = Bounds2d.from_loops( loops, uvlayer )
				target_bounds = hotspot.overlapping( source_bounds )

				mat = source_bounds.transform( target_bounds )		
				for l in loops:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()

		return { 'FINISHED' }


class MESH_OT_matchhotspot( bpy.types.Operator ):
	bl_idname = 'mesh.matchhotspot'
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

		hotspot = Hotspot.from_bmesh( rmlib.rmMesh( context.scene.subrect_atlas ) )

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			faces = GetFaceSelection( context, rmmesh )
			if len( faces ) < 1:
				return { 'CANCELLED' }

			for island in faces.island( uvlayer ):
				loops = set()
				for f in island:
					for l in f.loops:
						loops.add( l )
				source_bounds = Bounds2d.from_loops( loops, uvlayer )
				target_bounds = hotspot.match( source_bounds, tollerance=self.tollerance )

				mat = source_bounds.transform( target_bounds )		
				for l in loops:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( OBJECT_OT_loadrect )
	bpy.utils.register_class( MESH_OT_matchhotspot )
	bpy.utils.register_class( MESH_OT_nrsthotspot )
	bpy.utils.register_class( MESH_OT_moshotspot )
	bpy.utils.register_class( MESH_OT_grabapplyuvbounds )
	bpy.types.Scene.subrect_atlas = bpy.props.PointerProperty( name='atlas',type=bpy.types.Object,description='atlas object' )
	

def unregister():
	bpy.utils.unregister_class( OBJECT_OT_loadrect )
	bpy.utils.unregister_class( MESH_OT_matchhotspot )
	bpy.utils.unregister_class( MESH_OT_nrsthotspot )
	bpy.utils.unregister_class( MESH_OT_moshotspot )
	bpy.utils.unregister_class( MESH_OT_grabapplyuvbounds )
	del bpy.types.Scene.subrect_atlas