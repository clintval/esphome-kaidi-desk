"""Dimensions in millimeters shared by the footprints, the 3D models, the board geometry and the enclosure."""

# Mornsun B0505S-2WR3 SIP from its datasheet; the pin row's offset from the body face is ESTIMATED.
B0505S_LENGTH = 19.65
B0505S_THICKNESS = 7.05
B0505S_HEIGHT = 10.16
B0505S_STANDOFF = 0.5
B0505S_PIN1_INSET = 2.21
B0505S_PIN_ROW_INSET = 1.5

# The box wall and its gap to the board, so the jacks' faces sit flush with the outside of the box.
BOX_GAP = 0.5
BOX_WALL = 2.2
JACK_OVERHANG = BOX_GAP + BOX_WALL
