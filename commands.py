import FreeCAD, FreeCADGui, Part
from pivy.coin import SoEvent, SoSeparator, SoCoordinate3, SoLineSet, SoLocation2Event, SoMouseButtonEvent, SoKeyboardEvent
from pivy.coin import SoBaseColor, SoPointSet, SoDrawStyle, SoNormal, SoNormalBinding
from DraftGui import todo
from Line import Line, ViewProviderLine
from Arc import Arc, ViewProviderArc
from operator import itemgetter
from math import sin, cos, pi
from tools import functions

class edge(object):
	"edge creation base class"
	def Activated(self, obj = None, sp=None):
		#initalise some variables
		self.obj = obj
		self.doc = FreeCAD.ActiveDocument
		self.view = FreeCADGui.ActiveDocument.ActiveView
		self.currentPoint = None #will be type FreeCAD.Vector
		self.lockLine = False #will be type FreeCAD.Vector
		self.snapPoints = functions.getSnapPoints() #get list of snap points and lines in current view
		self.snapLines = functions.getSnapLines()
		if sp: #if a  start point is predefined then jump into the appropriate state.
			self.sp = sp
			self.snapLines=self.spSnapEntry(self.sp, self.snapLines) #add  start point snap lines
			self.state = 2
		else:	
			self.state=0
		functions.edgeSelection(False) #turn off selection of existing edge objects
		self.call = self.view.addEventCallbackPivy(SoEvent.getClassTypeId(),self.event) #create callback for any event
		self.sceneGraph = self.view.getSceneGraph() #temp geometry inialize for drawing temporary geometry
		self.tempNode = SoSeparator() #top node for all temp geometry
		#line node
		self.tempLine = SoSeparator()
		self.lineCoords = SoCoordinate3()
		self.lineSet = SoLineSet()
		self.lineColor = SoBaseColor()
		self.lineColor.rgb = (0,0,0)
		self.tempLine.addChild(self.lineCoords)
		self.tempLine.addChild(self.lineColor)
		self.tempLine.addChild(self.lineSet)
		#point highlight node
		self.tempPoint = SoSeparator() 
		self.pointCoords = SoCoordinate3()
		self.pointSet = SoPointSet()
		self.pointColor = SoBaseColor()		
		self.drawStyle = SoDrawStyle()
		self.pointColor.rgb = (1,1,1)
		self.drawStyle.style.setValue("INVISIBLE")
		self.drawStyle.pointSize = 5
		self.tempPoint.addChild(self.pointCoords)
		self.tempPoint.addChild(self.pointColor)
		self.tempPoint.addChild(self.drawStyle)
		self.tempPoint.addChild(self.pointSet)		
		#snap line node
		self.snapLine = SoSeparator()
		self.snapLineCoords = SoCoordinate3()
		self.snapLineSet = SoLineSet()
		self.snapLineColor = SoBaseColor()
		self.snapLineDrawStyle = SoDrawStyle()
		self.snapLineColor.rgb = (1,1,1)
		self.snapLineDrawStyle.style.setValue("INVISIBLE")
		self.snapLine.addChild(self.snapLineCoords)
		self.snapLine.addChild(self.snapLineColor)
		self.snapLine.addChild(self.snapLineDrawStyle)
		self.snapLine.addChild(self.snapLineSet)
		#add temp geometry nodes to scene graph
		self.tempNode.addChild(self.tempPoint)
		self.tempNode.addChild(self.snapLine)
		self.tempNode.addChild(self.tempLine)
		self.sceneGraph.addChild(self.tempNode)

	def event(self,eventCB):
		"Checks event type, passes on to appropriate function"
		event = eventCB.getEvent()
		type = event.getTypeId()
		leftButton = 1
		rollerButton = 3
		down = 1
		up = 0
		if type == SoLocation2Event.getClassTypeId():
			self.mouseMove(event)
		elif type == SoMouseButtonEvent.getClassTypeId() and event.getButton() == leftButton:	
			if event.getState() == down:
				self.mouseButtonDown()	
			elif event.getState() == up:
				self.mouseButtonUp()	
		elif type == SoKeyboardEvent.getClassTypeId():
			self.keyboard(event)			
		else:
			FreeCAD.Console.PrintMessage("Some other event just happened\n")
	
	def mouseMove(self,event):
		pos = event.getPosition() #get mouse position from event (in xy pixel coordinates)
		linePoint, lineSnapped, snapLine1, snapLine2,  self.cursorDir = functions.snapLine(self.view, pos, self.snapLines, 10,self.lockLine) #check if in range of snap line(s)
		if self.state ==4: #get the snap point, depending on state
			pointSnapped = False #at state 4 there is no snap points (state 4 is for picking center point of an arc)
		else: 
			pointPoint, pointSnapped = functions.snapPoint(self.view, pos, self.snapPoints, 10) #check if in range of snap point
		#next draw the snap lines or points and assign the current point
		if pointSnapped:
			self.snapLineDrawStyle.style.setValue("INVISIBLE") # turns off the visualisation of any previous snap lines
			self.pointCoords.point.set1Value(0,pointPoint[0],pointPoint[1],pointPoint[2]) #puts the snap cooridinates into the scene graph
			self.drawStyle.style.setValue("POINTS") #turns on the visualisation of the snap point
			self.currentPoint = pointPoint #sets the current point to the snap point such that if the mouse is clicked the snap point is used
		elif lineSnapped: #line snap only if no point snap, so point snap had priority
			self.snapLineSet.numVertices.setValue(2)#two vertices for a line from snap point to base point
			self.pointCoords.point.set1Value(0,linePoint[0],linePoint[1],linePoint[2])#adds line snap point to scene graph
			self.drawStyle.style.setValue("POINTS") #turns on visualiation of point
			basePoint = snapLine1[0] # get first vertex of snap line from the snap line base point
			self.snapLineCoords.point.set1Value(0,basePoint[0],basePoint[1],basePoint[2])	#put the line coordinates into the scene graph
			self.snapLineCoords.point.set1Value(1,linePoint[0],linePoint[1],linePoint[2])
			if snapLine2: #if there is a second snap line
				basePoint2 = snapLine2[0]	# get last point from base point of second line(line is drawn from base point to snap point to base point)
				self.snapLineCoords.point.set1Value(2,basePoint2[0],basePoint2[1],basePoint2[2]) #put the line coordinates into the scene graph
				self.snapLineSet.numVertices.setValue(3)  #tell line set there are 3 vertexes to be drawn
			self.snapLineDrawStyle.style.setValue("LINES") #turns on visualisation of lines
			self.currentPoint = linePoint #sets current point to line snap point
		else: #if no snap is found, don't draw to screen and find cursor point
			self.drawStyle.style.setValue("INVISIBLE") #turn of visualisation of snap point
			self.snapLineDrawStyle.style.setValue("INVISIBLE") #turn of visualisation of snap line
			self.currentPoint = self.view.getPoint(pos[0],pos[1]) #get cursor point for current point

	def mouseButtonDown(self):		
		if self.state == 0:
			self.sp = self.currentPoint #record first point
			self.snapLines=self.spSnapEntry(self.sp, self.snapLines) #add first point to snaplines
			self.state = 1	#update to new state
				
	def mouseButtonUp(self):
		if self.state == 1:
			self.state = 2 
	
	def spSnapEntry(self,sp,snapLines):
		"this block adds the first coordinate selected to the snap line list so the line will snap to the orthogonal projections of it"
		entry= [sp,FreeCAD.Vector(1,0,0),None] #horizontal snap direction
		entry2 = [sp,FreeCAD.Vector(0,1,0),None] #vertical snap direction
		entry3 = [sp,FreeCAD.Vector(1,1,0),None] #45 snap direction
		entry4 = [sp,FreeCAD.Vector(1,-1,0),None] #-45 snap direction
		snapLines.append(entry)
		snapLines.append(entry2)
		snapLines.append(entry3)
		snapLines.append(entry4)
		return snapLines
	
	def keyboard(self,event):	
		pass #don't currently use any key functionality
		
	def cleanUp(self):
		self.view.removeEventCallbackPivy(SoEvent.getClassTypeId(),self.call) #remove event callback
		#remove the temporary geormety by sending the removal function throught to a delay function (of the Draft Module)
		#This must be done as the callback traversal is still occuring and will crash if the scene grapth objects are removed underneith it
		nodeRef = self.sceneGraph.findChild(self.tempNode) #First we get the index ofour temp geometry node under the scene graph node
		#(I don't like this, can we use a use a name instead that can't be confused with another node?)
		f = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph().removeChild #this is the function that removes a node node from the scene grapth
		todo.delay(f, nodeRef) #pass the index and the function onto the delay method
		functions.edgeSelection(True) #turn back on selection of existing edge objects
	
