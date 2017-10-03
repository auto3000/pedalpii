#!/usr/bin/env python3

import sys
import os.path
import tornado.ioloop
import tornado.web
from time import sleep
from tornado.iostream import PipeIOStream
from tornado import ioloop, iostream
from tornado.tcpserver import TCPServer
from tornado.tcpclient import TCPClient
from tornado.web import RequestHandler, asynchronous
from tornado.locks import Lock
from tornado.iostream import StreamClosedError
from tornado import gen
import csv
from tornado.queues import Queue
import logging
import logging.handlers
from time import sleep

HMI_SOCKET_PORT = 9999
NETCONSOLE_CONSOLE_PORT = 9998

global logger
global GPIO
global enablePhysicalMode

enablePhysicalMode = ("RPI_GPIO_CONNECTED" in os.environ) and (not os.environ["RPI_GPIO_CONNECTED"] in ("0"))


def setupLogging():
	global logger
	access_log = logging.getLogger("tornado.access")
	app_log = logging.getLogger("tornado.application")
	gen_log = logging.getLogger("tornado.general")
	logger = logging.getLogger("pedalpII")
	access_log.setLevel(logging.DEBUG)
	app_log.setLevel(logging.DEBUG)
	gen_log.setLevel(logging.DEBUG)
	logger.setLevel(logging.DEBUG)

	consoleHandler = logging.StreamHandler(sys.stdout)
	consoleFormatter = logging.Formatter('%(name)s %(levelname)s %(funcName)s:%(lineno)d: %(message)s')
	consoleHandler.formatter = consoleFormatter

	syslogHandler = logging.handlers.SysLogHandler('/dev/log')
	syslogFormatter = logging.Formatter('%(name)s %(levelname)s %(funcName)s:%(lineno)d: %(message)s')
	syslogHandler.formatter = syslogFormatter

	logger.addHandler(syslogHandler)
	access_log.addHandler(syslogHandler)
	app_log.addHandler(syslogHandler)
	gen_log.addHandler(syslogHandler)

	logger.addHandler(consoleHandler)
	access_log.addHandler(consoleHandler)
	app_log.addHandler(consoleHandler)
	gen_log.addHandler(consoleHandler)

	logger.info("Logging to syslog and console is ready.")
	return

class FakeGPIO(object):
	BOARD = -1
	BCM = -1
	def output(self, a,b):
		pass

	def cleanup(self, *args):
		pass

	def setwarnings(self, x):
		pass

	def input(self, x):
		pass

	@classmethod
	def setmode(self, x):
		pass

	def add_event_detect(self, x, y, **args):
		pass

def setupGPIOmode():
	global GPIO
	global enablePhysicalMode
	if enablePhysicalMode:
		try:
			import RPi.GPIO as GPIO
			logger.info("pedalpII is connected to physical devices." )

			GPIO.setmode(GPIO.BOARD) #Initialize Raspberry PI GPIO

		except ImportError:
			logger.error("No RPi.GPIO detected while RPI_GPIO_CONNECTED is defined. pedalpII is not connected to physical devices but console is ready." )
			GPIO = FakeGPIO()
	else:
		logger.info("RPI_GPIO_CONNECTED is false or undefined. pedalpII is not connected to physical devices but console is ready." )
		GPIO = FakeGPIO()
	return

# #define LCD_SETCGRAMADDR 0x40
#// Allows us to fill the first 8 CGRAM locations
#// with custom characters
#void LiquidCrystal_I2C::createChar(uint8_t location, uint8_t charmap[]) {
#	location &= 0x7; // we only have 8 locations 0-7
#	command(LCD_SETCGRAMADDR | (location << 3));
#	for (int i=0; i<8; i++) {
#		write(charmap[i]);
#	}
#}
#uint8_t bell[8]  = {0x4, 0xe, 0xe, 0xe, 0x1f, 0x0, 0x4};
#uint8_t note[8]  = {0x2, 0x3, 0x2, 0xe, 0x1e, 0xc, 0x0};
#uint8_t clock[8] = {0x0, 0xe, 0x15, 0x17, 0x11, 0xe, 0x0};
#uint8_t heart[8] = {0x0, 0xa, 0x1f, 0x1f, 0xe, 0x4, 0x0};
#uint8_t duck[8]  = {0x0, 0xc, 0x1d, 0xf, 0xf, 0x6, 0x0};
#uint8_t check[8] = {0x0, 0x1 ,0x3, 0x16, 0x1c, 0x8, 0x0};
#uint8_t cross[8] = {0x0, 0x1b, 0xe, 0x4, 0xe, 0x1b, 0x0};
#uint8_t retarrow[8] = {	0x1, 0x1, 0x5, 0x9, 0x1f, 0x8, 0x4};

