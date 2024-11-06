import bpy
from bpy.app.handlers import persistent

class rmKitPannel_parent( bpy.types.Panel ):
	bl_idname = "VIEW3D_PT_RMKIT_PARENT"
	bl_label = "rmKit"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "rmKit"

	def draw( self, context ):
		layout = self.layout

class rmKitPannel_parent_uv( bpy.types.Panel ):
	bl_idname = "UV_PT_RMKIT_PARENT"
	bl_label = "rmKit"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_category = "rmKit"

	def draw( self, context ):
		layout = self.layout

def callback_workspace_change( *args ):
	if bpy.context.workspace.name == 'Sculpting':
		bpy.context.preferences.inputs.use_mouse_emulate_3_button = True
		bpy.context.workspace.status_text_set( 'use_mouse_emulate_3_button: True' )
	else:
		bpy.context.preferences.inputs.use_mouse_emulate_3_button = False
		bpy.context.workspace.status_text_set( None )

owner = object()
def subscribe_workspace_change():
	subscribe_to = ( bpy.types.Window, "workspace" )
	bpy.msgbus.subscribe_rna(
		key=subscribe_to,
		owner=owner,
		args=( None, ),
		notify=callback_workspace_change,
	)

def unsubscribe_workspace_change():
	bpy.msgbus.clear_by_owner( owner )

@persistent
def load_workspace_handler( dummy ):
	subscribe_workspace_change()

from . import polypatch
from . import reduce
from . import context_bevel
from . import loopring
from . import move_to_furthest
from . import knifescreen
from . import extrudealongpath
from . import connect_edges
from . import arcadjust
from . import targetweld
from . import createtube
from . import vnormals
from . import copypaste
from . import cursor
from . import workplane
from . import screenreflect
from . import selectionmode
from . import radial_align
from . import edgeweight
from . import grabapplymat
from . import extend
from . import quickmaterial
from . import thicken
from . import stitch
from . import panel
from . import gridify
from . import relativeislands
from . import uvtransform
from . import unrotate
from . import rectangularize
from . import hotspot
from . import uvboundstransform
from . import dimensions
from . import uvgrowshrink
from . import preferences
from . import quickboolean
from . import naming
from . import linear_deformer
from . import linear_deformer_uv
from . import exportmanager

def register():
	bpy.utils.register_class( rmKitPannel_parent )
	bpy.utils.register_class( rmKitPannel_parent_uv )
	bpy.app.handlers.load_post.append( load_workspace_handler )
	subscribe_workspace_change()
	polypatch.register()
	reduce.register()
	context_bevel.register()
	loopring.register()
	move_to_furthest.register()
	knifescreen.register()
	extrudealongpath.register()
	connect_edges.register()
	arcadjust.register()
	targetweld.register()
	createtube.register()
	copypaste.register()
	cursor.register()
	workplane.register()
	linear_deformer.register()
	linear_deformer_uv.register()
	screenreflect.register()
	selectionmode.register()
	radial_align.register()
	edgeweight.register()
	grabapplymat.register()
	extend.register()
	quickmaterial.register()
	thicken.register()
	panel.register()
	vnormals.register()
	stitch.register()
	gridify.register()
	relativeislands.register()
	unrotate.register()
	uvtransform.register()
	rectangularize.register()
	hotspot.register()
	uvboundstransform.register()
	dimensions.register()
	quickboolean.register()
	uvgrowshrink.register()	
	preferences.register()
	exportmanager.register()
	naming.register()

def unregister():
	bpy.utils.unregister_class( rmKitPannel_parent )
	bpy.utils.unregister_class( rmKitPannel_parent_uv )
	bpy.app.handlers.load_post.remove( load_workspace_handler )
	unsubscribe_workspace_change()
	polypatch.unregister()
	reduce.unregister()
	context_bevel.unregister()
	loopring.unregister()
	move_to_furthest.unregister()
	knifescreen.unregister()
	extrudealongpath.unregister()
	connect_edges.unregister()
	arcadjust.unregister()
	targetweld.unregister()
	createtube.unregister()	
	copypaste.unregister()
	cursor.unregister()
	workplane.unregister()
	linear_deformer.unregister()
	linear_deformer_uv.unregister()
	screenreflect.unregister()
	selectionmode.unregister()
	radial_align.unregister()
	edgeweight.unregister()
	grabapplymat.unregister()
	extend.unregister()
	quickmaterial.unregister()	
	thicken.unregister()
	panel.unregister()
	vnormals.unregister()
	stitch.unregister()
	gridify.unregister()
	relativeislands.unregister()
	unrotate.unregister()
	uvtransform.unregister()
	rectangularize.unregister()
	hotspot.unregister()
	uvboundstransform.unregister()
	dimensions.unregister()
	quickboolean.unregister()
	uvgrowshrink.unregister()
	preferences.unregister()
	exportmanager.unregister()
	naming.unregister()