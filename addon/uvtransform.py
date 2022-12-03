import bpy, mathutils
from bpy.app.handlers import persistent
import rmKit.rmlib as rmlib
import math

ANCHOR_PROP_LIST = ( 'uv_anchor_nw', 'uv_anchor_n', 'uv_anchor_ne',
			'uv_anchor_w', 'uv_anchor_c', 'uv_anchor_e',
			'uv_anchor_sw', 'uv_anchor_s', 'uv_anchor_se' )

def GetLoopGroups( context, rmmesh, uvlayer, local ):
	loop_groups = []
	sel_sync = context.tool_settings.use_uv_select_sync
	if sel_sync:
		sel_mode = context.tool_settings.mesh_select_mode[:]
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
			loop_groups += loop_selection.group_vertices()
			
		elif sel_mode == 'EDGE' and local:
			loop_selection = rmlib.rmUVLoopSet.from_edge_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			loop_groups = loop_selection.group_edges()
			for i in range( len( loop_groups ) ):
				loop_groups[i].add_overlapping_loops( True )

		elif sel_mode == 'FACE' and local:
			loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
			loop_groups += loop_selection.group_faces()

		else:
			loop_groups = [ rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer ) ]

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

				print( '{} ::  {}'.format( anchor_str, anchor_pos ) )

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

				#transform loops
				for l in g:
					uv = mathutils.Vector( l[uvlayer].uv )
					uv -= anchor_pos
					uv = scl_mat @ uv
					uv += anchor_pos
					l[uvlayer].uv = uv
					
		return { 'FINISHED' }


def redraw_view3d( context ):
	for window in context.window_manager.windows:
		for area in window.screen.areas:
			if area.type == 'IMAGE_EDITOR':
				for region in area.regions:
					if region.type == 'UI':
						region.tag_redraw()


class MESH_OT_uvmodkey( bpy.types.Operator ):
	bl_idname = 'view3d.rm_modkey_uvtools'
	bl_label = 'View3d Modkey Tracker'
	bl_options = { 'INTERNAL' }
	mod_state = [ False, False, False ]

	running = False
	
	@classmethod
	def poll( cls, context ):
		return True
	
	def invoke( self, context, event ):
		if not MESH_OT_uvmodkey.running:
			MESH_OT_uvmodkey.running = True
			wm = context.window_manager
			self._timer = wm.event_timer_add( 0.0625, window=context.window )
			wm.modal_handler_add( self )

		return {'RUNNING_MODAL'}

	def modal(self, context, event):
		if event.type == 'TIMER':
			state = [ event.ctrl, event.shift, event.alt ]

			if ( MESH_OT_uvmodkey.mod_state[0] != state[0] or
			MESH_OT_uvmodkey.mod_state[1] != state[1] or
			MESH_OT_uvmodkey.mod_state[2] != state[2] ):
				MESH_OT_uvmodkey.mod_state[0] = state[0]
				MESH_OT_uvmodkey.mod_state[1] = state[1]
				MESH_OT_uvmodkey.mod_state[2] = state[2]
				redraw_view3d( context )

		return { 'PASS_THROUGH' }


