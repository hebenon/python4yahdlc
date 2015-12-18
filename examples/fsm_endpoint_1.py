#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
from yahdlc import *
from fysom import Fysom
from sys import stdout, stderr
from time import sleep

# Serial port configuration
ser = serial.Serial()
ser.port = '/dev/pts/5'
ser.baudrate = 9600
ser.timeout = 0

def serial_connection(e):
	stdout.write('[*] Connection ...\n')

	try:
		ser.open()
		e.fsm.connection_ok()
	except serial.serialutil.SerialException as err:
		stderr.write('[x] Serial connection problem : {0}\n'.format(err))
		e.fsm.connection_ko()

def retry_serial_connection(e):
	stdout.write('[*] Retry in 3 seconds ...\n')
	sleep(3)

def send_data_frame(e):
	stdout.write('[*] Sending data frame ...\n')
	ser.write(frame_data('test', FRAME_DATA, 1))
	e.fsm.send_ok()

def wait_for_ack(e):
	stdout.write('[*] Waiting for (N)ACK ...\n')

	while True:
		try:
			data, type, seq_no = get_data(ser.read(ser.inWaiting()))
			break
		except MessageError:
			pass

	if type != FRAME_ACK and type != FRAME_NACK:
		stderr.write('[x] Bad frame type: {0}\n'.format(type))
	elif type == FRAME_ACK:
		stdout.write('[*] ACK received\n')
		e.fsm.ack_received()
	else:
		stdout.write('[*] NACK received\n')
		e.fsm.nack_received()

def pause(e):
	sleep(1)
	e.fsm.timesup()

try:
	fsm = Fysom({
		'initial': 'init',
		'events': [
			{'name': 'connection_ok', 'src': 'init', 'dst': 'send_data'},
			{'name': 'connection_ko', 'src': 'init', 'dst': 'init'},
			{'name': 'send_ok', 'src': 'send_data', 'dst': 'wait_ack'},
			{'name': 'ack_received', 'src': 'wait_ack', 'dst': 'pause'},
			{'name': 'nack_received', 'src': 'wait_ack', 'dst': 'send_data'},
			{'name': 'timeout', 'src': 'wait_ack', 'dst': 'send_data'},
			{'name': 'timesup', 'src': 'pause', 'dst': 'send_data'},
		],
		'callbacks': {
			'oninit': serial_connection,
			'onreenterinit': retry_serial_connection,
			'onconnection_ko': serial_connection,
			'onconnection_ok': send_data_frame,
			'onsend_ok': wait_for_ack,
			'onack_received': pause,
			'ontimesup': send_data_frame,
		},
	})
except KeyboardInterrupt:
	stdout.write('[*] Bye !\n')
	ser.close()
	exit(0)
