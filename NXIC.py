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

gadget = os.open('/dev/hidg0', os.O_RDWR | os.O_NONBLOCK)
mouse = os.open('/dev/hidraw5', os.O_RDWR | os.O_NONBLOCK)
# mouse_sub = os.open('/dev/hidraw1', os.O_RDWR | os.O_NONBLOCK)

#////////////////////////////////USERCONFIG////////////////////////////////////
gyro_y_scale = 350.0
gyro_z_scale = 150.0
angle_y_scale = 0.04 #0.035
stick_z_scale = 10
stick_z_offset = 320 # 160.0

#If the x,y values taken from the mouse are 16 bits each, set to True.
#If the x,y value does not start from the second byte (the first byte is probably the button input, but there is an unnecessary byte after it), enter the number of bytes to be skipped in the offset.
xy_is_16bit = True
xy_offset = 0

#If the byte signifying the button press is not the first, enter the number of bytes to be skipped in the offset.
button_offset = 0

print_debug = False

#//////////////////////////////////////////////////////////////////////////////

counter = 0
mac_addr = 'D4F0578D7423'
initial_input = '81008000f8d77a22c87b0c'
loopcount = False

mouse_left = False
mouse_right = False
mouse_middle = False
mouse_prev = False
mouse_next = False
mouse_speed_x = 0
mouse_speed_y = 0
mouse_timeout = 0

submouse_left = False
submouse_right = False
submouse_middle = False
submouse_prev = False
submouse_next = False

gyro_x = 0
gyro_y = 0
gyro_z = 0
angle_x = 0
angle_y = 0
angle_z = 4096
y_hold = False
angle_y_reset_rate = 100
angle_y_reset_start_value = 0
angle_y_reset_gyro = 0
angle_y_reset_finished = 0
gyro_y_resetcount = 0
gyro_y_resetcount_max = 16000
gyro_y_reset_start_flag = False
gyro_y_reset_sending_count = 0
viewpoint_reset_ready_flag = False
minimum_sending_count = 3
nice_mode = True
nice_mode_changed = False
nice_counter = 0
nice_flag = False
gattling_mode = False
gattling_mode_changed = False
jumping_mode = False
jumping_mode_changed = False
jumping_shoot = False
jumping_shoot_changed = False
angle_y_prev = 0

gamepad_sending = False
gamepad_receiving = False

# Sleep functions
cyclic_sleep_start_time = time.perf_counter_ns()

def precise_sleep(duration):
    now = time.perf_counter_ns()
    previous = now
    passed = 0.0
    while duration > passed:
        now = time.perf_counter_ns()
        passed = passed + float(now - previous)*1e-9

def init_cyclic_sleep():
    global cyclic_sleep_curernt_time
    cyclic_sleep_curernt_time = time.perf_counter_ns()

def cyclic_sleep(duration):
    global cyclic_sleep_start_time
    now = time.perf_counter_ns()
    previous = cyclic_sleep_start_time
    passed = float(now - previous)*1e-9
    while duration > passed:
        now = time.perf_counter_ns()
        passed = passed + float(now - previous)*1e-9
    cyclic_sleep_start_time = now

# Function for gattling mode
def gattling_flag(rate):
    now = time.perf_counter_ns()
    loop_ns = int(1e9/rate)
    remain = now // loop_ns
    if remain < loop_ns / 2:
        return True
    else:
        return False

    
def countup():
    global counter
    while True:
        counter = (counter + 3) % 256
        time.sleep(0.03)