class UV_PT_UVTransformTools( bpy.types.Panel ):
	bl_parent_id = 'UV_PT_RMKIT_PARENT'
	bl_idname = 'UV_PT_UVTransformTools'
	bl_label = 'Transform and Orient'
	bl_region_type = 'UI'
	bl_space_type = 'IMAGE_EDITOR'
	bl_options = { 'DEFAULT_CLOSED' }

	def draw( self, context ):
		layout = self.layout
		box = layout.box()

		if MESH_OT_uvmodkey.mod_state[0] and not MESH_OT_uvmodkey.mod_state[1] and not MESH_OT_uvmodkey.mod_state[2]:
			box.label( text='Slam Local' )

			r1 = box.row()
			r1.alignment = 'EXPAND'
			r1.operator( MESH_OT_uvslam.bl_idname, text='LNW' ).dir = 'lnw'
			r1.operator( MESH_OT_uvslam.bl_idname, text='LN' ).dir = 'ln'
			r1.operator( MESH_OT_uvslam.bl_idname, text='LNE' ).dir = 'lne'

			r2 = box.row()
			r2.alignment = 'EXPAND'
			r2.operator( MESH_OT_uvslam.bl_idname, text='LW' ).dir = 'lw'
			r2.prop( context.scene, 'uv_uvmove_offset' )
			r2.operator( MESH_OT_uvslam.bl_idname, text='LE' ).dir = 'le'

			r3 = box.row()
			r3.alignment = 'EXPAND'
			r3.operator( MESH_OT_uvslam.bl_idname, text='LSW' ).dir = 'lsw'
			r3.operator( MESH_OT_uvslam.bl_idname, text='LS' ).dir = 'ls'
			r3.operator( MESH_OT_uvslam.bl_idname, text='LSE' ).dir = 'lse'

		elif not MESH_OT_uvmodkey.mod_state[0] and MESH_OT_uvmodkey.mod_state[1] and not MESH_OT_uvmodkey.mod_state[2]:
			box.label( text='Slam' )

			r1 = box.row()
			r1.alignment = 'EXPAND'
			r1.operator( MESH_OT_uvslam.bl_idname, text='^NW' ).dir = 'nw'
			r1.operator( MESH_OT_uvslam.bl_idname, text='^N' ).dir = 'n'
			r1.operator( MESH_OT_uvslam.bl_idname, text='^NE' ).dir = 'ne'

			r2 = box.row()
			r2.alignment = 'EXPAND'
			r2.operator( MESH_OT_uvslam.bl_idname, text='^W' ).dir = 'w'
			r2.prop( context.scene, 'uv_uvmove_offset' )
			r2.operator( MESH_OT_uvslam.bl_idname, text='^E' ).dir = 'e'

			r3 = box.row()
			r3.alignment = 'EXPAND'
			r3.operator( MESH_OT_uvslam.bl_idname, text='^SW' ).dir = 'sw'
			r3.operator( MESH_OT_uvslam.bl_idname, text='^S' ).dir = 's'
			r3.operator( MESH_OT_uvslam.bl_idname, text='^SE' ).dir = 'se'

		elif not MESH_OT_uvmodkey.mod_state[0] and not MESH_OT_uvmodkey.mod_state[1] and MESH_OT_uvmodkey.mod_state[2]:
			box.label( text='Anchor' )

			r1 = box.row()
			r1.alignment = 'EXPAND'
			r1.prop( context.scene.anchorprops, 'uv_anchor_nw', toggle=1 )
			r1.prop( context.scene.anchorprops, 'uv_anchor_n', toggle=1 )
			r1.prop( context.scene.anchorprops, 'uv_anchor_ne', toggle=1 )

			r2 = box.row()
			r2.alignment = 'EXPAND'
			r2.prop( context.scene.anchorprops, 'uv_anchor_w', toggle=1 )
			r2.prop( context.scene.anchorprops, 'uv_anchor_c', toggle=1 )
			r2.prop( context.scene.anchorprops, 'uv_anchor_e', toggle=1 )

			r3 = box.row()
			r3.alignment = 'EXPAND'
			r3.prop( context.scene.anchorprops, 'uv_anchor_sw', toggle=1 )
			r3.prop( context.scene.anchorprops, 'uv_anchor_s', toggle=1 )
			r3.prop( context.scene.anchorprops, 'uv_anchor_se', toggle=1 )

		else:
			box.label( text='Move' )

			r1 = box.row()
			r1.alignment = 'EXPAND'
			r1.operator( MESH_OT_uvmove.bl_idname, text='NW' ).dir = 'nw'
			r1.operator( MESH_OT_uvmove.bl_idname, text='N' ).dir = 'n'
			r1.operator( MESH_OT_uvmove.bl_idname, text='NE' ).dir = 'ne'

			r2 = box.row()
			r2.alignment = 'EXPAND'
			r2.operator( MESH_OT_uvmove.bl_idname, text='W' ).dir = 'w'
			r2.prop( context.scene, 'uv_uvmove_offset' )
			r2.operator( MESH_OT_uvmove.bl_idname, text='E' ).dir = 'e'

			r3 = box.row()
			r3.alignment = 'EXPAND'
			r3.operator( MESH_OT_uvmove.bl_idname, text='SW' ).dir = 'sw'
			r3.operator( MESH_OT_uvmove.bl_idname, text='S' ).dir = 's'
			r3.operator( MESH_OT_uvmove.bl_idname, text='SE' ).dir = 'se'

		layout.separator( factor=0.1 )
		box = layout.box()

		if MESH_OT_uvmodkey.mod_state[0] and not MESH_OT_uvmodkey.mod_state[1] and not MESH_OT_uvmodkey.mod_state[2]:
			box.label( text='Rotate Local' )

			box.prop( context.scene, 'uv_uvrotation_offset' )
			r4 = box.row()
			r4.alignment = 'EXPAND'
			r4.operator( MESH_OT_uvrotate.bl_idname, text='LCW' ).dir = 'lcw'
			r4.operator( MESH_OT_uvrotate.bl_idname, text='LCCW' ).dir = 'lccw'

		else:
			box.label( text='Rotate' )

			box.prop( context.scene, 'uv_uvrotation_offset' )
			r4 = box.row()
			r4.alignment = 'EXPAND'
			r4.operator( MESH_OT_uvrotate.bl_idname, text='CW' ).dir = 'cw'
			r4.operator( MESH_OT_uvrotate.bl_idname, text='CCW' ).dir = 'ccw'
			box.operator( 'mesh.rm_uvunrotate', text='Unrotate' )

		layout.separator( factor=0.1 )
		box = layout.box()

		if MESH_OT_uvmodkey.mod_state[0] and not MESH_OT_uvmodkey.mod_state[1] and not MESH_OT_uvmodkey.mod_state[2]:
			box.label( text='Scale Local' )

			box.prop( context.scene, 'uv_uvscale_factor' )
			r5 = box.row()
			r5.alignment = 'EXPAND'
			r5.operator( MESH_OT_uvscale.bl_idname, text='LUV-' ).dir = 'luv-'
			r5.operator( MESH_OT_uvscale.bl_idname, text='LUV+' ).dir = 'luv+'
			r6 = box.row()
			r6.alignment = 'EXPAND'
			r6.operator( MESH_OT_uvscale.bl_idname, text='LU-' ).dir = 'lu-'
			r6.operator( MESH_OT_uvscale.bl_idname, text='LU+' ).dir = 'lu+'
			r7 = box.row()
			r7.alignment = 'EXPAND'
			r7.operator( MESH_OT_uvscale.bl_idname, text='LV-' ).dir = 'lv-'
			r7.operator( MESH_OT_uvscale.bl_idname, text='LV+' ).dir = 'lv+'

		else:
			box.label( text='Scale' )

			box.prop( context.scene, 'uv_uvscale_factor' )
			r5 = box.row()
			r5.alignment = 'EXPAND'
			r5.operator( MESH_OT_uvscale.bl_idname, text='UV-' ).dir = 'uv-'
			r5.operator( MESH_OT_uvscale.bl_idname, text='UV+' ).dir = 'uv+'
			r6 = box.row()
			r6.alignment = 'EXPAND'
			r6.operator( MESH_OT_uvscale.bl_idname, text='U-' ).dir = 'u-'
			r6.operator( MESH_OT_uvscale.bl_idname, text='U+' ).dir = 'u+'
			r7 = box.row()
			r7.alignment = 'EXPAND'
			r7.operator( MESH_OT_uvscale.bl_idname, text='V-' ).dir = 'v-'
			r7.operator( MESH_OT_uvscale.bl_idname, text='V+' ).dir = 'v+'

		layout.separator( factor=0.1 )
		box = layout.box()

		if MESH_OT_uvmodkey.mod_state[0] and not MESH_OT_uvmodkey.mod_state[1] and not MESH_OT_uvmodkey.mod_state[2]:
			box.label( text='Flip Local' )

			r8 = box.row()
			r8.alignment = 'EXPAND'
			r8.operator( MESH_OT_uvflip.bl_idname, text='LU' ).dir = 'lu'
			r8.operator( MESH_OT_uvflip.bl_idname, text='LV' ).dir = 'lv'

		else:
			box.label( text='Flip' )

			r8 = box.row()
			r8.alignment = 'EXPAND'
			r8.operator( MESH_OT_uvflip.bl_idname, text='U' ).dir = 'u'
			r8.operator( MESH_OT_uvflip.bl_idname, text='V' ).dir = 'v'


