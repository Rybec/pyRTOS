import board
import neopixel
import touchio

import pyRTOS

###
# pyRTOS Sample Program for the Adafruit Rotary Trinkey
#
# Author: Ben Williams
#
# Description:
#
# This program uses pyRTOS to run three tasks: a touch input 
# handler, a rainbow color cycler, and a renderer that sends
# color output to the NeoPixel.  When no input is present,
# the NeoPixel will cycle through a rainbow color effect.
# When the touch strip on the edge of the Trinkey is being
# touched, the NeoPixel will display red.  When the bottom
# pin of the three rotary encoder pins in touched, the
# NeoPixel will display blue.  When both the touch strip and
# the bottom rotary encode pin are touched, the NeoPixel
# will display green.  When touch input is removed, the
# NeoPixel will return to the rainbow cycle, wherever it
# would have been, had the touch input never happened.
###


# User defined message types start at 128
COLOR_DATA = 128
COLOR_RESUME = 129


def touch_handler(self):
	# Task initialization

	touch_pad = touchio.TouchIn(board.TOUCH)
	# The following is the bottom rotary pin,
	# when the touch pad is oriented to the
	# right, looking at the board from the top.
	touch_rota = touchio.TouchIn(board.ROTA)
	touched = False

	NONE = 0b00
	PAD  = 0b01
	ROTA = 0b10
	BOTH = 0b11

	yield

	# Main Task Loop
	while True:
		touch = touch_pad.value | touch_rota.value << 1
		if touch == BOTH and touched != BOTH:
			touched = BOTH
			self.send(pyRTOS.Message(COLOR_DATA, "touch",
			                         "renderer", (0b000, 0b111, 0b000)))
		elif touch == PAD and touched != PAD:
			touched = PAD
			self.send(pyRTOS.Message(COLOR_DATA, "touch",
			                         "renderer", (0b111, 0b000, 0b000)))
		elif touch == ROTA and touched != ROTA:
			touched = ROTA
			self.send(pyRTOS.Message(COLOR_DATA, "touch",
			                         "renderer", (0b000, 0b000, 0b111)))
		elif touch == NONE and touched != NONE:
				touched = NONE
				self.send(pyRTOS.Message(COLOR_RESUME, "touch", "renderer"))

		yield [pyRTOS.timeout(0.100)]


def color_update(self):
	# Task initialization
	r = 0b000
	g = 0b000
	b = 0b111

	yield

	# Main Task Loop
	while True:
		if b == 0b000 and g > 0b000:
			c0 = g
			c1 = r
		elif g == 0b000 and r > 0b000:
			c0 = r
			c1 = b
		elif r == 0b000 and b > 0b000:
			c0 = b
			c1 = g

		if c1 < 0b111:
			c1 = c1 + 1
		else:
			c0 = c0 - 1

		if b == 0b000 and g > 0b000:
			g = c0
			r = c1
		elif g == 0b000 and r > 0b000:
			r = c0
			b = c1
		elif r == 0b000 and b > 0b000:
			b = c0
			g = c1

		self.send(pyRTOS.Message(COLOR_DATA, "color",
		          "renderer", (r, g, b)))

		yield [pyRTOS.timeout(0.050)]



def renderer(self):
	# Task initialization
	pixels = neopixel.NeoPixel(board.NEOPIXEL, 1)
	color = 0

	touched = False

	yield

	# Main Task Loop
	while True:
		# If there are multiple messages instructing
		# this to change the color, only the most
		# recent one will be applied.
		msgs = self.recv()
		for msg in msgs:
			if msg.source == "touch":
				if msg.type == COLOR_DATA:
					touched = True
					color = msg.message
				elif msg.type == COLOR_RESUME:
					touched = False
			else:
				if msg.type == COLOR_DATA and touched == False:	
					color = msg.message

		pixels.fill(color)

		yield


pyRTOS.add_task(pyRTOS.Task(touch_handler, priority=0, name="touch"))
pyRTOS.add_task(pyRTOS.Task(color_update, priority=1, name="color"))
pyRTOS.add_task(pyRTOS.Task(renderer, priority=2, name="renderer", mailbox=True))

pyRTOS.start()
