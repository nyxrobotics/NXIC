#!/usr/bin/env python3

import os
import threading
import time
import keyboard
import signal

# Reset USB Gadget
os.system('echo > /sys/kernel/config/usb_gadget/procon/UDC')
os.system('ls /sys/class/udc > /sys/kernel/config/usb_gadget/procon/UDC')
time.sleep(0.5)

mouse = os.open('/dev/hidraw2', os.O_RDWR | os.O_NONBLOCK)
gadget = os.open('/dev/hidg0', os.O_RDWR | os.O_NONBLOCK)

#////////////////////////////////USERCONFIG////////////////////////////////////

#Change here if you want to adjust the mouse sensitivity.
#If the mouse sends x,y values in 8 bits, this value is approximately 12.
#In the case of 16bit, this value is approximately 3000.
mouse_threshold = 3000

#If the x,y values taken from the mouse are 16 bits each, set to True.
#If the x,y value does not start from the second byte (the first byte is probably the button input, but there is an unnecessary byte after it), enter the number of bytes to be skipped in the offset.
xy_is_16bit = True
xy_offset = 0

#If the byte signifying the button press is not the first, enter the number of bytes to be skipped in the offset.
button_offset = 0

# Set the minimum value for the gyroscope as it does not respond to small values.
gyro_diff_smallest = 20
gyroy_scale = 4.0 
gyroz_scale = 1.0 

#//////////////////////////////////////////////////////////////////////////////

counter = 0
mac_addr = 'D4F0578D7423'
initial_input = '81008000f8d77a22c87b0c'
loopcount = False
bleft = False
bright = False
bmiddle = False
bprev = False
bnext = False
x = 0
y = 0
x_last = 0
y_last = 0
gyrox = 0
gyroy = 0
gyroz = 0
y_hold = False

def countup():
    global counter
    while True:
        counter = (counter + 3) % 256
        time.sleep(0.03)

# Communication Functions
def response(code, cmd, data):
    buf = bytearray([code, cmd])
    buf.extend(data)
    buf.extend(bytearray(64-len(buf)))
    # print(buf.hex())
    try:
        os.write(gadget, buf)
    except BlockingIOError:
        pass
    except:
        os._exit(1)

def uart_response(code, subcmd, data):
    buf = bytearray.fromhex(initial_input)
    buf.extend([code, subcmd])
    buf.extend(data)
    response(0x21, counter, buf)

def disconnect_response():
    buf = bytearray.fromhex(initial_input)
    buf.extend([0x80, 0x30])
    response(0x21, counter, buf)
    buf[10] = 0x0a
    response(0x21, counter, buf)
    buf[10] = 0x09
    response(0x21, counter, buf)

def spi_response(addr, data):
    buf = bytearray(addr)
    buf.extend([0x00, 0x00])
    buf.append(len(data))
    buf.extend(data)
    uart_response(0x90, 0x10, buf)

def get_mouse_input():
    global bleft, bright, bmiddle, bprev, bnext, x, y, button_offset, xy_offset
    try:
        buf = os.read(mouse, 64)
        if (buf[button_offset] & 1) == 1:
            bleft = True
        else:
            bleft = False
        if (buf[button_offset] & 2) == 2:
            bright = True
        else:
            bright = False
        if (buf[button_offset] & 4) == 4:
            bmiddle = True
        else:
            bmiddle = False
        if (buf[button_offset] & 8) == 8:
            bprev = True
        else:
            bprev = False
        if (buf[button_offset] & 16) == 16:
            bnext = True
        else:
            bnext = False
        if xy_is_16bit:
            uint_x = (buf[1+xy_offset] << 8) | buf[2+xy_offset]
            uint_y = (buf[3+xy_offset] << 8) | buf[4+xy_offset]
            x = (int(uint_x^0xffff) * -1)-1 if (uint_x & 0x8000) else int(uint_x)
            y = (int(uint_y^0xffff) * -1)-1 if (uint_y & 0x8000) else int(uint_y)
        else:
            x = -(buf[1] & 0b10000000) | (buf[1] & 0b01111111)
            y = -(buf[2] & 0b10000000) | (buf[2] & 0b01111111)
    except BlockingIOError:
        x = 0 
        y = 0
    except:
        os._exit(1)

