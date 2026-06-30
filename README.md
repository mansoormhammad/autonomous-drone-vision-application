# Public Repository Notice

This repository contains the public-facing components of a larger research and development project. It focuses on the user interface, visualization pipeline, operator interaction, and selected perception modules.

Some core components—including autonomous decision-making, navigation, hardware integration, communication interfaces, and other research-specific implementations—are intentionally not included. These modules remain private due to ongoing development, research considerations, and project scope.

The purpose of this repository is to demonstrate the overall software architecture, engineering approach, and implementation of key real-time computer vision and interface components while preserving the integrity of the complete research system.



# Autonomous Drone Vision Application

A modular real-time aerial perception and control interface for drone systems combining computer vision, operator interaction, telemetry visualization, and safety-aware scene monitoring.

---

## Abstract

This project explores a modular architecture for real-time drone perception and control interfaces.  
It focuses on separating **control input**, **scene understanding**, and **visualization layers** to ensure scalability and research flexibility.

The system is designed for experimentation in:
- Real-time computer vision
- Human–machine interaction
- Aerial telemetry visualization
- Automated scene awareness

---

## System Modules (Public Scope)

### Control Layer
- Keyboard-based flight input handling

### Perception Layer
- Scene analysis and object classification
- Threat level estimation and alert generation

### Visualization Layer
- HUD overlay rendering
- Video stream visualization
- Telemetry + horizon display interface

---


## Demo

### Main Interface

![Interface](screenshots/interface.png)

### HUD Overlay

![HUD](screenshots/hud.png)

### Telemetry

![Telemetry](screenshots/telemetry.png)


## Features

- Real-time video visualization
- Telemetry monitoring
- Keyboard flight control
- HUD rendering
- Scene alert monitoring
- Modular UI architecture



## System Architecture
!(architecture/system_overview.md)