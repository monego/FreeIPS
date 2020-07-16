#!/usr/bin/env python3

# Name: FreeIPS.py
# Copyright (c) 2012 Boris Timofeev <mashin87@gmail.com> www.emunix.org
# Copyright (c) 2020 Vinicius Monego <monego@posteo.net>
# License: GNU GPL v3

import argparse
import os
import sys


parser = argparse.ArgumentParser()
mutual = parser.add_mutually_exclusive_group(required=False)

mutual.add_argument('-c', '--check', action='store_true',
                    help="Check whether ROM contains a SMC header")
mutual.add_argument('-a', '--add', action='store_true', help="Add SMC header")
mutual.add_argument('-r', '--remove', action='store_true',
                    help="Remove SMC header")
parser.add_argument('-f', '--rom', type=str, nargs=1,
                    help="ROM file (.s(f|m)c)", required=True)
parser.add_argument('-p', '--patch', nargs='+',
                    help="Patch(es) to apply (.ips)")

args = parser.parse_args()


class Patch:

    def __init__(self, rom_file):
        self.rom_file = rom_file
        self.rom_name = rom_file.split('/')[-1]
        try:
            self.rom = open(self.rom_file, "rb+")
        except IOError:
            print("File %s not found!".format(rom_file))
            sys.exit(0)
        self.headered = self._is_headered()
        self.rom.seek(0)
        if self.headered is None:
            print("Something's wrong with the memory map of ROM '{}'! Skipping..".format(
                self.rom_name))
            sys.exit(0)

    def __del__(self):
        self.rom.close()

    def _is_headered(self):
        """Checks for the existence of a header"""
        data = self.rom.read()
        if len(data) % 1024 == 512:
            return True
        elif len(data) % 1024 == 0:
            return False
        return

    def add_header(self):
        if not self.headered:
            print("Adding header to ROM '{}'".format(self.rom_name), end="")
            headered_rom = open("[Headered] " + self.rom_name, "wb+")
            length = len(self.rom.read())
            self.rom.seek(0)
            bit0 = bytes([length//8192 & 0xFF])
            bit1 = bytes([length//8192 >> 8])
            bit2 = bytes(0x00)
            rest = bytes([0] * 510)
            headered_rom.write(bit0)
            headered_rom.write(bit1)
            headered_rom.write(bit2)
            headered_rom.write(rest)
            headered_rom.write(self.rom.read())
            print(" ... DONE!")
            self.rom = headered_rom
        else:
            print("ROM '{}' is already headered! Skipping..".format(self.rom_name))

    def remove_header(self):
        if self.headered:
            print("Removing header of ROM '{}'".format(self.rom_name), end="")
            unheadered_rom = open("[Unheadered] " + self.rom_name, "wb+")
            self.rom.seek(512)
            unheadered_rom.write(self.rom.read())
            print(" ... DONE!")
            self.rom = unheadered_rom
        else:
            print("ROM '{}' doesn't have a header already! Skipping..".format(
                self.rom_name), end="")

    def check_header(self):
        if self.headered:
            print("ROM '{}' *is* headered.".format(self.rom_name))
        elif not self.headered:
            print("ROM '{}' *is not* headered".format(self.rom_name))
        else:
            print("Something's wrong with ROM '{}'!".format(self.rom_name))

    def apply_patches(self, patches):
        patched_rom = open("[Patched] " + self.rom_name, "wb+")
        self.rom.seek(0)
        patched_rom.write(self.rom.read())
        patched_rom.seek(0)
        for ips in patches:
            ipsfile = ips
            try:
                patch = open(ipsfile, "rb+")
            except IOError:
                print("File %s not found!".format(ipsfile))
                break
            data = "".join(map(chr, patch.read(5)))
            if data != "PATCH":
                print("IPS file is unknown format.")
                patched_rom.close()
                patch.close()
                break
            patchsize = os.path.getsize(ipsfile)
            print("{} patchsize: {}".format(ipsfile, patchsize))
            while 1:
                data = "".join(map(chr, patch.read(3)))
                if data == "" or data == "EOF":
                    patch.close()
                    break
                try:
                    address = ord(data[0:1])*256*256 + \
                        ord(data[1:2])*256 + ord(data[2:3])
                except:
                    print("Address error")
                    patch.close()
                    break
                try:
                    patched_rom.seek(address)
                except:
                    patched_rom.seek(0, 2)
                data = "".join(map(chr, patch.read(2)))
                try:
                    length = ord(data[0:1])*256 + ord(data[1:2])
                except:
                    print("Length error")
                    patched_rom.close()
                    patch.close()
                    break
                if length:
                    data = patch.read(length)
                    patched_rom.write(data)
                else:  # RLE
                    data = "".join(map(chr, patch.read(2)))
                    try:
                        length = ord(data[0:1]) * 256 + ord(data[1:2])
                    except:
                        print("Length error 2")
                        patched_rom.close()
                        patch.close()
                        break
                    byte = patch.read(1)
                    patched_rom.write(byte * length)

        patch.close()
        patched_rom.close()
        print("All patches were applied succesfully!")


if __name__ == "__main__":
    patch = Patch(args.rom[0])
    if args.check:
        patch.check_header()
    elif args.add:
        patch.add_header()
    elif args.remove:
        patch.remove_header()
    else:
        print("Wrong arguments!")
    if args.patch:
        patch.apply_patches(args.patch)
