import bpy, mathutils
from bpy.app.handlers import persistent
from .. import rmlib
import math, os, random

ANCHOR_PROP_LIST = ( 'uv_anchor_nw', 'uv_anchor_n', 'uv_anchor_ne',
			'uv_anchor_w', 'uv_anchor_c', 'uv_anchor_e',
			'uv_anchor_sw', 'uv_anchor_s', 'uv_anchor_se' )

STATE_PROP_LIST = ( 'uv_state_ctrl', 'uv_state_shift', 'uv_state_alt' )

def GetLoopGroups( context, rmmesh, uvlayer, local ):
	sel_mode = context.tool_settings.mesh_select_mode[:]
	visible_faces = rmlib.rmPolygonSet()
	if sel_mode[0]:		
		for f in rmmesh.bmesh.faces:
			if f.hide:
				continue
			visible = True
			for v in f.verts:
				if not v.select:
					visible = False
					break
			if visible:
				visible_faces.append( f )
	elif sel_mode[1]:
		for f in rmmesh.bmesh.faces:
			if f.hide:
				continue
			visible = True
			for e in f.edges:
				if not e.select:
					visible = False
					break
			if visible:
				visible_faces.append( f )
	else:
		visible_faces = rmlib.rmPolygonSet.from_selection( rmmesh )

	loop_groups = []
	sel_sync = context.tool_settings.use_uv_select_sync
	if sel_sync:
		if sel_mode[0]:
			vert_selection = rmlib.rmVertexSet.from_selection( rmmesh )
			loop_selection = rmlib.rmUVLoopSet( vert_selection.loops, uvlayer=uvlayer )
			if local:
				loop_groups += loop_selection.group_vertices()
			else:
				loop_groups.append( loop_selection )

		elif sel_mode[1]:
			edge_selection = rmlib.rmEdgeSet.from_selection( rmmesh )
			loop_selection = rmlib.rmUVLoopSet( edge_selection.vertices.loops, uvlayer=uvlayer )
			if local:
				loop_groups += loop_selection.group_vertices()
			else:
				loop_groups.append( loop_selection )

		elif sel_mode[2]:
			face_selection = rmlib.rmPolygonSet.from_selection( rmmesh )
			loopset = set()
			for f in face_selection:
				loopset |= set( f.loops )
			loop_selection = rmlib.rmUVLoopSet( loopset, uvlayer=uvlayer )
			if local:
				loop_groups += loop_selection.group_vertices()
			else:
				loop_groups.append( loop_selection )

	else:
		sel_mode = context.tool_settings.uv_select_mode
		if sel_mode == 'VERTEX' and local:
			loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
			for l in loop_selection:
				if l.face in visible_faces:
					visible_loop_selection.append( l )
			loop_groups += visible_loop_selection.group_vertices()
			
		elif sel_mode == 'EDGE':
			loop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
			for l in loop_selection:
				if l.face in visible_faces:
					visible_loop_selection.append( l )
			if local:
				loop_groups = visible_loop_selection.group_edges()
				for i in range( len( loop_groups ) ):
					loop_groups[i].add_overlapping_loops( True )
			else:
				visible_loop_selection.add_overlapping_loops( True )
				loop_groups.append( visible_loop_selection )


		elif sel_mode == 'FACE' and local:
			loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
			for l in loop_selection:
				if l.face in visible_faces:
					visible_loop_selection.append( l )
			loop_groups += visible_loop_selection.group_faces()

		else:
			loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			visible_loop_selection = rmlib.rmUVLoopSet( uvlayer=uvlayer )
			for l in loop_selection:
				if l.face in visible_faces:
					visible_loop_selection.append( l )
			loop_groups = [ visible_loop_selection ]

	return loop_groups


class MESH_OT_uvmove( bpy.types.Operator ):
	"""Move selection in uv space."""
	bl_idname = 'mesh.rm_uvmove'
	bl_label = 'Move UVs'
	bl_options = { 'UNDO' }

	dir: bpy.props.EnumProperty(
		items=[ ( "n", "N", "", 1 ),
				( "s", "S", "", 2 ),
				( "e", "E", "", 3 ),
				( "w", "W", "", 4 ),
				( "nw", "NW", "", 5 ),
				( "ne", "NE", "", 6 ),
				( "sw", "SW", "", 7 ),
				( "se", "SE", "", 8 ) ],
		name="Direction",
		default="n"
	)

	'''
	def __init__( self ):
		self.__ctrl = False
		self.__shift = False
		self.__alt = False
	'''

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
	
	'''
	def invoke( self, context, event ):
		self.__ctrl = event.ctrl and event.value == 'PRESS'
		self.__shift = event.shift and event.value == 'PRESS'
		self.__alt = event.alt and event.value == 'PRESS'
		return self.execute( context )
	'''

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		'''
		if self.__ctrl:
			bpy.ops.mesh.rm_uvslam( "INVOKE_DEFAULT", dir=( 'l' + self.dir ) )
			print( 'CTRL' )
			return { 'FINISHED' }
		if self.__shift:
			bpy.ops.mesh.rm_uvslam( "INVOKE_DEFAULT", dir=( self.dir ) )
			print( 'SHIFT' )
			return { 'FINISHED' }
		if self.__alt:
			print( 'ALT' )
			return { 'FINISHED' }
		'''
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			#get loop groups	
			groups = GetLoopGroups( context, rmmesh, uvlayer, False )

			#compute offset vec
			offset = context.scene.uv_uvmove_offset
			offset_vec = mathutils.Vector( ( 0.0, 0.0 ) )
			if 'n' in self.dir:
				offset_vec[1] += 1.0
			if 's' in self.dir:
				offset_vec[1] -= 1.0
			if 'w' in self.dir:
				offset_vec[0] -= 1.0
			if 'e' in self.dir:
				offset_vec[0] += 1.0
			offset_vec *= offset

			#offset loops
			for g in groups:
				if context.scene.uv_fit_movecontinuous:
					g = g.group_vertices( element=True )[0]
					g.add_overlapping_loops( True )

				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv.copy() )
					l[uvlayer].uv = uv + offset_vec

		return { 'FINISHED' }


