class Parent(object):
    def __init__(self):
        self.joze = 10
        self.ivan = {'1':1}
    def neki(self):
        ivan = Ivan(self)
class Ivan(object):
    def __init__(self, data):
    	self.data = data
        self.joze = 10
        self.data.joze = 350

