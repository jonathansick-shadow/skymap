#!/usr/bin/env python
#
# LSST Data Management System
# Copyright 2015 AURA/LSST.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <https://www.lsstcorp.org/LegalNotices/>.
#

from __future__ import print_function

import argparse
import matplotlib.pyplot as pyplot

import lsst.afw.cameraGeom as cameraGeom
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.daf.persistence as dafPersist
from lsst.pipe.base.argumentParser import IdValueAction, DataIdContainer


def bboxToRaDec(bbox, wcs):
    """Get the corners of a BBox and convert them to lists of RA and Dec."""
    corners = []
    for corner in bbox.getCorners():
        p = afwGeom.Point2D(corner.getX(), corner.getY())
        coord = wcs.pixelToSky(p).toIcrs()
        corners.append([coord.getRa().asDegrees(), coord.getDec().asDegrees()])
    ra, dec = zip(*corners)
    return ra, dec


def percent(values, p=0.5):
    """Return a value a faction of the way between the min and max values in a list."""
    m = min(values)
    interval = max(values) - m
    return m + p*interval


def main(rootDir, tract, visits, ccds=None, ccdKey='ccd', showPatch=False, saveFile=None):
    butler = dafPersist.Butler(rootDir)
    mapper = butler.mapper
    camera = mapper.camera

    # draw the CCDs
    ras, decs = [], []
    for i_v, visit in enumerate(visits):
        print("%r visit=%r" % (i_v, visit))
        for ccd in camera:
            bbox = ccd.getBBox()
            ccdId = int(ccd.getSerial())

            if (ccds is None or ccdId in ccds) and ccd.getType() is cameraGeom.SCIENCE:
                dataId = {'visit': visit, ccdKey: ccdId}
                try:
                    md = butler.get("calexp_md", dataId)
                    wcs = afwImage.makeWcs(md)

                    ra, dec = bboxToRaDec(bbox, wcs)
                    ras += ra
                    decs += dec
                    color = ('r', 'b', 'c', 'g', 'm')[i_v%5]
                    pyplot.fill(ra, dec, fill=True, alpha=0.2, color=color, edgecolor=color)
                except:
                    pass

    buff = 0.1
    xlim = max(ras)+buff, min(ras)-buff
    ylim = min(decs)-buff, max(decs)+buff

    # draw the skymap
    if showPatch:
        skymap = butler.get('deepCoadd_skyMap', {'tract': 0})
        for tract in skymap:
            for patch in tract:
                ra, dec = bboxToRaDec(patch.getInnerBBox(), tract.getWcs())
                pyplot.fill(ra, dec, fill=False, edgecolor='k', lw=1, linestyle='dashed')
                if xlim[1] < percent(ra) < xlim[0] and ylim[0] < percent(dec) < ylim[1]:
                    pyplot.text(percent(ra), percent(dec, 0.9), str(patch.getIndex()),
                                fontsize=6, horizontalalignment='center', verticalalignment='top')

    # add labels and save
    ax = pyplot.gca()
    ax.set_xlabel("R.A. (deg)")
    ax.set_ylabel("Decl. (deg)")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    fig = pyplot.gcf()
    if saveFile is not None:
        fig.savefig(saveFile)
    else:
        fig.show()


def splitId(argName):
    class SplitIdValueAction(IdValueAction):

        def __call__(self, parser, namespace, values, option_string):
            # Hack to use IdValueAction
            keyValues = [argName + "=" + str(values[0])]
            setattr(namespace, "config", "hack")
            setattr(namespace, argName, DataIdContainer())
            # Parse the data into namespace.argName.idList
            IdValueAction.__call__(self, parser, namespace, keyValues, "--"+argName)
            # Save the list into namespace.argName
            setattr(namespace, argName,
                    list({int(dataId[argName]) for dataId in getattr(namespace, argName).idList}))
    return SplitIdValueAction

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Root directory of data repository")
    parser.add_argument("tract", type=int, help="Tract to show")
    parser.add_argument("visits", nargs=1, action=splitId("visits"),
                        help="Visits to show", metavar="VISIT1[^VISIT2[^VISIT3...]")
    parser.add_argument("-c", "--ccds", nargs=1, action=splitId("ccds"), default=None,
                        help="CCDs to show", metavar="CCD1[^CCD2[^CCD3...]")
    parser.add_argument("-p", "--showPatch", action='store_true', default=False,
                        help="Show the patch boundaries")
    parser.add_argument("--saveFile", type=str, default=None,
                        help="Filename to write the plot to")
    parser.add_argument("--ccdKey", default="ccd", help="Data ID name of the CCD key")
    args = parser.parse_args()

    main(args.root, args.tract, visits=args.visits, ccds=args.ccds,
         ccdKey=args.ccdKey, showPatch=args.showPatch, saveFile=args.saveFile)