def GetActiveAnchorStr( context ):
	for a in ANCHOR_PROP_LIST:
		try:
			if context.scene.anchorprops[a]:
				return a[9:]
		except KeyError:
			pass
	return ''


def GetUVBounds( loops, uvlayer ):
	bbmin = loops[0][uvlayer].uv.copy()
	bbmax = loops[0][uvlayer].uv.copy()
	for i in range( 1, len( loops ) ):
		l = loops[i]
		uv = l[uvlayer].uv.copy()
		if uv[0] < bbmin[0]:
			bbmin[0] = uv[0]
		if uv[1] < bbmin[1]:
			bbmin[1] = uv[1]
		if uv[0] > bbmax[0]:
			bbmax[0] = uv[0]
		if uv[1] > bbmax[1]:
			bbmax[1] = uv[1]
	return ( mathutils.Vector( bbmin ), mathutils.Vector( bbmax ) )


class MESH_OT_uvslam( bpy.types.Operator ):
	"""Move selection in uv space."""
	bl_idname = 'mesh.rm_uvslam'
	bl_label = 'Smal UVs'
	bl_options = { 'UNDO' }

	dir: bpy.props.EnumProperty(
		items=[ ( "n", "N", "", 1 ),
				( "s", "S", "", 2 ),
				( "e", "E", "", 3 ),
				( "w", "W", "", 4 ),
				( "nw", "NW", "", 5 ),
				( "ne", "NE", "", 6 ),
				( "sw", "SW", "", 7 ),
				( "se", "SE", "", 8 ),
				( "ln", "LN", "", 9 ),
				( "ls", "LS", "", 10 ),
				( "le", "LE", "", 11 ),
				( "lw", "LW", "", 12 ),
				( "lnw", "LNW", "", 13 ),
				( "lne", "LNE", "", 14 ),
				( "lsw", "LSW", "", 15 ),
				( "lse", "LSE", "", 16 ) ],
		name="Direction",
		default="n"
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			anchor_str = GetActiveAnchorStr( context )

			#get loop groups	
			groups = GetLoopGroups( context, rmmesh, uvlayer, 'l' in self.dir )
			
			for g in groups:
				#compute the anchor pos
				bbmin, bbmax = GetUVBounds( g, uvlayer )
				bbcenter = ( bbmin + bbmax ) * 0.5

				#compute target position
				target_pos = bbcenter.copy()
				if 'n' in self.dir:
					target_pos[1] = 1.0
				if 's' in self.dir:
					target_pos[1] = 0.0
				if 'e' in self.dir:
					target_pos[0] = 1.0
				if 'w' in self.dir:
					target_pos[0] = 0.0

				anchor_pos = bbcenter.copy()
				if anchor_str == '':
					if 'n' in self.dir:
						anchor_pos[1] = bbmax[1]
					if 's' in self.dir:
						anchor_pos[1] = bbmin[1]
					if 'e' in self.dir:
						anchor_pos[0] = bbmax[0]
					if 'w' in self.dir:
						anchor_pos[0] = bbmin[0]
				else:
					if 'n' in anchor_str:
						anchor_pos[1] = bbmax[1]
					if 's' in anchor_str:
						anchor_pos[1] = bbmin[1]
					if 'e' in anchor_str:
						anchor_pos[0] = bbmax[0]
					if 'w' in anchor_str:
						anchor_pos[0] = bbmin[0]

				if context.scene.uv_fit_movecontinuous:
					g = g.group_vertices( element=True )[0]
					g.add_overlapping_loops( True )

				#transform loops
				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv.copy() )
					uv += target_pos - anchor_pos
					l[uvlayer].uv = uv

		return { 'FINISHED' }


class MESH_OT_uvrotate( bpy.types.Operator ):
	"""Rotate selection in uv space."""
	bl_idname = 'mesh.rm_uvrotate'
	bl_label = 'Rotate UVs'
	bl_options = { 'UNDO' }

	dir: bpy.props.EnumProperty(
		items=[ ( "cw", "CW", "", 1 ),
				( "lcw", "LCW", "", 2 ),
				( "ccw", "CCW", "", 3 ),
				( "lccw", "LCCW", "", 4 ) ],
		name="Direction",
		default="ccw"
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			anchor_str = GetActiveAnchorStr( context )
			
			#compute affine transform
			angle_offset = context.scene.uv_uvrotation_offset
			theta = math.radians( angle_offset )
			if 'ccw' not in self.dir:
				theta *= -1.0
			r1 = [ math.cos( theta ), -math.sin( theta ) ]
			r2 = [ math.sin( theta ), math.cos( theta ) ]
			rot_mat = mathutils.Matrix( [ r1, r2 ] )

			#get loop groups	
			groups = GetLoopGroups( context, rmmesh, uvlayer, 'l' in self.dir )
			
			for g in groups:
				#compute the anchor pos
				bbmin, bbmax = GetUVBounds( g, uvlayer )
				bbcenter = ( bbmin + bbmax ) * 0.5
				anchor_pos = bbcenter.copy()
				if 'n' in anchor_str:
					anchor_pos[1] = bbmax[1]
				if 's' in anchor_str:
					anchor_pos[1] = bbmin[1]
				if 'e' in anchor_str:
					anchor_pos[0] = bbmax[0]
				if 'w' in anchor_str:
					anchor_pos[0] = bbmin[0]

				if context.scene.uv_fit_movecontinuous:
					g = g.group_vertices( element=True )[0]
					g.add_overlapping_loops( True )

				#transform loops
				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv )
					uv -= anchor_pos
					uv = rot_mat @ uv
					uv += anchor_pos
					l[uvlayer].uv = uv
					
		return { 'FINISHED' }


