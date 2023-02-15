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

class Patient:
    def __init__(self):
        self.down = False
        self.mouse_track = []
        self.wacom_x = 0
        self.wacom_y = 0
        self.origin_x = 0
        self.origin_y = 0


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


def handle_pygame_events(name, pub, ze, screen):
    global RUNNING

    keydown_up = False
    keydown_down = False
    keydown_right = False
    keydown_left = False

    li = python_libinput.libinput()
    assert li.start()

    print("Listening to pygame events...")
    while RUNNING:
        # Non-blocking polling of events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Received quit!")
                RUNNING = False
                break

            if event.type == pygame.MOUSEMOTION:
                w_x, w_y = event.pos
                PATIENTS[name].wacom_x = w_x
                PATIENTS[name].wacom_y = w_y
                if PATIENTS[name].down:
                    PATIENTS[name].mouse_track[-1].append(event.pos)
                msg = ze.mouse_motion(w_x, w_y)
                pub.send_string(msg)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                PATIENTS[name].down = True
                PATIENTS[name].mouse_track.append([])
                msg = ze.mouse_down()
                pub.send_string(msg)

            elif event.type == pygame.MOUSEBUTTONUP:
                PATIENTS[name].down = False
                msg = ze.mouse_up()
                pub.send_string(msg)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    keydown_up = True
                elif event.key == pygame.K_DOWN:
                    keydown_down = True
                elif event.key == pygame.K_RIGHT:
                    keydown_right = True
                elif event.key == pygame.K_LEFT:
                    keydown_left = True

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

        events = li.poll()
        for event in events:
            # tip up / down
            if event.type == 0:
                if event.tip_is_down:
                    PATIENTS[name].down = True
                    PATIENTS[name].mouse_track.append([])
                    msg = ze.mouse_down()
                    pub.send_string(msg)
                else:
                    PATIENTS[name].down = False
                    msg = ze.mouse_up()
                    pub.send_string(msg)
            # cursor move
            elif event.type == 1:
                x, y = event.x, event.y
                size = screen.get_rect()
                w, h = size.w, size.h
                w_x, w_y = x * w, y * h
                PATIENTS[name].wacom_x = w_x
                PATIENTS[name].wacom_y = w_y
                if PATIENTS[name].down:
                    PATIENTS[name].mouse_track[-1].append((w_x, w_y))
                msg = ze.mouse_motion(w_x, w_y)
                pub.send_string(msg)

        sleep(0.02)

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
            w_x, w_y = int(msg[3]), int(msg[4])
            PATIENTS[patient].wacom_x = w_x
            PATIENTS[patient].wacom_y = w_y
            if PATIENTS[patient].down:
                PATIENTS[patient].mouse_track[-1].append((w_x, w_y))

        elif event == "MouseDown":
            PATIENTS[patient].down = True
            PATIENTS[patient].mouse_track.append([])

        elif event == "MouseUp":
            PATIENTS[patient].down = False

        elif event == "Origin":
            o_x, o_y = int(msg[3]), int(msg[4])
            PATIENTS[patient].origin_x = o_x
            PATIENTS[patient].origin_y = o_y

    sub.close()


def main(frontend, backend, name, topic):
    pygame.init()
    pygame.display.set_caption("Therapy Session")
    screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)

    p = Patient()
    PATIENTS[name] = p

    ctx = zmq.Context()
    pub = ctx.socket(zmq.PUB)
    pub.connect(backend)

    sub = ctx.socket(zmq.SUB)
    sub.connect(frontend)
    sub.setsockopt_string(zmq.SUBSCRIBE, topic)

    ze = ZmqEvent(topic, name)

    pygame_event_thread = Thread(target=handle_pygame_events, args=(name, pub, ze, screen))
    zmq_event_thread = Thread(target=handle_zmq_events, args=(name, sub))

    pygame_event_thread.start()
    zmq_event_thread.start()

    c_red = (255,0,0)
    c_white = (255,255,255)

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
                for end in segment[1:]:
                    start_x, start_y = start
                    end_x, end_y = end

                    start_x += patient.origin_x
                    start_y += patient.origin_y
                    end_x += patient.origin_x
                    end_y += patient.origin_y

                    start = (start_x, start_y)
                    adj_end = (end_x, end_y)

                    pygame.draw.line(screen, c_red, start, adj_end, width=1)
                    start = end

            pygame.draw.circle(screen, c_white, (patient.wacom_x, patient.wacom_y), 4)

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
    parser.add_argument("-t", "--topic", default="Therapy")
    args = parser.parse_args()

    try:
        main(args.frontend, args.backend, args.patient, args.topic)
    except KeyboardInterrupt:
        print("\rCaught interrupt. Stopping...")
        RUNNING = False
