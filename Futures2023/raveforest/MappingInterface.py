import json
import random
import random

class MappingInterface(object):
    Active_Tubes = [0,0,0,0,0,0,0]
    Init_Tubes_Notes = []
    Init_Tubes_Colors = [[]]  # first item in hue , second item is the value
    Tubes_Notes = []
    Tubes_Colors = [[]] # first item in hue , second item is the value
    notes_to_color = True
    mapping_id =1

    def __init__(self, cfg):
        self.Init_Tubes_Notes=cfg['notes']
        self.Init_Tubes_Colors = cfg['colors']
        self.Tubes_Notes = cfg['notes']
        self.Tubes_Colors = cfg['colors']
        self.mapping_id=cfg['mapping_id']
        self.notes_to_color = cfg['notes_to_color']

        self.notes_to_light_mappings = [
            self.notes_to_light1,
            self.notes_to_light2,
            self.notes_to_light3
        ]

        self.light_to_notes_mappings = [
            self.light_to_notes1,
            self.light_to_notes2,
            self.light_to_notes3
        ]

    def generate_tubes(self,active):
        # A tube is active if its cap sensor is being touched
        # 'active' is a list of boolean touch sensor results where 1=cap sensor active
        self.Active_Tubes=active
        if self.notes_to_color:
            self.update_notes() # Updates notes
            self.notes_to_light_mappings[self.mapping_id]() # Uses mapping to update colours based on chosen notes
        else:
            self.update_light()
            self.light_to_notes_mappings[self.mapping_id]()
        return self.send_light(), self.send_notes()

    def update_notes (self):
        for t in range(len(self.Active_Tubes)):
            # if self.Active_Tubes[t]==1:
            #self.Tubes_Notes[t] = self.Init_Tubes_Notes[t]
            self.Tubes_Notes[t] = (self.Tubes_Notes[t] + 2) % 16
            # else:
            #     self.Tubes_Notes[t]=255

    def update_light (self):
        for t in range(len(self.Active_Tubes)):
            # if self.Active_Tubes[t]==1:
            self.Tubes_Colors[t][0]= self.Init_Tubes_Colors[t][0]
            self.Tubes_Colors[t][1] = self.Init_Tubes_Colors[t][1]
            # else:
            #     self.Tubes_Colors[t][0] = 255
            #     self.Tubes_Colors[t][1] = 255

    def notes_to_light1 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0]= random.randrange(0,255)

    def notes_to_light2 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0]= self.Tubes_Notes[t]

    def notes_to_light3 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0] = (self.Tubes_Colors[t][0] + 5) % 255
               #self.Tubes_Notes[t] = (self.Tubes_Notes[t] + 2) % 16

    def light_to_notes1 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = random.randrange(20,100)

    def light_to_notes2 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = self.Tubes_Colors[t]
    
    def light_to_notes3 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = max(20, (self.Tubes_Notes[t] + 5) % 100)

    def send_notes (self):
        return self.Tubes_Notes

    def send_light (self):
        return self.Tubes_Colors


