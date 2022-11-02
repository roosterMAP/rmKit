import bpy, bmesh, mathutils
import rmKit.rmlib as rmlib

CUSTOM_VNORM_LAYERNAME = 'rm_vnorm'

def AddSelSet( bm, polys, layername, value ):
	strlayers = bm.faces.layers.string
	selset = strlayers.get( layername, None )
	if selset is None:
		selset = strlayers.new( layername )
	for p in polys:
		current_value = p[selset].decode( 'utf-8' ).strip()
		value += ';'
		if value not in current_value:
			strlist = current_value.split( ';' )
			for s in strlist:
				if s == '':
					continue
				value += s + ';'
		p[selset] = bytes( value, 'utf-8' )
		
def RemoveSelSet( bm, polys, layername, value ):
	strlayers = bm.faces.layers.string
	selset = strlayers.get( layername, None )
	if selset is None:
		selset = strlayers.new( layername )
	for p in polys:
		current_value = p[selset].decode( 'utf-8' ).strip()
		value += ';'
		if value in current_value:
			p[selset] = bytes( current_value.replace( value, '' ), 'utf-8' )
		
def ClearSelSet( bm, polys, layername ):
	strlayers = bm.faces.layers.string
	selset = strlayers.get( layername, None )
	if selset is None:
		selset = strlayers.new( layername )
	for p in polys:
		p[selset] = bytes( '', 'utf-8' )
		
def GetSelSetValues( bm, polys, layername ):
	strlayers = bm.faces.layers.string
	selset = strlayers.get( layername, None )
	if selset is None:
		selset = strlayers.new( layername )
	for p in polys:
		current_value = p[selset].decode( 'utf-8' ).strip()
		if ';' in current_value:
			return current_value.split( ';' )
		
def GetPolysBySelSet( bm, layername, value ):
	strlayers = bm.faces.layers.string
	selset = strlayers.get( layername, None )
	if selset is None:
		selset = strlayers.new( layername )
	value += ';'
	member_polys = rmlib.rmPolygonSet()
	for p in bm.faces:
		current_value = p[selset].decode( 'utf-8' ).strip()
		if value in current_value:
			member_polys.append( value )
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

	def __init__( self ):
		self.override = False
	
	@classmethod
	def poll( cls, context ):
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )

	def invoke( self, event, context ):
		self.override = event.ctrl
		return { 'FINISHED' }
		
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
			if self.override:
				polys = rmlib.rmPolygonSet.from_mesh( rmmesh, filter_hidden=True )
			else:
				polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				
			if self.selset == 'CLEAR':
				ClearSelSet( rmmesh.bm, polys, CUSTOM_VNORM_LAYERNAME )
			else:
				AddSelSet( rmmesh.bm, polys, CUSTOM_VNORM_LAYERNAME, self.selset )
			
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
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
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
			polys = rmlib.rmPolygonSet.from_selection( rmmesh )
				
			RemoveSelSet( rmmesh.bm, polys, CUSTOM_VNORM_LAYERNAME, self.selset )
			
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
		#used by blender to test if operator can show up in a menu or as a button in the UI
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
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
				
			polys = GetPolysBySelSet( rmmesh.bm, CUSTOM_VNORM_LAYERNAME, self.selset )
			for p in polys:
				p.selet = True
			
		return { 'FINISHED' }