class LCD:
	# commands
	LCD_CLEARDISPLAY 		= 0x01
	LCD_RETURNHOME 		    = 0x02
	LCD_ENTRYMODESET 		= 0x04
	LCD_DISPLAYCONTROL 		= 0x08
	LCD_CURSORSHIFT 		= 0x10
	LCD_FUNCTIONSET 		= 0x20
	LCD_SETCGRAMADDR 		= 0x40
	LCD_SETDDRAMADDR 		= 0x80

	# flags for display entry mode
	LCD_ENTRYRIGHT 		= 0x00
	LCD_ENTRYLEFT 		= 0x02
	LCD_ENTRYSHIFTINCREMENT 	= 0x01
	LCD_ENTRYSHIFTDECREMENT 	= 0x00

	# flags for display on/off control
	LCD_DISPLAYON 		= 0x04
	LCD_DISPLAYOFF 		= 0x00
	LCD_CURSORON 		= 0x02
	LCD_CURSOROFF 		= 0x00
	LCD_BLINKON 		= 0x01
	LCD_BLINKOFF 		= 0x00

	# flags for display/cursor shift
	LCD_DISPLAYMOVE 	= 0x08
	LCD_CURSORMOVE 		= 0x00

	# flags for display/cursor shift
	LCD_DISPLAYMOVE 	= 0x08
	LCD_CURSORMOVE 		= 0x00
	LCD_MOVERIGHT 		= 0x04
	LCD_MOVELEFT 		= 0x00

	# flags for function set
	LCD_8BITMODE 		= 0x10
	LCD_4BITMODE 		= 0x00
	LCD_2LINE 			= 0x08
	LCD_1LINE 			= 0x00
	LCD_5x10DOTS 		= 0x04
	LCD_5x8DOTS 		= 0x00

	def __init__(self, pin_rs=27, pin_e=22, pins_db=[25, 24, 23, 18], MyGPIO = None):
		global GPIO
		# Emulate the old behavior of using RPi.GPIO if we haven't been given
		# an explicit GPIO interface to use
		if not MyGPIO:
			self.GPIO = GPIO
			self.pin_rs = pin_rs
			self.pin_e = pin_e
			self.pins_db = pins_db

			self.used_gpio = self.pins_db[:]
			self.used_gpio.append(pin_e)
			self.used_gpio.append(pin_rs)

			self.GPIO.setwarnings(False)
			self.GPIO.setup(self.pin_e, GPIO.OUT)
			self.GPIO.setup(self.pin_rs, GPIO.OUT)

			for pin in self.pins_db:
				self.GPIO.setup(pin, GPIO.OUT)
		else:
			self.GPIO = MyGPIO

		self.writeLock = Lock()
		self.setTornadoWorld( True )
		self.initDone = False #initialization is done on start() completion

	@gen.coroutine
	def setup(self):
		with (yield self.writeLock.acquire()):
			logger.info("LCD setup is started")
			self.directWrite4bits(0x33) # initialization
			self.directWrite4bits(0x32) # initialization
			self.directWrite4bits(0x28) # 2 line 5x7 matrix
			self.directWrite4bits(0x0C) # turn cursor off 0x0E to enable cursor
			self.directWrite4bits(0x06) # shift cursor right

			self.displaycontrol = self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF

			self.displayfunction = self.LCD_4BITMODE | self.LCD_1LINE | self.LCD_5x8DOTS
			self.displayfunction |= self.LCD_2LINE

			""" Initialize to default text direction (for romance languages) """
			self.displaymode =  self.LCD_ENTRYLEFT | self.LCD_ENTRYSHIFTDECREMENT
			self.directWrite4bits(self.LCD_ENTRYMODESET | self.displaymode) #  set the entry mode

			#self.clear()
			self.directWrite4bits(self.LCD_CLEARDISPLAY) # command to clear display
			self.delayMicroseconds(3000)	# 3000 microsecond sleep, clearing the display takes a long time

			self.initDone = True
			logger.info("LCD setup is done")


	def begin(self, cols, lines):
		if (lines > 1):
			self.numlines = lines
			self.displayfunction |= self.LCD_2LINE
			self.currline = 0

	def home(self):
		self.write4bits(self.LCD_RETURNHOME) # set cursor position to zero
		self.delayMicroseconds(3000) # this command takes a long time!

	def clear(self):
		self.write4bits(self.LCD_CLEARDISPLAY) # command to clear display
		self.delayMicroseconds(3000)	# 3000 microsecond sleep, clearing the display takes a long time

	def setCursor(self, col, row):
		self.row_offsets = [ 0x00, 0x40, 0x14, 0x54 ]

		if ( row > self.numlines ):
			row = self.numlines - 1 # we count rows starting w/0

		self.write4bits(self.LCD_SETDDRAMADDR | (col + self.row_offsets[row]))

	def noDisplay(self):
		# Turn the display off (quickly)
		self.displaycontrol &= ~self.LCD_DISPLAYON
		self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)

	def display(self):
		# Turn the display on (quickly)
		self.displaycontrol |= self.LCD_DISPLAYON
		self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)

	def noCursor(self):
		# Turns the underline cursor on/off
		self.displaycontrol &= ~self.LCD_CURSORON
		self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)

	def cursor(self):
		# Cursor On
		self.displaycontrol |= self.LCD_CURSORON
		self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)

	def noBlink(self):
		# Turn on and off the blinking cursor
		self.displaycontrol &= ~self.LCD_BLINKON
		self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)

	def noBlink(self):
		# Turn on and off the blinking cursor
		self.displaycontrol &= ~self.LCD_BLINKON
		self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)

	def DisplayLeft(self):
		# These commands scroll the display without changing the RAM
		self.write4bits(self.LCD_CURSORSHIFT | self.LCD_DISPLAYMOVE | self.LCD_MOVELEFT)

	def scrollDisplayRight(self):
		# These commands scroll the display without changing the RAM
		self.write4bits(self.LCD_CURSORSHIFT | self.LCD_DISPLAYMOVE | self.LCD_MOVERIGHT);

	def leftToRight(self):
		# This is for text that flows Left to Right
		self.displaymode |= self.LCD_ENTRYLEFT
		self.write4bits(self.LCD_ENTRYMODESET | self.displaymode);

	def rightToLeft(self):
		# This is for text that flows Right to Left
		self.displaymode &= ~self.LCD_ENTRYLEFT
		self.write4bits(self.LCD_ENTRYMODESET | self.displaymode)

	def autoscroll(self):
		# This will 'right justify' text from the cursor
		self.displaymode |= self.LCD_ENTRYSHIFTINCREMENT
		self.write4bits(self.LCD_ENTRYMODESET | self.displaymode)

	def noAutoscroll(self):
		# This will 'left justify' text from the cursor
		self.displaymode &= ~self.LCD_ENTRYSHIFTINCREMENT
		self.write4bits(self.LCD_ENTRYMODESET | self.displaymode)

	@gen.coroutine
	def write4bits(self, bits, char_mode=False):
		with (yield self.writeLock.acquire()):
			if self.initDone:
				self.directWrite4bits(bits, char_mode)
			else:
				logger.error("write4bits has been called while LCD initDone = False")

	def directWrite4bits(self, bits, char_mode=False):
		# Send command to LCD
		self.delayMicroseconds(1000) # 1000 microsecond sleep
		bits=bin(bits)[2:].zfill(8)
		self.GPIO.output(self.pin_rs, char_mode)
		for pin in self.pins_db:
			self.GPIO.output(pin, False)
		for i in range(4):
			if bits[i] == "1":
				self.GPIO.output(self.pins_db[::-1][i], True)
		self.pulseEnable()
		for pin in self.pins_db:
			self.GPIO.output(pin, False)
		for i in range(4,8):
			if bits[i] == "1":
				self.GPIO.output(self.pins_db[::-1][i-4], True)
		self.pulseEnable()

	def setTornadoWorld(self, status):
		self.tornadoWorld = status

	def delayMicroseconds(self, microseconds):
		seconds = microseconds / float(1000000)	# divide microseconds by 1 million for seconds
		if self.tornadoWorld:
			self.delayInTornadoWorld(seconds)
		else:
			self.delayInNormalWorld(seconds)

	@gen.coroutine
	def delayInTornadoWorld(self, seconds):
		result = yield gen.sleep(seconds)
		return result

	def delayInNormalWorld(self, seconds):
		sleep(seconds)

	def pulseEnable(self):
		self.GPIO.output(self.pin_e, False)
		self.delayMicroseconds(1)		# 1 microsecond pause - enable pulse must be > 450ns
		self.GPIO.output(self.pin_e, True)
		self.delayMicroseconds(1)		# 1 microsecond pause - enable pulse must be > 450ns
		self.GPIO.output(self.pin_e, False)
		self.delayMicroseconds(1)		# commands need > 37us to settle

	def message(self, text):
		# Send string to LCD. Newline wraps to second line
		logger.debug("message:\n%s" % text)
		for char in text:
			if char == '\n':
				self.write4bits(0xC0) # next line
			else:
				self.write4bits(ord(char),True)

	def destroy(self):
		logger.info("LCD clean up used_gpio")
		self.GPIO.setmode(self.GPIO.BOARD)
		self.GPIO.cleanup(self.used_gpio)



