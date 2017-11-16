from numpy import interp
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty,\
    ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.graphics import Line, Color
from kivy.animation import Animation
from kivy.lang import Builder
from random import randint
from geometry_funcs import find_intersection
from frame import frame
import math
from kivy.uix.textinput import TextInput
Builder.load_file("Sim.kv")
from kivy.config import Config

import rospy
from race.msg import pid_input

import json
from enum import Enum
import pickle
from datetime import datetime
import os

class SAVE_OPTIONS(Enum):
    NO = 1
    FAILURE = 2
    SUCCESS_FAILURE = 3


pub = rospy.Publisher('error', pid_input, queue_size=1)

Config.set('graphics', 'width', '1400')
Config.set('graphics', 'height', '720')
Config.set('graphics', 'resizable', False)

RENDERED_FRAMES =[frame()]
CURRENT_FRAME_ID = 0
LATEST_PUB_ANGLE = 0
SAVE_TRIGGER = SAVE_OPTIONS.NO

from race.msg import pid_input

### BARRIER AND WALL CLASSSES
class Wall(Widget):
    pass

class Barrier(Widget):
    pass

def get_current_frame_id():
    global CURRENT_FRAME_ID
    return CURRENT_FRAME_ID

def set_current_frame_id(num):
    global CURRENT_FRAME_ID
    CURRENT_FRAME_ID= num

def update_drive_params():
    global LATEST_PUB_ANGLE
    try:
        line = None
        with open("published_dp.txt", "r") as infile:
            line = infile.read()
            LATEST_PUB_ANGLE += float(line)
    except Exception as e:
        pass

def get_save_trigger(n):
    if n == 1:
        return SAVE_OPTIONS.NO
    elif n == 2:
        return SAVE_OPTIONS.FAILURE
    else:
        return SAVE_OPTIONS.SUCCESS_FAILURE

def get_next_frame(RENDERED_FRAMES):

    """
    testing moving around frames
    if get_current_frame_id() == 200:
        print ("reseting")
        set_current_frame_id(0)
        return get_next_frame(RENDERED_FRAMES)
    """

    current_frame = RENDERED_FRAMES[get_current_frame_id()]

    if not (current_frame.tick == len(RENDERED_FRAMES)-1):
        # if current is not the latest frame (we are repeating our steps)
        set_current_frame_id(current_frame.tick + 1)
        return RENDERED_FRAMES[get_current_frame_id()]
    else:

        update_drive_params();
        new_angle = LATEST_PUB_ANGLE
        curr_tick = current_frame.tick + 1

        ##print new_angle

        velocity_x = math.cos((new_angle * math.pi) / 180)
        velocity_y = math.sin((new_angle * math.pi) / 180)

        new_position = current_frame.pos + Vector(velocity_x,velocity_y)

        new_frame = frame(new_position,curr_tick,new_angle)
        RENDERED_FRAMES.append(new_frame)
        set_current_frame_id(curr_tick)

        return new_frame



class SimCar(Widget):

    def move(self, frame):

        self.angle = frame.curr_angle
        self.pos = frame.pos


