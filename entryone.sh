#!/bin/bash

# Function to install required packages
install_packages() {
    sudo apt-get update
    sudo apt-get install -y curl jq
    if ! command -v pip &> /dev/null; then
        sudo apt-get install -y python3-pip
    fi
    if ! command -v Xvfb &> /dev/null; then
        sudo apt-get install -y xvfb
    fi
}

# Function to install Python dependencies from requirements.txt
install_python_dependencies() {
    if [ -f "requirements.txt" ]; then
        if command -v pip &> /dev/null; then
            pip install -r requirements.txt
        elif command -v pip3 &> /dev/null; then
            pip3 install -r requirements.txt
        else
            echo "pip is not installed. Please install pip or pip3."
            exit 1
        fi
    else
        echo "requirements.txt not found. Skipping Python dependencies installation."
    fi
}

# Function to kill all related processes
kill_related_processes() {
    pkill -f "python main.py"
    pkill -f chrome
    pkill -f undetected_chromedriver
}

# Function to display IP and system information
display_ip_info() {
    IP_INFO=$(curl -s ipinfo.io)
    IP=$(echo $IP_INFO | jq -r '.ip')
    ISP=$(echo $IP_INFO | jq -r '.org')
    COUNTRY=$(echo $IP_INFO | jq -r '.country')
    REGION=$(echo $IP_INFO | jq -r '.region')
    CITY=$(echo $IP_INFO | jq -r '.city')
    HOSTNAME=$(hostname)

    echo "Hostname: $HOSTNAME"
    echo "IP Address: $IP"
    echo "ISP: $ISP"
    echo "Country: $COUNTRY"
    echo "Region: $REGION"
    echo "City: $CITY"
}

# Install required packages
install_packages

# Install Python dependencies
install_python_dependencies

# Remove temp file when previous execution crashed
rm -f /tmp/.X99-lock

# Set display port and dbus env to avoid hanging (https://github.com/joyzoursky/docker-python-chromedriver)
export DISPLAY=:99
export DBUS_SESSION_BUS_ADDRESS=/dev/null

# Display IP and system information
display_ip_info

# Start virtual display
Xvfb $DISPLAY -screen 0 1280x800x16 -nolisten tcp &

# Wait for 10 seconds
sleep 10

# Kill all related processes again
kill_related_processes

python main.py

# Kill all related processes again
kill_related_processes
