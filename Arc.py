import FreeCAD, FreeCADGui, Part, PartGui
from pivy.coin import SoGroup, SoSeparator, SoCoordinate3, SoLineSet, SoBaseColor, SoDrawStyle, SoPointSet, SoType, SoIndexedLineSet,SoNormal
from math import sin, cos, degrees, radians, pi
from tools import functions

class Arc:
	def __init__(self, obj, sp, ep, cp, cwRot):
		"Add our custom geometric properties to the Arc object"
		obj.addProperty("App::PropertyVector","StartPoint","Arc","Start point of the line").StartPoint=sp
		obj.addProperty("App::PropertyVector","EndPoint","Arc","End point of the line").EndPoint=ep
		obj.addProperty("App::PropertyVector","CenterPoint","Arc","End point of the line").CenterPoint=cp
		obj.addProperty("App::PropertyBool","CWRotation","Arc","True if arc is drawn clockwise from start to end point").CWRotation=cwRot
		obj.addProperty("App::PropertyString","EdgeType","Arc","Type of edge").EdgeType = "Arc"
		obj.addProperty("App::PropertyString","ShapeType","Arc","Type of shape").ShapeType = "Edge"
		obj.addProperty("App::PropertyVectorList","SnapPoints","Arc", "All the points that can be snapped to")
		obj.addProperty("App::PropertyIntegerList","SnapLinesIndex","Arc", "Index of which snap point each snap line starts from")		
		obj.addProperty("App::PropertyVectorList","SnapDirections","Arc", "Directions of all the lines that can be snapped to")
		obj.addProperty("Part::PropertyPartShape","Shape","Arc", "Shape of the arc")
		obj.Proxy = self

	def execute(self, fp):
		"Create all of the assosiated goemetry"	
		radius = fp.CenterPoint.sub(fp.StartPoint).Length #length between start point and center point
		centerBase = fp.CenterPoint
		centerDir = fp.StartPoint.sub(fp.CenterPoint).normalize()
		angle1 = 0.0
		angle2 = degrees(centerDir.getAngle(fp.EndPoint.sub(fp.CenterPoint).normalize())) ###############PROBLEM HERE, ONLY 180deg MAX#############
		fp.Shape = Part.makeCircle(radius,centerBase,centerDir,angle1,angle2) #this is just the basic  arc shape
		#create snap points (start and end points of line)
		sps = []
		sps.append(fp.StartPoint)
		sps.append(fp.EndPoint)
		fp.SnapPoints = sps
		#create all the snap line direction vectors
		startVec = fp.StartPoint.sub(fp.CenterPoint).normalize()
		endVec = fp.EndPoint.sub(fp.CenterPoint).normalize()
		startVecPerp = FreeCAD.Vector(startVec.y,-startVec.x,startVec.z)
		endVecPerp = FreeCAD.Vector(endVec.y,-endVec.x,endVec.z)
		vert = FreeCAD.Vector(0,1,0)#vertical
		horiz = FreeCAD.Vector(1,0,0)#horizontal
		#fill out index list. index and vector list must be same length
		fp.SnapLinesIndex = [0,0,0,0,1,1,1,1]
		#create assosiated (with index list) vector list
		spvs = [startVec,startVecPerp,vert,horiz,endVec,endVecPerp,vert,horiz]
		fp.SnapDirections = spvs # I don't know why I have to do it like this and not just add directly
			
