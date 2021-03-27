import logging
import os
import sys
import time
import argparse 

import font

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
    global challenges_found

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
        help = 'Filename to read the input data from (default: %(default))',
        dest = 'inputfilename',
        metavar = 'filename'
    )

    parser.add_argument('-of', '--output-file',
        action = 'store',
        default = 'output.svg',
        help = 'Output file for the SVG data (default: %(default))',
        dest = 'outputfilename',
        metavar = 'filename'
    )

    parser.add_argument('-bc', '--bit-count',
        action = 'store',
        default = 8,
        help = 'How many bits in the tape, supported values are 5,7 and 8 (default: %(default))',
        dest = 'bitcount',
        metavar = 'num'
    )

    parser.add_argument('-li', '--lead-in',
        action = 'store',
        default = 10,
        help = 'How many rows of lead-in should we "punch" (default: %(default))',
        dest = 'leadin',
        metavar = 'num'
    )

    parser.add_argument('-lo', '--lead-out',
        action = 'store',
        default = 10,
        help = 'How many rows of lead-out should we "punch" (default: %(default))',
        dest = 'leadout',
        metavar = 'num'
    )

    parser.add_argument('-pt', '--punch-title',
        action = 'store',
        default = '',
        help = 'When set will punch a human-readable title at the front of the tape (default: %(default))',
        dest = 'punchtitle',
        metavar = 'string'
    )

    parser.add_argument('-tc', '--tape-color',
        action = 'store',
        default = '#ccc', #'#fff7e0',
        help = 'How to render the paper color (default: %(default))',
        dest = 'tapecolor',
        metavar = 'html-color'
    )

    parser.add_argument('-hc', '--hole-color',
        action = 'store',
        default = 'white',
        help = 'How to render the hole color (default: %(default))',
        dest = 'holecolor',
        metavar = 'html-color'
    )

    parser.add_argument('-os', '--open-svg',
        action = 'store',
        default = True,
        type = str2bool,
        help = 'Open resulting SVG file for viewing (default: %(default)s)',
        dest = 'opensvg',
        metavar = 'flag'
    )

    options = parser.parse_args()
    options.log_level_int = getattr(logging, options.log_level, logging.INFO)

    # The two most common widths were 11/16 inch (17.46 mm) for five bit codes,
    # and 1 inch (25.4 mm) for tapes with six or more bits.
    options.tapewidth = 11/16 if (options.bitcount <= 5) else 1.0

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
        width="{tapewidth}in" height="{tapelength}in">
        <title>tape2svg</title>
        <desc>Generated from binary data</desc>
'''.format(
    tapewidth = options.tapewidth,
    tapelength = options.tapelength
))

    options.indent = indent(options.indent)
    options.indent = indent(options.indent)

def writeSVGDrawTape():
    
    global options

    options.outputfile.write(options.indent + '<!-- Tape background -->\n')
    options.indent = indent(options.indent)
    try:
        options.outputfile.write(options.indent + '<rect x="0in" y="0in" width="{tapewidth}in" height="{tapelength}in" stroke="none" fill="{tapecolor}"/>\n'.format(
            tapewidth=options.tapewidth,
            tapelength=options.tapelength,
            tapecolor=options.tapecolor
        ))

    finally:
        options.indent = unindent(options.indent)

def writeSVGDrawByte(data):

    global options

    # Tape for punching was 0.00394 inches (0.1 mm) thick. The two most common widths 
    # were 11/16 inch (17.46 mm) for five bit codes, and 1 inch (25.4 mm) for tapes with 
    # six or more bits. Hole spacing was 0.1 inch (2.54 mm) in both directions. Data holes 
    # were 0.072 inches (1.83 mm) in diameter; feed holes were 0.046 inches (1.17 mm).[4]

    options.outputfile.write(options.indent + '<!-- {data:#02x} - {data:#010b} -->\n'.format(
        data=data
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

            options.outputfile.write(options.indent + '<circle cx="{cx:.3f}in" cy="{cy:.3f}in" r="0.036in" fill="{fill}"/>\n'.format(
                cx=cx,
                cy=options.y,
                fill=fill
            ))

            cx -= 0.1

            if bitindex==2:
                # Feed hole
                options.outputfile.write(options.indent + '<circle cx="{cx:.3f}in" cy="{cy:.3f}in" r="0.023in" fill="{fill}"/>\n'.format(
                    cx=cx,
                    cy=options.y,
                    fill=options.holecolor
                ))                
                cx -= 0.1
    finally:
        options.indent = unindent(options.indent)
    
    # Next row
    options.y += 0.1 
    options.rowspunched += 1

def writeSVGDrawData():

    global options

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

    logger.info('{bytecount} bytes of input processed.'.format(
        bytecount=bytecount
    ))

def writeSVGDrawPunchString(string):

    options.outputfile.write(options.indent + '<!-- {string} -->\n'.format(
        string=string
    ))
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

def writeSVGFooter():

    global options

    options.indent = ''
    options.outputfile.write('''</svg>''')

def main():
  
    global options
    
    parse_commandline()
    setup_logging()

    logger = logging.getLogger('main')
    logger.info('Starting. Writing to {outputfilename}.'.format(
        outputfilename=options.outputfilename))

    # Size the tape in inches
    options.tapelength = options.leadin * 0.1
    
    if options.inputfilename:
        options.tapelength += os.stat(options.inputfilename).st_size * 0.1 

    if options.punchtitle:
        if options.punchtitle:
            options.tapelength += 8 * len(options.punchtitle) * 0.1 + 20 * 0.1

    options.tapelength += options.leadout * 0.1
    options.y = -0.005
    options.rowspunched = 0

    # Create output file
    options.outputfile = open(options.outputfilename, 'w')
    options.indent = ''
    try:                      
        writeSVGHeader()
        writeSVGDrawTape()

        for _ in range(0, options.leadin):
            writeSVGDrawByte(0)

        if options.punchtitle:
            writeSVGDrawPunchString(options.punchtitle)
            
            # Separate human-readable title from the data
            for _ in range(0, 20):
                writeSVGDrawByte(0)
    
        if options.inputfilename:
            writeSVGDrawData()

        for _ in range(0, options.leadout + 2):
            writeSVGDrawByte(0)

        writeSVGFooter()

    finally:
        options.outputfile.close()
        options.outputfile = None
    
    logger.info('Done. {rowspunched} rows punched.'.format(
        rowspunched=options.rowspunched
    ))

if __name__ == '__main__':
    main()

