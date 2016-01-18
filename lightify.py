#!/usr/bin/python
#
# Copyright 2014 Mikael Magnusson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

#
# WIP Python module for Osram lightify
# Communicates with a gateway connected to the same LAN via TCP port 4000
# using a binary protocol
#

import binascii
import socket
import sys
import struct
import time
import logging

MODULE = __name__
PORT = 4000

COMMAND_ALL_LIGHT_STATUS = 0x13
COMMAND_GROUP_LIST = 0x1e
COMMAND_GROUP_INFO = 0x26
COMMAND_LUMINANCE = 0x31
COMMAND_ONOFF = 0x32
COMMAND_TEMP = 0x33
COMMAND_COLOUR = 0x36
COMMAND_LIGHT_STATUS = 0x68

# Commands
# 13 all light status (returns list of light address, light status, light name)
# 1e group list (returns list of group id, and group name)
# 26 group status (returns group id, group name, and list of light addresses)
# 31 set group luminance
# 32 set group onoff
# 33 set group temp
# 36 set group colour
# 68 light status (returns light address and light status (?))

class Luminary(object):
    def __init__(self, conn, logger, name):
        self.__logger = logger
        self.__conn = conn
        self.__name = name

    def name(self):
        return self.__name

    def set_onoff(self, on):
        data = self.__conn.build_onoff(self, on)
        self.__conn.send(data)
        self.__conn.recv()

    def set_luminance(self, lum, time):
        data = self.__conn.build_luminance(self, lum, time)
        self.__conn.send(data)
        self.__conn.recv()

    def set_temperature(self, temp, time):
        data = self.__conn.build_temp(self, temp, time)
        self.__conn.send(data)
        self.__conn.recv()

    def set_rgb(self, r, g, b, time):
        data = self.__conn.build_colour(self, r, g, b, time)
        self.__conn.send(data)
        self.__conn.recv()


class Light(Luminary):
    def __init__(self, conn, logger, addr, name):
        super(Light, self).__init__(conn, logger, name)
        self.__logger = logger
        self.__conn = conn
        self.__addr = addr

    def addr(self):
        return self.__addr

    def __str__(self):
        return "<light: %s>" % self.name()

    def update_status(self, on, lum, temp, r, g, b):
        self.__on = on
        self.__lum = lum
        self.__temp = temp
        self.__r = r
        self.__g = g
        self.__b = b

    def on(self):
        return self.__on

    def set_onoff(self, on):
        self.__on = on
        super(Light, self).set_onoff(on)

    def lum(self):
        return self.__lum

    def set_luminance(self, lum, time):
        self.__lum = lum
        super(Light, self).set_luminance(lum, time)

    def temp(self):
        return self.__temp

    def set_temperature(self, temp, time):
        self.__temp = temp
        super(Light, self).set_temperature(temp, time)

    def rgb(self):
        return (self.red(), self.green(), self.blue())

    def set_rgb(self, r, g, b, time):
        self.__r = r
        self.__g = g
        self.__b = b

        super(Light, self).set_rgb(r, g, b, time)

    def red(self):
        return self.__r

    def green(self):
        return self.__g

    def blue(self):
        return self.__b

    def build_command(self, command, data):
        return self.__conn.build_light_command(command, self, data)

class Group(Luminary):
    def __init__(self, conn, logger, idx, name):
        super(Group, self).__init__(conn, logger, name)
        self.__conn = conn
        self.__logger = logger
        self.__idx = idx
        self.__lights = []

    def idx(self):
        return self.__idx

    def lights(self):
        return self.__lights

    def set_lights(self, lights):
        self.__lights = lights

    def __str__(self):
        s = ""
        for light_addr in self.lights():
            if light_addr in self.__conn.lights():
                light = self.__conn.lights()[light_addr]
            else:
                light = "%x" % light_addr
            s = s + str(light) + " "

        return "<group: %s, lights: %s>" % (self.name(), s)

    def build_command(self, command, data):
        return self.__conn.build_command(command, self, data)

