# rom-locate

A set of routines to help locate the position of a fixed set of ROM LUTs in
an FPGA, and to generate a patching routine to layer new values into the LUTs
in a bitstream that has already been generated.

## WBSTAR attack mitigation

Rom-locate by default patches a set of ROM locations to facilitate
WBSTAR-mitigated readout oracle attacks (please see
https://www.usenix.org/system/files/sec20fall_ender_prepub.pdf).

The mitigiation consists of connecting the RS[0] pin to an on-board "kill
switch", which erases any key that happens to be stored in the
BBRAM. Because we know the mapping of bitstream positions to ROM LUT
locations, we can induce the correct bit pattern to activate the kill
switch whenever the attacker attempts to access the values inside our
ROM LUTs. The cost of this mitigation is losing 64 bytes out of 1024
bytes to the fixed bit pattern striped across the ROM LUT array.

## Building

_nothing to build_

## Testing

_TBD_

## Contribution Guidelines

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.0%20adopted-ff69b4.svg)](CODE_OF_CONDUCT.md)

Please see [CONTRIBUTING](CONTRIBUTING.md) for details on
how to make a contribution.

Please note that this project is released with a
[Contributor Code of Conduct](CODE_OF_CONDUCT.md).
By participating in this project you agree to abide its terms.

## License

Copyright © 2020

Licensed under the [CERN OHL v1.2](https://ohwr.org/project/licenses/wikis/cern-ohl-v1.2) [LICENSE](LICENSE)