def response(code, cmd, data):
    global gamepad_sending, gamepad_receiving

    receiving_detected = False
    while gamepad_receiving:
        receiving_detected = True
    if receiving_detected:
        time.sleep(1/250)

    buf = bytearray([code, cmd])
    buf.extend(data)
    buf.extend(bytearray(64-len(buf)))

    if print_debug:
        print(buf.hex())
    try:
        gamepad_sending = True
        os.write(gadget, buf)
        gamepad_sending = False
    except BlockingIOError:
        print('response:BlockingIOError')
        gamepad_sending = False
        pass
    except:
        print('response:os.write Failed')
        gamepad_sending = False
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
    global mouse_left, mouse_right, mouse_middle, mouse_prev, mouse_next, mouse_speed_x, mouse_speed_y, button_offset, xy_offset, mouse_timeout
    try:
        buf = os.read(mouse, 64)
        mouse_timeout = 0
        # print(buf)
        if (buf[0+button_offset] & 1) == 1:
            mouse_left = True
        else:
            mouse_left = False
        if (buf[0+button_offset] & 2) == 2:
            mouse_right = True
        else:
            mouse_right = False
        if (buf[0+button_offset] & 4) == 4:
            mouse_middle = True
        else:
            mouse_middle = False
        if (buf[0+button_offset] & 0x08) == 8:
            mouse_prev = True
        else:
            mouse_prev = False
        if (buf[0+button_offset] & 0x10) == 16:
            mouse_next = True
        else:
            mouse_next = False
        if xy_is_16bit:
            uint_mouse_speed_x = (buf[2+xy_offset] << 8) | buf[1+xy_offset]
            uint_mouse_speed_y = (buf[4+xy_offset] << 8) | buf[3+xy_offset]
            mouse_speed_x = int(uint_mouse_speed_x&0xffff)
            mouse_speed_y = int(uint_mouse_speed_y&0xffff)
            if mouse_speed_x > 0x8000:
                mouse_speed_x = mouse_speed_x - 0x10000
            if mouse_speed_y > 0x8000:
                mouse_speed_y = mouse_speed_y - 0x10000
            # print('mouse data:',buf)
            # print('mouse speed:',mouse_speed_x,',',mouse_speed_y)
        else:
            mouse_speed_x = -(buf[1] & 0b10000000) | (buf[1] & 0b01111111)
            mouse_speed_y = -(buf[2] & 0b10000000) | (buf[2] & 0b01111111)
    except BlockingIOError:
        # if mouse_timeout < 3:
        #     mouse_timeout = mouse_timeout + 1
        # else:
        if mouse_speed_x > 0:
            mouse_speed_x = mouse_speed_x - 1
        elif mouse_speed_x < 0:
            mouse_speed_x = mouse_speed_x + 1
        if mouse_speed_y > 0:
            mouse_speed_y = mouse_speed_y - 1
        elif mouse_speed_y < 0:
            mouse_speed_y = mouse_speed_y + 1
    except:
        os._exit(1)

def calc_gyro():
    global gyro_x, gyro_y, gyro_z, angle_x, angle_y, angle_z, gyro_y_scale, gyro_z_scale, angle_y_scale, mouse_speed_x, mouse_speed_y, angle_y_prev
    gyro_x = 0
    gyro_y = int(float(mouse_speed_y) * gyro_y_scale)
    gyro_z = int(float(-mouse_speed_x) * gyro_z_scale)
    angle_y_prev = angle_y_prev
    angle_y = angle_y - int(float(gyro_y) * angle_y_scale)
    if angle_y > 3000:
        angle_y = 3000
        gyro_y = 0
    elif angle_y < -3000:
        angle_y = -3000
        gyro_y = 0
    # print('gyro output:',gyro_z)

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

def simulate_procon():
    global gamepad_sending, gamepad_receiving
    while True:
        try:
            sending_detected = False
            while gamepad_sending:
                sending_detected = True
            if sending_detected:
                time.sleep(1/250)
            gamepad_receiving = True
            data = os.read(gadget, 128)
            gamepad_receiving = False
            # print('>>>', data.hex())
            if data[0] == 0x80:
                if data[1] == 0x01:
                    response(0x81, data[1], bytes.fromhex('0003' + mac_addr))
                elif data[1] == 0x02:
                    response(0x81, data[1], [])
                elif data[1] == 0x04:
                    threading.Thread(target=input_response).start()
                else:
                    if print_debug:
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
                    if print_debug:
                        print('>>> [UART]', data.hex())
            elif data[0] == 0x10 and len(data) == 10:
                pass
            else:
                if print_debug:
                    print('>>>', data.hex())
            time.sleep(1/125)
        except BlockingIOError:
            gamepad_receiving = False
            time.sleep(1/125)
            # print("simulate_procon():BlockingIOError")
            pass
        except:
            gamepad_receiving = False
            os._exit(1)

