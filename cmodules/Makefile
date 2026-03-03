# VoidEye · cmodules/Makefile
CC      = gcc
CFLAGS  = -O2 -shared -fPIC -Wall -Wextra

all: bannergrab.so fastscan.so

bannergrab.so: bannergrab.c
	$(CC) $(CFLAGS) -o $@ $<
	@echo "[✓] bannergrab.so built"

fastscan.so: fastscan.c
	$(CC) $(CFLAGS) -o $@ $<
	@echo "[✓] fastscan.so built"

clean:
	rm -f *.so

.PHONY: all clean
