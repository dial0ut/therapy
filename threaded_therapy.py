#!/usr/bin/env python3
from argparse import ArgumentParser
from threading import Thread
from time import sleep

import pygame
import zmq

import python_libinput

FPS = 30
RUNNING = True
PATIENTS = {}

CLR_BLACK = (0, 0, 0)
CLR_WHITE = (255, 255, 255)
CLR_RED = (255, 0, 0)
CLR_GREEN = (0, 255, 0)
CLR_CYAN = (0, 255, 255)
CLR_YELLOW = (255, 255, 0)

class Patient:
    def __init__(self):
        self.down = False
        self.mouse_track = []
        self.wacom_x = 0
        self.wacom_y = 0
        self.origin_x = 0
        self.origin_y = 0
        self.brush_size = 1
        self.brush_color = CLR_RED


class ZmqEvent:
    def __init__(self, topic, name):
        self.topic = topic
        self.name = name

    def mouse_motion(self, x, y):
        return f"{self.topic}:{self.name}:MouseMotion:{x}:{y}"

    def mouse_down(self):
        return f"{self.topic}:{self.name}:MouseDown"

    def mouse_up(self):
        return f"{self.topic}:{self.name}:MouseUp"

    def origin(self, x, y):
        return f"{self.topic}:{self.name}:Origin:{x}:{y}"

    def set_color(self, color):
        return f"{self.topic}:{self.name}:SetColor:{color[0]}:{color[1]}:{color[2]}"

    def set_size(self, size):
        return f"{self.topic}:{self.name}:SetSize:{size}"


def handle_pygame_events(name, pub, ze, is_libbinput_enabled):
    global RUNNING

    keydown_up = False
    keydown_down = False
    keydown_right = False
    keydown_left = False

    print("Listening to pygame events...")
    while RUNNING:
        event = pygame.event.wait()

        if event.type == pygame.QUIT:
            print("Received quit!")
            RUNNING = False
            break

        elif event.type == pygame.MOUSEMOTION:
            if is_libbinput_enabled:
                continue

            w_x, w_y = event.pos
            PATIENTS[name].wacom_x = w_x
            PATIENTS[name].wacom_y = w_y
            if PATIENTS[name].down:
                brush = (PATIENTS[name].brush_size, PATIENTS[name].brush_color)
                PATIENTS[name].mouse_track[-1].append((brush, event.pos))
            pub.send_string(ze.mouse_motion(w_x, w_y))

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if is_libbinput_enabled:
                continue

            PATIENTS[name].down = True
            PATIENTS[name].mouse_track.append([])
            pub.send_string(ze.mouse_down())

        elif event.type == pygame.MOUSEBUTTONUP:
            if is_libbinput_enabled:
                continue

            PATIENTS[name].down = False
            pub.send_string(ze.mouse_up())

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                keydown_up = True
            elif event.key == pygame.K_DOWN:
                keydown_down = True
            elif event.key == pygame.K_RIGHT:
                keydown_right = True
            elif event.key == pygame.K_LEFT:
                keydown_left = True

            elif event.key == pygame.K_0:
                PATIENTS[name].brush_color = CLR_BLACK
                pub.send_string(ze.set_color(CLR_BLACK))
            elif event.key == pygame.K_1:
                PATIENTS[name].brush_color = CLR_WHITE
                pub.send_string(ze.set_color(CLR_WHITE))
            elif event.key == pygame.K_2:
                PATIENTS[name].brush_color = CLR_RED
                pub.send_string(ze.set_color(CLR_RED))
            elif event.key == pygame.K_3:
                PATIENTS[name].brush_color = CLR_GREEN
                pub.send_string(ze.set_color(CLR_GREEN))
            elif event.key == pygame.K_4:
                PATIENTS[name].brush_color = CLR_CYAN
                pub.send_string(ze.set_color(CLR_CYAN))
            elif event.key == pygame.K_5:
                PATIENTS[name].brush_color = CLR_YELLOW
                pub.send_string(ze.set_color(CLR_YELLOW))

            elif event.key == pygame.K_q:
                PATIENTS[name].brush_size = 1
                pub.send_string(ze.set_size(1))
            elif event.key == pygame.K_w:
                PATIENTS[name].brush_size = 2
                pub.send_string(ze.set_size(2))
            elif event.key == pygame.K_e:
                PATIENTS[name].brush_size = 3
                pub.send_string(ze.set_size(3))
            elif event.key == pygame.K_r:
                PATIENTS[name].brush_size = 4
                pub.send_string(ze.set_size(4))
            elif event.key == pygame.K_t:
                PATIENTS[name].brush_size = 5
                pub.send_string(ze.set_size(5))
            elif event.key == pygame.K_y:
                PATIENTS[name].brush_size = 6
                pub.send_string(ze.set_size(6))


        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                keydown_up = False
            elif event.key == pygame.K_DOWN:
                keydown_down = False
            elif event.key == pygame.K_RIGHT:
                keydown_right = False
            elif event.key == pygame.K_LEFT:
                keydown_left = False

        """ Origin is a bit buggy
        if keydown_up:
            PATIENTS[name].origin_y -= 20
        if keydown_down:
            PATIENTS[name].origin_y += 20
        if keydown_left:
            PATIENTS[name].origin_x -= 20
        if keydown_right:
            PATIENTS[name].origin_x += 20

        if keydown_up or keydown_down or keydown_left or keydown_right:
            msg = ze.origin(PATIENTS[name].origin_x, PATIENTS[name].origin_y)
            pub.send_string(msg)
        """

    pub.close()

