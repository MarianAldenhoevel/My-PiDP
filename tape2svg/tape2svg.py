import math
import logging
import os
import sys
import time
import argparse 

import font

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas

# Conversion function for argparse booleans
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

# Set up argparse and get the command line options.
def parse_commandline():

    global options

    parser = argparse.ArgumentParser(
        description = 'Create a SVG image of a computer paper tape from binary data.', 
    )

    parser.add_argument('-ll', '--log-level',
        action = 'store',
        default = 'DEBUG',
        help ='Set the logging output level to CRITICAL, ERROR, WARNING, INFO or DEBUG (default: %(default)s)',
        dest ='log_level',
        metavar = 'level'
    )

    parser.add_argument('-if', '--input-file',
        action = 'store',
        default = '',
        help = 'Filename to read the input data from (default: %(default)s)',
        dest = 'inputfilename',
        metavar = 'filename'
    )

    parser.add_argument('-of', '--output-file',
        action = 'store',
        default = 'output.svg',
        help = 'Output file for the SVG data, for multiple pages a numerical suffix is added (default: %(default)s)',
        dest = 'outputfilename',
        metavar = 'filename'
    )

    parser.add_argument('-bc', '--bit-count',
        action = 'store',
        default = 8,
        help = 'How many bits in the tape, supported values are 5,7 and 8 (default: %(default)s)',
        dest = 'bitcount',
        metavar = 'num'
    )

    parser.add_argument('-li', '--lead-in',
        action = 'store',
        default = 10,
        help = 'How many rows of lead-in should we "punch" (default: %(default)s)',
        dest = 'leadin',
        metavar = 'num'
    )

    parser.add_argument('-lo', '--lead-out',
        action = 'store',
        default = 10,
        help = 'How many rows of lead-out should we "punch" (default: %(default)s)',
        dest = 'leadout',
        metavar = 'num'
    )

    parser.add_argument('-pt', '--punch-title',
        action = 'store',
        default = '',
        help = 'When set will punch a human-readable title at the front of the tape (default: %(default)s)',
        dest = 'punchtitle',
        metavar = 'string'
    )

    parser.add_argument('-cm', '--cut-marks',
        action = 'store',
        default = True,
        type = str2bool,
        help = 'When set will add cut-marks just outside of the page margins (default: %(default)s)',
        dest = 'cutmarks',
        metavar = 'flag'
    )

    parser.add_argument('-tc', '--tape-color',
        action = 'store',
        default = '#ccc', #'#fff7e0',
        help = 'How to render the paper color (default: %(default)s)',
        dest = 'tapecolor',
        metavar = 'html-color'
    )

    parser.add_argument('-hc', '--hole-color',
        action = 'store',
        default = 'white',
        help = 'How to render the hole color (default: %(default)s)',
        dest = 'holecolor',
        metavar = 'html-color'
    )

    parser.add_argument('-orh', '--only-render-holes',
        action = 'store',
        default = True,
        type = str2bool,
        help = 'Only render holes, not space for holes. This is useful if you want to post-process the SVG (default: %(default)s)',
        dest = 'onlyrenderholes',
        metavar = 'flag'
    )

    parser.add_argument('-ps', '--page-size',
        action = 'store',
        default = '',
        help = 'When given the tape is split up into parts no bigger than the given page format supports ''Tape'', ''A4'', ''Letter'' and ''Legal'' (default: %(default)s)',
        dest = 'pagesize',
        metavar = 'inches'
    )

    parser.add_argument('-ml', '--margin-left',
        action = 'store',
        default = 0.5,
        help = 'Left margin of the page in inches (default: %(default)sin) not used it page-size is ''Tape''',
        dest = 'marginleft',
        metavar = 'inches'
    )

    parser.add_argument('-mt', '--margin-top',
        action = 'store',
        default = 0.5,
        help = 'Top margin of the page in inches (default: %(default)sin) not used it page-size is ''Tape''',
        dest = 'margintop',
        metavar = 'inches'
    )

    parser.add_argument('-mr', '--margin-right',
        action = 'store',
        default = 0.5,
        help = 'Right margin of the page in inches (default: %(default)sin) not used it page-size is ''Tape''',
        dest = 'marginright',
        metavar = 'inches'
    )

    parser.add_argument('-mb', '--margin-bottom',
        action = 'store',
        default = 0.5,
        help = 'Bottom margin of the page in inches (default: %(default)sin) not used it page-size is ''Tape''',
        dest = 'marginbottom',
        metavar = 'inches'
    )

    parser.add_argument('-cs', '--column-space',
        action = 'store',
        default = 0.1,
        help = 'Space between columns in inches (default: %(default)sin) not used it page-size is ''Tape''',
        dest = 'columnspace',
        metavar = 'inches'
    )

    parser.add_argument('-os', '--open-svg',
        action = 'store',
        default = True,
        type = str2bool,
        help = 'Open resulting SVG file for viewing (default: %(default)s)',
        dest = 'opensvg',
        metavar = 'flag'
    )

    parser.add_argument('-da', '--dec-arrows',
        action = 'store',
        default = True,
        type = str2bool,
        help = 'When set draw DEC decorations on the tape (default: %(default)s)',
        dest = 'decarrows',
        metavar = 'flag'
    )

    parser.add_argument('-ff', '--fan-fold',
        action = 'store',
        default = 0.0,
        type = float,
        help = 'When set breaks the column at every fan-fold inches so you can tape it there (default: %(default)s)',
        dest = 'fanfold',
        metavar = 'inches'
    )

    parser.add_argument('-pdf', '--pdffile-name',
        action = 'store',
        default = '',
        help = 'When given creates a single PDF file from all output pages (default: %(default)s)',
        dest = 'pdffilename',
        metavar = 'filename'
    )


    options = parser.parse_args()
    options.log_level_int = getattr(logging, options.log_level, logging.INFO)

    # The two most common widths were 11/16 inch (17.46 mm) for five bit codes,
    # and 1 inch (25.4 mm) for tapes with six or more bits.
    options.tapewidth = 11/16 if (options.bitcount <= 5) else 1.0

    # Find a page size
    if options.pagesize.upper() == 'A4':
        options.pagesize = (210 / 2.54/10, 297 / 2.54/10)
    elif options.pagesize.upper() == 'Letter'.upper():
        options.pagesize = (8.5, 11.0)
    elif options.pagesize.upper() == 'Legal'.upper():
        options.pagesize = (8.5, 14.0)
    elif (options.pagesize == '') or (options.pagesize.upper() == 'Tape'.upper()):
        options.marginleft = 0
        options.margintop = 0
        options.marginright = 0
        options.marginbottom = 0
        options.pagesize = (options.tapewidth, 0)
    else: 
        raise ValueError('Pagesize ''{pagesize}'' is not supported'.format(pagesize=options.pagesize))
        
    # How much space is on the page in total?
    space = options.pagesize[1] - options.margintop - options.marginbottom

    # If fan-fold requested limit the printable area to that inches.
    if options.fanfold and (space > options.fanfold):
        space = options.fanfold
        options.marginbottom = options.pagesize[1] - options.margintop - space

    # We want this to be a integer multiple of the hole spacing of 0.1 inch
    rowspace = math.floor(space/0.1)*0.1
    options.marginbottom = options.marginbottom + (space-rowspace)

    options.pagefilenames = []

    options.outputfile = None

