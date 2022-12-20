import bpy, mathutils
import rmKit.rmlib as rmlib
import math
import numpy as np

def DoubleTriangleArea( p1, p2, p3 ):
	return ( p1[0] * p2[1] - p1[1] * p2[0] ) + ( p2[0] * p3[1] - p2[1] * p3[0] ) + ( p3[0] * p1[1] - p3[1] * p1[0] )

def GetPinnedIndexesFromBounds( coords ):
	min_idx = 0
	max_idx = 0
	min_pos = coords[0]
	max_pos = coords[0]
	for i, pos in enumerate( coords ):
		if pos[0] < min_pos[0] or pos[1] < min_pos[1] or pos[2] < min_pos[2]:
			min_pos = pos
			min_idx = i
		elif pos[0] > max_pos[0] or pos[1] > max_pos[1] or pos[2] > max_pos[2]:
			max_pos = pos
			max_idx = i
	return [ min_idx, max_idx ]


def clear_tags( rmmesh ):
	for f in rmmesh.bmesh.faces:
		for l in f.loops:
			l.tag = False
		f.tag = False
	for v in rmmesh.bmesh.verts:
		v.tag = False
		

class MESH_OT_uvrelax( bpy.types.Operator ):
	"""Relax Selected UVs"""
	bl_idname = 'mesh.rm_relax'
	bl_label = 'Relax'
	bl_options = { 'UNDO' }

	@classmethod
	def poll( cls, context ):
		return ( ( context.area.type == 'VIEW_3D' or context.area.type == 'IMAGE_EDITOR' ) and
				context.active_object is not None and
				context.active_object.type == 'MESH' and
				context.object.data.is_editmode and
				not context.tool_settings.use_uv_select_sync )

	def execute( self, context ):
		rmmesh = rmlib.rmMesh.GetActive( context )
		if rmmesh is None:
			return { 'CANCELLED' }
		
		with rmmesh as rmmesh:			
			uvlayer = rmmesh.active_uv

			selected_faces = rmlib.rmPolygonSet.from_selection( rmmesh )
			for group in selected_faces.group():
				clear_tags( rmmesh )

				#tag faces
				for f in group:
					f.tag = True

				#gather input 3dcoords, uvcoords, tri index mappings, and loops
				verts = []
				tris = []
				unique_3d_coords = []
				pinned_verts = set()
				pinned_indexes = []
				pinned_uv_coords = []
				for f in group:
					if not f.tag:
						continue

					face_verts = list( f.verts )
					count = len( face_verts )
					if count < 3:
						continue

					#first vert for all tris in face triangulation
					start_vidx = -1
					if face_verts[0].tag:
						start_vidx = verts.index( face_verts[0] )
					else:
						start_vidx = len( verts )
						verts.append( face_verts[0] )
						unique_3d_coords.append( mathutils.Vector( face_verts[0].co.copy() ) )
						if f.loops[0][uvlayer].pin_uv:
							pinned_indexes.append( start_vidx )
							pinned_uv_coords.append( mathutils.Vector( f.loops[0][uvlayer].uv.copy() ) )
							pinned_verts.add( face_verts[0] )
						face_verts[0].tag = True

					#generate tris for face
					for i in range( 2, count ):
						tris.append( start_vidx )
						for j in [ i-1, i ]:
							v = face_verts[j]
							if v.tag:
								vidx = verts.index( v )
								tris.append( vidx )
							else:
								vidx = len( verts )
								verts.append( v )
								unique_3d_coords.append( mathutils.Vector( v.co.copy() ) )
								tris.append( vidx )
								if f.loops[j][uvlayer].pin_uv:
									pinned_indexes.append( vidx )
									pinned_uv_coords.append( mathutils.Vector( f.loops[j][uvlayer].uv.copy() ) )
									pinned_verts.add( v )
								v.tag = True
						
				#gather indexes of pinned uv coordinates
				if len( pinned_indexes ) < 2:
					pinned_indexes = GetPinnedIndexesFromBounds( unique_3d_coords ) #get list of indexes of pinned verts
					for pidx in pinned_indexes:
						pinned_uv_coords.append( mathutils.Vector( verts[pidx].link_loops[0][uvlayer].uv ) )
						pinned_verts.add( verts[pidx] )
					
				#allocate memory for block matrices and pinned vert vector
				tcount = int( len( tris ) / 3 )
				pinned_vcount = len( pinned_indexes )
				vcount = len( verts ) - pinned_vcount
				Mr_f = np.zeros( ( tcount, vcount ) )
				Mi_f = np.zeros( ( tcount, vcount ) )
				Mr_p = np.zeros( ( tcount, pinned_vcount ) )
				Mi_p = np.zeros( ( tcount, pinned_vcount ) )
				b = np.zeros( ( pinned_vcount * 2 ) )
				
				#compute coefficients
				for i in range( tcount ):
					idx1 = tris[i*3]
					idx2 = tris[i*3+1]
					idx3 = tris[i*3+2]
					
					#project 3d tri to its own plane to get rid of z component
					tri3d = [ unique_3d_coords[idx1], unique_3d_coords[idx2], unique_3d_coords[idx3] ]
					edge_lengths = [ ( tri3d[n-1] - tri3d[n-2] ).length for n in range( 3 ) ]
					theta = math.acos( ( edge_lengths[1] * edge_lengths[1] + edge_lengths[2] * edge_lengths[2] - edge_lengths[0] * edge_lengths[0] ) / ( 2.0 * edge_lengths[1] * edge_lengths[2] ) )                
					proj_tri = []
					proj_tri.append( mathutils.Vector( ( 0.0, 0.0 ) ) )
					proj_tri.append( mathutils.Vector( ( edge_lengths[2], 0.0 ) ) )
					proj_tri.append( mathutils.Vector( ( edge_lengths[1] * math.cos( theta ), edge_lengths[1] * math.sin( theta )  ) ) )
					
					#compute projected tri area
					a = DoubleTriangleArea( proj_tri[0], proj_tri[1], proj_tri[2] )
							
					#compute tris as complex numbers     
					ws = []
					for j in range( 3 ):
						vec = proj_tri[j-1] - proj_tri[j-2]
						w = vec / math.sqrt( a )
						ws.append( w )
						
					#build A (free) and B (pinned) block matrices as well as pinned uv vector ( b )
					for j, vidx in enumerate( [ idx1, idx2, idx3 ] ):
						if vidx in pinned_indexes:
							pvidx = pinned_indexes.index( vidx )
							Mr_p[i][pvidx] = ws[j][0]
							Mi_p[i][pvidx] = ws[j][1]
							
							b[pvidx] = pinned_uv_coords[pvidx][0]
							b[pvidx+pinned_vcount] = pinned_uv_coords[pvidx][1]
						else:
							#adjust for pinned vert indexes
							count = 0
							for pidx in pinned_indexes:
								if vidx > pidx:
									count += 1
							Mr_f[i][vidx-count] = ws[j][0]
							Mi_f[i][vidx-count] = ws[j][1]
							
				A = np.block( [
					[ Mr_f, Mi_f * -1.0 ],
					[ Mi_f, Mr_f ] ] )
					
				B = np.block( [
					[ Mr_p, Mi_p * -1.0 ],
					[ Mi_p, Mr_p ] ] )
					
				#compute r = -(B * b)
				r = B @ b
				r = r * -1.0
				
				#solve for x inf Ax=b
				x = np.linalg.lstsq( A, r, rcond=None )[0]

				#assign new uv values
				for vidx, v in enumerate( verts ):
					count = 0
					for pidx in pinned_indexes:
						if vidx > pidx:
							count += 1
					if vidx in pinned_indexes:
						continue
					for l in verts[vidx].link_loops:
						if not l.face.tag:
							continue
						l[uvlayer].uv = mathutils.Vector( ( x[vidx-count], x[(vidx-count+vcount)] ) )
			
			clear_tags( rmmesh )

		return { 'FINISHED' }


def register():
	bpy.utils.register_class( MESH_OT_uvrelax )


def unregister():
	bpy.utils.unregister_class( MESH_OT_uvrelax )


register()