class MESH_OT_uvscale( bpy.types.Operator ):
	"""Scale selection in uv space."""
	bl_idname = 'mesh.rm_uvscale'
	bl_label = 'Scale UVs'
	bl_options = { 'UNDO' }

	dir: bpy.props.EnumProperty(
		items=[ ( "u+", "U+", "", 1 ),
				( "u-", "U-", "", 2 ),
				( "uv+", "UV+", "", 3 ),
				( "uv-", "UV-", "", 4 ),
				( "v+", "V+", "", 5 ),
				( "v-", "V-", "", 6 ),
				( "lu+", "LU+", "", 7 ),
				( "lu-", "LU-", "", 8 ),
				( "luv+", "LUV+", "", 9 ),
				( "luv-", "LUV-", "", 10 ),
				( "lv+", "LV+", "", 11 ),
				( "lv-", "LV-", "", 12 ) ],
		name="Direction",
		default="uv+"
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			anchor_str = GetActiveAnchorStr( context )
			
			#compute affine transform
			scale_factor = context.scene.uv_uvscale_factor
			scl_mat = mathutils.Matrix.Identity( 2 )
			if 'u' in self.dir:
				scl_mat[0][0] = scale_factor
				if '-' in self.dir:
					scl_mat[0][0] = 1.0 / scl_mat[0][0]				
			if 'v' in self.dir:
				scl_mat[1][1] = scale_factor
				if '-' in self.dir:
					scl_mat[1][1] = 1.0 / scl_mat[1][1]
			
			#get loop groups	
			groups = GetLoopGroups( context, rmmesh, uvlayer, 'l' in self.dir )
			
			for g in groups:
				#compute the anchor pos
				bbmin, bbmax = GetUVBounds( g, uvlayer )
				bbcenter = ( bbmin + bbmax ) * 0.5
				anchor_pos = bbcenter.copy()
				if 'n' in anchor_str:
					anchor_pos[1] = bbmax[1]
				if 's' in anchor_str:
					anchor_pos[1] = bbmin[1]
				if 'e' in anchor_str:
					anchor_pos[0] = bbmax[0]
				if 'w' in anchor_str:
					anchor_pos[0] = bbmin[0]

				if context.scene.uv_fit_movecontinuous:
					g = g.group_vertices( element=True )[0]
					g.add_overlapping_loops( True )

				#transform loops
				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv )
					uv -= anchor_pos
					uv = scl_mat @ uv
					uv += anchor_pos
					l[uvlayer].uv = uv
					
		return { 'FINISHED' }


class MESH_OT_uvflip( bpy.types.Operator ):
	"""Flip selection in uv space."""
	bl_idname = 'mesh.rm_uvflip'
	bl_label = 'Flip UVs'
	bl_options = { 'UNDO' }

	dir: bpy.props.EnumProperty(
		items=[ ( "u", "U", "", 1 ),
				( "v", "V", "", 2 ),
				( "lu", "LU", "", 3 ),
				( "lv", "LV", "", 4 ) ],
		name="Direction",
		default="u"
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv

			anchor_str = GetActiveAnchorStr( context )
			
			#compute affine transform
			scl_mat = mathutils.Matrix.Identity( 2 )
			if 'u' in self.dir:
				scl_mat[0][0] *= -1.0
			if 'v' in self.dir:
				scl_mat[1][1] *= -1.0
			
			#get loop groups	
			groups = GetLoopGroups( context, rmmesh, uvlayer, 'l' in self.dir )
			
			for g in groups:
				#compute the anchor pos
				bbmin, bbmax = GetUVBounds( g, uvlayer )
				bbcenter = ( bbmin + bbmax ) * 0.5
				anchor_pos = bbcenter.copy()
				if 'n' in anchor_str:
					anchor_pos[1] = bbmax[1]
				if 's' in anchor_str:
					anchor_pos[1] = bbmin[1]
				if 'e' in anchor_str:
					anchor_pos[0] = bbmax[0]
				if 'w' in anchor_str:
					anchor_pos[0] = bbmin[0]

				if context.scene.uv_fit_movecontinuous:
					g = g.group_vertices( element=True )[0]
					g.add_overlapping_loops( True )

				#transform loops
				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv )
					uv -= anchor_pos
					uv = scl_mat @ uv
					uv += anchor_pos
					l[uvlayer].uv = uv
					
		return { 'FINISHED' }


class MESH_OT_uvfitsample( bpy.types.Operator ):
	"""Store the uv bounds of the selection."""
	bl_idname = 'mesh.rm_uvfitsample'
	bl_label = 'Store Bounds'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			
			#get loop groups	
			groups = GetLoopGroups( context, rmmesh, uvlayer, False )			
			for g in groups:
				#compute the anchor pos
				bbmin, bbmax = GetUVBounds( g, uvlayer )
				context.scene.uv_fit_bounds_min = bbmin
				context.scene.uv_fit_bounds_max = bbmax
					
		return { 'FINISHED' }


