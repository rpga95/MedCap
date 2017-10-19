This directory contains three files:

- REST_server.py
- Requirements.txt
- mimic.csv

These files are necessary to run the MedCap REST API service and host a backend application to support the front-end mobile application developed by another member of the MedCap team.

This project was a senior design project for team MedCap at Georgia Tech's School of Electrical and Computer Engineering. The goal of the project was to leverage embedded systems and a processing framework to determine of wearers of the MedCap baseball cap were experiencing levels of heat stress that could lead to heat stroke (commonly known as early heat illness). This server is responsible for:

- Serving custom REST API handles for the mobile application to send and retrieve unprocessed and processed data, respectively.
- Serving as an authentication handshaking method.
- Implementing the necessary infrastructure to support MedCap (DynamoDB, SQS, EC2 Compute, etc.).
- Performing machine learning training and processing based on live data from users of MedCap.
- Serving as the computational backbone of MedCap when user data was sent to be processed.