class Simulator(Widget): # Root Widget

    global x, y
    global RENDERED_FRAMES

    lidar_angle = 0
    car_x_label = NumericProperty(0)
    car_y_label = NumericProperty(0)

    car = ObjectProperty(None) # Get a reference of the car object defined
                              # in the widget rules

    barriers = None

    def load_map(self,map_id):
        print "loading the map"
        with self.canvas:
            with open ("maps.json", "r") as mapfile:
                map_data = json.load(mapfile)
                m = map_data[str(map_id)]
                self.barriers = [ObjectProperty(None,allownone=True) for i in range (len(m))]

                print ("barriers: " + str(len(self.barriers)))

                for i,line in enumerate(m):
                    _line = map(int,m[line].split(","))
                    points = _line[0:4] 
                    c  = _line[4:7]
                    # set color and draw the line 
                    print line, points, c
                    Color(c)
                    self.barriers[i] = Line(points=points)
                    #Line(points=points, width=1)
        print ("end load map")

    def start_vehicle(self):
        with self.canvas:
            self.lidar_beam = Line(points=[0,0,0,0])



    def check_border_collision(self):
        if self.car.collide_widget(self.wall_left) or self.car.collide_widget(self.wall_right):
            return True
        if self.car.collide_widget(self.wall_top) or self.car.collide_widget(self.wall_down):
            return True

        return False

    def reset(self):
        set_current_frame_id(0)


    def update(self, dt):

        frame = get_next_frame(RENDERED_FRAMES)
        self.car.move(frame)
        self.car_x_label = frame.pos[0]
        self.car_y_label = frame.pos[1]


        if self.check_border_collision():
            if SAVE_TRIGGER == SAVE_OPTIONS.FAILURE or SAVE_TRIGGER == SAVE_OPTIONS.SUCCESS_FAILURE:
                if SAVE_TRIGGER == SAVE_OPTIONS.SUCCESS_FAILURE:
                    tag = "ANY"
                else:
                    tag = "FAILURE"
                label = "simulations/"+tag+str(datetime.now())
                with open (label, "w") as outfile:
                    try:
                        pickle.dump(RENDERED_FRAMES, outfile)
                        print ("saved log file: " + label)
                    except Exception as e:
                        print ("failure to save log")

            self.reset()
        else:
            LIDAR_TO_CAR_ANGLE = 45 # degrees
            LIDAR_RANGE = 250 # in cms

            car_center_x, car_center_y = self.car.center[0], self.car.center[1]

            # adjust angle so it remains relative to the car
            adj_angle = self.lidar_angle + self.car.angle + LIDAR_TO_CAR_ANGLE

            # define a x for the lidar's end point
            lidar_target_x = (math.cos((adj_angle * math.pi)/180) * LIDAR_RANGE) + car_center_x
            # define a y for the lidar's end point
            lidar_target_y = (math.sin((adj_angle * math.pi)/180) * LIDAR_RANGE) + car_center_y

            # update the lidar
            self.lidar_beam.points = [car_center_x, car_center_y, lidar_target_x, lidar_target_y]

            # lidar collisions with barriers
            distance = 1000
            p1 = (self.lidar_beam.points[0], self.lidar_beam.points[1])
            p2 = (self.lidar_beam.points[2], self.lidar_beam.points[3])
            for b in self.barriers:
                p3 = (b.points[0], b.points[1])
                p4 = (b.points[2], b.points[3])
                _distance = find_intersection(p1,p2,p3,p4)
                if _distance is not None: 
                    # on many intersecting walls, pick the closest one
                    distance = min(distance,_distance)
            #print distance

            msg = pid_input()
            if distance is not None:
                #print ("distance to barrier:", distance)
                msg.pid_error = interp(distance, [0,250],[-100,100])
            else:
                msg.pid_error = 1000
            #print (msg.pid_error)
            pub.publish(msg)


class SimApp(App):
    def build(self):
        simulator = Simulator()
        simulator.start_vehicle()
        simulator.load_map(1)
        Clock.schedule_interval(simulator.update, 1.0/120.0)
        return simulator

if __name__ == '__main__':

    print "Load Simulation?: "
    load_sim = raw_input()

    if load_sim == "y" or load_sim == "yes":
        # if loading dont need to save
        SAVE_TRIGGER = SAVE_OPTIONS.NO
        l = os.listdir("simulations/")
        for index,sim in enumerate(l):
            print ( "[ " + str(index) + " ] " + sim)
        sim = -1
        while sim < 0 or sim > len(l) - 1:
            print ("select a simulation's number: ")
            sim = int(raw_input())

        file = l[sim]
        with open ("simulations/"+file, "rb") as infile:
            RENDERED_FRAMES = pickle.load(infile)

    else:
        print "Save simulation? 1 = no, 2 = on success, 3 = on success or failure"
        _save = int(raw_input())
        assert _save == 1 or _save == 2 or _save == 3
        SAVE_TRIGGER = get_save_trigger(_save)

    rospy.init_node('sim_error', anonymous=True)

    SimApp().run()