# Set up a logger each for a file in the output folder and the console.      
def setup_logging():
  
    global options
  
    fh = logging.FileHandler(os.path.dirname(os.path.realpath(__file__)) + '\\tape2svg.log')
    fh.setLevel(options.log_level_int)

    ch = logging.StreamHandler()
    ch.setLevel(options.log_level_int)

    ch.setFormatter(logging.Formatter('({thread}) [{levelname:7}] {name} - {message}', style='{'))
    fh.setFormatter(logging.Formatter('{asctime} ({thread}) [{levelname:7}] {name} - {message}', style='{'))

    root = logging.getLogger()
    root.addHandler(ch)
    root.addHandler(fh)
    root.setLevel(logging.DEBUG)

    logging.getLogger('svglib.svglib').setLevel(logging.INFO)
  
def indent(str):
    return str + ' '*4

def unindent(str):
    return str[0:-4]

def writeSVGHeader():

    global options

    options.outputfile.write('''<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        version="1.1" baseProfile="full"
        width="{width:.3f}in" height="{height:.3f}in">
        <title>tape2svg</title>
        <desc>Generated from binary data</desc>
'''.format(
    width = options.pagesize[0],
    height = options.pagesize[1]
))

    options.indent = indent(options.indent)
    options.indent = indent(options.indent)

