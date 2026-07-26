#!/bin/bash
set -ex
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo apt-get install ./cuda-keyring_1.1-1_all.deb
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y gcc g++ make cmake
sudo apt-get install -y cuda-drivers
sudo apt-get install -y cuda-toolkit

echo 'export PATH=/usr/local/cuda/bin:$PATH' >> /home/ubuntu/.bashrc