class FakeLCD(LCD):
	def __init__(self, pin_rs=27, pin_e=22, pins_db=[25, 24, 23, 18], MyGPIO = None):
		self.GPIO = FakeGPIO()
		self.pin_rs = None
		self.pin_e = None
		self.pins_db = [None, None, None, None]
		self.used_gpio = [None]
		self.setTornadoWorld( True )
		self.writeLock = Lock()
		self.initDone = True
		return



class LCDProxyQueue(object):
	def __init__(self, hwlcd):
		self.hwlcd = hwlcd
		self.queue = Queue()
		self.queue.put_nowait( ("setup", self.hwlcd.setup) )

	def setup(self, ioloop):
		ioloop.spawn_callback(self.consumer)

	@gen.coroutine
	def consumer(self):
		GPIO.setmode(GPIO.BOARD)
		while True:
			item = yield self.queue.get()
			try:
				#logger.debug("len of %s %d" % (item[0], len(item)))
				item[1](*item[2:]) #item[1:]
				#print('Doing work on %s' % func)
			finally:
				self.queue.task_done()

	def message(self, text):
		self.queue.put_nowait( ("clear", self.hwlcd.clear) )
		self.queue.put_nowait( ("message", self.hwlcd.message, text) )

	def clear(self):
		GPIO.setmode(GPIO.BOARD)
		self.hwlcd.setTornadoWorld(False)
		self.hwlcd.clear()
		self.hwlcd.message("PEDALP II\nSHUTDOWN...")

	def destroy(self):
		self.hwlcd.destroy()


