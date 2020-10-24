import asyncio
import json
import logging
import os
import re
import subprocess

from collections import OrderedDict
from pprint import pformat as pf

import cothread
from annotypes import Anno

from kasa import (
    Discover,
    SmartBulb,
    SmartDevice,
    SmartLightStrip,
    SmartPlug,
    SmartStrip,
)

from malcolm import __version__
from malcolm.core import (
    Alarm,
    AlarmSeverity,
    BadValueError,
    ProcessStartHook,
    ProcessStopHook,
    StringMeta,
    Widget,
)
from malcolm.modules import builtin

class KasaController(builtin.controllers.ManagerController):
    def __init__(
        self,
        mri: builtin.controllers.AMri,
        config_dir: builtin.controllers.AConfigDir,
    ) -> None:
        super().__init__(mri, config_dir)
        self.finder = Discover()
        self.devices = None
        
        self.register_hooked(ProcessStartHook, self.init)

    def init(self):
        devices = OrderedDict(asyncio.run(self.finder.discover()))
        print(devices)

        dev_controllers = []
        devMris = []
        devNames = []
        for dev in devices.items():
            devMris += [host_to_mri(dev[1], self.mri)]
            devNames += [host_to_camel(dev[1])]
            dev_controller = make_kasa_controller(dev, devMris[-1])
            dev_controllers += [dev_controller]
        self.process.add_controllers(dev_controllers)
        for ind in range(len(devMris)):
            self.add_part(builtin.parts.ChildPart(name=devNames[ind], mri=devMris[ind]))        
        super().init()


def host_to_camel(device):
    splitName = device.alias.split(' ')
    camelName = [x.lower() for x in splitName]
    for ind in range(1, len(camelName)):
        namePart = camelName[ind][0].upper()
        namePart += camelName[ind][1:]
        camelName[ind] = namePart
    return ''.join(camelName)
    

def host_to_mri(device, mri):
    return mri + ':' + ':'.join([x.upper() for x in device.alias.split(' ')])
    

def make_kasa_controller(device, mri):
    controller = builtin.controllers.StatefulController(mri)

    controller.add_part(builtin.parts.IconPart(os.path.split(__file__)[0] + "/../icons/kasa-logo.svg"))    

    controller.add_part(builtin.parts.StringPart("address", "IP address of device", value=device[0]))
    return controller

