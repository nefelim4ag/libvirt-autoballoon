#!/usr/bin/env python3

from time import sleep
import libvirt
import sys

SZ_1KiB = 1
SZ_4KiB = 4
SZ_1MiB = 1024
SZ_4MiB = 4096

THRESHOLD_RATIO = 0.125


def get_connection():
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to the hypervisor', flush=True)
        sys.exit(1)
    return conn


def dom_balloon(dom, restrict_to):
    name = dom.name()
    memstat = dom.memoryStats()
    actual = memstat["actual"]
    restrict_to = int(restrict_to)
    actual_m = int(actual / SZ_1MiB)
    restrict_to_m = int(restrict_to / SZ_1MiB)
    if actual > restrict_to:
        print("Shrink dom:", name, actual_m, "->", restrict_to_m, "MiB", flush=True)
    else:
        print("Grow dom:",   name, restrict_to_m, "<-", actual_m, "MiB", flush=True)
    dom.setMemory(restrict_to)


def process_domainID(dom):
    memstat = dom.memoryStats()

    actual = memstat["actual"]
    available = memstat["available"]
    usable = memstat["usable"]
    used = actual - usable

    keep_avail_threshold = available*THRESHOLD_RATIO
    ratio_current = usable/keep_avail_threshold
    if ratio_current < 0.9:
        if actual < available:
            # Balloon memory by some diff of diff
            diff = (actual - used)*THRESHOLD_RATIO
            if diff < SZ_4MiB:
                diff = 0
            dom_balloon(dom, actual + diff + SZ_4KiB)
    else:
        if ratio_current > 1.4:
            diff = (actual - usable)*THRESHOLD_RATIO
            if diff < SZ_4MiB:
                diff = 0
            dom_balloon(dom, actual - diff - SZ_4KiB)


def daemon():
    SLEEP_TIME = 1
    print("Connecting to libvirt", flush=True)
    conn = get_connection()

    print("Start daemon", flush=True)
    domainNames = []

    for i in conn.listAllDomains():
        domainNames.append(i.name())

    print("Found domains:", domainNames, flush=True)

    while True:
        domainIDs = conn.listDomainsID()
        if domainIDs is None:
            print('No active domains', file=sys.stderr, flush=True)
            if SLEEP_TIME < 10:
                SLEEP_TIME += 1
        else:
            if SLEEP_TIME > 1:
                SLEEP_TIME -= 1
            for domainID in domainIDs:
                dom = conn.lookupByID(domainID)
                process_domainID(dom)
        sleep(SLEEP_TIME)


def status():
    print("Connecting to libvirt", flush=True)
    conn = get_connection()
    domainIDs = conn.listDomainsID()
    if domainIDs is None:
        print('No active domains', file=sys.stderr, flush=True)
        return

    print("Name", "Total", "Active", "Used", "Usable", "Thrshld", "Units", "Ratio", sep='\t', flush=True)
    for domainID in domainIDs:
        dom = conn.lookupByID(domainID)
        memstat = dom.memoryStats()
        Name = dom.name()
        actual = memstat["actual"]
        available = memstat["available"]
        usable = memstat["usable"]
        used = actual - usable
        keep_avail_threshold = available*THRESHOLD_RATIO
        ratio_current = usable/keep_avail_threshold
        print(Name,
              int(available/SZ_1MiB),
              int(actual/SZ_1MiB),
              int(used/SZ_1MiB),
              int(usable/SZ_1MiB),
              int(keep_avail_threshold/SZ_1MiB),
              "MiB",
              format(ratio_current, '2.2'), sep='\t', flush=True)


def main():
    print("Start libvirt-autoballoon, argv:", sys.argv, flush=True)
    if sys.argv[1] == "start":
        daemon()
    if sys.argv[1] == "status":
        status()


main()
