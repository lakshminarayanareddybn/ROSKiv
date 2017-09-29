from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty,\
    ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.graphics import Line
from kivy.animation import Animation

from random import randint

from geometry_funcs import find_intersection

from frame import frame

import math

from kivy.config import Config
Config.set('graphics', 'width', '1400')
Config.set('graphics', 'height', '720')
Config.set('graphics', 'resizable', False)

x = 0
y = 0
center = 0
ticks = 0
xv = 1
yv = 1
default_frame = frame((700,360),0)

RENDERED_FRAMES =[]

def render_frame(RENDERED_FRAMES, current_frame):
    # if the current frame is new make a new frame to be rendered

    # if the current frame is not new return the next frame


class Wall(Widget):
    pass

class Barrier(Widget):
    pass

class SimCar(Widget):

    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)

    angle = NumericProperty(0)

    velocity = ReferenceListProperty(velocity_x, velocity_y)


    def move(self, angle=.75):
        global x
        global y
        global center
        global ticks
        global xv, xy

        # update the car to new angle
        self.angle += angle

        self.velocity_x = math.cos((self.angle * math.pi) / 180)
        self.velocity_y = math.sin((self.angle * math.pi) / 180)

        # update vehicle's location
        self.pos = Vector(*self.velocity) + self.pos

        x = self.center_x
        y = self.center_y
        center = self.center

class Simulator(Widget): # Root Widget

    global x, xv
    global y, yv
    global center

    lidar_angle = 0
    car_x_label = NumericProperty(0)
    car_y_label = NumericProperty(0)

    car = ObjectProperty(None) # Get a reference of the car object defined
                              # in the widget rules

    barrier = ObjectProperty(None)

    def start_vehicle(self):
        self.car.center = self.center
        with self.canvas:
            self.lidar_beam = Line(points=[0,0,0,0])
            self.barrier = Line(points=[2000,900,800,900])

    def update(self, dt,frame = default_frame):

        self.car.move()


        self.car_x_label = x
        self.car_y_label = y

        # Collisions with edges of map

        if self.car.collide_widget(self.wall_left) or self.car.collide_widget(self.wall_right):
            self.car.center = self.center

        if self.car.collide_widget(self.wall_top) or self.car.collide_widget(self.wall_down):
            self.car.center = self.center

        # update lidar widget

        # angle of lidar relative to the car, 0 = directly forward

        LIDAR_TO_CAR_ANGLE = 45
        LIDAR_RANGE = 250

        # adjust angle so it remains relative to the car
        adj_angle = self.lidar_angle + self.car.angle + LIDAR_TO_CAR_ANGLE
        # define a x for the lidar's end point
        lidar_target_x = (math.cos((adj_angle * math.pi)/180) * LIDAR_RANGE) + center[0]
        # define a y for the lidar's end point
        lidar_target_y = (math.sin((adj_angle * math.pi)/180) * LIDAR_RANGE) + center[1]

        # update the lidar
        self.lidar_beam.points = [center[0], center[1], lidar_target_x, lidar_target_y]

        # lidar collisions with barrier

        p1 = (self.lidar_beam.points[0], self.lidar_beam.points[1])
        p2 = (self.lidar_beam.points[2], self.lidar_beam.points[3])
        p3 = (self.barrier.points[0], self.barrier.points[1])
        p4 = (self.barrier.points[2], self.barrier.points[3])
        distance = find_intersection(p1,p2,p3,p4)
        if distance is not None:
            print (distance)




class SimApp(App):
    def build(self):
        simulator = Simulator()
        simulator.start_vehicle()
        Clock.schedule_interval(simulator.update, 1.0/60.0)
        return simulator

if __name__ == '__main__':
    SimApp().run()
