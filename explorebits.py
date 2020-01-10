#!/usr/bin/python3

import argparse

import binascii
import pdb
import os

position = 0
framecount = 0

"""
sf-slack
<tmichalak> @bunnie: tilegrid.json holds this type of information: https://raw.githubusercontent.com/SymbiFlow/prjxray-db/master/artix7/tilegrid.json


litghost
bunnie: My recommendation is to round trip to/from FASM
bunnie: Use bit2fasm.py to convert the bitstream to FASM
bunnie: Then you can find the LUT, change it's init value in the FASM file, then use fasm2frames.py + xc7frames2bit to create a new bitstream
bunnie: This works as long as all FASM features decode
bunnie: Make sure to pass "--verbose" to bit2fasm.py to ensure that unknown features get emitted into the FASM file (if any)
bunnie: Then grep the output FASM file for "unknown"
"""

def bitflip(data_block, bitwidth=32):
    if bitwidth == 0:
        return data_block

    bytewidth = bitwidth // 8
    bitswapped = bytearray()

    i = 0
    while i < len(data_block):
        data = int.from_bytes(data_block[i:i+bytewidth], byteorder='big', signed=False)
        b = '{:0{width}b}'.format(data, width=bitwidth)
        bitswapped.extend(int(b[::-1], 2).to_bytes(bytewidth, byteorder='big'))
        i = i + bytewidth

    return bytes(bitswapped)

# read in a .bin file
def readbin(name):
    global position

    with open(name, "rb") as f:
        bitstream = f.read()
        bitstream = bitstream[0x34:]

        return bitstream

# read in the decrypted portion of an encrypted .bin file
def read_decrypt(name):
    global position

    with open(name, "rb") as f:
        bitstream = f.read()
        bitstream = bitstream[0x40:-0xA0] # strip off cryptographic headers

    return bitstream

# open bitfile and scan just past sync "aa995566"
def readbit(name):
    global position

    position = 0
    with open(name, "rb") as f:
        bitstream = f.read()
        while True:
            command = int.from_bytes(bitstream[position:position + 4], byteorder='big')
            position = position + 1
            if command == 0xaa995566:
                position = position + 3 # take it to the end of the word
                break
            if position > 500:
                print("sync header not found")
                break

    print("position: ", position)
    return bitstream


def decode_reg(cmd):
    if cmd == 0b00000:
        return 'CRC'
    elif cmd == 0b00001:
        return 'FAR'
    elif cmd == 0b00010:
        return 'FDRI'
    elif cmd == 0b00011:
        return 'FDRO'
    elif cmd == 0b00100:
        return 'CMD'
    elif cmd == 0b00101:
        return 'CTL0'
    elif cmd == 0b00110:
        return 'MASK'
    elif cmd == 0b00111:
        return 'STAT'
    elif cmd == 0b01000:
        return 'LOUT'
    elif cmd == 0b01001:
        return 'COR0'
    elif cmd == 0b01010:
        return 'MFWR'
    elif cmd == 0b01011:
        return 'CBC'
    elif cmd == 0b01100:
        return 'IDCODE'
    elif cmd == 0b01101:
        return 'AXSS'
    elif cmd == 0b01110:
        return 'COR1'
    elif cmd == 0b10000:
        return 'WBSTAR'
    elif cmd == 0b10001:
        return 'TIMER'
    elif cmd == 0b10110:
        return 'BOOTSTS'
    elif cmd == 0b11000:
        return 'CTL1'
    elif cmd == 0b11010:
        return 'CIPHERTEXT'
    elif cmd == 0b11111:
        return 'BSPI'
    else:
        return 'UNKNOWN'


