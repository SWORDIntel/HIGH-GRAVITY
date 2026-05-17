CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O3 -mavx2 -msse4.2
CPPFLAGS ?= -D_GNU_SOURCE

BIN_DIR := build
BIN := $(BIN_DIR)/hg-edge
SRC := hg_edge.c

.PHONY: all clean check

all: $(BIN)

$(BIN): $(SRC) | $(BIN_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $<

$(BIN_DIR):
	mkdir -p $@

check: $(BIN)
	./$(BIN) --check-config --listen 127.0.0.1:18080 --upstream 127.0.0.1:8000

clean:
	rm -rf $(BIN_DIR)
