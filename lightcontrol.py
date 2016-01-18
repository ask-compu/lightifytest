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

import lightify
import sys
import time
import logging

MODULE = "__main__"

def main(argv):
    logging.basicConfig()

    logger = logging.getLogger(MODULE)
    logger.setLevel(logging.DEBUG)
    #logger.addHandler(logging.StreamHandler())

    liblogger = logging.getLogger('lightify')
    #liblogger.addHandler(logging.StreamHandler())
    liblogger.setLevel(logging.INFO)

    logger.info("Logging %s", MODULE)

    try:
        conn = lightify.Lightify(argv[1])
    except:
        print("Usage: ipaddress luminance(1-100) temperature(2700-6500) onoff(0-1) groupname")
        sys.exit(0)

    conn.update_all_light_status()
    conn.update_group_list()
    for (name, group) in conn.groups().items():
        logger.info("group: %s %s", name, group)

    print("keys:" + str(conn.groups().keys()))
    try:
        #desk = conn.groups()["DJs Room"]
        desk = conn.groups()[argv[5]]
        #desk.set_onoff(0)
        #desk.set_luminance(0, 0)
        desk.set_onoff(1)
        desk.set_luminance(int(argv[2]), 10)
        desk.set_onoff(1)
        desk.set_temperature(int(argv[3]), 10)
        if int(argv[4])==0:
            desk.set_onoff(0)
        elif int(argv[4])==1:
            desk.set_onoff(1)
        else:
            print("Usage: ipaddress luminance(1-100) temperature(2700-6500) onoff(0-1) groupname")
    except:
        print("Usage: ipaddress luminance(1-100) temperature(2700-6500) onoff(0-1) groupname")
        sys.exit(0)


    #sys.exit(0)


    for (addr, light) in conn.lights().items():
        print("%x %d %d %d %s %s" % (addr, light.on(), light.lum(), light.temp(), light.rgb(), light))
        #print(str(addr + light.on() + light.lum() + light.temp() + light.rgb() + light))

    sys.exit(0)

main(sys.argv)
