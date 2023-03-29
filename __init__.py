bl_info = {
    "name": "rmKit",
    "author": "Timothee Yeramian",
    "category": "",
    "blender": ( 3, 3, 1),
    "location": "View3D > Sidebar",
    "warning": "",
    "description": "Collection of Tools",
    "doc_url": "https://rmkit.readthedocs.io/en/latest/",
}


from . import addon

def register():
    addon.register()


def unregister():
    addon.unregister()