import bpy, bmesh, mathutils
from bpy.app.handlers import persistent
import rmKit.rmlib as rmlib

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
		return { 'FINISHED' }

class MESH_OT_uvslam( bpy.types.Operator ):
	"""Move selection in uv space."""
	bl_idname = 'mesh.rm_uvmove'
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


ANCHOR_PROP_LIST = ( 'uv_anchor_nw', 'uv_anchor_n', 'uv_anchor_ne',
			'uv_anchor_w', 'uv_anchor_c', 'uv_anchor_e',
			'uv_anchor_sw', 'uv_anchor_s', 'uv_anchor_se' )

def anchor_update( prop, context ):
	prev_value = context.scene.anchor_val_prev
	try:
		if not prop[prev_value]:
			prop[prev_value] = True
			return
	except KeyError:
		pass
	prop[prev_value] = False	
	for a in ANCHOR_PROP_LIST:
		try:
			if prop[a]:
				context.scene.anchor_val_prev = a
				break
		except KeyError:
			pass


class AnchorProps( bpy.types.PropertyGroup ):
	uv_anchor_nw: bpy.props.BoolProperty( name='ANW', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_n: bpy.props.BoolProperty( name='AN', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_ne: bpy.props.BoolProperty( name='ANE', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_w: bpy.props.BoolProperty( name='AW', default=False, update=lambda self, context : anchor_update( self, context ) )
	uv_anchor_c: bpy.props.BoolProperty( name='AC', default=True, update=lambda self, context : anchor_update( self, context ) )
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
	bpy.types.Scene.uv_uvscale_factor = bpy.props.FloatProperty( name='Offset', default=1.0 )
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