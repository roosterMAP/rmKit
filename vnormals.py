import bpy, bmesh, mathutils
from bpy.app.handlers import persistent
import rmlib

CUSTOM_VNORM_LAYERNAME = 'rm_vnorm'

def AddSelSet( polys, selset, value ):
	for p in polys:
		current_value = p[selset].decode( 'utf-8' ).strip()
		contained_selsets = current_value.split( ';' )
		if value in contained_selsets:
			continue
		contained_selsets.append( value )
		new_value = ''
		for ss in contained_selsets:
			if ss == '':
				continue
			new_value += ss + ';'
		p[selset] = bytes( new_value, 'utf-8' )
		
def RemoveSelSet( polys, selset, value ):
	for p in polys:
		current_value = p[selset].decode( 'utf-8' ).strip()
		contained_selsets = current_value.split( ';' )
		if value not in contained_selsets:
			continue
		new_value = ''
		for ss in contained_selsets:
			if ss == '' or ss == value:
				continue
			new_value += ss + ';'
		if value in current_value:
			p[selset] = bytes( new_value, 'utf-8' )
		
def ClearSelSet( polys, selset ):
	for p in polys:
		p[selset] = bytes( '', 'utf-8' )
		
def GetPolysBySelSet( bm, selset, value ):
	value += ';'
	member_polys = rmlib.rmPolygonSet()
	for p in bm.faces:
		current_value = p[selset].decode( 'utf-8' ).strip()
		if value in current_value:
			member_polys.append( p )
	return member_polys
	