class RotaryEncoder:

	CLOCKWISE=1
	ANTICLOCKWISE=2
	BUTTONDOWN=3
	BUTTONUP=4

	rotary_a = 0
	rotary_b = 0
	rotary_c = 0
	last_state = 0
	privDirection = 0
	direction = 0

	# Initialise rotary encoder object
	def __init__(self,pinA,pinB,button,callback):
		global GPIO
		self.pinA = pinA
		self.pinB = pinB
		self.button = button
		self.callback = callback

		GPIO.setmode(GPIO.BOARD)

		# The following lines enable the internal pull-up resistors
		# on version 2 (latest) boards
		GPIO.setwarnings(True)
		GPIO.setup(self.pinA, GPIO.IN) #, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.pinB, GPIO.IN) #, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		# For version 1 (old) boards comment out the above four lines
		# and un-comment the following 3 lines
		#GPIO.setup(self.pinA, GPIO.IN)
		#GPIO.setup(self.pinB, GPIO.IN)
		#GPIO.setup(self.button, GPIO.IN)

		# Add event detection to the GPIO inputs
		GPIO.add_event_detect(self.pinA, GPIO.BOTH, callback=self.switch_event)#, bouncetime=1000)
		GPIO.add_event_detect(self.pinB, GPIO.BOTH, callback=self.switch_event)#, bouncetime=500)
		GPIO.add_event_detect(self.button, GPIO.BOTH, callback=self.button_event)#, bouncetime=1000)
		return

	# Call back routine called by switch events
	def switch_event(self,switch):
		valA = GPIO.input(self.pinA)
		valB = GPIO.input(self.pinB)
		if valA:
			self.rotary_a = 1
		else:
			self.rotary_a = 0

		if valB:
			self.rotary_b = 1
		else:
			self.rotary_b = 0

		self.rotary_c = self.rotary_a ^ self.rotary_b
		new_state = self.rotary_a * 4 + self.rotary_b * 2 + self.rotary_c * 1

		delta1 = (new_state - self.last_state) % 4
		self.last_state = new_state
		event = 0

		logger.info ( "switch_event " + str(delta1) + " - privDirection: " + str(self.privDirection) + " a="   + str(self.rotary_a) + " b=" + str(self.rotary_b))
		if delta1 == 1:
			if self.direction == self.CLOCKWISE:
				logger.info("Clockwise")
