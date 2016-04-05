#!/usr/bin/env python
"""
Creates an OSM file with two ways: one for the center of each lane. The ways are
closed (first == last). No tags are added.

Requires osmium library and python wrapper. Available here:
  https://github.com/osmcode/libosmium
  https://github.com/osmcode/pyosmium
These work as of the time of writing, but the above libraries are still under 
heavy development

Usage:
  python centers_to_osm.py </path/to/destination.osm>

This file can be extended so that it will output any of the survey circuits with 
some intelligent command line parsing.

Robert Cofield
2016-03-29
"""
import osmwriter
import os, sys
from copy import deepcopy as dcp

survey_centers_dir = os.path.join(os.path.dirname(__file__), '..', 'survey', 'centers')
lane_center_file_names = [os.path.join(survey_centers_dir, name) for name in ('inner.txt', 'outer.txt')]
destination_file_name = os.path.abspath(sys.argv[1])
try:
  os.remove(destination_file_name)
except:
  pass

# read data into list, with each item corresponding to a different lane center file
# 
data = []
for center_file_name in lane_center_file_names:
  pts = []
  with open(center_file_name, 'r') as file:
    for line in file:
      pts.append([float(val) for val in line.split()])
  data.append(pts)

writer = osmwriter.OSMWriter(destination_file_name)
version = int(1)
uuid = 1
for way_ in data:
  way_ids = []
  way_node0_uuid = None
  for pt in way_:
    # lat, lon
    writer.node(uuid, pt[0], pt[1], version=version)
    way_ids.append(uuid)
    if len(way_ids) == 1:
      # this is the first node in the way. We want the way to be closed since 
      # the track is circular, so save this uuid for later to append it to the
      # end of the way's uuid's.
      way_node0_uuid = dcp(uuid)
    uuid += 1
  # add the first node to the end since we know this is a nice perfect loop
  way_ids.append(way_node0_uuid)
  writer.way(uuid, {}, way_ids, version=version)
  uuid += 1
writer.close()