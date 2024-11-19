bl_info = {
	"name": "rmKit",
	"author": "Timothee Yeramian",
	"location": "View3D > Sidebar",
	"description": "Collection of Tools",
	"doc_url": "https://rmkit.readthedocs.io/en/latest/",
}

from . import addon

def register():
	addon.register()


def unregister():
	addon.unregister()