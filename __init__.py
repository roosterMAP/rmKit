bl_info = {
	"name": "rmKit",
	"author": "Timothee Yeramian",
	"location": "View3D > Sidebar",
	"description": "Collection of Tools",
	"category": "",
	"blender": ( 3, 3, 1),
	"warning": "",
	"doc_url": "https://rmkit.readthedocs.io/en/latest/",
}

import bpy

from . import (
	propertygroup,
	polypatch,
	reduce,
	context_bevel,
	loopring,
	move_to_furthest,
	knifescreen,
	extrudealongpath,
	connect_edges,
	arcadjust,
	targetweld,
	createtube,
	vnormals,
	copypaste,
	cursor,
	workplane,
	screenreflect,
	selectionmode,
	radial_align,
	edgeweight,
	grabapplymat,
	extend,
	quickmaterial,
	thicken,
	panel,
	dimensions,
	preferences,
	quickboolean,
	naming,
	linear_deformer,
)


class rmKitPannel_parent( bpy.types.Panel ):
	bl_idname = "VIEW3D_PT_RMKIT_PARENT"
	bl_label = "rmKit"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "rmKit"

	def draw( self, context ):
		layout = self.layout


def register():
	bpy.utils.register_class( rmKitPannel_parent )
	propertygroup.register()	
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
	dimensions.register()
	quickboolean.register()
	preferences.register()
	naming.register()


def unregister():
	bpy.utils.unregister_class( rmKitPannel_parent )
	propertygroup.unregister()		
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
	dimensions.unregister()
	quickboolean.unregister()
	preferences.unregister()
	naming.unregister()