class MESH_OT_setvnormselset( bpy.types.Operator ):    
	"""Add face to selection set."""
	bl_idname = 'mesh.rm_setvnorm'
	bl_label = 'Set VNorm Selection Set'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	selset: bpy.props.EnumProperty(
		items=[ ( "SELSET1", "SETSET1", "", 1 ),
				( "SELSET2", "SELSET2", "", 2 ),
				( "SELSET3", "SELSET3", "", 3 ),
				( "CLEAR", "CLEAR", "", 4 ) ],
		name="Selection Set",
		default="CLEAR"
	)

	override: bpy.props.BoolProperty(
		name="Override",
		default=False
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:

			strlayers = rmmesh.bmesh.faces.layers.string
			selset = strlayers.get( CUSTOM_VNORM_LAYERNAME, None )
			if selset is None:
				selset = strlayers.new( CUSTOM_VNORM_LAYERNAME )
			rmmesh.bmesh.faces.ensure_lookup_table()

			if self.override:
				overridden_polys = rmlib.rmPolygonSet.from_mesh( rmmesh, filter_hidden=True )
				RemoveSelSet( overridden_polys, selset, self.selset )
			
			polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				
			if self.selset == 'CLEAR':
				ClearSelSet( polys, selset )
			else:
				AddSelSet( polys, selset, self.selset )
			
		return { 'FINISHED' }
	
	
class MESH_OT_removevnormselset( bpy.types.Operator ):    
	"""Remove face from selection set."""
	bl_idname = 'mesh.rm_removevnorm'
	bl_label = 'Remove VNorm Selection Set'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	selset: bpy.props.EnumProperty(
		items=[ ( "SELSET1", "SETSET1", "", 1 ),
				( "SELSET2", "SELSET2", "", 2 ),
				( "SELSET3", "SELSET3", "", 3 ) ],
		name="Selection Set",
		default="SELSET1"
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			strlayers = rmmesh.bmesh.faces.layers.string
			selset = strlayers.get( CUSTOM_VNORM_LAYERNAME, None )
			if selset is None:
				selset = strlayers.new( CUSTOM_VNORM_LAYERNAME )
			rmmesh.bmesh.faces.ensure_lookup_table()

			polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				
			RemoveSelSet( polys, selset, self.selset )
			
		return { 'FINISHED' }
	
	
class MESH_OT_selectvnormselset( bpy.types.Operator ):
	"""Select faces based on face membership to this selection sets."""
	bl_idname = 'mesh.rm_selectvnormselset'
	bl_label = 'Select VNorm Selection Set'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	selset: bpy.props.EnumProperty(
		items=[ ( "SELSET1", "SETSET1", "", 1 ),
				( "SELSET2", "SELSET2", "", 2 ),
				( "SELSET3", "SELSET3", "", 3 ) ],
		name="Selection Set",
		default="SELSET1"
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		if context.object is None or context.mode == 'OBJECT':
			return { 'CANCELLED' }
		
		if context.object.type != 'MESH':
			return { 'CANCELLED' }

		sel_mode = context.tool_settings.mesh_select_mode[:]
		if not sel_mode[2]:
			return { 'CANCELLED' }

		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			for f in rmmesh.bmesh.faces:
				f.select = False

			strlayers = rmmesh.bmesh.faces.layers.string
			selset = strlayers.get( CUSTOM_VNORM_LAYERNAME, None )
			if selset is None:
				selset = strlayers.new( CUSTOM_VNORM_LAYERNAME )
			rmmesh.bmesh.faces.ensure_lookup_table()
				
			polys = GetPolysBySelSet( rmmesh.bmesh, selset, self.selset )
			for p in polys:
				p.select = True
			
		return { 'FINISHED' }


def GetSortedLoops( vert ):
	vert_loops = list( vert.link_loops )
	for l in vert_loops:
		l.tag = False

	sorted_loops = []
	while len( vert_loops ) > 0:
		start_idx = 0
		for i, l in enumerate( vert_loops ):
			if l.edge.is_boundary or not l.edge.smooth:
				start_idx = i
				break

		start_loop = vert_loops[start_idx]
		sorted_group = [ start_loop ]
		start_loop.tag = True

		next_loop = start_loop
		while( next_loop is not None ):
			l = sorted_group[-1]
			n_l = l.link_loop_prev
			if n_l.edge.is_boundary or not n_l.edge.smooth:
				break
			next_loop = None
			for f in n_l.edge.link_faces:
				if f == l.face:
					continue
				for face_loop in f.loops:
					if face_loop.edge == n_l.edge and not face_loop.tag:
						next_loop = face_loop
						next_loop.tag = True
						sorted_group.append( next_loop )
						break

		sorted_loops += sorted_group

		for l in sorted_group:
			vert_loops.remove( l )

	for l in vert.link_loops:
		l.tag = False

	return sorted_loops

def ApplyVNorms( context, selset ):
	if context.object is None or context.mode == 'OBJECT':
		return { 'CANCELLED' }
	
	if context.object.type != 'MESH':
		return { 'CANCELLED' }

	bpy.ops.object.mode_set( mode='OBJECT', toggle=False )

	weighted = context.scene.rmkit_props.vn_selsetweighted
	
	#use rmmesh interface to init vnorms
	vnorms = []
	rmmesh = rmlib.rmMesh.GetActive( context )
	with rmmesh as rmmesh:
		rmmesh.readonly = True
		
		#get selset layer
		str_layer = rmmesh.bmesh.faces.layers.string.get( CUSTOM_VNORM_LAYERNAME, None )
		if str_layer is not None:
			#set smoothing on mesh object to make custom vnorms visible
			if bpy.app.version < (4,0,0):
				rmmesh.mesh.use_auto_smooth = True
				rmmesh.mesh.create_normals_split()
			
			vnorms = [ mathutils.Vector( loop.normal ) for loop in rmmesh.mesh.loops ]
				
			#store all pidxs and vertices for this selset
			vertices = set()
			selset_pidxs = set()

			for p in GetPolysBySelSet( rmmesh.bmesh, str_layer, selset ):
				vertices |= set( p.verts )
				selset_pidxs.add( p.index )
			
			for v in vertices:					
				#compute the vnorm for this poly group. a group is all polys that link a vert broken up by sharp edges
				loop_group = []
				for loop in GetSortedLoops( v ):
					if not loop.edge.smooth or loop.edge.is_boundary :
						nml = loopgroupnormal( loop_group, weighted, selset_pidxs )
						if nml.length > 0.0:
							for l in loop_group:
								vnorms[l.index] = nml							
						loop_group.clear()

					loop_group.append( loop )
					
				if len( loop_group ) > 0:
					nml = loopgroupnormal( loop_group, weighted, selset_pidxs )
					if nml.length > 0.0:
						for l in loop_group:
							vnorms[l.index] = nml

	if len( vnorms ) > 0:
		mesh = context.active_object.data
		mesh.normals_split_custom_set( vnorms )
		mesh.update()
	
	bpy.ops.object.mode_set( mode='EDIT', toggle=False )

	return { 'FINISHED' }
	
class MESH_OT_applyvnorms( bpy.types.Operator ):
	"""Generated Split Normals based on face membership to this selection set."""
	bl_idname = 'mesh.rm_applyvnorms'
	bl_label = 'Apply VNorms'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	selset: bpy.props.EnumProperty(
		items=[ ( "SELSET1", "SETSET1", "", 1 ),
				( "SELSET2", "SELSET2", "", 2 ),
				( "SELSET3", "SELSET3", "", 3 ) ],
		name="Selection Set",
		default="SELSET1"
	)
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		return ApplyVNorms( context, self.selset )
	
class MESH_OT_applyall( bpy.types.Operator ):
	"""Generated Split Normals based on face membership to all selection sets."""
	bl_idname = 'mesh.rm_applyall'
	bl_label = 'Apply All'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		ApplyVNorms( context, 'SELSET1' )
		ApplyVNorms( context, 'SELSET2' )
		ApplyVNorms( context, 'SELSET3' )
		return { 'FINISHED' }
	
def FaceSurfaceArea( f ):
	area = 0.0
	verts = f.verts
	if len(verts) < 3:
		return area

	# Calculate the area using the shoelace formula for polygons
	for i in range(len(verts)):
		v1 = verts[i].co
		v2 = verts[(i + 1) % len(verts)].co
		area += v1.cross(v2).length / 2.0

	return area

def loopgroupnormal( loops, weighted, member_pidxs ):
	avg = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	for l in loops:
		f = l.face
		if f.index not in member_pidxs:
			continue
		if weighted:
			avg += f.normal.copy() * FaceSurfaceArea( f )
		else:
			avg += f.normal.copy()
	return avg.normalized()

def redraw_view3d( context ):
	for window in context.window_manager.windows:
		for area in window.screen.areas:
			if area.type == 'VIEW_3D':
				for region in area.regions:
					if region.type == 'UI':
						region.tag_redraw()


class VIEW3D_PT_VNORMS( bpy.types.Panel ):
	bl_parent_id = "VIEW3D_PT_LAYERS"
	bl_label = "VNormal Kit"
	bl_region_type = "UI"
	bl_space_type = "VIEW_3D"
	bl_options = set()

	def draw( self, context ):
		layout = self.layout
		box = layout.box()

		row_override = box.row()
		row_override.prop( context.scene.rmkit_props, 'vn_selsetweighted', toggle=1 )
		row_override.alignment = 'LEFT'

		row_selset1 = box.row()
		row_selset1.operator( MESH_OT_selectvnormselset.bl_idname, text='SEL1' ).selset = 'SELSET1'


		op = row_selset1.operator( MESH_OT_setvnormselset.bl_idname, text='++' )
		op.selset = 'SELSET1'
		op.override = True
		
		op = row_selset1.operator( MESH_OT_setvnormselset.bl_idname, text='+' )
		op.selset = 'SELSET1'
		op.override = False

		row_selset1.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET1'

		row_selset2 = box.row()
		row_selset2.operator( MESH_OT_selectvnormselset.bl_idname, text='SEL2' ).selset = 'SELSET2'
		
		op = row_selset2.operator( MESH_OT_setvnormselset.bl_idname, text='++' )
		op.selset = 'SELSET2'
		op.override = True
		
		op = row_selset2.operator( MESH_OT_setvnormselset.bl_idname, text='+' )
		op.selset = 'SELSET2'
		op.override = False

		row_selset2.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET2'

		row_selset3 = box.row()
		row_selset3.operator( MESH_OT_selectvnormselset.bl_idname, text='SEL3' ).selset = 'SELSET3'
		
		op = row_selset3.operator( MESH_OT_setvnormselset.bl_idname, text='++' )
		op.selset = 'SELSET3'
		op.override = True
		
		op = row_selset3.operator( MESH_OT_setvnormselset.bl_idname, text='+' )
		op.selset = 'SELSET3'
		op.override = False

		row_selset3.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET3'

		row_applyall = box.row()
		row_applyall.operator( MESH_OT_applyall.bl_idname, text='APPLY' )
		row_applyall.alignment = 'EXPAND'
	
	
def register():
	bpy.utils.register_class( MESH_OT_setvnormselset )
	bpy.utils.register_class( MESH_OT_removevnormselset )
	bpy.utils.register_class( MESH_OT_selectvnormselset )
	bpy.utils.register_class( MESH_OT_applyvnorms )
	bpy.utils.register_class( MESH_OT_applyall )
	bpy.utils.register_class( VIEW3D_PT_VNORMS )
	

def unregister():
	bpy.utils.unregister_class( MESH_OT_setvnormselset )
	bpy.utils.unregister_class( MESH_OT_removevnormselset )
	bpy.utils.unregister_class( MESH_OT_selectvnormselset )
	bpy.utils.unregister_class( MESH_OT_applyvnorms )
	bpy.utils.unregister_class( MESH_OT_applyall )
	bpy.utils.unregister_class( VIEW3D_PT_VNORMS )