def writeSVGDrawTape():
    
    global options

    writeSVGComment('Tape background')
    options.indent = indent(options.indent)
    try:
        height = height=min(options.tapelength, options.pagesize[1] - options.margintop - options.marginbottom)

        # Create a clip path around the current tape section
        options.clippathid = 'tape-section-' + str(options.rowspunched) 

        options.outputfile.write(options.indent + '<clipPath id="{id}">\n'.format(id = options.clippathid))
        
        options.indent = indent(options.indent)
        try:
            options.outputfile.write(options.indent + '<rect x="{left:.3f}in" y="{top:.3f}in" width="{width:.3f}in" height="{height:.3f}in" />\n'.format(
                left=options.x,
                top=options.y,
                width=options.tapewidth,
                height=height
            ))
            
        finally:
            options.indent = unindent(options.indent)
        
        options.outputfile.write(options.indent + '</clipPath>\n')
            
        # Tape background
        options.outputfile.write(options.indent + '<rect x="{left:.3f}in" y="{top:.3f}in" width="{width:.3f}in" height="{height:.3f}in" stroke="none" fill="{tapecolor}" />\n'.format(
            left=options.x,
            top=options.y,
            width=options.tapewidth,
            height=height,
            tapecolor=options.tapecolor
        ))

        # Draw DEC-Arrows?
        if options.decarrows:
            
            arrowdistance = 10 # inches
            
            # How far along the tape are we at the top of this column
            toptapeoffset = options.rowspunched * 0.1

            # Round that position down to the nearest marker position and make
            # relative to the top tape offset. This is a negative number indicating
            # a position along the complete tape, relative to the top of this section.
            markerpos = math.floor(toptapeoffset / arrowdistance) * arrowdistance - arrowdistance - toptapeoffset + 2
            
            while markerpos < toptapeoffset + height:
                
                # Group for common clipping.
                options.outputfile.write(options.indent + '<g clip-path="url(#{clippathid})">\n'.format(
                    clippathid = options.clippathid
                ))
                options.indent = indent(options.indent)
                try:

                    left = options.x + 0.1
                    bottom = markerpos + options.margintop
                    right = options.x + options.tapewidth - 0.1
                    top = bottom - (right - left) / 2
                    center = (left + right) / 2

                    options.outputfile.write(options.indent + '<line x1="{x1:.3f}in" y1="{y1:.3f}in" x2="{x2:.3f}in" y2="{y2:.3f}in" stroke="blue" stroke-width="0.02in" />\n'.format(
                        x1 = left,
                        y1 = bottom,
                        x2 = right,
                        y2 = bottom
                    ))

                    options.outputfile.write(options.indent + '<line x1="{x1:.3f}in" y1="{y1:.3f}in" x2="{x2:.3f}in" y2="{y2:.3f}in" stroke="blue" stroke-width="0.02in" />\n'.format(
                        x1 = right,
                        y1 = bottom,
                        x2 = center,
                        y2 = top
                    ))

                    options.outputfile.write(options.indent + '<line x1="{x1:.3f}in" y1="{y1:.3f}in" x2="{x2:.3f}in" y2="{y2:.3f}in" stroke="blue" stroke-width="0.02in" />\n'.format(
                        x1 = center,
                        y1 = top,
                        x2 = left,
                        y2 = bottom
                    ))

                    left = left + 0.12
                    right = right - 0.12
                    bottom = bottom - 0.05
                    top = top + 0.07
                    
                    options.outputfile.write(options.indent + '<line x1="{x1:.3f}in" y1="{y1:.3f}in" x2="{x2:.3f}in" y2="{y2:.3f}in" stroke="blue" stroke-width="0.02in" />\n'.format(
                        x1 = left,
                        y1 = bottom,
                        x2 = right,
                        y2 = bottom
                    ))

                    options.outputfile.write(options.indent + '<line x1="{x1:.3f}in" y1="{y1:.3f}in" x2="{x2:.3f}in" y2="{y2:.3f}in" stroke="blue" stroke-width="0.02in" />\n'.format(
                        x1 = right,
                        y1 = bottom,
                        x2 = center,
                        y2 = top
                    ))

                    options.outputfile.write(options.indent + '<line x1="{x1:.3f}in" y1="{y1:.3f}in" x2="{x2:.3f}in" y2="{y2:.3f}in" stroke="blue" stroke-width="0.02in" />\n'.format(
                        x1 = center,
                        y1 = top,
                        x2 = left,
                        y2 = bottom
                    ))

                    options.outputfile.write(options.indent + '<text stroke="none" fill="blue" font-size="10pt" font-family="sans-serif" transform="translate({left}, {top}) rotate(90)">D I G I T A L   E Q U I P M E N T   C O R P O R A T I O N   -   P R O G R A M M E D   D A T A    P R O C E S S O R</text>\n'.format(
                        left = 96 * (options.x + options.tapewidth - 0.2),
                        top = 96 * (markerpos + options.margintop + 0.5)
                    ))

                    options.outputfile.write(options.indent + '<text stroke="blue" stroke-width="2px" fill="none" font-size="44pt" font-family="sans-serif" transform="translate({left}, {top}) rotate(90)">PDP</text>\n'.format(
                        left = 96 * (options.x + 0.15),
                        top = 96 * (markerpos + options.margintop + 3.5)
                    ))
                finally:
                    options.indent = unindent(options.indent)

                options.outputfile.write(options.indent + "</g>\n")

                # Advance marker position until we drop out of the bottom of the current section of tape
                markerpos += arrowdistance # inches

    finally:
        options.indent = unindent(options.indent)

    if options.cutmarks:
        
        writeSVGComment('Cut marks')
        options.indent = indent(options.indent)
        
        try:
            #  In left margin top
            options.outputfile.write(options.indent + '<line x1="{left:.3f}in" y1="{top:.3f}in" x2="{right:.3f}in" y2="{top:.3f}in" stroke-dasharray="1,2" stroke="#ccc" stroke-width="1px" />\n'.format(
                left = 0,
                right = options.marginleft,
                top = options.margintop
            ))

            # In left margin bottom
            options.outputfile.write(options.indent + '<line x1="{left:.3f}in" y1="{top:.3f}in" x2="{right:.3f}in" y2="{top:.3f}in" stroke-dasharray="1,2" stroke="#ccc" stroke-width="1px" />\n'.format(
                left = 0,
                right = options.marginleft,
                top = options.pagesize[1] - options.marginbottom                
            ))

            #  In right margin top
            options.outputfile.write(options.indent + '<line x1="{left:.3f}in" y1="{top:.3f}in" x2="{right:.3f}in" y2="{top:.3f}in" stroke-dasharray="1,2" stroke="#ccc" stroke-width="1px" />\n'.format(
                left = options.pagesize[0] - options.marginright,
                right = options.pagesize[0],
                top = options.margintop
            ))

            # In right margin bottom
            options.outputfile.write(options.indent + '<line x1="{left:.3f}in" y1="{top:.3f}in" x2="{right:.3f}in" y2="{top:.3f}in" stroke-dasharray="1,2" stroke="#ccc" stroke-width="1px" />\n'.format(
                left = options.pagesize[0] - options.marginright,
                right = options.pagesize[0],
                top = options.pagesize[1] - options.marginbottom             
            ))

            # In top margin left
            options.outputfile.write(options.indent + '<line x1="{left:.3f}in" y1="{top:.3f}in" x2="{left:.3f}in" y2="{bottom:.3f}in" stroke-dasharray="1,2" stroke="#ccc" stroke-width="1px" />\n'.format(
                left = options.x,
                top = 0,
                bottom = options.margintop             
            ))

            # In top margin right
            options.outputfile.write(options.indent + '<line x1="{left:.3f}in" y1="{top:.3f}in" x2="{left:.3f}in" y2="{bottom:.3f}in" stroke-dasharray="1,2" stroke="#ccc" stroke-width="1px" />\n'.format(
                left = options.x + options.tapewidth,
                top = 0,
                bottom = options.margintop             
            ))

            # In bottom margin left
            options.outputfile.write(options.indent + '<line x1="{left:.3f}in" y1="{top:.3f}in" x2="{left:.3f}in" y2="{bottom:.3f}in" stroke-dasharray="1,2" stroke="#ccc" stroke-width="1px" />\n'.format(
                left = options.x,
                top = options.pagesize[1] - options.marginbottom,
                bottom = options.pagesize[1]             
            ))

            # In top margin right
            options.outputfile.write(options.indent + '<line x1="{left:.3f}in" y1="{top:.3f}in" x2="{left:.3f}in" y2="{bottom:.3f}in" stroke-dasharray="1,2" stroke="#ccc" stroke-width="1px" />\n'.format(
                left = options.x + options.tapewidth,
                top = options.pagesize[1] - options.marginbottom,
                bottom = options.pagesize[1]             
            ))

        finally:
            options.indent = unindent(options.indent)