class MESH_OT_uvfit( bpy.types.Operator ):
	"""Map uv selection to the stored bounds."""
	bl_idname = 'mesh.rm_uvfit'
	bl_label = 'UV Fit'
	bl_options = { 'UNDO' }

	dir: bpy.props.EnumProperty(
		items=[ ( "u", "U", "", 1 ),
				( "v", "V", "", 2 ),
				( "uv", "UV", "", 3 ),
				( "lu", "LU", "", 4 ),
				( "lv", "LV", "", 5 ),
				( "luv", "LUV", "", 6 ),
				( "u0", "U0", "", 7 ),
				( "v0", "V0", "", 8 ),
				( "uv0", "UV0", "", 9 ) ],
		name="Direction",
		default="u"
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }

		use_aspect = context.scene.uv_fit_aspect

		if '0' in self.dir:
			target_bounds_min = mathutils.Vector( ( 0.0, 0.0 ) )
			target_bounds_max = mathutils.Vector( ( 1.0, 1.0 ) )
		else:
			target_bounds_min = mathutils.Vector( context.scene.uv_fit_bounds_min )
			target_bounds_max = mathutils.Vector( context.scene.uv_fit_bounds_max )
		target_bounds_center = ( target_bounds_max + target_bounds_min ) * 0.5
		
		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			
			#get loop groups	
			groups = GetLoopGroups( context, rmmesh, uvlayer, 'l' in self.dir )
			for g in groups:
				#compute the anchor pos
				bbmin, bbmax = GetUVBounds( g, uvlayer )
				bbcenter = ( bbmin + bbmax ) * 0.5
				bbwidth = bbmax[0] - bbmin[0]
				bbheight = bbmax[1] - bbmin[1]

				trans_mat = mathutils.Matrix.Identity( 3 )
				trans_mat[0][2] = bbcenter[0] * -1.0
				trans_mat[1][2] = bbcenter[1] * -1.0
				
				trans_mat_inverse = mathutils.Matrix.Identity( 3 )
				if context.scene.uv_fit_moveto:
					trans_mat_inverse[0][2] = target_bounds_center[0]
					trans_mat_inverse[1][2] = target_bounds_center[1]
				else:
					trans_mat_inverse[0][2] = bbcenter[0]
					trans_mat_inverse[1][2] = bbcenter[1]

				target_bounds_width = bbwidth
				target_bounds_height = bbheight
				if 'uv' in self.dir:
					target_bounds_width = target_bounds_max[0] - target_bounds_min[0]
					target_bounds_height = target_bounds_max[1] - target_bounds_min[1]
				elif 'u' in self.dir:
					target_bounds_width = target_bounds_max[0] - target_bounds_min[0]
					if use_aspect:
						target_bounds_height = target_bounds_width * ( bbheight / bbwidth )
				elif 'v' in self.dir:
					target_bounds_height = target_bounds_max[1] - target_bounds_min[1]
					if use_aspect:
						target_bounds_width = target_bounds_height * ( bbwidth / bbheight )
				
				scl_mat = mathutils.Matrix.Identity( 3 )
				scl_mat[0][0] = target_bounds_width / bbwidth
				scl_mat[1][1] = target_bounds_height / bbheight

				mat = trans_mat_inverse @ scl_mat @ trans_mat

				if context.scene.uv_fit_movecontinuous:
					g = g.group_vertices( element=True )[0]
					g.add_overlapping_loops( True )

				#transform loops
				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()
					
		return { 'FINISHED' }


class MESH_OT_uvrandom( bpy.types.Operator ):
	'''Randomize UV Selection'''
	bl_idname = 'mesh.rm_uvrandom'
	bl_label = 'Randomize Island Transforms'
	bl_options = { 'UNDO' }

	flip_axis: bpy.props.EnumProperty(
		name='Flip Axis',
		default=2,
		items=[
			( 'u', 'U', 'U Axis', 0 ),
			( 'v', 'V', 'V Axis', 1 ),
			( 'uv', 'UV', 'Both', 2 ),
			( 'none', 'None', 'None', 3 )
		]
	)

	rot_step: bpy.props.FloatProperty(
		name='Rotate Range',
		default=math.pi,
		subtype='ANGLE',
		unit='ROTATION'
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }

		with rmmesh as rmmesh:
			uvlayer = rmmesh.active_uv
			
			#get loop groups	
			groups = GetLoopGroups( context, rmmesh, uvlayer, True )
			for g in groups:
				#compute the anchor pos
				bbmin, bbmax = GetUVBounds( g, uvlayer )
				bbcenter = ( bbmin + bbmax ) * 0.5
				bbwidth = bbmax[0] - bbmin[0]
				bbheight = bbmax[1] - bbmin[1]

				trans_mat = mathutils.Matrix.Identity( 3 )
				trans_mat[0][2] = bbcenter[0] * -1.0
				trans_mat[1][2] = bbcenter[1] * -1.0
				
				trans_mat_inverse = mathutils.Matrix.Identity( 3 )
				trans_mat_inverse[0][2] = bbcenter[0]
				trans_mat_inverse[1][2] = bbcenter[1]
				
				u_sign = 1.0
				if self.flip_axis == 'u' or self.flip_axis == 'uv':
					u_sign = 1 if random.random() < 0.5 else -1

				v_sign = 1.0
				if self.flip_axis == 'v' or self.flip_axis == 'uv':
					v_sign = 1 if random.random() < 0.5 else -1

				scl_mat = mathutils.Matrix.Identity( 3 )
				scl_mat[0][0] = u_sign
				scl_mat[1][1] = v_sign			

				rot_mat = mathutils.Matrix.Identity( 3 )
				if self.rot_step != 0.0:
					theta = self.rot_step * math.floor( random.random() * 100.0 )
					rot_mat[0][0] = math.cos( theta )
					rot_mat[1][0] = math.sin( theta ) * -1.0
					rot_mat[0][1] = math.sin( theta )
					rot_mat[1][1] = math.cos( theta )

				mat = trans_mat_inverse @ scl_mat @ rot_mat @ trans_mat

				#include continuous elems in transformation
				g = g.group_vertices( element=True )[0]
				g.add_overlapping_loops( True )

				#transform loops
				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv.copy() ).to_3d()
					uv[2] = 1.0
					uv = mat @ uv
					l[uvlayer].uv = uv.to_2d()
					
		return { 'FINISHED' }

	def draw( self, context ):
		layout= self.layout
		layout.prop( self, 'flip_axis' )
		layout.prop( self, 'rot_step' )

	def invoke( self, context, event ):			
		return context.window_manager.invoke_props_dialog( self, width=230 )