def calc_gyro():
    global gyrox, gyroy, gyroz, x, y, mouse_threshold, x_last, y_last
    gyrox = 0
    gyroy_diff = int(y - y_last) * 820.0 * gyroy_scale / mouse_threshold
    gyroz_diff = -int(x - x_last) * 820.0 * gyroz_scale / mouse_threshold
    gyroy_next = gyroy + gyroy_diff
    gyroz_next = gyroz + gyroz_diff
    gyro_diff = ((gyroy_diff ** 2) + (gyroz_diff ** 2)) ** 0.5
    if gyro_diff < gyro_diff_smallest and gyro_diff > 0.0:
        gyroy_diff = gyroy_diff * gyro_diff_smallest / gyro_diff
        gyroz_diff = gyroz_diff * gyro_diff_smallest / gyro_diff
        gyroy_next = gyroy + gyroy_diff
        gyroz_next = gyroz + gyroz_diff
    x_last = x
    y_last = y
    gyroy = int(gyroy_next)
    gyroz = int(gyroz_next)

def get_mouse_and_calc_gyro():
    while True:
        get_mouse_input()
        calc_gyro()
        time.sleep(1/60)

def bottle():
    global loopcount
    while True:
        time.sleep(2/60)
        loopcount = True
        time.sleep(2/60)
        loopcount = False


def input_response():
    global loopcount, bleft, bright, bmiddle, bprev, bnext, gyrox, gyroy, gyroz, y_hold
    while True:
        buf = bytearray.fromhex(initial_input)
        buf[2] = 0x00
        if keyboard.is_pressed('l') or bnext:
            #A
            buf[1] |= 0x08
        if keyboard.is_pressed('k') or bprev:
            #B
            buf[1] |= 0x04
        if keyboard.is_pressed('i'):
            #X
            buf[1] |= 0x02
        #y button hold
        if keyboard.is_pressed('y'):
            if y_hold:
                y_hold = False
            else:
                y_hold = True
        if keyboard.is_pressed('j') or y_hold or keyboard.is_pressed(' '):
            #Y
            buf[1] |= 0x01
        if keyboard.is_pressed('f'):
            #DUP
            buf[3] |= 0x02
        elif keyboard.is_pressed('v'):
            #DDOWN
            buf[3] |= 0x01
        if keyboard.is_pressed('c'):
            #DLEFT
            buf[3] |= 0x08
        elif keyboard.is_pressed('b'):
            #DRIGHT
            buf[3] |= 0x04
        if keyboard.is_pressed('h'):
            #HOME
            buf[2] |= 0x10
        if keyboard.is_pressed('u'):
            #PLUS
            buf[2] |= 0x02
        if keyboard.is_pressed('t'):
            #MINUS
            buf[2] |= 0x01
        if keyboard.is_pressed('g'):
            #CAPTURE
            buf[2] |= 0x20
        if keyboard.is_pressed('q'):
            #LCLICK
            buf[2] |= 0x08
        if keyboard.is_pressed('r'):
            #L
            buf[3] |= 0x40
        if keyboard.is_pressed('e'):
            #ZL
            buf[3] |= 0x80
        if bleft:
            #ZR
            if keyboard.is_pressed('p') and not loopcount:
                pass
            else:
                buf[1] |= 0x80
        if bright:
            #R
            buf[1] |= 0x40
        if bmiddle:
            #RSTICK
            buf[2] |= 0x04
        lh = 0x800
        lv = 0x800
        rh = 0x800
        rv = 0x800
        if keyboard.is_pressed('w'):
            lv = 0xFFF
        elif keyboard.is_pressed('s'):
            lv = 0x000
        if keyboard.is_pressed('a'):
            lh = 0x000
        elif keyboard.is_pressed('d'):
            lh = 0xFFF
        if keyboard.is_pressed('up'):
            rv = 0xFFF
        elif keyboard.is_pressed('down'):
            rv = 0x000
        if keyboard.is_pressed('left'):
            rh = 0x000
        elif keyboard.is_pressed('right'):
            rh = 0xFFF
        stick_l_flg = lh | (lv << 12)
        stick_r_flg = rh | (rv << 12)
        buf[4] = stick_l_flg & 0xff
        buf[5] = (stick_l_flg >> 8) & 0xff
        buf[6] = (stick_l_flg >> 16) & 0xff
        buf[7] = stick_r_flg & 0xff
        buf[8] = (stick_r_flg >> 8) & 0xff
        buf[9] = (stick_r_flg >> 16) & 0xff
        sixaxis = bytearray(36)
        sixaxis[6] = sixaxis[18] = sixaxis[30] = gyrox & 0xff
        sixaxis[7] = sixaxis[19] = sixaxis[31] = (gyrox >> 8) & 0xff
        sixaxis[8] = sixaxis[20] = sixaxis[32] = gyroy & 0xff
        sixaxis[9] = sixaxis[21] = sixaxis[33] = (gyroy >> 8) & 0xff
        sixaxis[10] = sixaxis[22] = sixaxis[34] = gyroz & 0xff
        sixaxis[11] = sixaxis[23] = sixaxis[35] = (gyroz >> 8) & 0xff
        buf.extend(sixaxis)
        response(0x30, counter, buf)
        time.sleep(1/125)

