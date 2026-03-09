#!/bin/bash

RED='\e[31m'
BLUE='\e[34m'
NC='\e[0m'

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

if ! command_exists "mdl"; then
    echo "${RED}Please install mdl:${NC}"
    echo "sudo apt install ruby-mdl"
    exit 1
fi

if ! command_exists "xz"; then
    echo "${RED}Please install xz:${NC}"
    echo "sudo apt install xz-utils"
    exit 1
fi

if ! command_exists "qemu-system-riscv64"; then
    echo "${RED}Please install qemu-system-riscv64:${NC}"
    echo "sudo apt install qemu-system-riscv64"
    exit 1
fi

if [ ! -f "/usr/lib/u-boot/qemu-riscv64_smode/uboot.elf" ]; then
    echo "${RED}Please install u-boot-qemu:${NC}"
    echo "sudo apt install u-boot-qemu"
    exit 1
fi

if ! command_exists "sshpass"; then
    echo "${RED}Please install sshpass:${NC}"
    echo "sudo apt install sshpass"
    exit 1
fi

if ! command_exists "uv"; then
    if command_exists "curl"; then
        echo -e "${BLUE}Installing uv with curl...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif  command_exists "wget"; then
        echo -e "${BLUE}Installing uv with wget...${NC}"
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
         echo "Please install curl for check CI:"
         echo "sudo apt install curl"
         exit 1
    fi

fi

if ! command_exists "uv"; then
    echo -e "${RED}Error: UV installation failed - command 'uv' not found${NC}"
    exit 1
fi

uv sync
