bl_info = {
    "name": "rmKit",
    "author": "Timothee Yeramian",
    "category": "",
    "blender": ( 3, 3, 1),
    "location": "View3D > Sidebar",
    "warning": "",
    "description": "Collection of Tools",
    "doc_url": "https://github.com/roosterMAP",
}


from . import addon
from . import rmlib


def register():
    addon.register()


def unregister():
    addon.unregister()