class UV_PT_UVTransformTools( bpy.types.Panel ):
	bl_parent_id = 'UV_PT_RMKIT_PARENT'
	bl_idname = 'UV_PT_UVTransformTools'
	bl_label = 'Transform and Orient'
	bl_region_type = 'UI'
	bl_space_type = 'IMAGE_EDITOR'
	bl_options = { 'DEFAULT_CLOSED' }

	def draw( self, context ):
		layout = self.layout

		r = layout.row()
		r.prop( context.scene.stateprops, 'uv_state_ctrl', toggle=1 )
		r.prop( context.scene.stateprops, 'uv_state_shift', toggle=1 )
		r.prop( context.scene.stateprops, 'uv_state_alt', toggle=1 )
		layout.separator( factor=0.2 )

		pcoll = preview_collections['main']
		flow = layout.grid_flow( columns=3, even_columns=True, align=True )

		if context.scene.stateprops.uv_state_ctrl:
			c1 = flow.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['nw_c'].icon_id ).dir = 'lnw'
			c1.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['w_c'].icon_id ).dir = 'lw'
			c1.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['sw_c'].icon_id ).dir = 'lsw'

			c2 = flow.column()
			c2.alignment = 'EXPAND'
			c2.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['n_c'].icon_id ).dir = 'ln'
			c2.prop( context.scene, 'uv_uvmove_offset', text='' )
			c2.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['s_c'].icon_id ).dir = 'ls'
			
			c3 = flow.column()
			c3.alignment = 'EXPAND'			
			c3.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['ne_c'].icon_id ).dir = 'lne'
			c3.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['e_c'].icon_id ).dir = 'le'			
			c3.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['se_c'].icon_id ).dir = 'lse'

		elif context.scene.stateprops.uv_state_shift:
			c1 = flow.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['nw_b'].icon_id ).dir = 'nw'
			c1.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['w_b'].icon_id ).dir = 'w'
			c1.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['sw_b'].icon_id ).dir = 'sw'

			c2 = flow.column()
			c2.alignment = 'EXPAND'
			c2.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['n_b'].icon_id ).dir = 'n'
			c2.prop( context.scene, 'uv_uvmove_offset', text='' )
			c2.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['s_b'].icon_id ).dir = 's'
			
			c3 = flow.column()
			c3.alignment = 'EXPAND'			
			c3.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['ne_b'].icon_id ).dir = 'ne'
			c3.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['e_b'].icon_id ).dir = 'e'			
			c3.operator( MESH_OT_uvslam.bl_idname, text='', icon_value=pcoll['se_b'].icon_id ).dir = 'se'

		elif context.scene.stateprops.uv_state_alt :
			c1 = flow.column()
			c1.alignment = 'EXPAND'
			c1.prop( context.scene.anchorprops, 'uv_anchor_nw', toggle=1, icon_only =True, icon_value=pcoll['anch_nw'].icon_id )
			c1.prop( context.scene.anchorprops, 'uv_anchor_w', toggle=1, icon_only =True, icon_value=pcoll['anch_w'].icon_id )
			c1.prop( context.scene.anchorprops, 'uv_anchor_sw', toggle=1, icon_only =True, icon_value=pcoll['anch_sw'].icon_id )

			c2 = flow.column()
			c2.alignment = 'EXPAND'
			c2.prop( context.scene.anchorprops, 'uv_anchor_n', toggle=1, icon_only =True, icon_value=pcoll['anch_n'].icon_id )
			c2.prop( context.scene.anchorprops, 'uv_anchor_c', toggle=1, icon_only =True, icon_value=pcoll['anch_c'].icon_id )
			c2.prop( context.scene.anchorprops, 'uv_anchor_s', toggle=1, icon_only =True, icon_value=pcoll['anch_s'].icon_id )

			c3 = flow.column()
			c3.alignment = 'EXPAND'
			c3.prop( context.scene.anchorprops, 'uv_anchor_ne', toggle=1, icon_only =True, icon_value=pcoll['anch_ne'].icon_id )
			c3.prop( context.scene.anchorprops, 'uv_anchor_e', toggle=1, icon_only =True, icon_value=pcoll['anch_e'].icon_id )
			c3.prop( context.scene.anchorprops, 'uv_anchor_se', toggle=1, icon_only =True, icon_value=pcoll['anch_se'].icon_id )

		else:
			c1 = flow.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvmove.bl_idname, text='', icon_value=pcoll['nw_a'].icon_id ).dir = 'nw'
			c1.operator( MESH_OT_uvmove.bl_idname, text='', icon_value=pcoll['w_a'].icon_id ).dir = 'w'
			c1.operator( MESH_OT_uvmove.bl_idname, text='', icon_value=pcoll['sw_a'].icon_id ).dir = 'sw'

			c2 = flow.column()
			c2.alignment = 'EXPAND'
			c2.operator( MESH_OT_uvmove.bl_idname, text='', icon_value=pcoll['n_a'].icon_id ).dir = 'n'
			c2.prop( context.scene, 'uv_uvmove_offset', text='' )
			c2.operator( MESH_OT_uvmove.bl_idname, text='', icon_value=pcoll['s_a'].icon_id ).dir = 's'
			
			c3 = flow.column()
			c3.alignment = 'EXPAND'			
			c3.operator( MESH_OT_uvmove.bl_idname, text='', icon_value=pcoll['ne_a'].icon_id ).dir = 'ne'
			c3.operator( MESH_OT_uvmove.bl_idname, text='', icon_value=pcoll['e_a'].icon_id ).dir = 'e'			
			c3.operator( MESH_OT_uvmove.bl_idname, text='', icon_value=pcoll['se_a'].icon_id ).dir = 'se'

		layout.separator( factor=0.2 )
		rot_grid = layout.grid_flow( columns=3, even_columns=True, align=True )

		if context.scene.stateprops.uv_state_ctrl:
			c1 = rot_grid.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvrotate.bl_idname, text='', icon_value=pcoll['lcw'].icon_id ).dir = 'lcw'
			c2 = rot_grid.column()			
			c2.alignment = 'EXPAND'
			c2.prop( context.scene, 'uv_uvrotation_offset', text='' )
			c3 = rot_grid.column()
			c3.alignment = 'EXPAND'
			c3.operator( MESH_OT_uvrotate.bl_idname, text='', icon_value=pcoll['lccw'].icon_id ).dir = 'lccw'

		else:
			c1 = rot_grid.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvrotate.bl_idname, text='', icon_value=pcoll['cw'].icon_id ).dir = 'cw'
			c2 = rot_grid.column()
			c2.alignment = 'EXPAND'
			c2.prop( context.scene, 'uv_uvrotation_offset', text='' )
			c3 = rot_grid.column()
			c3.alignment = 'EXPAND'
			c3.operator( MESH_OT_uvrotate.bl_idname, text='', icon_value=pcoll['ccw'].icon_id ).dir = 'ccw'

		layout.separator( factor=0.2 )
		scl_grid = layout.grid_flow( columns=3, even_columns=True, align=True )

		if context.scene.stateprops.uv_state_ctrl:			
			c1 = scl_grid.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['LUV+'].icon_id ).dir = 'luv+'
			c1.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['LU+'].icon_id ).dir = 'lu+'
			c1.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['LV+'].icon_id ).dir = 'lv+'
			c2 = scl_grid.column()
			c2.alignment = 'EXPAND'
			c2.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['LUV-'].icon_id ).dir = 'luv-'
			c2.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['LU-'].icon_id ).dir = 'lu-'
			c2.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['LV-'].icon_id ).dir = 'lv-'
			c3 = scl_grid.column()
			c3.alignment = 'EXPAND'
			c3.prop( context.scene, 'uv_uvscale_factor', text='' )
			c3.operator( MESH_OT_uvflip.bl_idname, text='', icon_value=pcoll['LU'].icon_id ).dir = 'lu'
			c3.operator( MESH_OT_uvflip.bl_idname, text='', icon_value=pcoll['LV'].icon_id ).dir = 'lv'

		else:
			c1 = scl_grid.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['UV+'].icon_id ).dir = 'uv+'
			c1.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['U+'].icon_id ).dir = 'u+'
			c1.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['V+'].icon_id ).dir = 'v+'
			c2 = scl_grid.column()
			c2.alignment = 'EXPAND'
			c2.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['UV-'].icon_id ).dir = 'uv-'
			c2.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['U-'].icon_id ).dir = 'u-'
			c2.operator( MESH_OT_uvscale.bl_idname, text='', icon_value=pcoll['V-'].icon_id ).dir = 'v-'
			c3 = scl_grid.column()
			c3.alignment = 'EXPAND'
			c3.prop( context.scene, 'uv_uvscale_factor', text='' )
			c3.operator( MESH_OT_uvflip.bl_idname, text='', icon_value=pcoll['U'].icon_id ).dir = 'u'
			c3.operator( MESH_OT_uvflip.bl_idname, text='', icon_value=pcoll['V'].icon_id ).dir = 'v'


		layout.separator( factor=0.2 )
		r1 = layout.row()
		r1.prop( context.scene, 'uv_fit_aspect' )
		r1.prop( context.scene, 'uv_fit_moveto' )
		r2 = layout.row()
		r2.operator( MESH_OT_uvfitsample.bl_idname )
		fit_grid = layout.grid_flow( columns=3, even_columns=True, align=True )

		if context.scene.stateprops.uv_state_ctrl:
			c1 = fit_grid.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvfit.bl_idname, text='LU' ).dir = 'lu'
			c2 = fit_grid.column()
			c2.alignment = 'EXPAND'
			c2.operator( MESH_OT_uvfit.bl_idname, text='LV' ).dir = 'lv'
			c3 = fit_grid.column()
			c3.alignment = 'EXPAND'
			c3.operator( MESH_OT_uvfit.bl_idname, text='LUV' ).dir = 'luv'

		elif context.scene.stateprops.uv_state_shift:
			c1 = fit_grid.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvfit.bl_idname, text='GU' ).dir = 'u0'
			c2 = fit_grid.column()
			c2.alignment = 'EXPAND'
			c2.operator( MESH_OT_uvfit.bl_idname, text='GV' ).dir = 'v0'
			c3 = fit_grid.column()
			c3.alignment = 'EXPAND'
			c3.operator( MESH_OT_uvfit.bl_idname, text='GUV' ).dir = 'uv0'
		else:
			c1 = fit_grid.column()
			c1.alignment = 'EXPAND'
			c1.operator( MESH_OT_uvfit.bl_idname, text='U' ).dir = 'u'
			c2 = fit_grid.column()
			c2.alignment = 'EXPAND'
			c2.operator( MESH_OT_uvfit.bl_idname, text='V' ).dir = 'v'
			c3 = fit_grid.column()
			c3.alignment = 'EXPAND'
			c3.operator( MESH_OT_uvfit.bl_idname, text='UV' ).dir = 'uv'

		layout.prop( context.scene, 'uv_fit_movecontinuous' )

		layout.separator( factor=0.2 )
		layout.operator( MESH_OT_uvrandom.bl_idname )


