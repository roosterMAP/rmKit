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

from . import addon

def register():
	addon.register()


def unregister():
	addon.unregister()