#				if self.privDirection == self.CLOCKWISE:
				event = self.direction
			else:
				self.direction = self.CLOCKWISE
		elif delta1 == 3:
			if self.direction == self.ANTICLOCKWISE:
				logger.info("Anticlockwise")
#				if self.privDirection == self.ANTICLOCKWISE:
				event = self.direction
			else:
				self.direction = self.ANTICLOCKWISE

		self.privDirection = delta1
		if event > 0:
			self.callback(event)
		return


	# Push button up event
	def button_event(self,button):
		logger.info('button_event');
		if GPIO.input(button):
			event = self.BUTTONUP
		else:
			event = self.BUTTONDOWN
		self.callback(event)
		return

	# Get a switch state
	def getSwitchState(self, switch):
		return  GPIO.input(switch)


# End of RotaryEncoder class



class RpiProtocol(object):
    COMMANDS = {
        "ping": [],
        "control_rm": [int, str],
        "ui_dis": [],
        "ui_con": [],
        "bank_config": [int, int, int, int, int], #hw_type, hw_id, actuator_type, actuator_id, action
        "initial_state": [int, int, str], # bank_id, pedalboard_id, pedalboards #variadic couple 0 str0 1 str1 ...
        "control_add": [int, str, str, int, str, float, float, float, int, int, int, int, int, int, int ],
		"control_clean": [int, int, int, int]
		# instance_id, port, label, var_type, unit, value, min, max, steps, hw_type, hw_id, actuator_type, actuator_id, n_controllers, index, options
    }

    COMMANDS_FUNC = {}

    RESPONSES = [
        "resp", "few aguments", "many arguments", "not found"
    ]

    @classmethod
    def register_cmd_callback(cls, cmd, func):
        if cmd not in cls.COMMANDS.keys():
            raise ValueError("Command %s is not registered" % cmd)

        cls.COMMANDS_FUNC[cmd] = func

    def __init__(self, msg):
        self.msg = msg.replace("\0", "").strip()
        self.cmd = ""
        self.args = []
        self.parse()

    def is_resp(self):
        return any(self.msg.startswith(resp) for resp in self.RESPONSES)

    def run_cmd(self, callback):
        if not self.cmd:
            callback("-1003") # TODO: proper error handling
            return

        if not self.cmd in self.COMMANDS_FUNC.keys():
            logger.info(str(self.COMMANDS_FUNC.keys()) + " xxx " + self.cmd)
            callback("-1004") # TODO: proper error handling
            return
        args = [callback] + self.args
        self.COMMANDS_FUNC[self.cmd](*args)

    def process_resp(self, datatype):
        if "resp" in self.msg:
            resp = self.msg.replace("resp ", "")
            return process_resp(resp, datatype)
        return self.msg

    def parse(self):
        if self.is_resp():
            return

        #cmd = self.msg.split()
        for line in csv.reader([self.msg], delimiter=' ', quotechar='"'):
            cmd = line
        if not cmd or cmd[0] not in self.COMMANDS.keys():
            raise ProtocolError("not found") # Command not found

        try:
            self.cmd = cmd[0]
            #self.args = [ typ(arg) for typ, arg in zip(self.COMMANDS[self.cmd], cmd[1:]) ]
            self.args = [ typ(arg) for typ, arg in zip(self.COMMANDS[self.cmd], cmd[1:]) ]
            self.args = cmd[1:]
            #print ("xxx ", self.args)
            #if not all(str(a) for a in self.args):
            #    raise ValueError
        except ValueError:
            logger.error ("wrong arg type for: %s %s" % (self.cmd, self.args))
            raise ProtocolError("wrong arg type for: %s %s" % (self.cmd, self.args))


#  RotaryEncoderShell -> PedalController -> PedalModel <-> SocketService
#                                                       -> FakeLCD

