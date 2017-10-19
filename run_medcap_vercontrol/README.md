This directory contains many subdirectories. They are organized by version number, with the highest version number being the latest version.

These files are necessary to run the MedCap embedded system running on the bill of the MedCap baseball cap.

The most crucial file is run_medcap.ino. This file is responsible for running the entire framework of processing and data collection and transportation on MedCap.

This project was a senior design project for team MedCap at Georgia Tech's School of Electrical and Computer Engineering. The goal of the project was to leverage embedded systems and a processing framework to determine of wearers of the MedCap baseball cap were experiencing levels of heat stress that could lead to heat stroke (commonly known as early heat illness). This run_medcap.ino file is responsible for:

- Gathering data from the temperature and pulse oximeter sensors on MedCap to determine temperature and blood oxygen content, respectively.
- Performing post-processing of raw PPG data to convert a waveform into peaks and troughs.
- Sending and receiving data from the mobile application via Bluetooth.
