#!/usr/bin/env python3
from argparse import ArgumentParser
import zmq

def proxy(faddr, baddr):
    ctx = zmq.Context()

    try:
        frontend = ctx.socket(zmq.XPUB)
        frontend.bind(faddr)

        backend = ctx.socket(zmq.XSUB)
        backend.bind(baddr)

        print(f"Bound XPUB to {faddr}")
        print(f"Bound XSUB to {baddr}")

        zmq.proxy(frontend, backend)

    except KeyboardInterrupt:
        print("\rCaught interrupt. Exiting.")
        frontend.close()
        backend.close()
        ctx.term()

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-f", "--frontend", default="tcp://*:5559")
    parser.add_argument("-b", "--backend", default="tcp://*:5560")
    args = parser.parse_args()

    proxy(args.frontend, args.backend)