from enum import Enum
ViewState = Enum('ViewState', 'CONNECTING '
							'HOME '
							'PEDALBOARDSELECT '
							'EFFECTSELECT '
							'LCDLIGHT ')
ViewEvent = Enum('ViewEvent',  'PERIODIC_TICK_2S SOCKET_CONNECTED SHIFT ')

# empty socket.write callback
def socket_write_success():
	pass


class PedalView(object):
	def __init__(self, model, lcd):
		self.welcome_banner_state = 0
		self.model = model
		self.lcd = lcd
		self.lcd.message("PEDALP II       \nINITIALIZING    ")
		return

	def updateConnecting(self):
		if self.model.viewState == ViewState.CONNECTING:
			if self.welcome_banner_state == 0:
				self.lcd.message("PEDALP II       \nCONNECTING......")
				self.welcome_banner_state = 1
			else:
				self.lcd.message("PEDALP II       \nCONNECTING...   ")
				self.welcome_banner_state = 0
		return

	def updatePedalBoard(self):
		if self.model.viewState == ViewState.PEDALBOARDSELECT:
			new_pedalboard = (self.model.pedalboard_id + 1) % (self.model.pedalboards_len + 1)
			self.lcd.message("SELECT BOARD %03d\n%16s" % (new_pedalboard, self.model.pedalboards[self.model.pedalboard_id]))
		return

class PedalController(object):
	def __init__(self, model, view):
		self.model = model
		self.view = view
		self.smLock = Lock() # statemachine lock
		return

	def smSubmit_PERIODIC_TICK_2S_Callback(self):
		self.smNextEvent(ViewEvent.PERIODIC_TICK_2S)
		return

	def setButtonEvent(self, event):
		logger.info ('setButtonEvent entry')
		if hasattr(self, 'ioloop'):
			logger.info ('setButtonEvent entry')
			self.ioloop.add_callback(self.setButtonEventIOLOOP, event)

	@gen.coroutine
	def setButtonEventIOLOOP(self, event):
		logging.info("setButtonEvent: event=%s" % str(event))
		if event == RotaryEncoder.CLOCKWISE:
			self.controlShift(1)
		elif event == RotaryEncoder.ANTICLOCKWISE:
			self.controlShift(-1)
		elif event == RotaryEncoder.BUTTONDOWN:
			self.controlDown()
		elif event == RotaryEncoder.BUTTONUP:
			pass
		else:
			logging.error("setButtonEvent: invalid event=%d" % str(event))

	@gen.coroutine
	def smNextEvent(self, event, **kwargs):
		with ((yield self.smLock.acquire())):
			if self.model.viewState == ViewState.CONNECTING:
				if event == ViewEvent.SOCKET_CONNECTED:
					self.periodic_PERIODIC_TICK_2S_Callback.stop()
					self.model.viewState = ViewState.PEDALBOARDSELECT
					self.view.updatePedalBoard()
				elif event == ViewEvent.PERIODIC_TICK_2S:
					self.view.updateConnecting()
				else:
					logger.info("Error to the statemachine")
			elif self.model.viewState == ViewState.PEDALBOARDSELECT:
				if event == ViewEvent.SHIFT:
					self.model.change_pedalboards(kwargs['angle'])
					self.view.updatePedalBoard()
				else:
					logger.info("ignored controlShift(state=%s event=%s)" % (self.model.viewState, event))
			else:
				logger.error("Error to the statemachine")
		return

	def setup(self, ioloop):
		self.model.viewState = ViewState.CONNECTING
		self.ioloop = ioloop
		self.ioloop.add_callback(self.smNextEvent, ViewEvent.PERIODIC_TICK_2S)	 # Display connecting... first time
		self.periodic_PERIODIC_TICK_2S_Callback = tornado.ioloop.PeriodicCallback(self.smSubmit_PERIODIC_TICK_2S_Callback, 2000)
		self.periodic_PERIODIC_TICK_2S_Callback.start()
		return

	def controlShift(self, angle):
		self.smNextEvent(ViewEvent.SHIFT, angle=angle)
		return

	def controlUp(self):
		logger.info("controlUp is called")

	def controlDown(self):
		logger.info("controlDown is called")

	def controlLong(self):
		logger.info("controlLong is called")


