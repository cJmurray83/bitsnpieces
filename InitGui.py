
class MyWorkbench (Workbench): 
	MenuText = "Custom"
	def Initialize(self):
		import commands
		commandslist = ["Straight Edge", "Arc Edge"]
		self.appendToolbar("Custom",commandslist)
		
Gui.addWorkbench(MyWorkbench())
