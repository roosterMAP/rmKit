import bpy, mathutils
from .. import rmlib

def uv_border_edge( uvlayer, loop ):
	if loop.edge.is_boundary:
		return True
	
	uvcoord = mathutils.Vector( loop[uvlayer].uv.copy() )
	for n_l in loop.vert.link_loops:
		if n_l == loop:
			continue
		n_uvcoord = mathutils.Vector( n_l[uvlayer].uv.copy() )
		if not rmlib.AlmostEqual_v2( uvcoord, n_uvcoord ):
			return True
		
	return False
		

def shrink_face_loop( uvlayer, loops ):
	included_faces = set( [ l.face for l in loops ] )
	
	#shrink boundary loops first
	excluded_loops = set()
	for f in included_faces:
		for l in f.loops:
			if not l[uvlayer].select:
				continue
			if uv_border_edge( uvlayer, l ):
				excluded_loops.add( l )
	if len( excluded_loops ) > 0:
		for e_l in excluded_loops:
			e_l[uvlayer].select = False
			e_l[uvlayer].select_edge = False
			e_l.link_loop_next[uvlayer].select = False
			e_l.link_loop_next[uvlayer].select_edge = False
		excluded_faces = set( [ l.face for l in excluded_loops ] )
		for f in excluded_faces:
			for l in f.loops:
				l[uvlayer].select_edge = False
		for l in loops:
			if not l[uvlayer].select:
				continue
			uvcoord = mathutils.Vector( l[uvlayer].uv.copy() )
			for n_l in l.vert.link_loops:
				n_uvcoord = mathutils.Vector( n_l[uvlayer].uv.copy() )
				if rmlib.AlmostEqual_v2( uvcoord, n_uvcoord ):
					n_l[uvlayer].select = True
		return
		
	fully_selected_faces = set()
	for f in included_faces:
		count = 0
		for l in f.loops:
			if l[uvlayer].select:
				count += 1
		if count == len( f.loops ):
			fully_selected_faces.add( f )
			
	if len( fully_selected_faces ) == len( included_faces ):
		#shrink to next sequence of loops
		excluded_faces = set()
		for l in loops:
			uvcoord = mathutils.Vector( l[uvlayer].uv )
			deselect = False
			deselect_loops = set()
			for n_l in l.vert.link_loops:
				n_uvcoord = mathutils.Vector( n_l[uvlayer].uv )
				if rmlib.AlmostEqual_v2( uvcoord, n_uvcoord ):
					deselect_loops.add( n_l )
					if not n_l[uvlayer].select:
						deselect = True
			if deselect:
				excluded_faces.add( l.face )
				for d_l in deselect_loops:
					d_l[uvlayer].select = False	
		for f in excluded_faces:
			for l in f.loops:
				l[uvlayer].select_edge = False		
	else:
		#shrink to only fully_selected_faces
		for l in loops:
				l[uvlayer].select = False
				l[uvlayer].select_edge = False
		for f in fully_selected_faces:
			for l in f.loops:
				l[uvlayer].select = True
				l[uvlayer].select_edge = True
				
				
def grow_face_loop( uvlayer, loops ):
	included_faces = set( [ l.face for l in loops ] )
	fully_selected_faces = set()
	for f in included_faces:
		count = 0
		for l in f.loops:
			if l[uvlayer].select:
				count += 1
		if count == len( f.loops ):
			fully_selected_faces.add( f )
			
	if len( fully_selected_faces ) == len( included_faces ):
		#get next sequence of loops
		for l in loops:
			uvcoord = mathutils.Vector( l[uvlayer].uv )
			for n_l in l.vert.link_loops:
				if n_l[uvlayer].select or l == n_l:
					continue
				n_uvcoord = mathutils.Vector( n_l[uvlayer].uv )
				if rmlib.AlmostEqual_v2( uvcoord, n_uvcoord ):
					n_l[uvlayer].select = True
	else:
		#fill loop selection
		for f in included_faces:
			for l in f.loops:
				l[uvlayer].select = True
				l[uvlayer].select_edge = True


class MESH_OT_uvgrowshrink( bpy.types.Operator ):
	"""Grow or shrink uv selection."""
	bl_idname = 'mesh.rm_uvgrowshrink'
	bl_label = 'Grow / Shrink'
	bl_options = { 'UNDO' }

	mode: bpy.props.EnumProperty(
		items=[ ( "GROW", "Grow", "", 1 ),
				( "SHRINK", "Shrink", "", 2 ) ],
		name="Mode",
		default="GROW"
	)

	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'IMAGE_EDITOR' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
				
		sel_sync = context.tool_settings.use_uv_select_sync	
		if sel_sync:
			if self.mode == 'GROW':
				bpy.ops.uv.select_more( type=sel_mode_uv )
			else:
				bpy.ops.uv.select_less( type=sel_mode_uv )
		else:
			sel_mode_uv = context.tool_settings.uv_select_mode		
			if self.mode == 'GROW':
				if sel_mode_uv == 'FACE':
					with rmmesh as rmmesh:
						rmmesh.readonly = True
						uvlayer = rmmesh.active_uv
						loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
						grow_face_loop( uvlayer, loop_selection )
				else:
					bpy.ops.uv.select_more( type=sel_mode_uv )
			else:
				if sel_mode_uv == 'FACE':
					with rmmesh as rmmesh:
						rmmesh.readonly = True
						uvlayer = rmmesh.active_uv
						loop_selection = rmlib.rmUVLoopSet.from_selection( rmmesh=rmmesh, uvlayer=uvlayer )
						shrink_face_loop( uvlayer, loop_selection )
				else:
					bpy.ops.uv.select_less( type=sel_mode_uv )

			return { 'FINISHED' }


def register():
	print( 'register :: {}'.format( MESH_OT_uvgrowshrink.bl_idname ) )
	bpy.utils.register_class( MESH_OT_uvgrowshrink )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_uvgrowshrink.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_uvgrowshrink )