# Advance to the next row to punch. Some confusion here because they look like columns...
def nextPunchRow():

    global options

    options.y += 0.1 
    
    # Have we passed the bottom of the tape section?
    if options.y - (options.pagesize[1] - options.marginbottom) + 0.1 > 0.01: # Epsilonitis
        
        # Start a new tape section.
        options.x = options.x - options.tapewidth - options.columnspace
        options.y = options.margintop

        # Reduce tape length by what we have already rendered: One full column.
        options.tapelength = options.tapelength - (options.pagesize[1] - options.margintop - options.marginbottom)
        
        if options.x + options.tapewidth > options.pagesize[0]:
            # New page
            closepage()
        else:
            writeSVGDrawTape()

def writeSVGDrawByte(data):

    global options

    # Tape for punching was 0.00394 inches (0.1 mm) thick. The two most common widths 
    # were 11/16 inch (17.46 mm) for five bit codes, and 1 inch (25.4 mm) for tapes with 
    # six or more bits. Hole spacing was 0.1 inch (2.54 mm) in both directions. Data holes 
    # were 0.072 inches (1.83 mm) in diameter; feed holes were 0.046 inches (1.17 mm).[4]

    if not options.outputfile:
        newpage()

    writeSVGComment('{char} - {data:#04x} - {data:#010b}'.format(
        char = chr(data) if (data >= 0x20) and (data <= 0x7e) else ' ',
        data = data
    ))
    options.indent = indent(options.indent)
    try:
        cx = options.tapewidth - 0.1 # Least significant bit on the right
        for bitindex in range(0, 8):
            bit = data & 1
            data >>= 1

            if bit:
                fill = options.holecolor
            else:   
                fill = options.tapecolor

            if ((options.onlyrenderholes == True) and (bit)) or (options.onlyrenderholes == False):
                options.outputfile.write(options.indent + '<circle cx="{cx:.3f}in" cy="{cy:.3f}in" r="0.036in" fill="{fill}"/>\n'.format(
                    cx=options.x + cx,
                    cy=options.y + 0.05,
                    fill=fill
                ))

            cx -= 0.1

            if bitindex==2:
                # Feed hole
                options.outputfile.write(options.indent + '<circle cx="{cx:.3f}in" cy="{cy:.3f}in" r="0.023in" fill="{fill}"/>\n'.format(
                    cx=options.x + cx,
                    cy=options.y + 0.05,
                    fill=options.holecolor
                ))                
                cx -= 0.1
    finally:
        options.indent = unindent(options.indent)
    
    # Next row
    nextPunchRow()
    options.rowspunched += 1