class straight(edge):
	"this tool will create a straight edge after the user clicks 2 points on the screen"
	def Activated(self, obj = None, sp = None):
		edge.Activated(self,obj, sp)

	def mouseMove(self,event):
		edge.mouseMove(self,event)
		if self.state == 2:
			#if first point has been selected, complete coordinate list for temp scenegraph line (with current position)
			self.lineCoords.point.set1Value(0,self.sp[0],self.sp[1],self.sp[2])
			self.lineCoords.point.set1Value(1,self.currentPoint[0],self.currentPoint[1],self.currentPoint[2])
			
	def mouseButtonDown(self):
		edge.mouseButtonDown(self)
		if self.state == 2: #if first point has already been created
			self.ep = self.currentPoint #record second point
			self.state = 3 #update to new state
			
	def mouseButtonUp(self):
		edge.mouseButtonUp(self)
		if self.state == 3:
			self.cleanUp()  #clean up call backs and temp scene geometry
			self.createLine() #actually create the new line object
		
	def createLine(self):
		if self.obj:
			self.obj.StartPoint = self.sp
			self.obj.EndPoint = self.ep
		else:
			a=self.doc.addObject("Part::FeaturePython","Line") #create new basic object that will hold our line
			Line(a,self.sp,self.ep)	#pass the new application object throught this function to set up the properties and geometry
			ViewProviderLine(a.ViewObject) #pass the new view object throught this function to get up the properties and view style/geometry
		
		self.doc.recompute() #update document to show and recompute the line

	def GetResources(self):
		"required function for a command, returns dictionary of gui info"
		return {'Pixmap' :'Draft_Line', 
				'MenuText': 'Straight Edge', 
				'ToolTip': 'Creates a straight edge by clicking 2 points on the screen'} 
		