class PedalModel(object):

	def __init__(self):
		self.communicationLayer = None # it must be set after construction asap
		self.stateMachineController = None # it must be set after construction asap
		self.viewState = ViewState.CONNECTING
		return

	def change_pedalboards(self, counter):
		self.pedalboard_id = (self.pedalboard_id + counter) % self.pedalboards_len
		self.communicationLayer.set_pedalboard(self.bank_id, self.pedalboard_id)
		return

	def set_initial_state(self, bank_id, pedalboard_id, pedalboards):
		self.bank_id = int(bank_id)
		self.pedalboard_id = 0 #Force pedalboard to first entry
		self.pedalboards_len = max(int(pedalboard_id) - 1, 1) # ignore the last entry DEFAULT if we have more than one pedalboard.
		self.pedalboards = []
		for i in range(0, self.pedalboards_len): # recopy only text elements
			self.pedalboards = self.pedalboards + [ pedalboards[2*i] ]
		self.change_pedalboards(0)
		return

class SocketService(object):
	def __init__(self, pedalmodel, stateMachineController):
		self.pedalmodel = pedalmodel
		self.stateMachineController = stateMachineController
		self.stream = None
		RpiProtocol.register_cmd_callback("ping", self.ping)
		RpiProtocol.register_cmd_callback("ui_con", self.ui_connected)
		RpiProtocol.register_cmd_callback("ui_dis", self.ui_disconnected)
		RpiProtocol.register_cmd_callback("control_rm", self.control_rm)
		RpiProtocol.register_cmd_callback("bank_config", self.bank_config)
		RpiProtocol.register_cmd_callback("initial_state", self.initial_state)
		RpiProtocol.register_cmd_callback("control_add", self.control_add)
		RpiProtocol.register_cmd_callback("control_clean", self.control_clean)
		return

	def ui_connected(self, callback):
		logger.info("ignore ui connected")
		callback(True)

	def ping(self, callback):
		callback(True)

	def ui_disconnected(self, callback):
		logger.info("ignore ui disconnected")
		callback(True)

	def control_rm(self, callback, instance_id, port):
		logger.info("ignore control_rm command")
		callback(True)

	def bank_config(self, callback, hw_type, hw_id, actuator_type, actuator_id, action):
		logger.info("ignore bank_config command")
		callback(True)

	def initial_state(self, callback, bank_id, pedalboard_id, *pedalboards):
		logger.info("initial_state command bank_id=" + str(bank_id) + " pedalboard_id=" + str(pedalboard_id) + " pedalboards=" + str(pedalboards) )
		self.pedalmodel.set_initial_state( bank_id, pedalboard_id, pedalboards)
		self.stateMachineController.smNextEvent(ViewEvent.SOCKET_CONNECTED)
		callback(True)

	def control_add(self, callback, instance_id, port, label, var_type, unit, value, min, max, steps, hw_type, hw_id, actuator_type, actuator_id, n_controllers, index, *options):
		logger.info("control_add command")
		callback(True)

	def control_clean(self, callback, hw_type, hw_id, actuator_type, actuator_id):
		logger.info("control_clean command")
		callback(True)

	def error_run_callback(self, result):
		if result == True:
			self.socket_write(b'resp 0\0')
		else:
			logger.error("error_run_callback: " + str(result))
			self.socket_write(b'resp -1\0')
			#raise ProtocolError("error_run_callback: %s" % (result))

	def setup(self, ioloop):
		ioloop.spawn_callback(self.connectHMILoop)
		return


	@gen.coroutine
	def connectHMILoop(self):
		while True:
			client = TCPClient()
			try:
				logger.info("Try to connect to HMI service port=%d" % HMI_SOCKET_PORT)
				self.stream = yield client.connect("localhost", HMI_SOCKET_PORT)
				while True:
					data = yield self.stream.read_until(b'\0')
					logger.debug(">socketService read: %s" % str(data))
					p = RpiProtocol(data.decode('utf-8'))
					if not p.is_resp():
						p.run_cmd(self.error_run_callback)
			except tornado.iostream.StreamClosedError:
				pass
			except Exception as inst:
				logger.error("Connection error %s" % str(type(inst)), exc_info=True)
				self.stream = None

			result = yield gen.sleep(3)
		return

	@gen.coroutine
	def socket_write(self, str):
		logger.debug("> send: %s" % str )
		try:
			if self.stream:
				self.stream.write(str, socket_write_success)
			else:
				logger.error("socket_write HMI is not connected")
		except:
			logger.error("socket_write failure error", exc_info=True)
		return

	def set_pedalboard(self, bank_id, pedalboard_id):
		self.socket_write("pedalboard {0} {0}\0".format(bank_id, pedalboard_id).encode('ascii'));
		return


