#! /usr/bin/env python
"""Reads datafile in stdin, prints out requested route"""

from __future__ import print_function
from math import sin, cos, pi, sqrt
from heapq import heappush, heappop
from collections import namedtuple
import fileinput
import sys
import os

# coordinate types
coord = namedtuple('Coordinates', ['latitude', 'longitude', 'altitude'])
coord.__new__.__defaults__ = (0, 0, 0)
spher = namedtuple('Spherical', ['theta', 'phi', 'radius'])
horizon = namedtuple('Horizon', ['sin', 'cos'])

class RouteNotFound(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class Network(object):
    """ network (graph) of connected satellites """
    def __init__(self):
	self._satellites = set()

    def connect(self, satellite):
	satellite.neighbours = self.visible_satellites_at(satellite.coordinates)
	self._satellites.add(satellite)
	for n in satellite.neighbours:
	    n.connect_with(satellite)

    def __iter__(self):
	return self._satellites.__iter__()

    def reset(self):
	""" recalculate the network """
	# O(n^2), but n is small
	for s in self._satellites:
	    s.neighbours = self.visible_satellites_at(*s.coordinates)

    def visible_satellites_at(self, coordinates):
	""" return set of visible satellites at given coordinates """
	t = Satellite('T', coordinates)
	visible = (s for s in self._satellites if s.lineofsight(t))
	return set(visible)

    def route(self, start, finish):
	# visible satellites at start and finish coordinates
	startset = self.visible_satellites_at(start)
	if not startset:
	    raise RouteNotFound("No satellites in sight at start coordinates")
	finishset = self.visible_satellites_at(finish)
	if not finishset:
	    raise RouteNotFound("No satellites in sight at finish coordinates")
	queue = [(0, s, []) for s in startset]
	seen = set()
	try:
	    while True:
		(length, satellite, path) = heappop(queue)
		if satellite not in seen:
		    path = path + [satellite]
		    seen.add(satellite)
		    if satellite in finishset:
			return path
		    for neighbour in satellite.neighbours:
			heappush(queue, (length + 1, neighbour, path))
	except IndexError:
	    raise RouteNotFound("No route found between given coordinates")
	    
class Satellite(object):
    def __init__(self, id, coordinates):
	self._id = id
	self._coordinates = coord(*(float(c) for c in coordinates))

	# spherical coordinates
	conv = 2 * pi / 360
	radius_of_earth = float(6371)
	theta = (90 - self._coordinates.latitude) * conv
	phi = self._coordinates.longitude * conv
	self._spherical = spher(theta, phi, radius_of_earth + self._coordinates.altitude)

	# angle between the satellite and its horizon from the center of the earth
	coshorizon = radius_of_earth / self._spherical.radius
	sinhorizon = sqrt(1 - (coshorizon * coshorizon))
	self._horizon = horizon(sinhorizon, coshorizon)

	# known neighbour satellites within the line of sight
	self._neighbours = set()

    def __str__(self):
	return self._id

    def lineofsight(self, another):
	# cosine of the sum of horizon angles
	cossumhorizon = self._horizon.cos * another._horizon.cos - self._horizon.sin * another._horizon.sin
	# cosine of angle between the satellites
	cospsi = cos(self._spherical.theta) * cos(another._spherical.theta) + sin(self._spherical.theta) * sin(another._spherical.theta) * cos(self._spherical.phi - another._spherical.phi)
	return cossumhorizon < cospsi

    @property
    def coordinates(self):
	return self._coordinates

    @property
    def neighbours(self):
	return self._neighbours

    @neighbours.setter
    def neighbours(self, newset):
	self._neighbours = newset

    def connect_with(self, neighbour):
	self._neighbours.add(neighbour)

def fail(message, exitcode=1):
    print(message, file=sys.stderr)
    sys.exit(exitcode)

if __name__ == '__main__':
    network = Network()

    try:
	for line in fileinput.input():
	    if line.startswith('#'):
		continue
	    if line.startswith('SAT'):
		ID, lat, lon, alt = line.split(',')
		loc = coord(lat, lon, alt)
		s = Satellite(ID, loc) 
		network.connect(s)
	    if line.startswith('ROUTE'):
		(route, lat1, lon1, lat2, lon2) = line.split(',')
		start = coord(lat1, lon1) 
		finish = coord(lat2, lon2)
    except Exception as e:
	raise
	fail("Error while processing data", exitcode=os.EX_DATAERR)

    try:
	path = network.route(start, finish)
    except RouteNotFound as e:
	fail(e)
    # print out the path 
    print(*path, sep=',')
    