def writeSVGDrawData():

    global options

    logger = logging.getLogger('main')
    
    if not options.outputfile:
        newpage()
    
    writeSVGComment('{n} bytes of data'.format(n=os.stat(options.inputfilename).st_size))
    options.indent = indent(options.indent)
    try:        
    
        bytecount = 0    

        inputfile = open(options.inputfilename, 'rb')
        try:
            read = inputfile.read(1)
            while read != b'':
                bytecount += 1

                writeSVGDrawByte(read[0])

                read = inputfile.read(1)
        finally:
            inputfile.close()    

    finally:
        options.indent = unindent(options.indent)
        writeSVGComment('End of data')

    logger.info('{bytecount} bytes of input processed.'.format(
        bytecount=bytecount
    ))

def writeSVGComment(comment):

    global options

    logger = logging.getLogger('main')
    logger.debug('<!-- ' + comment + ' -->')

    if not options.outputfile:
        newpage()

    options.outputfile.write(options.indent + '<!-- ' + comment + ' -->\n')

def writeSVGDrawPunchString(string):

    global options

    if not options.outputfile:
        newpage()

    writeSVGComment('Punch text \'' + string + '\'')
    options.indent = indent(options.indent)
    
    try:
        fontdata = font.font8x8_basic

        for char in string:
            if ord(char) < len(fontdata):
                glyph = fontdata[ord(char)]
                
                # Skip characters we don't have glyphs for, but not the space
                if (char==' ') or (sum(glyph) != 0):
                    # We want to punch 8 rows, the first one with all the
                    # LSBs from each entry in the glyph. The second with
                    # second-LSB etc.. This turns the glyph on it's side.
                    for glyphcolumn in range(0,8):
                        colbitmask = 1 << glyphcolumn
                        
                        byte = 0
                        bit = 1
                        for g in glyph:
                            bitset = (g & colbitmask)
                            if bitset:
                                byte = byte | bit
                            bit *= 2
                            
                        writeSVGDrawByte(byte) 
    
    finally:
        options.indent = unindent(options.indent)
        writeSVGComment('End of readable text')