def simulate_procon():
    while True:
        try:
            data = os.read(gadget, 128)
            if data[0] == 0x80:
                if data[1] == 0x01:
                    response(0x81, data[1], bytes.fromhex('0003' + mac_addr))
                elif data[1] == 0x02:
                    response(0x81, data[1], [])
                elif data[1] == 0x04:
                    threading.Thread(target=input_response).start()
                else:
                    print('>>>', data.hex())
            elif data[0] == 0x01 and len(data) > 16:
                if data[10] == 0x01: # Bluetooth manual pairing
                    uart_response(0x81, data[10], [0x03])
                elif data[10] == 0x02: # Request device info
                    uart_response(0x82, data[10], bytes.fromhex('03490302' + mac_addr[::-1] + '0302'))
                elif data[10] == 0x03 or data[10] == 0x08 or data[10] == 0x30 or data[10] == 0x38 or data[10] == 0x40 or data[10] == 0x48:                
                    uart_response(0x80, data[10], [])
                elif data[10] == 0x04: # Trigger buttons elapsed time
                    uart_response(0x83, data[10], [])
                elif data[10] == 0x21: # Set NFC/IR MCU configuration
                    uart_response(0xa0, data[10], bytes.fromhex('0100ff0003000501'))
                elif data[10] == 0x10:
                    if data[11:13] == b'\x00\x60': # Serial number
                        spi_response(data[11:13], bytes.fromhex('ffffffffffffffffffffffffffffffff'))
                    elif data[11:13] == b'\x50\x60': # Controller Color
                        spi_response(data[11:13], bytes.fromhex('bc1142 75a928 ffffff ffffff ff')) # Raspberry Color
                    elif data[11:13] == b'\x80\x60': # Factory Sensor and Stick device parameters
                        spi_response(data[11:13], bytes.fromhex('50fd0000c60f0f30619630f3d41454411554c7799c333663'))
                    elif data[11:13] == b'\x98\x60': # Factory Stick device parameters 2
                        spi_response(data[11:13], bytes.fromhex('0f30619630f3d41454411554c7799c333663'))
                    elif data[11:13] == b'\x3d\x60': # Factory configuration & calibration 2
                        spi_response(data[11:13], bytes.fromhex('ba156211b87f29065bffe77e0e36569e8560ff323232ffffff'))
                    elif data[11:13] == b'\x10\x80': # User Analog sticks calibration
                        spi_response(data[11:13], bytes.fromhex('ffffffffffffffffffffffffffffffffffffffffffffb2a1'))
                    elif data[11:13] == b'\x28\x80': # User 6-Axis Motion Sensor calibration
                        spi_response(data[11:13], bytes.fromhex('beff3e00f001004000400040fefffeff0800e73be73be73b'))
                    else:
                        print("Unknown SPI address:", data[11:13].hex())
                else:
                    print('>>> [UART]', data.hex())
            elif data[0] == 0x10 and len(data) == 10:
                pass
            else:
                print('>>>', data.hex())
        except BlockingIOError:
            pass
        except:
            os._exit(1)

def hand(signal, frame):
    disconnect_response()
    os.system('echo > /sys/kernel/config/usb_gadget/procon/UDC')
    os.system('ls /sys/class/udc > /sys/kernel/config/usb_gadget/procon/UDC')
    time.sleep(0.5)
    os._exit(1)

threading.Thread(target=simulate_procon).start()
threading.Thread(target=countup).start()
threading.Thread(target=get_mouse_and_calc_gyro).start()
threading.Thread(target=bottle).start()
signal.signal(signal.SIGINT, hand)