def input_response():
    global loopcount, mouse_left, mouse_right, mouse_middle, mouse_prev, mouse_next, gyro_x, gyro_y, gyro_z, y_hold, angle_y, \
    nice, nice_counter, angle_y_reset_rate, angle_y_reset_start_value, angle_y_reset_gyro, \
    gyro_y_resetcount, gyro_y_resetcount_max, gyro_y_reset_start_flag, gyro_y_reset_sending_count, \
    minimum_sending_count, gattling_mode, gattling_mode_changed, \
    nice_mode,nice_mode_changed, nice_counter, nice_flag, jumping_mode, jumping_mode_changed, \
    jumping_shoot, jumping_shoot_changed, angle_y_prev, stick_z_scale, stick_z_offset, mouse_speed_x, mouse_speed_y
    while True:
        buf = bytearray.fromhex(initial_input)
        buf[2] = 0x00
        if keyboard.is_pressed('5') or mouse_next:
            #A
            buf[1] |= 0x08
        if keyboard.is_pressed('r') or keyboard.is_pressed('w') or mouse_prev:
            #B
            buf[1] |= 0x04
        if keyboard.is_pressed('4'):
            #X
            buf[1] |= 0x02
        #y button hold
        if keyboard.is_pressed('e'):
            #Y
            buf[1] |= 0x01
        if keyboard.is_pressed('s'): # or keyboard.is_pressed(' '):
            #ZL
            buf[3] |= 0x80
            loopcount = False
        if keyboard.is_pressed(' ') and gyro_y_reset_start_flag == False:
            #Y
            if angle_y == 0:
                gyro_y = 0
                buf[1] |= 0x01
            else:
                angle_y_reset_start_value = angle_y
                gyro_y_resetcount_max = int(abs(angle_y) / angle_y_reset_rate)
                angle_y_reset_gyro = int((angle_y / abs(angle_y)) * angle_y_reset_rate / angle_y_scale)
                gyro_y_resetcount = 0
                gyro_y_reset_start_flag = True
        if gyro_y_reset_start_flag == True:
            if gyro_y_resetcount < gyro_y_resetcount_max:
                gyro_y_resetcount = gyro_y_resetcount + 1
                if angle_y != 0:
                    gyro_y = angle_y_reset_gyro * 2
                    angle_y_next = int(angle_y_reset_start_value * (gyro_y_resetcount_max - gyro_y_resetcount) / gyro_y_resetcount_max)
                    if angle_y_next * angle_y > 0:
                        angle_y = angle_y_next
            else:
                angle_y = 0
                if gyro_y_resetcount < gyro_y_resetcount_max * 2:
                    gyro_y_resetcount = gyro_y_resetcount + 1
                    gyro_y = 0                
                if gyro_y_resetcount < gyro_y_resetcount_max * 2 + minimum_sending_count * 2:
                    gyro_y_resetcount = gyro_y_resetcount + 1
                    buf[1] |= 0x01
                else:
                    gyro_y_reset_start_flag = False
                    gyro_y_reset_sending_count = 0
                    buf[1] |= 0x01
        if keyboard.is_pressed('alt') and not loopcount:
            #DDOWN
            buf[3] |= 0x01
        if (keyboard.is_pressed('j') or y_hold) :
            #Y
            buf[1] |= 0x01
        if keyboard.is_pressed('3'):
            #DUP
            buf[3] |= 0x02
        elif keyboard.is_pressed('x'):
            #DDOWN
            buf[3] |= 0x01
        if keyboard.is_pressed('capslock'):
            #DLEFT
            buf[3] |= 0x08
        elif keyboard.is_pressed('f'):
            #DRIGHT
            buf[3] |= 0x04
        if keyboard.is_pressed('h'):
            #HOME
            buf[2] |= 0x10
        if keyboard.is_pressed('c'):
            #PLUS
            buf[2] |= 0x02
        if keyboard.is_pressed('shift'):
            #MINUS
            buf[2] |= 0x01
        if keyboard.is_pressed('g'):
            #CAPTURE
            buf[2] |= 0x20
        if keyboard.is_pressed('q'):
            #RCLICK
            buf[2] |= 0x04
        if keyboard.is_pressed('tab'):
            #LCLICK
            buf[2] |= 0x08
        if keyboard.is_pressed('z'):
            #L
            buf[3] |= 0x40
        if keyboard.is_pressed('e'):
            #ZL
            buf[3] |= 0x80
        # if keyboard.is_pressed(' '):
        #     #ZL
        #     buf[3] |= 0x80
        #     gyro_y = 0
        #     angle_y = angle_y_prev
        #     if angle_y > 0:
        #         angle_y = angle_y - 1
        #     elif angle_y < 0:
        #         angle_y = angle_y + 1
        if keyboard.is_pressed('1'):
            angle_y = 0
            buf[1] |= 0x01
            if mouse_left:
                #Switch gattling mode
                if not gattling_mode_changed:
                    gattling_mode_changed = True
                    gattling_mode = not gattling_mode
            else:
                gattling_mode_changed = False
            if mouse_middle:
                #Switch nice mode
                if not nice_mode_changed:
                    nice_mode_changed = True
                    nice_mode = not nice_mode
            else:
                nice_mode_changed = False
            if keyboard.is_pressed('2'):
                #Switch jump_shoot mode
                if not jumping_shoot_changed:
                    jumping_shoot_changed = True
                    jumping_shoot = not jumping_shoot
            else:
                jumping_shoot_changed = False
        else:
            if mouse_left:
                #ZR
                if (keyboard.is_pressed('p') or gattling_mode) and not loopcount:
                    pass
                else:
                    buf[1] |= 0x80
            if mouse_right:
                #R
                buf[1] |= 0x40
            if mouse_middle:
                if not nice_mode:
                    #RSTICK
                    buf[2] |= 0x04
                else:
                    if nice_counter < minimum_sending_count * 2:
                        #RSTICK
                        buf[2] |= 0x04
                        nice_counter = nice_counter + 1
                    else:
                        nice_flag  = True
                        if not loopcount:
                            #DDOWN
                            buf[3] |= 0x01
            elif nice_flag:
                #R
                buf[1] |= 0x40
                if nice_counter < minimum_sending_count * 4:
                    nice_counter = nice_counter + 1
                else:
                    nice_counter = 0
                    nice_flag = False

            if keyboard.is_pressed('2') and not loopcount and not keyboard.is_pressed(' '):
                if not jumping_shoot:
                    if not mouse_left  and not mouse_right  and not mouse_middle:
                        #B
                        buf[1] |= 0x04
                else:
                    #B
                    buf[1] |= 0x04
        lh = 0x800
        lv = 0x800
        rh = 0x800
        rv = 0x800
        if keyboard.is_pressed('up'):
            lv = 0xFFF
        elif keyboard.is_pressed('down'):
            lv = 0x000
        if keyboard.is_pressed('left'):
            lh = 0x000
        elif keyboard.is_pressed('right'):
            lh = 0xFFF
        # if keyboard.is_pressed('up'):
        #     rv = 0xFFF
        # elif keyboard.is_pressed('down'):
        #     rv = 0x000
        if keyboard.is_pressed('a'):
            rh = 0x000
        elif keyboard.is_pressed('d'):
            rh = 0xFFF
        # if stick_z_scale > 0:
        #     if mouse_speed_x > 0:
        #         rh_tmp = int(stick_z_offset + mouse_speed_x * stick_z_scale)
        #         if rh_tmp > 2047:
        #             rh_tmp = 2047
        #         rh = 0x800 + rh_tmp
        #     elif mouse_speed_x < 0:
        #         rh_tmp = int(-stick_z_offset + mouse_speed_x * stick_z_scale)
        #         if rh_tmp < -2047:
        #             rh_tmp = -2047
        #         rh = 0x800 + rh_tmp
        stick_l_flg = lh | (lv << 12)
        stick_r_flg = rh | (rv << 12)
        buf[4] = stick_l_flg & 0xff
        buf[5] = (stick_l_flg >> 8) & 0xff
        buf[6] = (stick_l_flg >> 16) & 0xff
        buf[7] = stick_r_flg & 0xff
        buf[8] = (stick_r_flg >> 8) & 0xff
        buf[9] = (stick_r_flg >> 16) & 0xff
        sixaxis = bytearray(36)
        sixaxis[0] = sixaxis[18] = sixaxis[30] = angle_y & 0xff
        sixaxis[1] = sixaxis[19] = sixaxis[31] = (angle_y >> 8) & 0xff
        sixaxis[2] = sixaxis[20] = sixaxis[32] = angle_x & 0xff
        sixaxis[3] = sixaxis[21] = sixaxis[33] = (angle_x >> 8) & 0xff
        sixaxis[4] = sixaxis[22] = sixaxis[34] = angle_z & 0xff
        sixaxis[5] = sixaxis[23] = sixaxis[35] = (angle_z >> 8) & 0xff
        sixaxis[6] = sixaxis[18] = sixaxis[30] = gyro_x & 0xff
        sixaxis[7] = sixaxis[19] = sixaxis[31] = (gyro_x >> 8) & 0xff
        sixaxis[8] = sixaxis[20] = sixaxis[32] = gyro_y & 0xff
        sixaxis[9] = sixaxis[21] = sixaxis[33] = (gyro_y >> 8) & 0xff
        sixaxis[10] = sixaxis[22] = sixaxis[34] = gyro_z & 0xff
        sixaxis[11] = sixaxis[23] = sixaxis[35] = (gyro_z >> 8) & 0xff
        buf.extend(sixaxis)
        response(0x30, counter, buf)
        time.sleep(1/125)
        # print('current_ns:',time.perf_counter_ns())
        # precise_sleep(1/100)

def hand(signal, frame):
    disconnect_response()
    os.system('echo > /sys/kernel/config/usb_gadget/procon/UDC')
    os.system('ls /sys/class/udc > /sys/kernel/config/usb_gadget/procon/UDC')
    time.sleep(0.5)
    os._exit(1)

init_cyclic_sleep()
threading.Thread(target=simulate_procon).start()
threading.Thread(target=countup).start()
threading.Thread(target=get_mouse_and_calc_gyro).start()
threading.Thread(target=bottle).start()
signal.signal(signal.SIGINT, hand)