def parseframe(bitstream):
    global position

    command = int.from_bytes(bitstream[position:position+4], byteorder='big')
    print('{:08x}'.format(command))
    position = position + 4
    if (command & 0xE0000000) == 0x20000000:
        type = 1
    elif (command & 0xE0000000) == 0x40000000:
        type = 2
    else:
        type = -1

    if type == 1:
        opcode = (command >> 27) & 0x3
        register = (command >> 13) & 0x3FFF
        count = command & 0x7FF

        if opcode == 0:
            op = 'NOP'
        elif opcode == 1:
            op = 'Read'
        elif opcode == 2:
            op = 'Write'
        else:
            op = 'Reserved'

        if op == 'Read' or op == 'Write':
            print(op, ": ", decode_reg(register), " len: ", count)
            if decode_reg(register) == 'UNKNOWN':
                print('  unknown address: 0b{:05b}'.format(register))
        else:
            print(op)

        data = -1
        if count < 32:
            for i in range(count):
                data = int.from_bytes(bitstream[position:position+4], byteorder='big')
                position = position + 4
                print('  0x{:08x}'.format(data))
        else:
            print('...skipped {} words...'.format(count))
            position = position + 4 * count

        if decode_reg(register) == 'CIPHERTEXT':
            print('...skipping {} words of ciphertext...'.format(data))
            position = position + 4 * data
        elif decode_reg(register) == 'BSPI':
            if data == 0xb:
                print('  Fast read x1')
            elif data == 0x3b:
                print('  Dual output fast read')
            elif data == 0x6b:
                print('  Quad output fast read')
            elif data == 0x0c:
                print('  Fast read, 32-bit addresses')
            elif data == 0x3c:
                print('  Dual output fast read, 32-bit addresses')
            elif data == 0x6c:
                print('  Quad output fast read, 32-bit addresses')



    elif type == 2:
        count = 0x3ffffff & command
        print('Type2')

        if count < 32:
            for i in range(count):
                data = int.from_bytes(bitstream[position:position+4], byteorder='big')
                position = position + 4
                print('  0x{:08x}'.format(data))
        else:
            print('...skipped {} words...'.format(count))
            position = position + 4 * count

    else:
        print('UNKNOWN TYPE')


# scan to the type 2 region
def type2(bitstream):
    global position

    type = -1

    command = 0
    while type != 2:
        command = int.from_bytes(bitstream[position:position+4], byteorder='big')
        position = position + 4
        if (command & 0xE0000000) == 0x20000000:
            type = 1
        elif (command & 0xE0000000) == 0x40000000:
            type = 2
        else:
            type = -1

    count = 0x3ffffff & command
    print('Type2')
    print('Position 0x{:x} starts type 2 run of frames of length {}'.format(position, count))
    return count

def scan(frame):
    global position

    position = position + frame * 101 * 4
    print('new position: {}'.format(position))

def dumpframe(bitstream):
    global position
    global framecount

    print('0x{:08x}'.format(framecount), end=',')
    framecount = framecount + 1
    for i in range(101):
        command = int.from_bytes(bitstream[position:position + 4], byteorder='big')
        position = position + 4
        print(' 0x{:08x}'.format(command), end=',')
    print('')

def setup(file):
    bitfile = readbit(file)
    type2(bitfile)

    return bitfile


def main():
    global position

    parser = argparse.ArgumentParser(description="bitstream utilities")
    parser.add_argument("-f", "--file", help="Initial bitstream to work with", type=str)
    parser.add_argument("-i", "--interactive", help="Break into interactive mode when done", default=False, action="store_true")
    args = parser.parse_args()

    if args.file == None:
        print("no file specified, breaking into debugger")
        pdb.set_trace() # fall back into interactive mode if no filename given

    ifile = args.file
    filename, file_extension = os.path.splitext(ifile)

    if file_extension == '.bit':
        bit = readbit(ifile)
    elif file_extension == '.clr':
        bit = read_decrypt(ifile)
    else:
        print("unrecognized extension")
        pdb.set_trace()

    count = type2(bit)
    end = position + count

    while position < end:
        dumpframe(bit)

    if args.interactive:
        pdb.set_trace()


if __name__ == "__main__":
    main()