class arc(edge):
	"this tool will create a straight edge after the user clicks 2 points on the screen"
	def Activated(self, obj = None, sp = None, ep = None):
		edge.Activated(self, obj, sp)
		self.currentcwRot = False
		self.cp = None #center point
		self.cwRot = False #clockwise rotation toggle
		if sp and ep:
			self.sp = sp
			self.ep = ep
			self.lockLine, self.snapLines=self.epSnapEntry(self.sp,self.ep,self.snapLines)
			self.state = 4

	def mouseMove(self,event):
		edge.mouseMove(self,event)
		#finally draw the temporary arc geometry
		if self.state == 2 :
			#if first point has been selected, complete coordinate list for temp scenegraph arc (with current position)
			#get the start and end points
			ep = self.currentPoint
			if self.sp != ep: #don't bother if points are coincident (eg. just after first point is selected)
				#Calculate center point for temporary arc	
				midpt = ep.add(self.sp).multiply(0.5)
				dir = ep.sub(self.sp).normalize()
				dirperp = FreeCAD.Vector(-dir.y, dir.x, dir.z)	
				len = ep.sub(self.sp).Length
				cp = midpt.add(dirperp.multiply(len/2))
				functions.drawArc(self.lineCoords,self.sp,ep,cp,False,10)
		elif self.state == 4:
			dir = self.ep.sub(self.sp).normalize()	
			cp = self.currentPoint	
			if dir == self.cursorDir:
				cwRot = True	
			else:
				cwRot = False
			self.currentcwRot = cwRot
			functions.drawArc(self.lineCoords,self.sp,self.ep,cp,cwRot,10)	
			
	def mouseButtonDown(self):
		edge.mouseButtonDown(self)
		if self.state == 2: 
			self.ep = self.currentPoint 
			self.lockLine, self.snapLines=self.epSnapEntry(self.sp,self.ep,self.snapLines)
			self.state = 3
		elif self.state == 4: 
			self.cp = self.currentPoint 
			self.cwRot = self.currentcwRot
			self.state = 5 

	def epSnapEntry(self,sp,ep,snapLines):
		midpt = ep.add(sp).multiply(0.5)		
		dir = ep.sub(sp).normalize()		
		dirperp = FreeCAD.Vector(dir.y, -dir.x, dir.z)
		lockLine = [midpt,dirperp,None]		
		snapLines.append(lockLine)		
		return lockLine, snapLines
			
	def mouseButtonUp(self):
		edge.mouseButtonUp(self)
		if self.state == 3:
			self.state = 4 
		elif self.state == 5:	
			self.cleanUp()  
			self.createLine() 
		
	def createLine(self):
		if self.obj:
			self.obj.StartPoint = self.sp
			self.obj.EndPoint = self.ep
			self.obj.CenterPoint = self.cp
			self.obj.CWRotation = self.cwRot
		else:
			a=self.doc.addObject("Part::FeaturePython","Arc") 	
			Arc(a,self.sp,self.ep,self.cp, self.cwRot)	
			ViewProviderArc(a.ViewObject) 
			self.doc.recompute() 	

	def GetResources(self):
		"required function for a command, returns dictionary of gui info"
		return {'Pixmap' : 'Draft_Arc', 
				'MenuText': 'Arc Edge', 
				'ToolTip': 'Creates an arc segment by clicking two end points and center'} 
					
#create new commands in gui	
FreeCADGui.addCommand('Straight Edge', straight())
FreeCADGui.addCommand('Arc Edge', arc())
