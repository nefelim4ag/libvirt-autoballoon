#!/usr/bin/env python3

import sys
import json
import libvirt

from time import sleep


SZ_1KiB = 1
SZ_4KiB = 4
SZ_1MiB = 1024
SZ_4MiB = 4096
SZ_32MiB = 32768

THRESHOLD_RATIO = 0.25


class ExitFailure(Exception):
    pass


class LibVirtAutoBalloon:
    sleep_time = 1
    conn = None
    config = None
    allowed_vms = []
    configfile = "/etc/libvirt/autoballoon.json"

    def __init__(self, qemu_addr='qemu:///system'):
        print("Connecting to libvirt", flush=True)
        self.conn = libvirt.open(qemu_addr)
        if self.conn is None:
            raise ExitFailure('Failed to open connection to the hypervisor')
        self.__load_config()

    def __load_config(self):
        print("Load config file: {}".format(self.configfile))
        content = open(self.configfile).read(-1)
        self.config = json.loads(content, parse_int=int)
        for i in self.config["vms"]:
            if i["balloon"] is True:
                self.allowed_vms += [i["name"]]

    def dom_status(self, dom):
        memstat = dom.memoryStats()
        total_ram = dom_ram_total(dom)
        Name = dom.name()
        actual = memstat.get("actual", 0)
        usable = memstat.get("usable", 0)
        used = dom_ram_used(dom)
        keep_usable = self.dom_keep_usable(dom)
        ratio_current = self.dom_usable_ratio(dom)
        print(Name,
              int(total_ram / SZ_1MiB),
              int(actual / SZ_1MiB),
              int(used / SZ_1MiB),
              int(usable / SZ_1MiB),
              int(keep_usable / SZ_1MiB),
              "MiB",
              format(ratio_current, '2.3'), sep='\t', flush=True)

    def status(self):
        domainIDs = self.conn.listDomainsID()
        if domainIDs is None:
            raise ExitFailure('No active domains')
        print("Name", "Total", "Actual", "Used", "Usable", "Thrshld", "Units", "Ratio", sep='\t', flush=True)
        for domainID in domainIDs:
            dom = self.conn.lookupByID(domainID)
            self.dom_status(dom)

    def process_domainID(self, dom):
        if dom.name() not in self.allowed_vms:
            return
        total_ram = dom_ram_total(dom)
        actual = dom_ram_actual(dom)
        keep_usable = self.dom_keep_usable(dom)
        used = dom_ram_used(dom)

        if actual != used:
            diff = used * THRESHOLD_RATIO
            diff = ALIGN_DOWN(diff, SZ_32MiB)
            if diff == 0:
                diff = SZ_1MiB

            ratio_current = self.dom_usable_ratio(dom)
            if ratio_current < 1.0 and actual < total_ram:
                dom_balloon(dom, actual + diff)
            elif ratio_current > 1.5 and actual > keep_usable:
                dom_balloon(dom, actual - diff)

    def dom_print_names(self):
        domainNames = []
        for i in self.conn.listAllDomains():
            domainNames += [i.name()]
        print("Found domains:", domainNames, flush=True)
        for i in domainNames:
            if i not in self.allowed_vms:
                print("{} not in autoballoon.json, ignored".format(i), flush=True)

    def dom_keep_usable(self, dom):
        name = dom.name()
        total_ram = dom_ram_total(dom)
        keep_usable = total_ram * THRESHOLD_RATIO
        for vm in self.config["vms"]:
            if vm.get("name") == name:
                if vm.get("keep_free_kb"):
                    keep_usable = int(vm.get("keep_free_kb"))

        if keep_usable > total_ram:
            keep_usable = total_ram

        return keep_usable

    def dom_usable_ratio(self, dom):
        usable = dom.memoryStats().get("usable", 0)
        return usable / self.dom_keep_usable(dom)

    def daemon(self):
        self.sleep_time = 1
        print("Start daemon", flush=True)

        domain_count = -1
        while True:
            domainIDs = self.conn.listDomainsID()

            if domainIDs is None:
                print('No active domains', file=sys.stderr, flush=True)
                if self.sleep_time < 10:
                    self.sleep_time += 1
            else:
                if domain_count != len(domainIDs):
                    domain_count = len(domainIDs)
                    self.dom_print_names()

                if self.sleep_time > 1:
                    self.sleep_time -= 1

                for domainID in domainIDs:
                    dom = self.conn.lookupByID(domainID)
                    self.process_domainID(dom)

            sleep(self.sleep_time)


def ALIGN_DOWN(x, a):
    x = int(x)
    a = int(a)
    return x & ~ (a - 1)


def dom_ram_total(dom):
    info = dom.info()
    total_ram = info[1]
    return total_ram


def dom_ram_used(dom):
    memstat = dom.memoryStats()
    return memstat.get("actual", 0) - memstat.get("usable", 0)


def dom_ram_actual(dom):
    memstat = dom.memoryStats()
    return memstat.get("actual", 0)


def dom_balloon(dom, restrict_to):
    name = dom.name()
    actual = dom_ram_actual(dom)
    restrict_to = int(restrict_to)
    total_ram = dom_ram_total(dom)

    if restrict_to > total_ram:
        restrict_to = total_ram

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


def help():
    print("Usage: libvirt-autoballoon <arg>", flush=True)
    print("    start  - start daemon", flush=True)
    print("    status - show what daemon see", flush=True)
    exit(0)


def libvirt_autoballoon(argv):
    if len(argv) < 2:
        help()

    lv_ctrl = LibVirtAutoBalloon()

    if argv[1] == "start":
        lv_ctrl.daemon()
    elif argv[1] == "status":
        lv_ctrl.status()
    else:
        help()


def main(argv):
    libvirt_autoballoon(argv)


if __name__ == '__main__':
    main(sys.argv)
