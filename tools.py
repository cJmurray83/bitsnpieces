import Part, FreeCAD, FreeCADGui
from operator import itemgetter
from math import sin, cos, pi

class functions:
	''' 
	This is a selection of static functions used by the commands and parametric objects
	'''
	@staticmethod
	def getEdges():
		'''
		Returns a list of all the edge objects in the document
		'''
		doc = FreeCAD.ActiveDocument
		objects = doc.Objects
		edgeList=[]	
		if objects:
			try:
				for n in objects:
					if n.getPropertyByName("ShapeType") == "Edge":
						edgeList.append(n)
				return	edgeList		
			except:
				return False	
		else:
			return False

	@staticmethod
	def getSnapPoints():
		'''
		Returns a list of all the snap points from all the edge objects in the document
		'''
		edges = functions.getEdges()
		snapPointList = []
		if edges:
			for edge in edges:
				for point in edge.SnapPoints:
					snapPointList.append(point)
		return snapPointList	
		
	@staticmethod
	def getSnapLines():
		'''
		Returns a list of all the snap lines of each edge object in the document
		return[basePoint as Vector, direction as Vector, length as None]
		'''
		edges = functions.getEdges()
		snapLines = []
		if edges:
			for edge in edges:
				for n in range(len(edge.SnapLinesIndex)):
					index = edge.SnapLinesIndex[n]
					basePoint = edge.SnapPoints[index]
					direction = edge.SnapDirections[n]
					entry = [basePoint,direction,None]
					snapLines.append(entry)
		return snapLines

	
	@staticmethod
	def snapPoint(view, pos, snapPoints, pixelRange = 4):
		'''
		Returns nearby snap points
		input [view as Gui.ActiveView, position as (x as Integer,y as Integer), snapPoints as snapPoints, pixelRange as Integer]
		return [closestPoint as Vector, snapped as True/False]
		'''
		range = pixelRange * functions.getPixelLen(view) #get range on view plane assosiated with pixel range
		snapLengths = []
		cursorPoint = view.getPoint(pos[0],pos[1]) #get the current cursor point
		if snapPoints: #this block calculates the lenghs between all the snap points and the cursor point, and returns the closest one if within snap range
			for n in snapPoints:
				line = cursorPoint.sub(n)
				lineLength = line.Length
				snapLengths.append(lineLength)
			closestLength = min(snapLengths)
			index = snapLengths.index(closestLength)
			closestPoint = snapPoints[index]	
			if closestLength <= range:
				return closestPoint, True 
			else:
				return cursorPoint, False	
		else:
			return cursorPoint, False
			
	@staticmethod
	def snapLine(view, pos, snapLines, pixelRange = 4, lockLine=False):
		'''
		Returns nearby snap point, snap line(s) and direction from snap point to cursor point
		input [view as Gui.ActiveView, position as (x,y) Integer, snapLines as snapLines, pixelRange as Integer, lockLine as (base as Vector, direction as Vector)]
		return [closestPoint as Vector, snapped as True/False, closestLine1 as (base as Vector, direction as Vector) or False, closestLine2 as (base as Vector, direction as Vector) or False, dir as Vector or False]
		'''	
		#some hardcode to be integrated
		zValue = 0.0 #since line intersection calculations are done in 2D we must choose a z value
		angleLow = 0.087 #radians, if the angle between the two closest lines is within this range it will allow snap to the intersection
		angleHigh = 3.054
		modifier = 2 #divisor that reduces the snap length for line intersections	
		fidelity = 0.000001
		
		viewRange = pixelRange * functions.getPixelLen(view) #get range on view plane assosiated with pixel range	
		cursorPoint = view.getPoint(pos[0],pos[1]) #get the current cursor point from the pixel coodinates of the mouse
		activePoint = cursorPoint
		if lockLine: #constrains cursor point to lockline if it exists
			perp = FreeCAD.Vector(lockLine[1].y, -lockLine[1].x, lockLine[1].z) 
			activePoint =  functions.vector_intersection(lockLine[0],lockLine[1],cursorPoint,perp,zValue) #calculate intersection between two 	
		if snapLines:	
			for n in range(len(snapLines)):# fill out the lengths to each line from the cursor point
				basePoint = snapLines[n][0]
				direction = snapLines[n][1]
				length = activePoint.distanceToLine(basePoint,direction)
				snapLines[n][2] = length
			minToMax = sorted(snapLines, key=itemgetter(2))	#sort the list from shortest length to largest	
		else:
			minToMax = []		
		if lockLine: #makes lockLine the first constrained line
			minToMax.append(lockLine)		
		snapCount = len(minToMax)
		if snapCount >= 2:
			same = True	
			while same: #this block filters out the first entry if the closest two lines are coincident, it continues untill the first two are not coincident.
				dir1 = minToMax[0][1]
				dir2 = minToMax[1][1]
				dir3 = minToMax[0][0].sub(minToMax[1][0])
				if dir3 != FreeCAD.Vector(0,0,0):
					dir3.normalize()
				if dir3 == FreeCAD.Vector(0,0,0) or dir2 == dir3 or dir2 == dir3.scale(-1,-1,0):
					if dir1 == dir2 or dir1 == dir2.scale(-1,-1,0):
						minToMax.pop(1) #removes second value to preserve lockline value if it exists
					else:
						same = False
				else:
					same = False	
			angle =minToMax[0][1].getAngle(minToMax[1][1])	#check angle between two closest lines, if angle is too small, intersecting snap point will not be established			
		snapCount = len(minToMax)
		if snapCount >=  1:
			if minToMax[0][2] <= viewRange/modifier: #this block checks if the closest two lines is are in the snap range, and sets the asosiated snap point and line(s)
				diff = FreeCAD.Vector() 
				diff.projectToLine(activePoint-minToMax[0][0],minToMax[0][1])
				point = activePoint + diff  #these three lines calculate projected point (between cursor and snap line)
				snapped = True
				closestLine1 = [minToMax[0][0],minToMax[0][1]]	
				closestLine2 = False
				dir = cursorPoint.sub(point)
				if dir.Length > fidelity:
					dir.normalize()				
				if snapCount >= 2:
					if minToMax[1][2] <= viewRange/modifier and angleLow < angle < angleHigh: #check second closest line, and make sure angle is ok
						point = functions.vector_intersection(minToMax[0][0] ,minToMax[0][1],minToMax[1][0] ,minToMax[1][1],zValue) #calculate intersection between two points
						closestLine2 =  [minToMax[1][0],minToMax[1][1]]		
			else: #if there are no snap lines within the snap range, just output the cursor point
				point = activePoint
				snapped = False
				closestLine1 = False	
				closestLine2 = False
				dir = False
		else:
			point = activePoint
			snapped = False
			closestLine1 = False	
			closestLine2 = False
			dir = False
		return point, snapped, closestLine1, closestLine2, dir
	
	@staticmethod
	def getPixelLen(view):
		'''
		Returns the length of one pixel in the current view
		input[view as Gui.View]
		return[pixelLen as Float]
		'''
		pos1 = view.getPoint(0,0)
		pos2 = view.getPoint(10,0)	
		pixelLen = abs((pos2.x - pos1.x)/10)
		return pixelLen
	
	@staticmethod
	def edgeSelection(toggle):
		'''
		Toggles selection of all edge objects on and off
		input[toggle as True/False]
		'''
		edges = functions.getEdges()
		if edges:
			for n in edges:
				n.ViewObject.Selectable = toggle
				
	@staticmethod	
	def vector_intersection(b1,d1,b2,d2,z):
		'''
		Calculates the intersection point between two vectors defined by their base point and direction (2D only)
		input[b1,d1,b2 and d2 as FreeCAD.Vector, z as float]
		return[FreeCAD.Vector]
		'''
		if d1[0] == 0 and d2[0] != 0 or d1[1] == 0 and d2[1] != 0:
			if d1[0] == 0 and d2[0] != 0:
				mu = float(b1[0] - b2[0])/d2[0]
			elif d1[1] == 0 and d2[1] != 0:
				mu = float(b1[1] - b2[1])/d2[1]
			return FreeCAD.Vector(b2[0] + mu* d2[0],b2[1] + mu * d2[1],z)
		else:
			if d1[0] != 0 and d1[1] != 0 and d2[0] != 0 and d2[1] != 0:
				if d1[1]*d2[0] - d1[0]*d2[1] == 0:
					raise ValueError("Direction vectors are invalid. (Parallel)")
				lmbda = float(b1[0]*d2[1] - b1[1]*d2[0] - b2[0]*d2[1] + b2[1]*d2[0])/(d1[1]*d2[0] - d1[0]*d2[1])
			elif d2[0] == 0 and d1[0] != 0:
				lmbda = float(b2[0] - b1[0])/d1[0]
			elif d2[1] == 0 and d1[1] != 0:
				lmbda = float(b2[1] - b1[1])/d1[1]
			else:
				raise ValueError("Direction vectors are invalid.")
			return FreeCAD.Vector(b1[0] + lmbda* d1[0],b1[1] + lmbda * d1[1], z)

	@staticmethod				
	def drawArc(lineCoords,sp,ep,cp,cwRot,div=10):
			'''
			Constructs coordinate points that make up an arc from start point, end point, center point, rotation direction and div as the number of arc segments
			input[lineCoords as pivy.coin.SoCoordinate3, sp as FreeCAD.Vector, ep as FreeCAD.Vector, cp as FreeCAD.Vector, cwRot as Boolean, div as integer]
			return[lineCoords as pivy.coin.SoCoordinate3]
			'''
			#this block checks which side of the line from start point to end point the center point is
			mp = sp.add(ep).multiply(0.5)
			spep = ep.sub(sp).normalize()
			if mp != cp:
				mpcp = cp.sub(mp).normalize()
				mpcpPerp = FreeCAD.Vector(mpcp.y, -mpcp.x, mpcp.z)
				if mpcpPerp == spep:
					right = False
				else:
					right = True
			else:
				right = True
			#translate to zero & set start end end points(depending on rotation direction)
			if cwRot:
				sp2 = ep.sub(cp)
				ep2 = sp.sub(cp)
				lineCoords.point.set1Value(0,ep[0],ep[1],ep[2])
				lineCoords.point.set1Value(div+1,sp[0],sp[1],sp[2])
				if right:
					angDiv = sp2.getAngle(ep2)/div
				else:
					angDiv = (2*pi - sp2.getAngle(ep2))/div
			else:
				sp2 = sp.sub(cp)
				ep2 = ep.sub(cp)
				lineCoords.point.set1Value(0,sp[0],sp[1],sp[2])
				lineCoords.point.set1Value(div+1,ep[0],ep[1],ep[2])
				if right:
					angDiv = (2*pi - sp2.getAngle(ep2))/div
				else:
					angDiv = sp2.getAngle(ep2)/div
			for n in range(div):
				ang = (n+1)*angDiv
				x = sp2.x*cos(ang) - sp2.y*sin(ang)
				y = sp2.x*sin(ang) + sp2.y*cos(ang)
				z = sp2.z
				np2 = FreeCAD.Vector(x, y, z)
				np = cp.add(np2)
				lineCoords.point.set1Value(n+1,np[0],np[1],np[2])
			return lineCoords
