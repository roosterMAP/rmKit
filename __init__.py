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
import os
import threading
import sys
import zipfile
import urllib.request


RMLIB_URL = "https://github.com/roosterMAP/rmlib/archive/refs/heads/main.zip"
RMLIB_DIR = os.path.join(bpy.utils.script_path_user(), "modules", "rmlib")
RMLIB = False

class RMLIB_OT_RestartPrompt(bpy.types.Operator):
	"""Prompt the user to restart Blender"""
	bl_idname = "rmlib.restart_prompt"
	bl_label = "Restart Blender"

	def execute(self, context):
		self.report({'INFO'}, "Please restart Blender to complete the installation.")
		return {'FINISHED'}

	def invoke(self, context, event):
		wm = context.window_manager
		return wm.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		layout.label(text="rmlib has been installed successfully.")
		layout.label(text="Please restart Blender to complete the installation.")

class RMLIB_OT_DownloadPrompt(bpy.types.Operator):
	"""Prompt to download rmlib"""
	bl_idname = "rmlib.download_prompt"
	bl_label = "Download rmlib"

	def download_rmlib(self):
		try:
			# define paths
			zip_path = os.path.join(bpy.utils.script_path_user(), "rmlib.zip")
			modules_dir = os.path.join(bpy.utils.script_path_user(), "modules")
			extracted_dir = os.path.join(modules_dir, "rmlib-main")
			target_dir = os.path.join(modules_dir, "rmlib")

			# Ensure the modules directory exists
			os.makedirs(modules_dir, exist_ok=True)

			# Download the zip file
			with urllib.request.urlopen(RMLIB_URL, timeout=10.0) as response, open(zip_path, 'wb') as out_file:
				out_file.write(response.read())

			# Extract the zip file
			with zipfile.ZipFile(zip_path, 'r') as zip_ref:
				zip_ref.extractall(modules_dir)

			# Rename the extracted folder to "rmlib"
			if os.path.exists(extracted_dir):
				if os.path.exists(target_dir):
					# Remove the old "rmlib" folder if it exists
					import shutil
					shutil.rmtree(target_dir)
				os.rename(extracted_dir, target_dir)

			# Clean up the zip file
			os.remove(zip_path)

			# Mark progress as complete
			return True

		except Exception as e:
			return False

	def invoke(self, context, event):
		return context.window_manager.invoke_confirm(self, event)

	def execute(self, context):
		if self.download_rmlib():
			self.report({'INFO'}, "rmlib successfully downloaded and installed.")
			bpy.ops.rmlib.restart_prompt('INVOKE_DEFAULT')
			return { 'FINISHED' }
		self.report({'ERROR'}, "Failed to download rmlib.")
		return { 'CANCELLED' }


class rmKitPannel_parent( bpy.types.Panel ):
	bl_idname = "VIEW3D_PT_RMKIT_PARENT"
	bl_label = "rmKit"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "rmKit"

	def draw( self, context ):
		layout = self.layout
		rmlib_exists = os.path.exists(RMLIB_DIR) #Check if rmlib exists
		button_label = "Update rmlib" if rmlib_exists else "Download rmlib" #Set the button label dynamically
		layout.operator(RMLIB_OT_DownloadPrompt.bl_idname, text=button_label) #Add the button with the dynamic label


def register():
	try:
		bpy.utils.register_class(RMLIB_OT_RestartPrompt)
	except ValueError:
		pass #registered by another rm addon
	
	try:
		bpy.utils.register_class(RMLIB_OT_DownloadPrompt)
	except ValueError:
		pass #registered by another rm addon

	bpy.utils.register_class( rmKitPannel_parent )

	global RMLIB
	RMLIB = os.path.exists( RMLIB_DIR )
	if RMLIB_DIR not in sys.path:
		sys.path.append(RMLIB_DIR)
	if not RMLIB:
		return

	from . import (
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
	try:
		bpy.utils.unregister_class(RMLIB_OT_RestartPrompt)
	except ValueError:
		pass #registered by another rm addon
	
	try:
		bpy.utils.unregister_class(RMLIB_OT_DownloadPrompt)
	except ValueError:
		pass #registered by another rm addon

	bpy.utils.unregister_class( rmKitPannel_parent )

	global RMLIB
	if not RMLIB:
		return
	
	from . import (
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