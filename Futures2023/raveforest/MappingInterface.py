import json
import random
import random

class MappingInterface:
    Active_Tubes = [0,0,0,0,0,0,0]
    Init_Tubes_Notes = []
    Init_Tubes_Colors = [[]]  # first item in hue , second item is the value
    Tubes_Notes = []
    Tubes_Colors = [[]] # first item in hue , second item is the value
    notes_to_color = True
    mapping_id =1

    def __init__(self, config_file="config.txt"):
        with open(config_file, 'r') as f:
            lines = f.readlines()
            cfg = json.loads(lines[0].strip())
        try:
            self.Init_Tubes_Notes=cfg['notes']
            self.Init_Tubes_Colors = cfg['colors']
            self.Tubes_Notes = cfg['notes']
            self.Tubes_Colors = cfg['colors']
            self.mapping_id=cfg['mapping_id']
            self.notes_to_color = cfg['notes_to_color']
        except Exception as e:
            print("Error parsing cfg "+e)



    def generate_tubes(self,input):
        self.Active_Tubes=input
        if self.notes_to_color:
            self.update_notes()
            if self.mapping_id==1:
                self.notes_to_color1()
            elif self.mapping_id==2:
                self.notes_to_color2()
        else:
            self.update_light()
            if self.mapping_id ==1:
                self.light_to_notes1()
            elif self.mapping_id ==2:
                self.light_to_notes2()
        self.send_light()
        self.send_notes()




    def update_notes (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Notes[t]= self.Init_Tubes_Notes[t]
            else:
                self.Tubes_Notes[t]=1000

    def update_light (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0]= self.Init_Tubes_Colors[t][0]
               self.Tubes_Colors[t][1] = self.Init_Tubes_Colors[t][1]
            else:
                self.Tubes_Colors[t][0] = 1000
                self.Tubes_Colors[t][1] = 1000

    def notes_to_light1 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0]= random.randrange(0,255)

    def notes_to_light2 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0]= self.Tubes_Notes[t]

    def light_to_notes1 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = random.randrange(20,100)

    def light_to_notes2 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = self.Tubes_Colors[t]

    def send_notes (self):
        return self.Tubes_Notes

    def send_light (self):
        return self.Tubes_Colors