class Lightify:
    def __init__(self, host):
        self.__logger = logging.getLogger(MODULE)
        self.__logger.addHandler(logging.NullHandler())
        self.__logger.info("Logging %s", MODULE)

        self.__seq = 1
        self.__groups = {}
        self.__lights = {}

        try:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
            sys.exit(1)
 
        try:
            self.__sock.connect((host, PORT))
        except socket.error as msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
            sys.exit(2)

    def groups(self):
        """Dict from group name to Group object."""
        return self.__groups

    def lights(self):
        """Dict from light addr to Light object."""
        return self.__lights

    def light_byname(self, name):
        self.__logger.debug(len(self.lights()))

        for light in list(self.lights().values()):
            if light.name() == name:
                return light

        return None

    def next_seq(self):
        self.__seq = self.__seq + 1
        return self.__seq

    def build_global_command(self, command, data):
        length = 6 + len(data)

        return struct.pack("<H6B", length, 0x02, command, 0, 0, 0x7, self.next_seq()) + data

    def build_basic_command(self, flag, command, group_or_light, data):
        length = 14 + len(data)

        return struct.pack("<H6B", length, flag, command, 0, 0, 0x7, self.next_seq()) + group_or_light + data

    def build_command(self, command, group, data):
        length = 14 + len(data)

        return self.build_basic_command(0x02, command, struct.pack("<8B", group.idx(), 0, 0, 0, 0, 0, 0, 0), data)

    def build_light_command(self, command, light, data):
        length = 6 + 8 + len(data)

        return self.build_basic_command(0x00, command, struct.pack("<Q", light.addr()), data)

    def build_onoff(self, item, on):
        return item.build_command(COMMAND_ONOFF, struct.pack("<B", on))

    def build_temp(self, item, temp, time):
        return item.build_command(COMMAND_TEMP, struct.pack("<HH", temp, time))

    def build_luminance(self, item, luminance, time):
        return item.build_command(COMMAND_LUMINANCE, struct.pack("<BH", luminance, time))

    def build_colour(self, item, red, green, blue, time):
        return item.build_command(COMMAND_COLOUR, struct.pack("<BBBBH", red, green, blue, 0xff, time))

    def build_group_info(self, group):
        return self.build_command(COMMAND_GROUP_INFO, group, "")

    def build_all_light_status(self, flag):
        return self.build_global_command(COMMAND_ALL_LIGHT_STATUS, struct.pack("<B", flag))

    def build_light_status(self, light):
        return light.build_command(COMMAND_LIGHT_STATUS, "")


    def build_group_list(self):
        return self.build_global_command(COMMAND_GROUP_LIST, "")

    def group_list(self):
        groups = {}
        data = str(self.build_group_list())
        self.send(data)
        data = self.recv()
        (num,) = struct.unpack("<H", data[7:9])
        self.__logger.debug('Num %d', num)

        for i in range(0, num):
            pos = 9+i*18
            payload = data[pos:pos+18]

            (idx, name) = struct.unpack("<H16s", payload)
            name = name.replace('\0', "")

            groups[idx] = name
            self.__logger.debug("Idx %d: '%s'", idx, name)

        return groups

    def update_group_list(self):
        lst = self.group_list()
        groups = {}

        for (idx, name) in list(lst.items()):
            group = Group(self, self.__logger, idx, name)
            group.set_lights(self.group_info(group))

            groups[name] = group

        self.__groups = groups


    def group_info(self, group):
        lights = []
        data = str(self.build_group_info(group))
        self.send(data)
        data = self.recv()
        payload = data[7:]
        (idx, name, num) = struct.unpack("<H16sB", payload[:19])
        name = name.replace('\0', "")
        self.__logger.debug("Idx %d: '%s' %d", idx, name, num)
        for i in range(0,num):
            pos = 7 + 19 + i * 8
            payload = data[pos:pos+8]
            (addr,) = struct.unpack("<Q", payload[:8])
            self.__logger.debug("%d: %x", i, addr)

            lights.append(addr)

        #self.read_light_status(addr)
        return lights

    def send(self, data):
        self.__logger.debug('sending "%s"', binascii.hexlify(data))
        return self.__sock.sendall(data)

    def recv(self):
        lengthsize = 2
        data = self.__sock.recv(lengthsize)
        (length,) = struct.unpack("<H", data[:lengthsize])

        self.__logger.debug(len(data))
        string = ""
        expected = length + 2 - len(data)
        self.__logger.debug("Length %d", length)
        self.__logger.debug("Expected %d", expected)

        while expected > 0:
            self.__logger.debug('received "%d %s"', length, binascii.hexlify(data))
            data = self.__sock.recv(expected)
            expected = expected - len(data)
            string = string + str(data)
        self.__logger.debug('received "%s"', binascii.hexlify(string))
        return data

    def update_light_status(self, light):
        data = bytes(self.build_light_status(light))
        self.send(data)
        data = self.recv()
        return


        (on,lum,temp,red,green,blue,h) = struct.unpack("<27x2BH4B16x", data)
        self.__logger.debug('status: %0x %0x %d %0x %0x %0x %0x', on,lum,temp,red,green,blue,h)

        self.__logger.debug( 'onoff: %d', on)
        self.__logger.debug('temp:  %d', temp)
        self.__logger.debug('lum:   %d', lum)
        self.__logger.debug('red:   %d', red)
        self.__logger.debug('green: %d', green)
        self.__logger.debug('blue:  %d', blue)
        return (on, lum, temp, red, green, blue)

    def update_all_light_status(self):
        data = str(self.build_all_light_status(1))
        self.send(data)
        data = self.recv()
        (num,) = struct.unpack("<H", data[7:9])

        self.__logger.debug('num: %d', num)

        old_lights = self.__lights
        new_lights = {}

        status_len = 50
        for i in range(0, num):
            pos = 9 + i * status_len
            payload = data[pos:pos+status_len]

            self.__logger.debug("%d %d %d", i, pos, len(payload))

            (a,addr,status,name,extra) = struct.unpack("<HQ16s16sQ", payload)
            name = name.replace('\0', "")

            self.__logger.debug('light: %x %x %s %x', a, addr, name, extra)
            if addr in old_lights:
                light = old_lights[addr]
            else:
                light = Light(self, self.__logger, addr, name)

            (b,on,lum,temp,red,green,blue,h) = struct.unpack("<Q2BH4B", status)
            self.__logger.debug('status: %x %0x', b, h)

            self.__logger.debug('onoff: %d', on)
            self.__logger.debug('temp:  %d', temp)
            self.__logger.debug('lum:   %d', lum)
            self.__logger.debug('red:   %d', red)
            self.__logger.debug('green: %d', green)
            self.__logger.debug('blue:  %d', blue)

            light.update_status(on, lum, temp, red, green, blue)
            new_lights[addr] = light
        #return (on, lum, temp, red, green, blue)

        self.__lights = new_lights