class MESH_OT_applyall( bpy.types.Operator ):
	bl_idname = 'mesh.rm_applyall'
	bl_label = 'Apply All'
	bl_options = { 'UNDO' } #tell blender that we support the undo/redo pannel
	
	@classmethod
	def poll( cls, context ):
		return ( context.area.type == 'VIEW_3D' and
				context.object is not None and
				context.object.type == 'MESH' and
				context.object.data.is_editmode )
		
	def execute( self, context ):
		bpy.ops.mesh.rm_applyvnorms( selset='SELSET1' )
		bpy.ops.mesh.rm_applyvnorms( selset='SELSET2' )
		bpy.ops.mesh.rm_applyvnorms( selset='SELSET3' )
		return { 'FINISHED' }
	
	
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
				context.object is not None and
				context.object.type == 'MESH' and
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
			
			str_layer = rmmesh.mesh.polygon_layers_string.get( CUSTOM_VNORM_LAYERNAME, None )
			if str_layer is None:
				bpy.ops.object.mode_set( mode='EDIT', toggle=False )
				return { 'CANCELLED' }
			
			rmmesh.mesh.polygons.foreach_set( 'use_smooth', [False] * len( rmmesh.mesh.polygons ) )
			rmmesh.mesh.use_auto_smooth = True
			
			for l in rmmesh.mesh.loops:
				vnorms.append( mathutils.Vector( l.normal ) )
			
			vertices = set()
			selset_pidxs = set()
			for p in rmmesh.bmesh.faces:
				val = str_layer.data[p.index].value.decode( 'utf-8' ).strip()
				if self.selset in val:
					vertices |= set( p.verts )
					selset_pidxs.add( p.index )
			
			for v in vertices:
				loops = v.link_loops
				faces = v.link_faces
				
				#get the index of the first loop with a sharp edge
				startIdx = 0
				lcount = len( loops )			
				for i in range( lcount ):
					e = loops[startIdx].edge
					if not e.smooth:
						break
					startIdx += 1		
					
				loop_group = []
				current_normal = mathutils.Vector( ( 0.0, 0.0, 0.0 ) )
				for i in range( lcount ):
					idx = ( startIdx + i ) % lcount
					loop_group.append( loops[idx] )		
					e = loops[idx].edge	
								
					p = v.link_faces[idx]
					if p.index in selset_pidxs:
						nml = p.normal.copy()
						if self.weighted:
							nml *= p.area
						current_normal += nml
									
					if i > 0 and not e.smooth:
						for l in loop_group:
							vnorms[l.index] = current_normal.normalized()
						current_normal = mathutils.Vector( 0.0, 0.0, 0.0 )
						loop_group.clear()
						continue

				if len( loop_group ) > 0:
					for l in loop_group:
						vnorms[l.index] = current_normal.normalized()
					
		#since split normals can only be set through mesh interface...	
		mesh = context.active_object.data
		mesh.normals_split_custom_set( vnorms )
		mesh.update()
		
		bpy.ops.object.mode_set( mode='EDIT', toggle=False )
		
		return { 'FINISHED' }


class VIEW3D_PT_VNORMS( bpy.types.Panel ):
	bl_parent_id = "VIEW3D_PT_RMKIT_PARENT"
	bl_label = "VNormal Kit"
	bl_region_type = "UI"
	bl_space_type = "VIEW_3D"
	bl_options = {'DEFAULT_CLOSED'}

	def draw( self, context ):
		layout = self.layout

		box = layout.box()

		row_selset1 = box.row()
		row_selset1.operator( MESH_OT_selectvnormselset.bl_idname, text='SELSET1' ).selset = 'SELSET1'
		row_selset1.operator( MESH_OT_setvnormselset.bl_idname, text='+' ).selset = 'SELSET1'
		row_selset1.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET1'
		row_selset1.operator( MESH_OT_applyvnorms.bl_idname, text='Apply' ).selset = 'SELSET1'

		row_selset2 = box.row()
		row_selset2.operator( MESH_OT_selectvnormselset.bl_idname, text='SELSET2' ).selset = 'SELSET2'
		row_selset2.operator( MESH_OT_setvnormselset.bl_idname, text='+' ).selset = 'SELSET2'
		row_selset2.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET2'
		row_selset2.operator( MESH_OT_applyvnorms.bl_idname, text='Apply' ).selset = 'SELSET2'

		row_selset3 = box.row()
		row_selset3.operator( MESH_OT_selectvnormselset.bl_idname, text='SELSET3' ).selset = 'SELSET3'
		row_selset3.operator( MESH_OT_setvnormselset.bl_idname, text='+' ).selset = 'SELSET3'
		row_selset3.operator( MESH_OT_removevnormselset.bl_idname, text='-' ).selset = 'SELSET3'
		row_selset3.operator( MESH_OT_applyvnorms.bl_idname, text='Apply' ).selset = 'SELSET3'

		row_applyall = box.row()
		row_applyall.operator( MESH_OT_applyall.bl_idname, text='ALL' )
		row_applyall.alignment = 'RIGHT'
	
	
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
	bpy.types.Scene.vn_selset1enum = bpy.props.EnumProperty(
		items=[ ( "SELSET1", "SETSET1", "", 1 ),
				( "SELSET2", "SELSET2", "", 2 ),
				( "SELSET3", "SELSET3", "", 3 ) ],
		name="Selection Set",
		default="SELSET1"
	)
	bpy.types.Scene.vn_selset2enum = bpy.props.EnumProperty(
		items=[ ( "SELSET1", "SETSET1", "", 1 ),
				( "SELSET2", "SELSET2", "", 2 ),
				( "SELSET3", "SELSET3", "", 3 ) ],
		name="Selection Set",
		default="SELSET2"
	)
	bpy.types.Scene.vn_selset3enum = bpy.props.EnumProperty(
		items=[ ( "SELSET1", "SETSET1", "", 1 ),
				( "SELSET2", "SELSET2", "", 2 ),
				( "SELSET3", "SELSET3", "", 3 ) ],
		name="Selection Set",
		default="SELSET3"
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
	del bpy.types.Scene.vn_selset1enum
	del bpy.types.Scene.vn_selset2enum
	del bpy.types.Scene.vn_selset3enum
	bpy.utils.unregister_class( VIEW3D_PT_VNORMS )


if __name__ == '__main__':
	register()