class ViewProviderArc:
	def __init__(self, obj):
		"Add our custom  features to this view provider"
		obj.addProperty("App::PropertyColor","StartPointColor","Arc","Start point color").StartPointColor=(0.0,0.0,0.0)	
		obj.addProperty("App::PropertyColor","EndPointColor","Arc","End point color").EndPointColor=(0.0,0.0,0.0)
		obj.addProperty("App::PropertyColor","CenterPointColor","Arc","Center point color").CenterPointColor=(0.5,0.5,0.5)
		obj.LineColor = (0.0,0.0,0.0) #existing Part::FeaturePython property		
		obj.PointSize = 4	#existing Part::FeaturePython property
		obj.LineWidth = 2	#existing Part::FeaturePython property
		obj.Selectable = True #existing Part::FeaturePython property
		obj.Proxy = self #some kind of FreeCAD internal here, this view provider object is set as the FreeCAD view object proxy. 
		#I guess if a proxy exists, it's used instead of the standard one.

	def attach(self, obj):
		"Setup the scene sub-graph of the view provider"
		self.group = SoSeparator()
		#create group for display mode and add line, start point and end point nodes
		self.arcNode = SoSeparator()
		self.startPointNode = SoSeparator()
		self.endPointNode = SoSeparator()
		self.centerPointNode = SoSeparator()
		self.group.addChild(self.arcNode)		
		self.group.addChild(self.startPointNode)		
		self.group.addChild(self.endPointNode)
		self.group.addChild(self.centerPointNode)	
		#add draw style
		self.drawStyle = SoDrawStyle()
		self.arcNode.addChild(self.drawStyle)
		self.startPointNode.addChild(self.drawStyle)
		self.endPointNode.addChild(self.drawStyle)
		self.centerPointNode.addChild(self.drawStyle)
		#add line colour
		self.arcLineColor = SoBaseColor()
		self.arcNode.addChild(self.arcLineColor)
		#add start point color
		self.startPointColor = SoBaseColor()
		self.startPointNode.addChild(self.startPointColor)
		#add end point colour
		self.endPointColor = SoBaseColor()
		self.endPointNode.addChild(self.endPointColor)	
		#add center point colour
		self.centerPointColor = SoBaseColor()
		self.centerPointNode.addChild(self.centerPointColor)
		#add start, end and center points coordinate node
		self.pointCoords = SoCoordinate3()
		self.endPointNode.addChild(self.pointCoords)
		self.startPointNode.addChild(self.pointCoords)
		self.centerPointNode.addChild(self.pointCoords)
		#add arc coordinates node
		self.arcCoords = SoCoordinate3()
		self.arcNode.addChild(self.arcCoords)
		#add arc edge (using PartGui::SoBrepEdgeSet, has selectability built in)
		self.arcLineSet = SoType.fromName("SoBrepEdgeSet").createInstance()
		self.arcNode.addChild(self.arcLineSet)
		#add start point (using PartGui::SoBrepPointSet, has selectability built in)
		self.startPoint = SoType.fromName("SoBrepPointSet").createInstance()
		self.startPoint.startIndex = 0
		self.startPoint.numPoints = 1
		self.startPointNode.addChild(self.startPoint)
		#add end point (using PartGui::SoBrepPointSet, has selectability built in)
		self.endPoint = SoType.fromName("SoBrepPointSet").createInstance()
		self.endPoint.startIndex = 1	
		self.endPoint.numPoints = 1
		self.endPointNode.addChild(self.endPoint)
		#add center point (using PartGui::SoBrepPointSet, has selectability built in)
		self.centerPoint = SoType.fromName("SoBrepPointSet").createInstance()
		self.centerPoint.startIndex = 2	
		self.centerPoint.numPoints = 1
		self.centerPointNode.addChild(self.centerPoint)
		#assign properties to nodes
		self.onChanged(obj,"LineColor")
		self.onChanged(obj,"StartPointColor")
		self.onChanged(obj,"EndPointColor")
		self.onChanged(obj,"PointSize")
		self.onChanged(obj,"LineWidth")
		#add display mode to view object
		obj.addDisplayMode(self.group,"Default");
	
	def updateData(self, fp, prop):
		"If a property of the handled feature has changed we have the chance to handle this here"
		# fp is the handled feature, prop is the name of the property that has changed
		if prop == "StartPoint" or prop == "EndPoint" or prop == "CenterPoint" or prop == "CWRotation"
			sp = fp.getPropertyByName("StartPoint")		
			ep = fp.getPropertyByName("EndPoint")		
			cp = fp.getPropertyByName("CenterPoint")
			cwRot = fp.getPropertyByName("CWRotation")
			self.pointCoords.point.set1Value(0,sp[0],sp[1],sp[2])
			self.pointCoords.point.set1Value(1,ep[0],ep[1],ep[2])
			self.pointCoords.point.set1Value(2,cp[0],cp[1],cp[2])
			div = 30
			#FreeCAD.Console.PrintMessage("prop: "+str(prop)+"\n")
			#FreeCAD.Console.PrintMessage("sp: "+str(sp)+"\n")
			#FreeCAD.Console.PrintMessage("ep: "+str(ep)+"\n")
			#FreeCAD.Console.PrintMessage("cp: "+str(cp)+"\n")
			#FreeCAD.Console.PrintMessage("cwRot: "+str(cwRot)+"\n\n\n")
			functions.drawArc(self.arcCoords,sp,ep,cp,cwRot,div)
			self.arcLineSet.coordIndex.setValues(0,div+1,range(div+1))

		
	def getDisplayModes(self,obj):
		"Return a list of display modes."
		modes=[]
		modes.append("Default")
		return modes
	
	def getDefaultDisplayMode(self):
		"Return the name of the default display mode. It must be defined in getDisplayModes."
		return "Default"
	
	def setDisplayMode(self,mode):
		return mode
	
	def onChanged(self, vp, prop):
		"Here we can do something when a single property got changed"
		if prop == "LineColor":
			c = vp.getPropertyByName("LineColor")
			self.arcLineColor.rgb.setValue(c[0],c[1],c[2])
		elif prop == "StartPointColor":
			c = vp.getPropertyByName("StartPointColor")
			self.startPointColor.rgb.setValue(c[0],c[1],c[2])
		elif prop == "EndPointColor":
			c = vp.getPropertyByName("EndPointColor")
			self.endPointColor.rgb.setValue(c[0],c[1],c[2])	
		elif prop == "CenterPointColor":
			c = vp.getPropertyByName("CenterPointColor")
			self.centerPointColor.rgb.setValue(c[0],c[1],c[2])		
		elif prop == "PointSize":
			c = vp.getPropertyByName("PointSize")
			self.drawStyle.pointSize = c
		elif prop == "LineWidth":
			c = vp.getPropertyByName("LineWidth")
			self.drawStyle.lineWidth = c
			
	def getIcon(self):
		return """
		/* XPM */
		static const char * ViewProviderBox_xpm[] = {
		"16 16 3 1",
		" 	c #FFFFFF",
		".	c #3F48CC",
		"+	c #00A2E8",
		"                ",
		"           ...  ",
		"          ..... ",
		"          ..+.. ",
		"         +..... ",
		"        +++...  ",
		"       +++++    ",
		"      +++++     ",
		"     +++++      ",
		"    +++++       ",
		" ...++++        ",
		".....++         ",
		"..+..+          ",
		".....           ",
		" ...            ",
		"                "};		
		"""
	
	def __getstate__(self):
		return None
	
	def __setstate__(self,state):
		return None
