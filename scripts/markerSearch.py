#!/usr/bin/env python
import rospy 
from marker_navigation.msg import Marker
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool
from std_srvs.srv import SetBool, SetBoolResponse, Trigger, TriggerResponse
from math import pi, sin, cos

min_angle = 0.02

increment = min_angle*10
goal = [0,0,0]

marker_detected = False
marker_search = False
marker_aligned = False
goal_set = False
goal_published = False
rot = False
motion = False
align_dist = False

goal_stop = rospy.ServiceProxy('ria/odom/goal/stop', SetBool)
goal_reset = rospy.ServiceProxy('ria/odom/goal/reset', Trigger)
odom_reset = rospy.ServiceProxy('ria/odom/reset', Trigger)

pub = rospy.Publisher("/ria/odom/local/goal",Twist, queue_size=1)

def start_search(msg):
    global min_angle, align_dist, increment, goal, marker_detected, marker_search, marker_aligned, goal_set, goal_published, rot, motion
    marker_search = msg.data
    if not marker_search:
        min_angle = 0.02

        increment = min_angle*10
        goal = [0,0,0]
        marker_detected = False
        marker_search = False
        marker_aligned = False
        goal_set = False
        goal_published = False
        rot = False
        motion = False
        align_dist = False
        try:
            goal_stop(True)
            goal_reset()
            odom_reset()
            goal_stop(False)
        except rospy.ServiceException as e:
            print("Service call falied: %s"%e)
    response = SetBoolResponse()
    response.success = True
    rospy.loginfo("Searching Set: {}".format(marker_search))
    return response

def detectCallback(msg):
    global increment, goal_set, goal_published, marker_aligned, motion, marker_detected, marker_search, goal_stop, goal_reset, odom_reset, align_dist
    if not marker_search or goal_published or align_dist:
        return
    increment = min_angle
    marker_aligned = msg.aligned
    if not marker_detected and msg.id == 2:
        rospy.loginfo("Marker Detected {}".format(msg))
        try:
            marker_detected = True
            goal_stop(True)
            rospy.loginfo("Goal Stopped Marker Detected")
            goal_reset()
            rospy.loginfo("Goal Reseted Marker Detected")
            odom_reset()
            rospy.loginfo("Odom Reseted Marker Detected")
            goal_stop(False)
        except rospy.ServiceException as e:
            print("Service call falied: %s"%e)
    elif marker_detected and marker_aligned and not goal_set:
        rospy.loginfo("Marker Aligned {}".format(msg))
        try:
            marker_detected = True
            goal_stop(True)
            rospy.loginfo("Goal Stopped Marker Aligned")
            goal_reset()
            rospy.loginfo("Goal Reseted Marker Aligned")
            odom_reset()
            rospy.loginfo("Odom Reseted Marker Aligned")
            #goal_stop(False)
        except rospy.ServiceException as e:
            print("Service call falied: %s"%e)
        if msg.distance > 1.2 and not align_dist:
            goal[1] = msg.distance - 1
            align_dist = True
            return
        goal[0] = ((90 - abs(msg.theta))*pi)/180.0
        if msg.theta > 0:
            goal[0] = -1*goal[0]
        goal[1] = msg.distance*sin(abs(msg.theta)*pi/180.0)
        goal[2] = msg.distance*cos(abs(msg.theta)*pi/180.0) - 0.15
        goal_set = True
        rospy.loginfo("Goal Set: {}".format(goal))
    motion = False

def posCallback(msg):
    global motion, marker_search, goal_stop,goal_set, increment, pub, goal_published, align_dist
    s_ang = msg
    if (not marker_search) or goal_published or motion:
        return
    if not goal_set:
        s_ang.angular.z += increment
        #goal_stop(False)
        pub.publish(s_ang)
    elif align_dist:
        s_ang.angular.z = 0.0
        s_ang.linear.x = goal[1]
        goal_stop(False)
        rospy.loginfo("Goal Started")
        pub.publish(s_ang)
        rospy.loginfo("Goal Published: {}".format(s_ang))
    elif goal_set:
        goal_published = True
        s_ang.angular.z = goal[0]
        s_ang.linear.x = goal[1]
        goal_stop(False)
        rospy.loginfo("Goal Started")
        pub.publish(s_ang)
        rospy.loginfo("Goal Published: {}".format(s_ang))
    motion = True

def goalArrived(msg):
    global motion, rot,goal_stop, goal_reset, odom_reset, goal, pub, goal_published, align_dist
    motion = False
    align_dist = False
    if goal_published and (not rot):
        goal_reset()
        rospy.loginfo("Goal Reseted")
        odom_reset()
        rospy.loginfo("Odom Reseted Marker")
        dock = Twist()
        dock.linear.x = -1*goal[2]
        if goal[0]>0:
            dock.angular.z = 1.5708
            pub.publish(dock)
        else:
            dock.angular.z = -1.5708
            pub.publish(dock)
        rot = True

def listner():
    rospy.init_node('marker_search', anonymous=True)

    rospy.wait_for_service('ria/odom/goal/stop')
    rospy.wait_for_service('ria/odom/goal/reset')
    rospy.wait_for_service('ria/odom/reset')

    rospy.Subscriber('/ria/odom/marker', Marker, detectCallback)
    rospy.Subscriber('/ria/odom/local', Twist, posCallback)
    rospy.Subscriber('/ria/odom/goal_fb', Bool, goalArrived)
    m_search = rospy.Service('ria/odom/marker/search',SetBool, start_search)
    rospy.spin()

if __name__=='__main__':
    listner()
