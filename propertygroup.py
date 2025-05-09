import bpy

class WorkplaneGridVisibility( bpy.types.PropertyGroup ):
	prop_show_floor: bpy.props.BoolProperty( name="Show Floor", default=True )
	prop_show_x: bpy.props.BoolProperty( name="Show X Axis", default=True )
	prop_show_y: bpy.props.BoolProperty( name="Show Y Axis", default=True )
	prop_show_z: bpy.props.BoolProperty( name="Show Z Axis", default=False )

class EdgeWeightProperties( bpy.types.PropertyGroup ):
	ew_weight_type_crease: bpy.props.EnumProperty(
			items=[ ( "crease", "Crease", "", 1 ),
					( "bevel_weight", "Bevel Weight", "", 2 ),
					( "sharp", "Sharp", "", 3 ) ],
			name="Weight Type",
			default="crease"
		)
	ew_weight_type_bevel_weight: bpy.props.EnumProperty(
			items=[ ( "crease", "Crease", "", 1 ),
					( "bevel_weight", "Bevel Weight", "", 2 ),
					( "sharp", "Sharp", "", 3 ) ],
			name="Weight Type",
			default="bevel_weight"
		)
	
class KnifeScreenProperties( bpy.types.PropertyGroup ):
	ks_alignment_topo: bpy.props.EnumProperty(
		items=[ ( "topology", "Topology", "", 1 ),
				( "grid", "Grid", "", 2 ),
				( "screen", "Screen", "", 3 ) ],
		name="Alignment",
		default="topology"
	)
	ks_alignment_grid: bpy.props.EnumProperty(
		items=[ ( "topology", "Topology", "", 1 ),
				( "grid", "Grid", "", 2 ),
				( "screen", "Screen", "", 3 ) ],
		name="Alignment",
		default="grid"
	)
	ks_alignment_screen: bpy.props.EnumProperty(
		items=[ ( "topology", "Topology", "", 1 ),
				( "grid", "Grid", "", 2 ),
				( "screen", "Screen", "", 3 ) ],
		name="Alignment",
		default="screen"
	)


class MoveToFurthestProperties( bpy.types.PropertyGroup ):
	mtf_prop_on: bpy.props.BoolProperty( default=True	)
	mtf_prop_off: bpy.props.BoolProperty( default=False )	


class ScreenReflectProperties( bpy.types.PropertyGroup ):
	sr_0: bpy.props.IntProperty( default=0 )
	sr_1: bpy.props.IntProperty( default=1 )
	sr_2: bpy.props.IntProperty( default=2 )


class RMKitSceneProperties(bpy.types.PropertyGroup):
	# Properties from dimensions.py
	dimensions_use_background_face_selection: bpy.props.BoolProperty(
		name="Use Background Face Selection",
	)

	# Properties from vnormals.py
	vn_selsetweighted: bpy.props.BoolProperty(
		name="Area Weights",
		default=False,
		description="Use triangle surface area weights when computing for vertex normals."
	)

	# Properties from workplane.py
	workplaneprops: bpy.props.PointerProperty( type=WorkplaneGridVisibility )

	# Properties from edgeweight.py
	edgeweightprops: bpy.props.PointerProperty( type=EdgeWeightProperties )

	# Properties from knifescreen.py
	knifescreenprops: bpy.props.PointerProperty( type=KnifeScreenProperties )

	# Properties from movetofurthest.py
	movetofurthestprops: bpy.props.PointerProperty( type=MoveToFurthestProperties )

	# Properties from screenreflect.py
	screenreflectprops: bpy.props.PointerProperty( type=ScreenReflectProperties )


def register():
	print(  "Registering RMKit Properties..." )
	bpy.utils.register_class(WorkplaneGridVisibility)
	bpy.utils.register_class(EdgeWeightProperties)
	bpy.utils.register_class(KnifeScreenProperties)
	bpy.utils.register_class(MoveToFurthestProperties)
	bpy.utils.register_class(ScreenReflectProperties)
	bpy.utils.register_class(RMKitSceneProperties)
	bpy.types.Scene.rmkit_props = bpy.props.PointerProperty(type=RMKitSceneProperties)
	
def unregister():
	bpy.utils.unregister_class(WorkplaneGridVisibility)
	bpy.utils.unregister_class(EdgeWeightProperties)
	bpy.utils.unregister_class(KnifeScreenProperties)
	bpy.utils.unregister_class(MoveToFurthestProperties)
	bpy.utils.unregister_class(ScreenReflectProperties)
	bpy.utils.unregister_class(RMKitSceneProperties)
	del bpy.types.Scene.rmkit_props