import bpy

class rmKitPannel( bpy.types.Panel ):
	bl_idname = "VIEW3D_PT_RMKIT_PARENT"
	bl_label = "rmKit"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "rmKit"

	def draw( self, context ):
		layout = self.layout

class rmKitPannel_uv( bpy.types.Panel ):
	bl_idname = "UV_PT_RMKIT_PARENT"
	bl_label = "rmKit"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_category = "rmKit"

	def draw( self, context ):
		layout = self.layout

from . import polypatch
from . import reduce
from . import context_bevel
from . import loopring
from . import move_to_furthest
from . import knifescreen
from . import screenreflect
from . import connect_edges
from . import arcadjust
from . import targetweld
from . import createtube
from . import vnormals
from . import copypaste
from . import workplane
from . import selectionmode
from . import radial_align
from . import edgeweight
from . import grabapplymat
from . import extend
from . import quickmaterial
from . import cursor
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
from . import preferences

def register():
	bpy.utils.register_class( rmKitPannel )
	bpy.utils.register_class( rmKitPannel_uv )	
	polypatch.register()
	reduce.register()
	context_bevel.register()
	loopring.register()
	move_to_furthest.register()
	knifescreen.register()
	screenreflect.register()
	connect_edges.register()
	arcadjust.register()
	targetweld.register()
	createtube.register()
	copypaste.register()
	workplane.register()
	selectionmode.register()
	radial_align.register()
	edgeweight.register()
	grabapplymat.register()
	extend.register()
	quickmaterial.register()
	cursor.register()
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
	preferences.register()

def unregister():
	bpy.utils.unregister_class( rmKitPannel )
	bpy.utils.unregister_class( rmKitPannel_uv )	
	polypatch.unregister()
	reduce.unregister()
	context_bevel.unregister()
	loopring.unregister()
	move_to_furthest.unregister()
	knifescreen.unregister()
	screenreflect.unregister()
	connect_edges.unregister()
	arcadjust.unregister()
	targetweld.unregister()
	createtube.unregister()	
	copypaste.unregister()
	workplane.unregister()
	selectionmode.unregister()
	radial_align.unregister()
	edgeweight.unregister()
	grabapplymat.unregister()
	extend.unregister()
	quickmaterial.unregister()
	cursor.unregister()
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
	preferences.unregister()