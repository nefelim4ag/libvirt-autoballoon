#!/usr/bin/env python3

from time import sleep
import libvirt
import sys

SZ_1KiB = 1
SZ_4KiB = 4
SZ_1MiB = 1024
SZ_4MiB = 4096
SZ_32MiB = 32768

THRESHOLD_RATIO = 0.125


def ALIGN_DOWN(x, a):
    x = int(x)
    a = int(a)
    return x & ~ (a-1)


def get_connection():
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to the hypervisor', flush=True)
        sys.exit(1)
    return conn


def dom_ram_total(dom):
    info = dom.info()
    total_ram = info[1]
    return total_ram


def dom_ram_used(dom):
    memstat = dom.memoryStats()
    return memstat["actual"] - memstat["usable"]


def dom_ram_actual(dom):
    memstat = dom.memoryStats()
    return memstat["actual"]


def dom_balloon(dom, restrict_to):
    name = dom.name()
    actual = dom_ram_actual(dom)
    restrict_to = int(restrict_to)
    actual_m = int(actual / SZ_1MiB)
    restrict_to_m = int(restrict_to / SZ_1MiB)
    diff = abs(actual_m - restrict_to_m)
    if actual > restrict_to:
        print("Shrink dom:",
              name,
              actual_m, "-", diff, "=", restrict_to_m, "MiB", flush=True)
    else:
        print("Grow dom:",
              name,
              actual_m, "+", diff, "=", restrict_to_m, "MiB", flush=True)
    dom.setMemory(restrict_to)


def dom_keep_usable(dom):
    total_ram = dom_ram_total(dom)
    return total_ram*THRESHOLD_RATIO


def dom_usable_ratio(dom):
    memstat = dom.memoryStats()
    usable = memstat["usable"]
    return usable/dom_keep_usable(dom)


def process_domainID(dom):
    total_ram = dom_ram_total(dom)
    actual = dom_ram_actual(dom)
    keep_usable = dom_keep_usable(dom)
    used = dom_ram_used(dom)

    diff = used*THRESHOLD_RATIO
    diff = ALIGN_DOWN(diff, SZ_32MiB)
    if diff == 0:
        diff = SZ_1MiB

    ratio_current = dom_usable_ratio(dom)
    if ratio_current < 1.0 and actual < total_ram:
        dom_balloon(dom, actual + diff)
    elif ratio_current > 1.5 and actual > keep_usable:
        dom_balloon(dom, actual - diff)


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


def dom_status(dom):
    memstat = dom.memoryStats()
    total_ram = dom_ram_total(dom)
    Name = dom.name()
    actual = memstat["actual"]
    usable = memstat["usable"]
    used = dom_ram_used(dom)
    keep_usable = dom_keep_usable(dom)
    ratio_current = dom_usable_ratio(dom)
    print(Name,
          int(total_ram/SZ_1MiB),
          int(actual/SZ_1MiB),
          int(used/SZ_1MiB),
          int(usable/SZ_1MiB),
          int(keep_usable/SZ_1MiB),
          "MiB",
          format(ratio_current, '2.3'), sep='\t', flush=True)


def status():
    print("Connecting to libvirt", flush=True)
    conn = get_connection()
    domainIDs = conn.listDomainsID()
    if domainIDs is None:
        print('No active domains', file=sys.stderr, flush=True)
        return

    print("Name", "Total", "Actual", "Used", "Usable", "Thrshld", "Units", "Ratio", sep='\t', flush=True)
    for domainID in domainIDs:
        dom = conn.lookupByID(domainID)
        dom_status(dom)


def main():
    if sys.argv[1] == "start":
        daemon()
    if sys.argv[1] == "status":
        status()


main()