def anchor_update( prop, context ):
	prev_value = context.scene.anchor_val_prev
	if prev_value != '':
		prop[prev_value] = False
	all_false = True
	for a in ANCHOR_PROP_LIST:
		try:
			if prop[a]:
				all_false = False
				context.scene.anchor_val_prev = a
				break
		except KeyError:
			continue
	if all_false:
		context.scene.anchor_val_prev = ''


def redraw_view3d( context ):
	for window in context.window_manager.windows:
		for area in window.screen.areas:
			if area.type == 'IMAGE_EDITOR':
				for region in area.regions:
					if region.type == 'UI':
						region.tag_redraw()


def state_update( prop, context ):
	prev_value = context.scene.state_val_prev
	if prev_value != '':
		prop[prev_value] = False
	all_false = True
	for a in STATE_PROP_LIST:
		try:
			if prop[a]:
				all_false = False
				context.scene.state_val_prev = a
				break
		except KeyError:
			continue
	if all_false:
		context.scene.state_val_prev = ''
	redraw_view3d( context )


class AnchorProps( bpy.types.PropertyGroup ):
	uv_anchor_nw: bpy.props.BoolProperty( name='ANW', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_n: bpy.props.BoolProperty( name='AN', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_ne: bpy.props.BoolProperty( name='ANE', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_w: bpy.props.BoolProperty( name='AW', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_c: bpy.props.BoolProperty( name='AC', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_e: bpy.props.BoolProperty( name='AE', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_sw: bpy.props.BoolProperty( name='ASW', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_s: bpy.props.BoolProperty( name='AS', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_se: bpy.props.BoolProperty( name='ASE', default=False, update=lambda self, context : anchor_update( self, context ) )

class StateProps( bpy.types.PropertyGroup ):
	uv_state_ctrl: bpy.props.BoolProperty( name='Local', default=False, update=lambda self, context : state_update( self, context ) )
	uv_state_shift: bpy.props.BoolProperty( name='Group', default=False, update=lambda self, context : state_update( self, context ) )
	uv_state_alt: bpy.props.BoolProperty( name='Anchor', default=False, update=lambda self, context : state_update( self, context ) )
	
preview_collections = {}

def load_icons():
	import bpy.utils.previews
	pcoll = bpy.utils.previews.new()

	icons_dir = os.path.join( os.path.dirname( __file__ ), 'icons' )
	pcoll.load( 'n_a', os.path.join( icons_dir, 'n_a.png' ), 'IMAGE' )
	pcoll.load( 's_a', os.path.join( icons_dir, 's_a.png' ), 'IMAGE' )
	pcoll.load( 'e_a', os.path.join( icons_dir, 'e_a.png' ), 'IMAGE' )
	pcoll.load( 'w_a', os.path.join( icons_dir, 'w_a.png' ), 'IMAGE' )
	pcoll.load( 'ne_a', os.path.join( icons_dir, 'ne_a.png' ), 'IMAGE' )
	pcoll.load( 'nw_a', os.path.join( icons_dir, 'nw_a.png' ), 'IMAGE' )
	pcoll.load( 'se_a', os.path.join( icons_dir, 'se_a.png' ), 'IMAGE' )
	pcoll.load( 'sw_a', os.path.join( icons_dir, 'sw_a.png' ), 'IMAGE' )
	pcoll.load( 'n_c', os.path.join( icons_dir, 'n_b.png' ), 'IMAGE' )
	pcoll.load( 's_c', os.path.join( icons_dir, 's_b.png' ), 'IMAGE' )
	pcoll.load( 'e_c', os.path.join( icons_dir, 'e_b.png' ), 'IMAGE' )
	pcoll.load( 'w_c', os.path.join( icons_dir, 'w_b.png' ), 'IMAGE' )
	pcoll.load( 'ne_c', os.path.join( icons_dir, 'ne_b.png' ), 'IMAGE' )
	pcoll.load( 'nw_c', os.path.join( icons_dir, 'nw_b.png' ), 'IMAGE' )
	pcoll.load( 'se_c', os.path.join( icons_dir, 'se_b.png' ), 'IMAGE' )
	pcoll.load( 'sw_c', os.path.join( icons_dir, 'sw_b.png' ), 'IMAGE' )
	pcoll.load( 'n_b', os.path.join( icons_dir, 'n_c.png' ), 'IMAGE' )
	pcoll.load( 's_b', os.path.join( icons_dir, 's_c.png' ), 'IMAGE' )
	pcoll.load( 'e_b', os.path.join( icons_dir, 'e_c.png' ), 'IMAGE' )
	pcoll.load( 'w_b', os.path.join( icons_dir, 'w_c.png' ), 'IMAGE' )
	pcoll.load( 'ne_b', os.path.join( icons_dir, 'ne_c.png' ), 'IMAGE' )
	pcoll.load( 'nw_b', os.path.join( icons_dir, 'nw_c.png' ), 'IMAGE' )
	pcoll.load( 'se_b', os.path.join( icons_dir, 'se_c.png' ), 'IMAGE' )
	pcoll.load( 'sw_b', os.path.join( icons_dir, 'sw_c.png' ), 'IMAGE' )
	pcoll.load( 'anch_n', os.path.join( icons_dir, 'anch_n.png' ), 'IMAGE' )
	pcoll.load( 'anch_ne', os.path.join( icons_dir, 'anch_ne.png' ), 'IMAGE' )
	pcoll.load( 'anch_nw', os.path.join( icons_dir, 'anch_nw.png' ), 'IMAGE' )
	pcoll.load( 'anch_e', os.path.join( icons_dir, 'anch_e.png' ), 'IMAGE' )
	pcoll.load( 'anch_w', os.path.join( icons_dir, 'anch_w.png' ), 'IMAGE' )
	pcoll.load( 'anch_se', os.path.join( icons_dir, 'anch_se.png' ), 'IMAGE' )
	pcoll.load( 'anch_s', os.path.join( icons_dir, 'anch_s.png' ), 'IMAGE' )
	pcoll.load( 'anch_sw', os.path.join( icons_dir, 'anch_sw.png' ), 'IMAGE' )
	pcoll.load( 'anch_c', os.path.join( icons_dir, 'anch_c.png' ), 'IMAGE' )
	pcoll.load( 'cw', os.path.join( icons_dir, 'cw.png' ), 'IMAGE' )
	pcoll.load( 'ccw', os.path.join( icons_dir, 'ccw.png' ), 'IMAGE' )
	pcoll.load( 'lcw', os.path.join( icons_dir, 'lcw.png' ), 'IMAGE' )
	pcoll.load( 'lccw', os.path.join( icons_dir, 'lccw.png' ), 'IMAGE' )
	pcoll.load( 'U+', os.path.join( icons_dir, 'U+.png' ), 'IMAGE' )
	pcoll.load( 'V+', os.path.join( icons_dir, 'V+.png' ), 'IMAGE' )
	pcoll.load( 'UV+', os.path.join( icons_dir, 'UV+.png' ), 'IMAGE' )
	pcoll.load( 'U-', os.path.join( icons_dir, 'U-.png' ), 'IMAGE' )
	pcoll.load( 'V-', os.path.join( icons_dir, 'V-.png' ), 'IMAGE' )
	pcoll.load( 'UV-', os.path.join( icons_dir, 'UV-.png' ), 'IMAGE' )
	pcoll.load( 'LU+', os.path.join( icons_dir, 'LU+.png' ), 'IMAGE' )
	pcoll.load( 'LV+', os.path.join( icons_dir, 'LV+.png' ), 'IMAGE' )
	pcoll.load( 'LUV+', os.path.join( icons_dir, 'LUV+.png' ), 'IMAGE' )
	pcoll.load( 'LU-', os.path.join( icons_dir, 'LU-.png' ), 'IMAGE' )
	pcoll.load( 'LV-', os.path.join( icons_dir, 'LV-.png' ), 'IMAGE' )
	pcoll.load( 'LUV-', os.path.join( icons_dir, 'LUV-.png' ), 'IMAGE' )
	pcoll.load( 'U', os.path.join( icons_dir, 'U.png' ), 'IMAGE' )
	pcoll.load( 'V', os.path.join( icons_dir, 'V.png' ), 'IMAGE' )
	pcoll.load( 'LU', os.path.join( icons_dir, 'LU.png' ), 'IMAGE' )
	pcoll.load( 'LV', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )

	pcoll.load( 'fLU', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )
	pcoll.load( 'fLV', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )
	pcoll.load( 'fLUV', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )
	pcoll.load( 'fU', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )
	pcoll.load( 'fV', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )
	pcoll.load( 'fUV', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )
	pcoll.load( 'U0', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )
	pcoll.load( 'V0', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )
	pcoll.load( 'UV0', os.path.join( icons_dir, 'LV.png' ), 'IMAGE' )

	preview_collections['main'] = pcoll
	
def register():
	load_icons()

	print( 'register :: {}'.format( UV_PT_UVTransformTools.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvmove.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvslam.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvrotate.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvscale.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvflip.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvfit.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvrandom.bl_idname ) )
	bpy.utils.register_class( UV_PT_UVTransformTools )
	bpy.utils.register_class( MESH_OT_uvmove )
	bpy.utils.register_class( MESH_OT_uvslam )
	bpy.utils.register_class( MESH_OT_uvrotate )
	bpy.utils.register_class( MESH_OT_uvscale )
	bpy.utils.register_class( MESH_OT_uvflip )
	bpy.utils.register_class( MESH_OT_uvfit )
	bpy.utils.register_class( MESH_OT_uvfitsample )
	bpy.utils.register_class( MESH_OT_uvrandom )
	bpy.types.Scene.uv_uvmove_offset = bpy.props.FloatProperty( name='Offset', default=1.0 )
	bpy.types.Scene.uv_uvrotation_offset = bpy.props.FloatProperty( name='RotationOffset', default=45.0, min=0.0, max=180.0 )
	bpy.types.Scene.uv_uvscale_factor = bpy.props.FloatProperty( name='Offset', default=2.0 )
	bpy.types.Scene.anchor_val_prev = bpy.props.StringProperty( name='Anchor Prev Val', default=ANCHOR_PROP_LIST[4] )
	bpy.types.Scene.state_val_prev = bpy.props.StringProperty( name='State Prev Val', default='' )
	bpy.types.Scene.uv_fit_aspect = bpy.props.BoolProperty( name='Use Aspect', default=False )
	bpy.types.Scene.uv_fit_moveto = bpy.props.BoolProperty( name='Move To', default=True )
	bpy.types.Scene.uv_fit_bounds_min = bpy.props.FloatVectorProperty( size=2, default=( 0.0, 0.0 ) )
	bpy.types.Scene.uv_fit_bounds_max = bpy.props.FloatVectorProperty( size=2, default=( 1.0, 1.0 ) )
	bpy.types.Scene.uv_fit_movecontinuous = bpy.props.BoolProperty( name='Transform Continuous', default=False )
	bpy.utils.register_class( AnchorProps )
	bpy.utils.register_class( StateProps )
	bpy.types.Scene.anchorprops = bpy.props.PointerProperty( type=AnchorProps )
	bpy.types.Scene.stateprops = bpy.props.PointerProperty( type=StateProps )
	

def unregister():
	for pcoll in preview_collections.values():
		bpy.utils.previews.remove( pcoll )
	preview_collections.clear()

	print( 'unregister :: {}'.format( UV_PT_UVTransformTools.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvmove.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvslam.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvrotate.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvscale.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvflip.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvfit.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvrandom.bl_idname ) )
	bpy.utils.unregister_class( UV_PT_UVTransformTools )
	bpy.utils.unregister_class( MESH_OT_uvmove )
	bpy.utils.unregister_class( MESH_OT_uvslam )
	bpy.utils.unregister_class( MESH_OT_uvrotate )
	bpy.utils.unregister_class( MESH_OT_uvscale )
	bpy.utils.unregister_class( MESH_OT_uvflip )
	bpy.utils.unregister_class( MESH_OT_uvfit )
	bpy.utils.unregister_class( MESH_OT_uvfitsample )
	bpy.utils.unregister_class( MESH_OT_uvrandom )
	del bpy.types.Scene.uv_uvmove_offset
	del bpy.types.Scene.uv_uvrotation_offset
	del bpy.types.Scene.uv_uvscale_factor
	del bpy.types.Scene.anchor_val_prev
	del bpy.types.Scene.state_val_prev
	del bpy.types.Scene.uv_fit_aspect
	del bpy.types.Scene.uv_fit_moveto
	del bpy.types.Scene.uv_fit_bounds_min
	del bpy.types.Scene.uv_fit_bounds_max
	del bpy.types.Scene.uv_fit_movecontinuous
	bpy.utils.unregister_class( AnchorProps )
	bpy.utils.unregister_class( StateProps )
	del bpy.types.Scene.anchorprops
	del bpy.types.Scene.stateprops