class RotaryEncoderShell(object):
	def __init__(self, controller, inStream, outStream):
		self.controller = controller
		self.consolein = inStream
		self.consoleout = outStream
		self.communicationLayer = None
		self.setup()
		return

#        "banks": [],
#        "pedalboards": [int],
#        "pedalboard": [int, str],
#        "hw_con": [int, int],
#        "hw_dis": [int, int],
#        "control_set": [int, str, float],
#        "control_get": [int, str],
#        "control_next": [int, int, int, int],
#        "tuner": [str],
#        "tuner_input": [int],
#        "pedalboard_save": [],
#        "pedalboard_reset": [],
#        "jack_cpu_load": [],

#{(0, 0, 2, 1): '/hmi/knob2',
# (0, 0, 2, 3): '/hmi/knob4',
# (0, 0, 1, 3): '/hmi/footswitch4',
# (0, 0, 1, 1): '/hmi/footswitch2',
# (0, 0, 2, 0): '/hmi/knob1',
# (0, 0, 2, 2): '/hmi/knob3',
# (0, 0, 1, 2): '/hmi/footswitch3',
# (0, 0, 1, 0): '/hmi/footswitch1'}

	def readNext(self, data):
		if data:
			if data.startswith(b"next"):
				self.controller.controlShift(1)
			elif data.startswith(b"prev"):
				self.controller.controlShift(-1)
			elif data.startswith(b"up"):
				self.controller.controlUp()
			elif data.startswith(b"down"):
				self.controller.controlDown()
			elif data.startswith(b"long"):
				self.controller.controlLong()
			elif data.startswith(b"exit"):
				self.consolein.close()
				self.consoleout.close()
				return #goto exit
			else:
				data = data[:-1]
				data = data.rstrip()
				data = data +  b"\0"
				self.communicationLayer.socket_write(data);
		self.consoleout.write(bytes('>Read on console (next/prev/up/down/long): ', 'utf-8'), socket_write_success)
		self.consolein.read_until(b'\n', self.readNext)

	def setup(self):
		self.readNext(None)
		return;

class NetConsoleServer(TCPServer):
	def __init__(self, my_ioloop, controller, ssocket):
		super().__init__(my_ioloop)
		self.controller = controller
		self.communicationLayer = ssocket
		return

	def setup(self):
		try:
			logger.info("NetConsole listens to port %d" % NETCONSOLE_CONSOLE_PORT)
			self.listen(NETCONSOLE_CONSOLE_PORT)
		except Exception as e:
			logger.error("Failed to open netconsole socket port, error was: %s" % e)
		return

	@gen.coroutine
	def handle_stream(self, stream, address):
		logger.info('[NetConsoleServer] connection from %s' % repr(address))
		netshell = RotaryEncoderShell(self.controller, stream, stream)
		netshell.communicationLayer = self.communicationLayer
		return





def main():
	global main_loop, GPIO
	global enablePhysicalMode
	setupLogging()
	setupGPIOmode()
	if enablePhysicalMode:
		hwlcd = LCD( 8, 10, [12, 16, 18, 22])
	else:
		hwlcd = FakeLCD()
	lcd = LCDProxyQueue(hwlcd)
	model = PedalModel()
	view  = PedalView(model, lcd)
	controller = PedalController(model, view)
	rshell = RotaryEncoderShell(controller, PipeIOStream(sys.stdin.fileno()), PipeIOStream(sys.stdout.fileno()))
	if enablePhysicalMode:
		encoder = RotaryEncoder(3, 5, 11, controller.setButtonEvent)
	ssocket = SocketService(model, controller)
	model.communicationLayer = ssocket
	model.stateMachineController = controller
	rshell.communicationLayer = ssocket
	try:
		main_loop = tornado.ioloop.IOLoop.instance()
		logger.info("Tornado Server started")
		lcd.setup(main_loop)
		controller.setup(main_loop)
		ssocket.setup(main_loop)
		netconsole = NetConsoleServer(main_loop, controller, ssocket)
		netconsole.setup()
		main_loop.start()
	except:
		logger.error("Exception triggered - Tornado Server stopped.", exc_info=True)
		lcd.clear()
		lcd.destroy()
		GPIO.cleanup()

if __name__ == "__main__":
	main()
