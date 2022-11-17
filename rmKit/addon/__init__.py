import bpy

class rmKitPannel( bpy.types.Panel ):
	bl_idname = "VIEW3D_PT_RMKIT_PARENT"
	bl_label = "rmKit"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "rmKit"
	bl_options = { "HIDE_HEADER" }

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
from . import push
from . import radial_align
from . import slide
from . import edgeweight
from . import grabapplymat
from . import extend
from . import quickmaterial
from . import cursor
from . import thicken

def register():
	bpy.utils.register_class( rmKitPannel )
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
	vnormals.register()
	copypaste.register()
	workplane.register()
	selectionmode.register()
	push.register()
	radial_align.register()
	slide.register()
	edgeweight.register()
	grabapplymat.register()
	extend.register()
	quickmaterial.register()
	cursor.register()
	thicken.register()

def unregister():
	bpy.utils.unregister_class( rmKitPannel )
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
	vnormals.unregister()
	copypaste.unregister()
	workplane.unregister()
	selectionmode.unregister()
	push.unregister()
	radial_align.unregister()
	slide.unregister()
	edgeweight.unregister()
	grabapplymat.unregister()
	extend.unregister()
	quickmaterial.unregister()
	cursor.register()
	thicken.unregister()