def writeSVGFooter():

    global options

    if not options.outputfile:
        newpage()

    options.indent = ''
    options.outputfile.write('''</svg>''')

def closepage():

    global options

    if options.outputfile:
        
        # For back sides: Close mirroring group        
        if options.reverse:
            options.outputfile.write(options.indent + '</g>\n')

        writeSVGFooter()
        options.outputfile.close()
        options.outputfile = None

def newpage():

    global options

    closepage()

    options.pagenumber += 1
    
    logger = logging.getLogger('main')
    logger.debug('Starting page #{pagenumber}.'.format(
        pagenumber = options.pagenumber + 1
    ))

    # Build a file name for this page
    (basename, ext) = os.path.splitext(options.outputfilename)
    pagefilename = basename
    if options.pagenumber > 0:
        pagefilename += '.' + str(options.pagenumber) 
    if options.reverse:
        pagefilename += '.reverse'
    pagefilename += ext

    options.pagefilenames.append(pagefilename)

    options.outputfile = open(pagefilename, 'w')
    options.indent = ''
    
    options.x = options.pagesize[0] - options.marginright - options.tapewidth
    options.y = options.margintop
    
    writeSVGHeader()

    # For back sides we need to mirror
    if options.reverse:
        writeSVGComment('Reverse image')
        options.outputfile.write(options.indent + '<g transform="scale(1,-1) translate(0, {translate:.3f})">\n'.format(
            translate = -96 * options.pagesize[1]            
        ))

    writeSVGDrawTape()

