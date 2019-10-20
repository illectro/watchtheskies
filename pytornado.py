#!/usr/bin/python

import tornado.ioloop
import tornado.web
import time
import threading
import ephem

satellites = []
rocks = []
all_rocks = []
sanFrancisco = ephem.Observer()
sanFrancisco.lon = '-122.4194'
sanFrancisco.lat = '37.7749'
sanFrancisco.elevation = 20
date = ephem.now()
prev_time = ephem.now()
alt = 0
az = 0
distance = 0
name = "None"
timeDelta = 0
fastTime = 0
deltaDist = 0
closeSatDat = None
dataMode = 0



def updateLoop():
    global rocks,sanFrancisco,date,alt,az,name,distance,timeDelta,fastTime,deltaDist,all_rocks,satellites,closeSatDat,dataMode
    while 1:
        date = ephem.date(ephem.now() + timeDelta)
        timeDelta = timeDelta + fastTime
        sanFrancisco.date = date
        close = 10000000000
        crock = None
        all_rocks = []
        for dats in rocks:
            rock = dats[0]
            rock.compute(date)
            rockInfo = (dats[1].split(',')[0],rock.earth_distance,rock.a_ra,rock.a_dec,rock.mag)
            all_rocks.append(rockInfo)
            if(rock.earth_distance < close):
                close = rock.earth_distance
                crock = dats

        closeSat = 100000000000
        closeSatDat = None
        for satdat in satellites:
            sat = satdat[0]
            try:
                sat.compute(sanFrancisco)
                if(sat.alt > 1):
                    interesting = sat.range / (90-sat.alt)
                else:
                    interesting = sat.range
                if(interesting < closeSat):
                    closeSat = interesting
                    closeSatDat = satdat
            except:
                x = 1

        rock = crock[0]
        rock.compute(sanFrancisco)
        parts = crock[1].split(',')
        name = parts[0]
        newDist = int(ephem.meters_per_au * close * 0.001)
        deltaDist = newDist - distance
        distance = newDist

        # reset dataMode if we move out of bounds
        if(closeSatDat == None):
            dataMode = 0

        if(dataMode == 0):
            alt = rock.alt
            az = rock.az
        else:
            alt = satdat[0].alt
            az = satdat[0].az  

        time.sleep(3)


def loadObjects():
    global rocks,satellites
    with open("minor_planets.txt") as fp:
        line = fp.readline()
    
        while line:
            if not (line[0] == '#'):
                rock = ephem.readdb(line)
                dat = (rock,line)
                rocks.append(dat)
            line = fp.readline()

    with open("active_satellites.txt") as fp:
        line1 = fp.readline()
        line2 = fp.readline()
        line3 = fp.readline()

        while line3:
            sat = ephem.readtle(line1, line2, line3)
            satdat = (sat, line1.rstrip())
            satellites.append(satdat)
            line1 = fp.readline()
            line2 = fp.readline()
            line3 = fp.readline()


class AllAsteroids(tornado.web.RequestHandler):
    def get(self):
        global all_rocks
        self.write('<head></head><body><p><table style="width:100%">')
        for rock in all_rocks:
            self.write('<tr>')
            for field in rock:
                 self.write('<td>' + str(field) + '</td>')
            self.write('</tr>')
        self.write('</table></body>')

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        global name,alt,az,distance,dataMode,closeSatDat
        self.write('<head><meta http-equiv="refresh" content="3"></head><body style="background-color:white;"><p style="text-align:center;font-size:60px;">')
        if(dataMode == 0):
            self.write('Watch the skies!<br>' + name + "<br>Altitude: " + str(alt) + "<br>Azimuth: " + str(az) + "<br>" + format(distance, ',d') + "km<br>" + str(date) + "<br>")
            if (deltaDist < 0):
                self.write("It's Coming Right For Us!!!!!<br>")
        else:
            self.write('They are Watching Us!<br>' + closeSatDat[1] + '<br>Altitude: ' + str(alt) + "<br>Azimuth: " + str(az) + "<br>" + str(int(closeSatDat[0].range * 0.001)) + "km<br>" + str(date) + "<br>") 

        self.write('</p></body>')

class ControlPanel(tornado.web.RequestHandler):
    def get(self):
        global fastTime,timeDelta 
        self.write('<head></head><body><p><a href="/timedelta/0">Reset time</a><br><a href="/fasttime/0">Reset Speed</a><br><a href="/setdate/2017/10/28">2017-10-28</a><br><a href="/setdate/2011/2/6">2019-2-10</a><br><a href="/fasttime/600">Fast Time!</a><br><a href="/sats">Set Satellite Mode</a><br><a href="/rocks">Set Asteroid Mode</a></body>')
        

class AltAz(tornado.web.RequestHandler):
    def get(self):
        global alt,az
        if(alt < 0):
            alt = ephem.degrees(0)
        stralt = str(alt).split(':')
        fracalt = str(float(stralt[1]) / 60.0)[1:4]
        straz = str(az).split(':')
        fracaz = str(float(straz[1]) / 60.0)[1:4]
        
        self.write(stralt[0] + fracalt + "\t" + straz[0] + fracaz)

class SetSatMode(tornado.web.RequestHandler):
    def get(self):
        global timeDelta,fastTime,dataMode
        timeDelta = 0
        fastTime = 0
        dataMode = 1 
        self.write("Satellite mode")

class SetRockMode(tornado.web.RequestHandler):
    def get(self):
        global timeDelta,fastTime,dataMode
        timeDelta = 0
        fastTime = 0
        dataMode = 0 
        self.write("Rock mode")


class SetTimeDelta(tornado.web.RequestHandler):
    def get(self,offset):
        global timeDelta
        timeDelta = int(offset)
        self.write(str(timeDelta))

class SetFastTime(tornado.web.RequestHandler):
    def get(self,offset):
        global fastTime
        fastTime = float(offset)
        self.write(str(fastTime))
        fastTime /= 86400

class SetDate(tornado.web.RequestHandler):
    def get(self,date):
        global timeDelta
        try:
            d = ephem.Date(date)
            timeDelta = (d - ephem.now())
            self.write(str(timeDelta))
        except:
            self.write("Error parsing Date")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/timedelta/([-0-9]+)", SetTimeDelta),
        (r"/fasttime/([-\.0-9]+)", SetFastTime),
        (r"/setdate/(.+)", SetDate),
        (r"/altaz", AltAz),
        (r"/controls",ControlPanel),
        (r"/all", AllAsteroids),
        (r"/sats", SetSatMode),
        (r"/rocks", SetRockMode),
    ])

if __name__ == "__main__":
    loadObjects()
    coreLoop = threading.Thread(target=updateLoop, args=())        
    coreLoop.start()

    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
