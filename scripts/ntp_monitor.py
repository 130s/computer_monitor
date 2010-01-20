#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of the Willow Garage nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import roslib
roslib.load_manifest('pr2_computer_monitor')

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

import sys
import rospy
import socket
from subprocess import Popen, PIPE

import time

import re

NAME = 'ntp_monitor'

def ntp_monitor(ntp_hostname, offset=500, self_offset=500):
    pub = rospy.Publisher("/diagnostics", DiagnosticArray)
    rospy.init_node(NAME, anonymous=True)

    hostname = socket.gethostname()

    stat = DiagnosticStatus()
    stat.level = 0
    stat.name = "NTP offset from: "+ hostname + " to: " +ntp_hostname
    stat.message = "Acceptable synchronization"
    stat.hardware_id = hostname
    stat.values = []

    self_stat = DiagnosticStatus()
    self_stat.level = 0
    self_stat.name = "NTP offset from: "+ hostname + " to: self."
    self_stat.message = "Acceptable synchronization"
    self_stat.hardware_id = hostname
    self_stat.values = []
    
    while not rospy.is_shutdown():
        for st,host,off in [(stat,ntp_hostname,offset), (self_stat, hostname,self_offset)]:

            try:
                p = Popen(["ntpdate", "-q", host], stdout=PIPE, stdin=PIPE, stderr=PIPE)
                res = p.wait()
                (o,e) = p.communicate()
            except OSError, (errno, msg):
                if errno == 4:
                    break #ctrl-c interrupt
                else:
                    raise
            if (res == 0):
                measured_offset = float(re.search("offset (.*),", o).group(1))*1000000

                st.level = 0
                st.message = "Acceptable synchronization"
                st.values = [ KeyValue("offset (us)", str(measured_offset)) ]
            
                if (abs(measured_offset) > off):
                    st.level = 1
                    st.message = "Offset too great"
                                
            else:
                st.level = 1
                st.message = "Error running ntpupdate"
                st.values = [ KeyValue("offset (us)", "N/A") ]


        msg = DiagnosticArray()
        msg.header.stamp = rospy.get_rostime()
        msg.status = [stat, self_stat]
        pub.publish(msg)
        time.sleep(1)

def ntp_monitor_main(argv=sys.argv):
    import optparse
    parser = optparse.OptionParser(usage="usage: ntp_monitor ntp-hostname []")
    parser.add_option("--offset-tolerance", dest="offset_tol",
                      action="store", default=500,
                      help="Offset from NTP host", metavar="OFFSET-TOL")
    parser.add_option("--self_offset-tolerance", dest="self_offset_tol", 
                      action="store", default=500,
                      help="Offset from self", metavar="SELF_OFFSET-TOL")
    options, args = parser.parse_args(rospy.myargv())
    if (len(args) == 2):
        try:
            offset = int(options.offset_tol)
            self_offset = int(options.self_offset_tol)
        except:
            parser.error("Offsets must be numbers")        
        ntp_monitor(args[1], offset, self_offset)
    else:
        parser.error("Invalid arguments. Must have HOSTNAME [args]. %s" % args)

if __name__ == "__main__":
    try:
        ntp_monitor_main(rospy.myargv())
    except KeyboardInterrupt: pass
    except:
        import traceback
        traceback.print_exc()
