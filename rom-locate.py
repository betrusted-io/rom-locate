#!/usr/bin/env python3

# This variable defines all the external programs that this module
# relies on.  lxbuildenv reads this variable in order to ensure
# the build will finish without exiting due to missing third-party
# programs.

LX_DEPENDENCIES = ["riscv", "vivado"]

# Import lxbuildenv to integrate the deps/ directory
import lxbuildenv

from random import SystemRandom
import argparse

from migen import *

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer

from litex.soc.integration.soc_core import SoCMini
from litex.soc.integration.builder import *

import binascii

# IOs ----------------------------------------------------------------------------------------------

io_7s = [
    ("address", 0, Pins("J6 K4 L4 K3 K2 K1 L1 K6"), IOStandard("LVCMOS18")),
    ("data", 0, Pins("M5 M3 M2 M1 N1 N3 N2 N5 N4 ",
                     "P2 P1 R2 R1 R3 T2 T1 U1 U3 ",
                     "U2 V3 V2 V5 V4 R4 T3 P6 P5 ",
                     "V7 V6 R5 T4 T6 T5 R7 R6 U7 "), IOStandard("LVCMOS18")),
    ("clk", 0, Pins("N15"), IOStandard("LVCMOS18"))
]

io_7a = [
    ("address", 0, Pins("A13 A14 A15 A16 P1 A18 A19 A20 A21"), IOStandard("LVCMOS18")),
    ("data", 0, Pins("B13 R1  B15 B16 B20 B21 B22 C13 ",
                     "C14 C15 C17 C18 C20 T1  C22 D14 ",
                     "AB1 D15 D16 D17 U1   D19 D20 D21 ",
                     "E13 E14 W1  Y1  E17 E18 E19 AA1 "), IOStandard("LVCMOS18")),
    ("clk", 0, Pins("J19"), IOStandard("LVCMOS18"))
]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    def __init__(self, part, io, toolchain="vivado", programmer="vivado", make_mod=True):
        XilinxPlatform.__init__(self, part, io, toolchain=toolchain)

        # NOTE: to do quad-SPI mode, the QE bit has to be set in the SPINOR status register. OpenOCD
        # won't do this natively, have to find a work-around (like using iMPACT to set it once)
        self.add_platform_command(
            "set_property CONFIG_VOLTAGE 1.8 [current_design]")
        self.add_platform_command(
            "set_property CFGBVS VCCO [current_design]")
        self.add_platform_command(
            "set_property BITSTREAM.CONFIG.CONFIGRATE 66 [current_design]")
        self.add_platform_command(
            "set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 1 [current_design]")
        self.toolchain.bitstream_commands = [
            "set_property CONFIG_VOLTAGE 1.8 [current_design]",
            "set_property CFGBVS GND [current_design]",
            "set_property BITSTREAM.CONFIG.CONFIGRATE 66 [current_design]",
            "set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 1 [current_design]",
        ]

        self.toolchain.additional_commands = \
            ["write_cfgmem -verbose -force -format bin -interface spix1 -size 64 "
             "-loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]
        self.programmer = programmer

        if make_mod:
            for bit in range(0, 32):
                for lut in range(4):
                    if lut == 0:
                        lutname = 'A'
                    elif lut == 1:
                        lutname = 'B'
                    elif lut == 2:
                        lutname = 'C'
                    else:
                        lutname = 'D'

                    self.toolchain.additional_commands += ["set_property INIT 64'hA6C355555555A6C3 [get_cells KEYROM" + str(bit) + lutname + "]"]

            self.toolchain.additional_commands += ["write_bitstream -force top-mod.bit"]
            self.toolchain.additional_commands += \
                ["write_cfgmem -verbose -force -format bin -interface spix1 -size 64 "
                 "-loadbit \"up 0x0 {build_name}-mod.bit\" -file {build_name}-mod.bin"]

    def create_programmer(self):
        if self.programmer == "vivado":
            return VivadoProgrammer(flash_part="n25q128-1.8v-spi-x1_x2_x4")
        else:
            raise ValueError("{} programmer is not supported".format(self.programmer))

    def do_finalize(self, fragment):
        XilinxPlatform.do_finalize(self, fragment)

class RomTest(Module):
    def __init__(self, platform, address, data):
        platform.toolchain.attr_translate["KEEP"] = ("KEEP", "TRUE")
        platform.toolchain.attr_translate["DONT_TOUCH"] = ("DONT_TOUCH", "TRUE")

        self.address = address
        self.data = data

        rng = SystemRandom()
        with open("rom.db", "w") as f:
            for bit in range(0,32):
                lutsel = Signal(4)
                for lut in range(4):
                    if lut == 0:
                        lutname = 'A'
                    elif lut == 1:
                        lutname = 'B'
                    elif lut == 2:
                        lutname = 'C'
                    else:
                        lutname = 'D'
                    romval = rng.getrandbits(64)
                    # print("rom bit ", str(bit), lutname, ": ", binascii.hexlify(romval.to_bytes(8, byteorder='big')))
                    rom_name = "KEYROM" + str(bit) + lutname
                    if bit % 2 == 0:
                        platform.toolchain.attr_translate[rom_name] = ("LOC", "SLICE_X36Y" + str(50 + bit // 2))
                    else:
                        platform.toolchain.attr_translate[rom_name] = ("LOC", "SLICE_X37Y" + str(50 + bit // 2))
                    platform.toolchain.attr_translate[rom_name + 'BEL'] = ("BEL", lutname + '6LUT')
                    platform.toolchain.attr_translate[rom_name + 'LOCK'] = ( "LOCK_PINS", "I5:A6, I4:A5, I3:A4, I2:A3, I1:A2, I0:A1" )
                    self.specials += [
                        Instance( "LUT6",
                                  name=rom_name,
                                  # p_INIT=0x0000000000000000000000000000000000000000000000000000000000000000,
                                  p_INIT=romval,
                                  i_I0= self.address[0],
                                  i_I1= self.address[1],
                                  i_I2= self.address[2],
                                  i_I3= self.address[3],
                                  i_I4= self.address[4],
                                  i_I5= self.address[5],
                                  o_O= lutsel[lut],
                                  attr=("KEEP", "DONT_TOUCH", rom_name, rom_name + 'BEL', rom_name + 'LOCK')
                                  )
                        # X36Y99 and counting down
                    ]
                    f.write("KEYROM " + str(bit) + ' ' + lutname + ' ' + platform.toolchain.attr_translate[rom_name][1] + ' ' + str(binascii.hexlify(romval.to_bytes(8, byteorder='big'))) + '\n')
                self.comb += [
                    If( self.address[6:] == 0,
                        self.data[bit].eq(lutsel[2]))
                    .Elif(self.address[6:] == 1,
                          self.data[bit].eq(lutsel[3]))
                    .Elif(self.address[6:] == 2,
                          self.data[bit].eq(lutsel[0]))
                    .Else(self.data[bit].eq(lutsel[1]))
                ]

class TestSoC(SoCMini):
    def __init__(self, platform, **kwargs):
        self.clock_domains.cd_sys   = ClockDomain()

        clk = platform.request("clk")
        platform.add_period_constraint(clk, 1e9/12e6)

        # This allows PLLs/MMCMEs to be placed anywhere and reference the input clock
        self.specials += Instance("BUFG", i_I=clk, o_O=self.cd_sys.clk)

        SoCMini.__init__(self, platform, clk_freq=12e6, **kwargs)

        # ROM test ---------------------------------------------------------------------------------
        self.submodules.romtest = RomTest(platform, platform.request("address"), platform.request("data"))


# Build --------------------------------------------------------------------------------------------

def main():
    global io_7a, io_7s

    if os.environ['PYTHONHASHSEED'] != "1":
        print( "PYTHONHASHEED must be set to 1 for consistent validation results. Failing to set this results in non-deterministic compilation results")
        exit()


    parser = argparse.ArgumentParser(description="Build the Betrusted SoC")
    parser.add_argument(
        "-b", "--betrusted", default=False, action="store_true", help="Build for betrusted part"
    )

    args = parser.parse_args()
    compile_gateware = True
    compile_software = False

    if args.betrusted:
        platform = Platform("xc7s50-csga324-1il", io_7s)
    else:
        platform = Platform("xc7a50tfgg484-1", io_7a)

    soc = TestSoC(platform)
    builder = Builder(soc, output_dir="build", csr_csv="test/csr.csv", compile_software=compile_software, compile_gateware=compile_gateware)
    vns = builder.build()
    soc.do_exit(vns)

if __name__ == "__main__":
    main()