def handle_libinput_events(name, pub, ze, screen):
    global RUNNING

    li = python_libinput.libinput()
    assert li.start()

    print("Listening to libinput events...")
    while RUNNING:
        events = li.poll()
        for event in events:
            # tip up / down
            if event.type == 0:
                if event.tip_is_down:
                    PATIENTS[name].down = True
                    PATIENTS[name].mouse_track.append([])
                    pub.send_string(ze.mouse_down())
                else:
                    PATIENTS[name].down = False
                    pub.send_string(ze.mouse_up())
            # cursor move
            elif event.type == 1:
                x, y = event.x, event.y
                size = screen.get_rect()
                w, h = size.w, size.h
                w_x, w_y = x * w, y * h
                PATIENTS[name].wacom_x = w_x
                PATIENTS[name].wacom_y = w_y
                if PATIENTS[name].down:
                    brush = (PATIENTS[name].brush_size, PATIENTS[name].brush_color)
                    PATIENTS[name].mouse_track[-1].append((brush, (w_x, w_y)))
                pub.send_string(ze.mouse_motion(w_x, w_y))
        li.wait()

    pub.close()

def handle_zmq_events(name, sub):
    global RUNNING

    print("Listening to ZMQ events...")
    while RUNNING:
        msg = sub.recv_string()  # This hangs once when RUNNING=False
        msg = msg.split(":")

        _topic = msg[0]
        patient = msg[1]
        event = msg[2]

        # Skip ourselves
        if name == patient:
            continue

        if not PATIENTS.get(patient):
            PATIENTS[patient] = Patient()

        if event == "MouseMotion":
            w_x, w_y = float(msg[3]), float(msg[4])
            PATIENTS[patient].wacom_x = w_x
            PATIENTS[patient].wacom_y = w_y
            if PATIENTS[patient].down:
                brush = (PATIENTS[patient].brush_size, PATIENTS[patient].brush_color)
                PATIENTS[patient].mouse_track[-1].append((brush, (w_x, w_y)))

        elif event == "MouseDown":
            PATIENTS[patient].down = True
            PATIENTS[patient].mouse_track.append([])

        elif event == "MouseUp":
            PATIENTS[patient].down = False

        elif event == "Origin":
            o_x, o_y = int(msg[3]), int(msg[4])
            PATIENTS[patient].origin_x = o_x
            PATIENTS[patient].origin_y = o_y

        elif event == "SetColor":
            r, g, b = int(msg[3]), int(msg[4]), int(msg[5])
            PATIENTS[patient].brush_color = (r, g, b)

        elif event == "SetSize":
            PATIENTS[patient].brush_size = int(msg[3])

    sub.close()


def main(frontend, backend, name, topic, is_libinput_enabled):
    pygame.init()
    pygame.display.set_caption("Therapy Session")
    screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)

    p = Patient()
    PATIENTS[name] = p

    ctx = zmq.Context()
    ze = ZmqEvent(topic, name)

    # Input event loops

    pygame_pub = ctx.socket(zmq.PUB)
    pygame_pub.connect(backend)

    pygame_event_thread = Thread(target=handle_pygame_events,
                                 args=(name, pygame_pub, ze,
                                       is_libinput_enabled))
    pygame_event_thread.start()

    if is_libinput_enabled:
        libinput_pub = ctx.socket(zmq.PUB)
        libinput_pub.connect(backend)

        libinput_event_thread = Thread(target=handle_libinput_events,
                                       args=(name, libinput_pub, ze,
                                             screen))
        libinput_event_thread.start()

    # Network event loop

    sub = ctx.socket(zmq.SUB)
    sub.connect(frontend)
    sub.setsockopt_string(zmq.SUBSCRIBE, topic)

    zmq_event_thread = Thread(target=handle_zmq_events, args=(name, sub))
    zmq_event_thread.start()

    print("Starting game loop...")
    time_func = pygame.time.get_ticks
    last_tick = time_func() or 0
    while RUNNING:
        screen.fill(pygame.Color("black"))

        for patient in PATIENTS.values():
            for segment in patient.mouse_track:
                if not segment:
                    continue

                start = segment[0]
                size, clr = start[0]
                for end in segment[1:]:
                    start_x, start_y = start[1]
                    end_x, end_y = end[1]

                    start_x += patient.origin_x
                    start_y += patient.origin_y
                    end_x += patient.origin_x
                    end_y += patient.origin_y

                    start = (start_x, start_y)
                    adj_end = (end_x, end_y)

                    pygame.draw.line(screen, clr, start, adj_end, width=size)
                    start = ((size, clr), end[1])

            pygame.draw.circle(screen,
                               patient.brush_color,
                               (patient.wacom_x, patient.wacom_y),
                               patient.brush_size * 2)

        pygame.display.flip()

        end_time = (1.0 / FPS) * 1000
        current = time_func()
        time_diff = current - last_tick
        delay = (end_time - time_diff) / 1000
        last_tick = current
        delay = max(delay, 0)
        sleep(delay)

    pygame_event_thread.join()
    #zmq_event_thread.join()
    pygame.quit()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-f", "--frontend", default="tcp://127.0.0.1:5559")
    parser.add_argument("-b", "--backend", default="tcp://127.0.0.1:5560")
    parser.add_argument("-p", "--patient", required=True, type=str)
    parser.add_argument("-i", "--libinput", action="store_true")
    parser.add_argument("-t", "--topic", default="Therapy")
    args = parser.parse_args()

    try:
        main(args.frontend, args.backend, args.patient, args.topic,
             args.libinput)
    except KeyboardInterrupt:
        print("\rCaught interrupt. Stopping...")
        RUNNING = False
