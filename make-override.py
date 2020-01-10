#!/usr/bin/python3

"""
Helper script that produces a .tcl file that can be run on the rom-locate.py project to change
the INIT values of all the LUTs. This allows us to do a diff on the .frames file to figure out the
frame offset of the ROM LUTs in the bitstream.
"""

for bit in range(0,32):
    for lut in range(4):
        if lut == 0:
            lutname = 'A'
        elif lut == 1:
            lutname = 'B'
        elif lut == 2:
            lutname = 'C'
        else:
            lutname = 'D'

        print("set_property INIT 64'hA6C355555555A6C3 [get_cells KEYROM",str(bit),lutname,"]", sep='')

print("set_property CONFIG_VOLTAGE 1.8 [current_design]")
print("set_property CFGBVS GND [current_design]")
print("set_property BITSTREAM.CONFIG.CONFIGRATE 66 [current_design] ")
print("set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 1 [current_design] ")
print("write_bitstream -force top-mod.bit")