@persistent
def uv_startup_handler( dummy ):
	bpy.ops.view3d.rm_modkey_uvtools( 'INVOKE_DEFAULT' )


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
	
	
def register():
	print( 'register :: {}'.format( UV_PT_UVTransformTools.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvmove.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvslam.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvrotate.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvscale.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvflip.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_uvmodkey.bl_idname ) )
	bpy.utils.register_class( UV_PT_UVTransformTools )
	bpy.utils.register_class( MESH_OT_uvmove )
	bpy.utils.register_class( MESH_OT_uvslam )
	bpy.utils.register_class( MESH_OT_uvrotate )
	bpy.utils.register_class( MESH_OT_uvscale )
	bpy.utils.register_class( MESH_OT_uvflip )
	bpy.types.Scene.uv_uvmove_offset = bpy.props.FloatProperty( name='Offset', default=1.0 )
	bpy.types.Scene.uv_uvrotation_offset = bpy.props.FloatProperty( name='RotationOffset', default=15.0, min=0.0, max=180.0 )
	bpy.types.Scene.uv_uvscale_factor = bpy.props.FloatProperty( name='Offset', default=2.0 )
	bpy.types.Scene.anchor_val_prev = bpy.props.StringProperty( name='Anchor Prev Val', default=ANCHOR_PROP_LIST[4] )
	bpy.utils.register_class( AnchorProps )
	bpy.types.Scene.anchorprops = bpy.props.PointerProperty( type=AnchorProps )	
	bpy.utils.register_class( MESH_OT_uvmodkey )
	bpy.app.handlers.load_post.append( uv_startup_handler )
	

def unregister():
	print( 'unregister :: {}'.format( UV_PT_UVTransformTools.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvmove.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvslam.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvrotate.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvscale.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvflip.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_uvmodkey.bl_idname ) )
	bpy.utils.unregister_class( UV_PT_UVTransformTools )
	bpy.utils.unregister_class( MESH_OT_uvmove )
	bpy.utils.unregister_class( MESH_OT_uvslam )
	bpy.utils.unregister_class( MESH_OT_uvrotate )
	bpy.utils.unregister_class( MESH_OT_uvscale )
	bpy.utils.unregister_class( MESH_OT_uvflip )
	del bpy.types.Scene.uv_uvmove_offset
	del bpy.types.Scene.uv_uvrotation_offset
	del bpy.types.Scene.uv_uvscale_factor
	del bpy.types.Scene.anchor_val_prev
	bpy.utils.unregister_class( AnchorProps )
	del bpy.types.Scene.anchorprops
	bpy.utils.unregister_class( MESH_OT_uvmodkey )