import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

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
	"""This is the tooltip for custom operator"""
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
	"""This is the tooltip for custom operator"""
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


class MESH_OT_applyall( bpy.types.Operator ):
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
		bpy.ops.mesh.rm_applyvnorms( selset='SELSET1' )
		bpy.ops.mesh.rm_applyvnorms( selset='SELSET2' )
		bpy.ops.mesh.rm_applyvnorms( selset='SELSET3' )
		return { 'FINISHED' }


def GetLoops( vert, face ):
	vlist = list( face.verts )
	idx = vlist.index( vert )

	
	
class MESH_OT_applyvnorms( bpy.types.Operator ):
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
	
	weighted: bpy.props.BoolProperty(
		name='Weighted Normals',
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

		bpy.ops.object.mode_set( mode='OBJECT', toggle=False )
		
		#use rmmesh interface to init vnorms
		vnorms = []
		rmmesh = rmlib.rmMesh.GetActive( context )
		with rmmesh as rmmesh:
			rmmesh.readonly = True
			
			#get selset layer
			str_layer = rmmesh.mesh.polygon_layers_string.get( CUSTOM_VNORM_LAYERNAME, None )
			if str_layer is None:
				bpy.ops.object.mode_set( mode='EDIT', toggle=False )
				return { 'CANCELLED' }
			
			#set smoothing on mesh object to make custom vnorms visible
			rmmesh.mesh.polygons.foreach_set( 'use_smooth', [False] * len( rmmesh.mesh.polygons ) )
			rmmesh.mesh.use_auto_smooth = True
			
			#load all existing vnorms
			rmmesh.mesh.calc_normals_split()
			vnorms = [ mathutils.Vector( loop.normal ) for loop in rmmesh.mesh.loops ]
				
			#store all pidxs and vertices for this selset
			vertices = set()
			selset_pidxs = set()
			for p in rmmesh.bmesh.faces:
				val = str_layer.data[p.index].value.decode( 'utf-8' ).strip()
				if self.selset in val:
					vertices |= set( p.verts )
					selset_pidxs.add( p.index )
			
			
			for v in vertices:
				#sort loops such that they wind around v in a clockwise order
				loops = []
				unsorted_loops = list( v.link_loops )
				unsorted_faces = list( v.link_faces )
				while len( unsorted_faces ) > 0:
					current_face = unsorted_faces.pop( 0 )

					while( current_face is not None ):
						for i in range( len( unsorted_loops ) ):
							if unsorted_loops[i].face == current_face:
								current_loop = unsorted_loops.pop( i )
								loops.append( current_loop )
								break
						
						prev_face = current_face
						current_face = None
						for f in current_loop.edge.link_faces:
							if f != prev_face:
								try:
									unsorted_faces.remove( f )
								except ValueError:
									try:
										loops.append( unsorted_loops[0] )
									except IndexError:
										break
								current_face = f
								break
				
				#get the index of the first loop with a sharp edge
				startIdx = 0
				lcount = len( loops )
				for i in range( lcount ):
					if not loops[i].edge.smooth:
						break
					startIdx += 1
					
				#compute the vnorm for this poly group.
				#a group is all polys that link a vert broken up by sharp edges
				loop_group = []
				last_loop_group = []
				for i in range( lcount ):
					idx = ( startIdx + i ) % lcount
					l = loops[idx]

					loop_group.append( l )

					if not l.edge.smooth:
						if i == 0:
							last_loop_group = [ l for l in loop_group ]
							loop_group.clear()
							continue

						nml = loopgroupnormal( loop_group, self.weighted, selset_pidxs )
						for l in loop_group:
							vnorms[l.index] = nml

						loop_group.clear()

				#store the computed normal into vnorms list
				last_loop_group += loop_group
				if len( last_loop_group ) > 0:
					nml = loopgroupnormal( last_loop_group, self.weighted, selset_pidxs )
					for l in last_loop_group:
						vnorms[l.index] = nml
					
		#since split normals can only be set through the old mesh interface which is pretty lame
		mesh = context.active_object.data
		mesh.normals_split_custom_set( vnorms )
		mesh.update()
		
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )
		
		return { 'FINISHED' }

