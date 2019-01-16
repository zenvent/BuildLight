from neopixel import *
import thread
import time
import requests
import argparse

# LED strip configuration:
LED_COUNT      = 51      # Number of LED pixels.
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 100     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
LED_PIN        = 18      # GPIO

# Animation Speed
REFRESH_RATE = 0.01

# Frequency of CI pulls
BUILD_UPDATE_SECONDS = 15

# Build configurations
class buildObj(object):
    pass

# This example has 3 builds to display on a 51 LED strand
# Configure start to be the first LED, end to be the last led for each build light
buildA = buildObj()
buildA.start = 1
buildA.end = 17
buildA.animation = 0
buildA.oldStatus = ""
buildA.newStatus = ""
buildA.url = "http://{yourJobUrl}/api/json?tree=builds[number,result]{0,2}"

buildB = buildObj()
buildB.start = 18
buildB.end = 34
buildB.animation = 0
buildB.oldStatus = ""
buildB.newStatus = ""
buildB.url = "http://{yourJobUrl}/api/json?tree=builds[number,result]{0,2}"

buildC = buildObj()
buildC.start = 35
buildC.end = 51
buildC.animation = 0
buildC.oldStatus = ""
buildC.newStatus = ""
buildC.url = "http://{yourJobUrl}/api/json?tree=builds[number,result]{0,2}"

builds = [buildA, buildB, buildC]

# Possible build statuses
GREEN_BUILD_STATUS = "GREEN_BUILD"
RED_BUILD_STATUS = "RED_BUILD"
GREEN_BUILDING_STATUS = "GREEN_BUILDING"
RED_BUILDING_STATUS = "RED_BUILDING"
UNKNOWN_BUILD_STATUS = "UNKNOWN"
UNKNOWN_BUILDING_STATUS = "UNKNOWN_BUILDING"

# Colors (note the pattern may be different per light strand, in this example it's GRB)
GREEN = Color(255, 0, 0)
RED = Color(0, 255, 0)
BLUE = Color(0, 0, 255)
WHITE = Color(255, 255, 255)
OFF = Color(0, 0, 0)

# Updates a segment of a neopixel strip
def setSegmentColor(strip, build, color):
    for i in range(build.start-1, build.end):
        strip.setPixelColor(i, color)

# Tracks where in the animation for each build
def animationSequence(build):
    colorRange = 255
    animationSequence = 0
    if(build.animation >= colorRange*2):
        build.animation = 0
        animationSequence = build.animation
    elif(build.animation < colorRange):
        build.animation += 1
        animationSequence = build.animation
    elif(build.animation >= colorRange):
        build.animation += 1
        animationSequence = colorRange - (build.animation - colorRange)
    return animationSequence

#Pulses to/from a color to indicate active build status
def pulseAnimation(strip, build, status):
    i = animationSequence(build)
    if (status == GREEN_BUILDING_STATUS):
        setSegmentColor(strip, build, Color(255, i, i))
    elif (status == RED_BUILDING_STATUS):
        setSegmentColor(strip, build, Color(i, 255, i))
    elif (status == UNKNOWN_BUILDING_STATUS):
        setSegmentColor(strip, build, Color(i, i, 225))

# Makes all led updates visible
def display(strip):
    strip.show()
    time.sleep(REFRESH_RATE)

# Instantly set all pixels to one color
def setStripColor(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

# Get and parse build status
def getBuildStatus(url):
    NEW_BUILD = 0 # The current build status
    OLD_BUILD = 1 # The previous build status
    try:
        data = requests.get(url).json()
    except requests.exceptions.RequestException as e:
        print ("Unable to connect to Jenkins")
        return UNKOWN_BUILD_STATUS
        
    if data is None or not data or data['builds'] is None or not data['builds']:
        print ("Unable to parse response from Jenkins")
        return UNKOWN_BUILD_STATUS

    newBuild = data['builds'][NEW_BUILD]['result']
    if newBuild == "SUCCESS":
        return GREEN_BUILD_STATUS
    elif newBuild == "FAILURE":
        return RED_BUILD_STATUS
    elif newBuild is None or newBuild == "":
        oldBuild = data['builds'][OLD_BUILD]['result']
        if oldBuild == "SUCCESS":
            return GREEN_BUILDING_STATUS
        elif oldBuild == "FAILURE":
            return RED_BUILDING_STATUS
        elif oldBuild == "ABORTED":
            return UNKNOWN_BUILDING_STATUS
    return UNKNOWN_BUILD_STATUS
    
# Threaded method for retreiving the build status from CI server
def updateAllBuilds():
    for build in builds:
        build.oldStatus = build.newStatus
        build.newStatus = getBuildStatus(build.url)
        if build.oldStatus != build.newStatus:
            build.animation = 0
        print(build.newStatus)
        print(build.url)

# Main program logic follows:
if __name__ == '__main__':

    # Create NeoPixel object with appropriate configuration. 
    # Note: the Raspberry PI only supports one pin with PWM, this is why it's virtually divided using the build class
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    setStripColor(strip, OFF)

    # Initial build status
    oldTime = time.time()
    updateAllBuilds()
    
    try:
        while True:
            # After set time fetch new build status without interoupting animations
            if time.time() - oldTime > BUILD_UPDATE_SECONDS:
                oldTime = time.time()
                thread.start_new_thread(updateAllBuilds, ())
            
            # Prepare LED strand with new color information
            for build in builds:
                if build.newStatus == GREEN_BUILD_STATUS:
                    setSegmentColor(strip, build, GREEN)
                elif build.newStatus == RED_BUILD_STATUS:
                    setSegmentColor(strip, build, RED)
                elif build.newStatus == GREEN_BUILDING_STATUS:
                    pulseAnimation(strip, build, GREEN_BUILDING_STATUS)
                elif build.newStatus == RED_BUILDING_STATUS:
                    pulseAnimation(strip, build, RED_BUILDING_STATUS)
                elif build.newStatus == UNKNOWN_BUILDING_STATUS:
                    pulseAnimation(strip, build, UNKNOWN_BUILDING_STATUS)
                elif build.newStatus == UNKNOWN_BUILD_STATUS:
                    setSegmentColor(strip, build, BLUE)
            
            display(strip)

    except:
        setStripColor(strip, OFF)
