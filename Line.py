import FreeCAD, FreeCADGui, Part, PartGui
from pivy.coin import SoGroup, SoSeparator, SoCoordinate3, SoLineSet, SoBaseColor, SoDrawStyle, SoPointSet, SoType, SoIndexedLineSet,SoNormal

class Line:
	def __init__(self, obj, sp=(0.0,0.0,0.0), ep=(1.0,1.0,0.0)):
		"Add our custom geometric properties to the line object"
		obj.addProperty("App::PropertyVector","StartPoint","Line","Start point of the line").StartPoint=sp
		obj.addProperty("App::PropertyVector","EndPoint","Line","End point of the line").EndPoint=ep
		obj.addProperty("App::PropertyString","EdgeType","Line","Type of edge").EdgeType = "Line"
		obj.addProperty("App::PropertyString","ShapeType","Line","Type of shape").ShapeType = "Edge"
		obj.addProperty("App::PropertyVectorList","SnapPoints","Line", "All the points that can be snapped to")
		obj.addProperty("App::PropertyIntegerList","SnapLinesIndex","Line", "Index of which snap point each snap line starts from")		
		obj.addProperty("App::PropertyVectorList","SnapDirections","Line", "Directions of all the lines that can be snapped to")
		obj.addProperty("Part::PropertyPartShape","Shape","Line", "Shape of the line")
		obj.Proxy = self

	def execute(self, fp):
		"Create all of the assosiated goemetry"	
		fp.Shape = Part.makeLine(fp.StartPoint,fp.EndPoint) #this is just the basic line shape
		#create snap points (start, midpoint and end point of line)
		sps = []
		midPoint = FreeCAD.Vector(0,0,0)
		midPoint.x = (fp.EndPoint.x + fp.StartPoint.x)/2
		midPoint.y = (fp.EndPoint.y + fp.StartPoint.y)/2
		midPoint.z = (fp.EndPoint.z + fp.StartPoint.z)/2
		sps.append(fp.StartPoint)
		sps.append(fp.EndPoint)
		sps.append(midPoint)
		fp.SnapPoints = sps
		#create a vector that points in direction of start point to end point
		startVec = FreeCAD.Vector(0,0,0)
		startVec.x = fp.EndPoint.x - fp.StartPoint.x
		startVec.y = fp.EndPoint.y - fp.StartPoint.y
		startVec.z = fp.EndPoint.z - fp.StartPoint.z
		startVec.normalize()
		#fill out index list. index and vector list must be same length
		fp.SnapLinesIndex = [0,0,1,0,1,0,1]
		#create all the snap vectors
		v1 = startVec #line direction
		v2 = FreeCAD.Vector(startVec.y,-startVec.x,startVec.z) #this rotates vector by 90deg in clockwise direction (for perpendicular snap)
		v3 = FreeCAD.Vector(0,1,0)#vertical
		v4 = FreeCAD.Vector(1,0,0)#horizontal
		spvs = [v1,v2,v2,v3,v3,v4,v4]
		fp.SnapDirections = spvs # I don't know why I have to do it like this and not just add directly
		
class ViewProviderLine:
	def __init__(self, obj):
		"Add our custom  features to this view provider"
		obj.addProperty("App::PropertyColor","StartPointColor","Line","Start point color").StartPointColor=(0.0,0.0,0.0)	
		obj.addProperty("App::PropertyColor","EndPointColor","Line","End point color").EndPointColor=(0.0,0.0,0.0)
		obj.LineColor = (0.0,0.0,0.0) #existing Part::FeaturePython property		
		obj.PointSize = 4	#existing Part::FeaturePython property
		obj.LineWidth = 2	#existing Part::FeaturePython property
		obj.Selectable = True #existing Part::FeaturePython property
		obj.Proxy = self #some kind of FreeCAD internal here, this view provider object is set as the FreeCAD view object proxy. 
		# I guess if a proxy exists, it's used instead of the standard one.

	def attach(self, obj):
		"Setup the scene sub-graph of the view provider"
		
		#create group for display mode and add line, start point and end point nodes
		self.group = SoSeparator()
		self.lineNode = SoSeparator()
		self.startPointNode = SoSeparator()
		self.endPointNode = SoSeparator()
		self.group.addChild(self.lineNode)		
		self.group.addChild(self.startPointNode)		
		self.group.addChild(self.endPointNode)
		#add line colour
		self.lineColor = SoBaseColor()
		self.lineNode.addChild(self.lineColor)
		#add draw style
		self.drawStyle = SoDrawStyle()
		self.lineNode.addChild(self.drawStyle)
		self.startPointNode.addChild(self.drawStyle)
		self.endPointNode.addChild(self.drawStyle)
		#add start point color
		self.startPointColor = SoBaseColor()
		self.startPointNode.addChild(self.startPointColor)
		#add end point colour
		self.endPointColor = SoBaseColor()
		self.endPointNode.addChild(self.endPointColor)	
		#add coordinate node
		self.coords = SoCoordinate3()
		self.lineNode.addChild(self.coords)
		self.endPointNode.addChild(self.coords)
		self.startPointNode.addChild(self.coords)		
		#add edge (using PartGui::SoBrepEdgeSet, has selectability built in)
		#self.lineSet = SoLineSet()
		self.lineSet = SoType.fromName("SoBrepEdgeSet").createInstance()
		self.lineSet.coordIndex.setValues(0,2,(0,1))
		self.lineNode.addChild(self.lineSet)
		#add start point (using PartGui::SoBrepPointSet, has selectability built in)
		#self.startPoint =  SoPointSet()
		self.startPoint = SoType.fromName("SoBrepPointSet").createInstance()
		self.startPoint.startIndex = 0
		self.startPoint.numPoints = 1
		self.startPointNode.addChild(self.startPoint)
		#add end point (using PartGui::SoBrepPointSet, has selectability built in)
		#self.endPoint =  SoPointSet()
		self.endPoint = SoType.fromName("SoBrepPointSet").createInstance()
		self.endPoint.startIndex = 1	
		self.endPoint.numPoints = 1
		self.endPointNode.addChild(self.endPoint)
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
		if prop == "StartPoint":
			s = fp.getPropertyByName("StartPoint")
			self.coords.point.set1Value(0,s[0],s[1],s[2])
		elif prop == "EndPoint":
			s = fp.getPropertyByName("EndPoint")
			self.coords.point.set1Value(1,s[0],s[1],s[2])
	
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
			self.lineColor.rgb.setValue(c[0],c[1],c[2])
		elif prop == "StartPointColor":
			c = vp.getPropertyByName("StartPointColor")
			self.startPointColor.rgb.setValue(c[0],c[1],c[2])
		elif prop == "EndPointColor":
			c = vp.getPropertyByName("EndPointColor")
			self.endPointColor.rgb.setValue(c[0],c[1],c[2])	
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
