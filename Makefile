PREFIX ?= /

SRC_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

S_SERVICE := $(SRC_DIR)/libvirt-autoballoon.service
S_BIN := $(SRC_DIR)/libvirt-autoballoon.py

SERVICE := $(PREFIX)/lib/systemd/system/libvirt-autoballoon.service
BIN := $(PREFIX)/usr/bin/libvirt-autoballoon

default:  help

$(BIN): $(S_BIN)
	install -Dm755 $< $@

$(SERVICE): $(S_SERVICE)
	install -Dm644 $< $@


install: ## Install libvirt-autoballoon
install: $(BIN) $(SERVICE)

uninstall: ## Delete libvirt-autoballoon
uninstall:
	@rm -fv $(BIN) $(SERVICE)

help: ## Show help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/\t/'