def createpages(reverse):

    global options

    logger = logging.getLogger('main')

    # Size the tape in inches
    options.tapelength = options.leadin * 0.1
     
    if options.inputfilename:
        options.tapelength += os.stat(options.inputfilename).st_size * 0.1 

    if options.punchtitle:
        if options.punchtitle:
            options.tapelength += 8 * len(options.punchtitle) * 0.1

    options.tapelength += options.leadout * 0.1

    # In Tape mode size page to the tape itself
    if options.pagesize[1] == 0:
        options.pagesize = (options.pagesize[0], options.tapelength)
    
    options.rowspunched = 0
    options.pagenumber = -1
    options.reverse = reverse

    writeSVGComment('{n} bytes of lead-in'.format(n=options.leadin))
    options.indent = indent(options.indent)
    try:        
        for _ in range(0, options.leadin):
            writeSVGDrawByte(0)    
    finally:
        options.indent = unindent(options.indent)

    if options.punchtitle:
        writeSVGDrawPunchString(options.punchtitle)
        
    if options.inputfilename:
        writeSVGDrawData()

    writeSVGComment('{n} bytes of lead-out'.format(n=options.leadout))
    options.indent = indent(options.indent)
    try:        
        for _ in range(0, options.leadout):
            writeSVGDrawByte(0)    
    finally:
        options.indent = unindent(options.indent)

    closepage()
    
    logger.info('{rowspunched} rows punched. Generated {pages} page{s} of SVG.'.format(
        rowspunched=options.rowspunched,
        pages=options.pagenumber + 1,
        s = 's' if options.pagenumber > 0 else ''
    ))

def convertpagestoPDF():

    logger = logging.getLogger('main')
    
    logger.info('Creating PDF in {pdffilename}.'.format(
            pdffilename = options.pdffilename
        ))

    pdfpagecount = 0

    # The pagesize argument is a tuple of two numbers in points (1/72 of an inch). 
    c = canvas.Canvas(options.pdffilename, pagesize = (options.pagesize[0] * 72, options.pagesize[1] * 72))    

    for pagefilename in options.pagefilenames: 
        drawing = svg2rlg(pagefilename)
        renderPDF.draw(drawing, c, 0, 0)
        c.showPage()
        pdfpagecount += 1   
        logger.debug('Generated page #{n}.'.format(
            n = pdfpagecount
        )) 

    c.save()

    logger.info('Generated {pdfpagecount} page{s} of PDF.'.format(
        pdfpagecount = pdfpagecount,
        s = 's' if pdfpagecount>1 else ''
    ))


def main():
  
    global options
    
    parse_commandline()
    setup_logging()

    logger = logging.getLogger('main')
    logger.info('Starting. Writing to {outputfilename}.'.format(
        outputfilename=options.outputfilename))

    logger.debug("Pagesize is {width:.3f}in x {height:.3f}in.".format(
        width = options.pagesize[0],
        height = options.pagesize[1]
    ))

    logger.debug("Margins are: Left: {left:.3f}in, Top: {top:.3f}in, Right: {right:.3f}in, Bottom: {bottom:.3f}in.".format(
        left = options.marginleft,
        top = options.margintop,
        right = options.marginright,
        bottom = options.marginbottom
    ))

    logger.debug('Create front pages.')
    createpages(False)

    logger.debug('Create back pages.')
    createpages(True) 

    if options.pdffilename:
        convertpagestoPDF()    
        
    logger.info('Done.')

if __name__ == '__main__':
    main()
