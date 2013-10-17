import os
import math
import pprint

import Image
import cairo
import StringIO
import rsvg

from xml.dom import minidom

def open_svg_as_image(icon, multiplier = 1.0, max_height = None):
    fn = icon["file"]
    max_height = max_height * multiplier
    maki_resize = [
        (18, 0.75, 12, 1),
        (18, 1.5,  24, 1),
        (18, 2,    24, 1.5),
        (18, 3,    24, 2),
        (12, 1.5,  18, 1),
        (12, 2,    24, 1),
        (12, 3,    24, 1.5),
        (24, 0.75, 18, 1)
    ]

    if "maki" in fn:
        for (srcsize, srcmul, dstsize, dstmul) in maki_resize:
            if str(srcsize) in fn and multiplier == srcmul:
                fn = fn.replace(str(srcsize), str(dstsize))
                multiplier = dstmul
                break

    dom = minidom.parse(fn)
    if icon.get("fill-color"):
        [a.setAttribute("fill", icon["fill-color"]) for a in dom.getElementsByTagName("path") if a.getAttribute("fill")]
        [a.setAttribute("fill", icon["fill-color"]) for a in dom.getElementsByTagName("g") if a.getAttribute("fill")]
    if icon.get("color"):
        [a.setAttribute("stroke", icon["color"]) for a in dom.getElementsByTagName("path") if a.getAttribute("stroke")]
        [a.setAttribute("stroke", icon["color"]) for a in dom.getElementsByTagName("g") if a.getAttribute("stroke")]

    tmpfile = StringIO.StringIO()
    outfile = StringIO.StringIO()
    #svg = rsvg.Handle(file=fn)
    svg = rsvg.Handle(data=dom.toxml())
    svgwidth = float(svg.get_property('width'))
    svgheight = float(svg.get_property('height'))
    resheight = svgheight * multiplier
    if max_height:
        resheight = min(resheight, max_height)
    reswidth = svgwidth * resheight / svgheight
    svgsurface = cairo.SVGSurface(outfile, reswidth, resheight)
    svgctx = cairo.Context(svgsurface)
    #size = max(24, svgwidth, svgheight)
    print fn, svgwidth / reswidth, svgheight / resheight
    svgctx.scale(reswidth / svgwidth, resheight / svgheight)
    svg.render_cairo(svgctx)
    svgsurface.write_to_png(tmpfile)
    svgsurface.finish()
    tmpfile.seek(0)
    im = Image.open(tmpfile)
    bbox = im.getbbox()
    if bbox:
        dx, dy = min(bbox[0], im.size[0]-bbox[2]), min(bbox[1], im.size[1]-bbox[3])
        bbox = (dx, dy, im.size[0] - dx, im.size[1] - dy)
        im = im.crop(bbox)
    return im


def pack_texture(icons=[], multiplier = 1.0, path = "", rasfilter = []):
    images = {}
    strips = []
    area = 0
    for (svg, icon, max_height) in icons:
        if os.path.exists(icon["file"]):
            images[svg] = open_svg_as_image(icon, multiplier, max_height)
            area += images[svg].size[0] * images[svg].size[1]
        else:
            print "bad icon!", icon
    width = 2 ** math.ceil(math.log(area ** 0.5, 2))

    queue = images.keys()
    queue.sort(key = lambda x: -images[x].size[1] * 10000 - images[x].size[0])

    for img in queue:
        for strip in strips:
            if strip["len"] + images[img].size[0] <= width:
                strip["len"] += images[img].size[0]
                if images[img].size[1] > 3*18:
                    print img
                strip["height"] = max(images[img].size[1], strip["height"])
                strip["list"].append(img)
                break
        else:
            strips.append({"len": images[img].size[0], "height": images[img].size[1], "list": [img]})
    height = 2 ** math.ceil(math.log(sum([i["height"] for i in strips]), 2))
    page = Image.new("RGBA", (int(width), int(height)))
    dx, dy = 0, 0
    icon_id = 0
    skin = open(os.path.join(path, 'basic.skn'), "w")
    print >> skin, """<!DOCTYPE skin>
    <skin>
    <page width="%s" height="%s" file="symbols.png">"""%(int(width), int(height))
    for strip in strips:
        for img in strip["list"]:
            page.paste(images[img], (dx, dy))
            icon_id += 1
            print >> skin,"""  <symbolStyle id="%s" name="%s">
    <resourceStyle x="%s" y="%s" width="%s" height="%s"/>
    </symbolStyle>""" % (icon_id, img, dx, dy, images[img].size[0], images[img].size[1])
            dx += images[img].size[0]
        dy += strip["height"]
        dx = 0
    pprint.pprint(strips)

    print >>skin, """ </page>
    </skin>"""
    page.save(os.path.join(path,"symbols.png"))