def loopgroupnormal( loops, weighted, member_pidxs ):
	avg = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
	for l in loops:
		f = l.face
		if f.index not in member_pidxs:
			continue
		if weighted:
			avg += f.normal.copy() * f.area
		else:
			avg += f.normal.copy()
	return avg.normalized()


class VIEW3D_PT_VNORMS( bpy.types.Panel ):
	bl_parent_id = "VIEW3D_PT_LAYERS"
	bl_label = "VNormal Kit"
	bl_region_type = "UI"
	bl_space_type = "VIEW_3D"
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout

		box = layout.box()

		row_override = box.row()
		row_override.prop( context.scene, 'vn_selsetweighted', toggle=1 )
		row_override.alignment = 'LEFT'

		row_selset1 = box.row()
		row_selset1.operator( MESH_OT_selectvnormselset.bl_idname, text='SEL1' ).selset = 'SELSET1'
		op = row_selset1.operator( MESH_OT_setvnormselset.bl_idname, text='+' )
		op.selset = 'SELSET1'
		op.override = False
		op = row_selset1.operator( MESH_OT_setvnormselset.bl_idname, text='++' )
		op.selset = 'SELSET1'
		op.override = True
		row_selset1.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET1'
		row_selset1.operator( MESH_OT_applyvnorms.bl_idname, text='Apply' ).selset = 'SELSET1'

		row_selset2 = box.row()
		row_selset2.operator( MESH_OT_selectvnormselset.bl_idname, text='SEL2' ).selset = 'SELSET2'
		op = row_selset2.operator( MESH_OT_setvnormselset.bl_idname, text='+' )
		op.selset = 'SELSET2'
		op.override = False
		op = row_selset2.operator( MESH_OT_setvnormselset.bl_idname, text='++' )
		op.selset = 'SELSET2'
		op.override = True
		row_selset2.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET2'
		row_selset2.operator( MESH_OT_applyvnorms.bl_idname, text='Apply' ).selset = 'SELSET2'

		row_selset3 = box.row()
		row_selset3.operator( MESH_OT_selectvnormselset.bl_idname, text='SEL3' ).selset = 'SELSET3'
		op = row_selset3.operator( MESH_OT_setvnormselset.bl_idname, text='+' )
		op.selset = 'SELSET3'
		op.override = False
		op = row_selset3.operator( MESH_OT_setvnormselset.bl_idname, text='++' )
		op.selset = 'SELSET3'
		op.override = True
		row_selset3.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET3'
		row_selset3.operator( MESH_OT_applyvnorms.bl_idname, text='Apply' ).selset = 'SELSET3'

		row_applyall = box.row()
		row_applyall.operator( MESH_OT_applyall.bl_idname, text='ALL' )
		row_applyall.alignment = 'EXPAND'
	
	
def register():
	print( 'register :: {}'.format( MESH_OT_setvnormselset.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_removevnormselset.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_selectvnormselset.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_applyvnorms.bl_idname ) )
	print( 'register :: {}'.format( MESH_OT_applyall.bl_idname ) )
	bpy.utils.register_class( MESH_OT_setvnormselset )
	bpy.utils.register_class( MESH_OT_removevnormselset )
	bpy.utils.register_class( MESH_OT_selectvnormselset )
	bpy.utils.register_class( MESH_OT_applyvnorms )
	bpy.utils.register_class( MESH_OT_applyall )
	bpy.types.Scene.vn_selsetweighted = bpy.props.BoolProperty(
		name="Area Weights",
		default=False
	)
	bpy.utils.register_class( VIEW3D_PT_VNORMS )
	

def unregister():
	print( 'unregister :: {}'.format( MESH_OT_setvnormselset.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_removevnormselset.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_selectvnormselset.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_applyvnorms.bl_idname ) )
	print( 'unregister :: {}'.format( MESH_OT_applyall.bl_idname ) )
	bpy.utils.unregister_class( MESH_OT_setvnormselset )
	bpy.utils.unregister_class( MESH_OT_removevnormselset )
	bpy.utils.unregister_class( MESH_OT_selectvnormselset )
	bpy.utils.unregister_class( MESH_OT_applyvnorms )
	bpy.utils.unregister_class( MESH_OT_applyall )
	del bpy.types.Scene.vn_selsetweighted
	bpy.utils.unregister_class( VIEW3D_PT_VNORMS )