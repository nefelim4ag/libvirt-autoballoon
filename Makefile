PREFIX ?= /

SRC_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

S_SERVICE := $(SRC_DIR)/libvirt-autoballoon.service
S_BIN := $(SRC_DIR)/libvirt-autoballoon.py
S_CONF := $(SRC_DIR)/autoballoon.json

SERVICE := $(PREFIX)/lib/systemd/system/libvirt-autoballoon.service
BIN := $(PREFIX)/usr/bin/libvirt-autoballoon
CONF := $(PREFIX)/etc/libvirt/autoballoon.json

default:  help

$(BIN): $(S_BIN)
	install -Dm755 $< $@

$(SERVICE): $(S_SERVICE)
	install -Dm644 $< $@

$(CONF): $(S_CONF)
	install -Dm644 $< $@

install: ## Install libvirt-autoballoon
install: $(BIN) $(SERVICE) $(CONF)

uninstall: ## Delete libvirt-autoballoon
uninstall:
	@rm -fv $(BIN) $(SERVICE) $(CONF)

help: ## Show help
	@grep -h "##" $(MAKEFILE_LIST) | grep -v grep | sed -e 's/\\$$//' | column -t -s '##'
