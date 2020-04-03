# Treat all division as float division even in python2
from __future__ import division

import re
from enum import Enum
import serial
import numpy as np
from annotypes import add_call_types, Anno, TYPE_CHECKING
from scanpointgenerator import CompoundGenerator

from malcolm.core import Future, NumberMeta, Block, PartRegistrar, Put, Request, Widget
from malcolm.modules import builtin, scanning
if TYPE_CHECKING:
    from typing import Dict, List

# Pull re-used annotypes into our namespace in case we are subclassed
AIV = builtin.parts.AInitialVisibility
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri

with Anno("serial port for arduino"):
    ASerialPort = str

with Anno("name of axis"):
    AAxisName = str


class ArduinoMotorChildPart(builtin.parts.ChildPart):
    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 axis_1,  # type: AAxisName
                 axis_2,  # type: AAxisName
                 port,  # type: ASerialPort
                 initial_visibility=None  # type: AIV
                 ):
        # type: (...) -> None
        super(ArduinoMotorChildPart, self).__init__(name, mri, initial_visibility)
        # Axis information stored from validate
        self.axis_mapping = None  # type: Dict[str, MotorInfo]
        # What sort of triggers to output
        self.output_triggers = None
        # Stored generator for positions
        self.generator = None  # type: CompoundGenerator
        self.posn = dict()
        self.posn[axis_1] = NumberMeta(
            description=axis_1,
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model()
        self.posn[axis_2] = NumberMeta(
            description=axis_2,
            tags=[Widget.TEXTUPDATE.tag()]).create_attribute_model()

        self.port = serial.Serial(port, 9600, timeout=10)
        # self.port.open()
 

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ArduinoMotorChildPart, self).setup(registrar)
        # Hooks
        # registrar.hook(scanning.hooks.ValidateHook, self.on_validate)
        registrar.hook(scanning.hooks.PreConfigureHook, self.do_home)
        registrar.hook((scanning.hooks.ConfigureHook,
                        scanning.hooks.PostRunArmedHook,
                        scanning.hooks.SeekHook), self.on_configure)
        registrar.hook(scanning.hooks.RunHook, self.on_run)
        registrar.hook((scanning.hooks.AbortHook,
                        scanning.hooks.PauseHook), self.on_abort)
        for k in self.posn.keys():
            registrar.add_attribute_model(k, self.posn[k])

    @add_call_types
    def do_home(self):
        # type: (...) -> None
        self.port.reset_input_buffer()
        self.port.write("home\n")
        resp = self.port.readline().rstrip()
        if resp != "HOME_START":
            raise Exception("Home returned bad state at start (%s)" % resp)
        resp = self.port.readline().rstrip()
        if resp != "HOME_END":
            raise Exception("Home returned bad state at end (%s)" % resp)             
        

    def parse_positions(self, resp):
        tokens = [x.split(':') for x in resp.split(';')]
        if tokens[0][0] == "posn":
            posn = [x.split('=') for x in tokens[0][1].split(',')]
            posn[0][1] = posn[0][1].split('/')
            posn[1][1] = posn[1][1].split('/')
            self.posn[posn[0][0]].set_value(posn[0][1][0])
            self.posn[posn[1][0]].set_value(posn[1][1][0])
            if len(posn[0][1]) == 2:
                 self.posn[posn[0][0]].meta.display.set_limitLow(int(-int(posn[0][1][1])/2))   
                 self.posn[posn[0][0]].meta.display.set_limitHigh(int(int(posn[0][1][1])/2))  
            if len(posn[1][1]) == 2:
                 self.posn[posn[1][0]].meta.display.set_limitLow(int(-int(posn[1][1][1])/2))   
                 self.posn[posn[1][0]].meta.display.set_limitHigh(int(int(posn[1][1][1])/2))


    def get_positions(self):
        self.port.reset_input_buffer()
        self.port.write("?\n")
        # "posn:x=0/260,r=0;lims:hi=0,lo=0"
        resp = self.port.readline().rstrip()
        self.parse_positions(resp)             
        

    # Allow CamelCase as arguments will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(self,
                     context,  # type: scanning.hooks.AContext
                     completed_steps,  # type: scanning.hooks.ACompletedSteps
                     steps_to_do,  # type: scanning.hooks.AStepsToDo
                     part_info,  # type: scanning.hooks.APartInfo
                     generator,  # type: scanning.hooks.AGenerator
                     axesToMove,  # type: scanning.hooks.AAxesToMove
                     ):
        # type: (...) -> None
        context.unsubscribe_all()
        child = context.block_view(self.mri)
       	scan_params = dict()
        scan_axes = generator.generators
        if len(scan_axes) != 2:
            raise Exception("Expected 2 axes, got %d" % len(scan_axes))
        self.generator = generator
        scan_params["fast_axis"] = scan_axes[1].axes[0]
        scan_params["slow_axis"] = scan_axes[0].axes[0]
        scan_params["slow_start"] = int(scan_axes[0].start[0])
        scan_params["slow_end"] = int(scan_axes[0].stop[0])
        scan_params["time_step"] = int(generator.duration*1000.0)  # convert s to ms
        
        scan_params["fast_step_cnt"] = int(scan_axes[1].size)
        scan_params["fast_speed"] =  1 #\
            #(scan_axes[1].stop[0] - scan_axes[1].start[0]) /\
            # (scan_axes[1].size * generator.duration*1000.0)

        scan_params["slow_step"] = int(
            (scan_axes[0].stop[0] - scan_axes[0].start[0]) / scan_axes[0].size)
        
        self.port.reset_input_buffer()
        self.port.write(("scan({fast_axis:s}:{fast_speed:f},{fast_step_cnt:d};" + \
                         "{slow_axis:s}:{slow_start:d},{slow_step:d}," + \
                         "{slow_end:d};{time_step:d})\n").format(**scan_params))

        resp = self.port.readline().rstrip()
        self.parse_positions(resp)                    

        resp = self.port.readline().rstrip()
        if resp != "SCAN_READY":
            raise Exception("Configure returned bad state (%s)" % resp)

    @add_call_types
    def on_run(self, context):
        # type: (scanning.hooks.AContext) -> None
        if self.generator is not None:
            self.port.write("run\n")
            resp = self.port.readline().rstrip()
            if resp != "SCAN_START":
                raise Exception("Run returned bad state (%s)" % resp)
            steps = 0
            while steps < self.generator.generators[0].size:
                resp = self.port.readline().rstrip()
                self.parse_positions(resp)
                steps += 1
                self.registrar.report(scanning.infos.RunProgressInfo(
                              steps*self.generator.generators[1].size))                
        

    @add_call_types
    def on_abort(self, context):
        # type: (scanning.hooks.AContext) -> None
        self.port.reset_input_buffer()
        self.port.write("abort\n");
        resp = self.port.readline().rstrip()
        if resp != "SCAN_ABRT":
            raise Exception("Abort returned bad state (%s)" % resp)
        

        
