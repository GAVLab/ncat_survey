#!/usr/bin/env python
"""
Sucessor to `centers_to_osm.py`, created for the Map-Aided Cooperative Inertial 
Navigation project.

Creates an OSM file with two ways: one for the center of each lane. The ways are
closed (first == last). Additionally, the data is smoothed with a spline and 
interpolated. Each node is given a tag with the width of the lane at that 
location. The width is calculated by projecting that individual center line 
survey point on to the adjacent lane markings.

This is different because it adds a 'width' tag for every node in the lane
centerlines, computed by projecting that node to the corresponding lane markings.
It requires the `ains` package which provides `rnet` (a special version)

Usage:
  ./to_osm.py </path/to/destination.osm>

Robert Cofield
2016-04-25
"""
from __future__ import division
import osmwriter
import os, sys
from copy import deepcopy as dcp
from rnet.osm_parser import OsmParserWrapper
from rnet.topology.nodal import NodalTopology
from rnet.topology import Coord
import utm
import numpy as np
import pyqtgraph as pg
from ipdb import set_trace


def list_to_osm(data, destination_file_name, lane_widths=None):
  writer = osmwriter.OSMWriter(destination_file_name)
  version = int(1)
  uuid = 1
  for k in range(len(data)):
    way_ = data[k]
    way_ids = []
    way_node0_uuid = None
    print 'First point in way: ', utm.from_latlon(way_[0][0], way_[0][1])
    for kk in range(len(way_)):
      pt = way_[kk]
      # lat, lon
      if lane_widths:
        tags = {'width': str(lane_widths[k][kk])}
      else:
        tags = None
      writer.node(uuid, pt[0], pt[1], tags=tags, version=version)
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


# lane center: (left lane edge , right lane edge)
correspondence = { 
  'inner': ('inner', 'middle'),
  'outer': ('middle', 'outer'),
}

survey_centers_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'survey', 'centers'))
survey_edges_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'survey', 'stripes'))
lane_file_names = {
  os.path.join(survey_centers_dir, center_file_name+'.txt'): [
    os.path.join(survey_edges_dir, name+'.txt') for name in correspondence[center_file_name]
  ] for center_file_name in correspondence
}

# where to save the OSM file
destination_file_name = os.path.abspath(sys.argv[1])
try: # delete old if necessary
  os.remove(destination_file_name)
except:
  pass

# read data into list, with each item corresponding to a different lane center 
# and being another list, this one containing lat, lon length 2 lists
# ---
# read data into list, same as above, but for lane edges instead of centers
# ignore the overlap, how each lane shares a lane edge with another lane (middle
# stripe) and just create new data list for simplicity 
center_line_data = []
edge_line_data = []
edge_ntops = []
edge_ntop_win = pg.GraphicsWindow()
edge_ntop_figs = []
edge_osm_file_no = 0
for center_file_name in lane_file_names:
  print center_file_name
  pts = [] # the way
  with open(center_file_name, 'r') as file:
    for line in file:
      pts.append([float(val) for val in line.split()]) # a single point
  center_line_data.append(pts)
  edges = [] # both edges for this lane
  ntops = [] # both lane marking NodalTopologies for this lane
  for edge_file_name in lane_file_names[center_file_name]:
    this_edge_osm_file_name = '/tmp/edge'+str(edge_osm_file_no)+'.osm'
    print ' ', edge_file_name
    pts = [] # the way
    with open(edge_file_name, 'r') as file:
      for line in file:
        pts.append([float(val) for val in line.split()]) # a single point
    # write each lane marking to its own OSM file
    list_to_osm([pts], this_edge_osm_file_name)
    ntop = NodalTopology(OsmParserWrapper(this_edge_osm_file_name))
    edge_ntop_figs.append(edge_ntop_win.addPlot())
    ntop.plot(fig=edge_ntop_figs[-1])
    ntops.append(ntop)
    edges.append(pts)
    # write this lane marking to its own OSM file
    # increment file name
    edge_osm_file_no += 1
  edge_ntops.append(ntops)
  edge_line_data.append(edges)
  
# find out the width of the road at every center survey point
lane_widths = []
for k in range(len(center_line_data)):
  ntop_l = edge_ntops[k][0]
  ntop_r = edge_ntops[k][1]
  widths = []
  for center_lla in center_line_data[k]:
    e, n, _, _ = utm.from_latlon(*center_lla)
    coord = Coord(e, n)
    _, _, dist_l = ntop_l.closest_link(coord)
    _, _, dist_r = ntop_r.closest_link(coord)
    widths.append(dist_l+dist_r)
  lane_widths.append(widths)

win_width = pg.GraphicsWindow()
fig_width = win_width.addPlot()
fig_width.addLegend()
fig_width.plot(range(len(lane_widths[0])), lane_widths[0], pen='g', name='first')
fig_width.plot(range(len(lane_widths[1])), lane_widths[1], pen='b', name='second')


win_all = pg.GraphicsWindow()
fig_all = win_all.addPlot()
for k in range(len(center_line_data)):
  clat, clon = zip(*center_line_data[k])
  fig_all.plot(clon, clat, pen='b')
  for kk in range(2):
    elat, elon = zip(*edge_line_data[k][kk])
    fig_all.plot(elon, elat, pen='y')
fig_all.setAspectLocked(ratio=1.0)
fig_all.showGrid(x=True, y=True, alpha=0.5)
fig_all.setLabels(top='all things')


list_to_osm(center_line_data, destination_file_name, lane_widths=lane_widths)

# debug using NodalTopology
centerline_ntop = NodalTopology(OsmParserWrapper(destination_file_name))
fig_final, win_final = centerline_ntop.plot()
fig_final.setLabels(top='Output ntop')

pg.QtGui.QApplication.instance().exec_()