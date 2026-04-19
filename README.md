# N X H  The Desktop Hud

![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square) ![Status](https://img.shields.io/badge/status-active-brightgreen?style=flat-square) ![Hardware](https://img.shields.io/badge/hardware-Raspberry%20Pi%20Pico-red?style=flat-square&logo=raspberrypi&logoColor=white) ![PCB](https://img.shields.io/badge/PCB-KiCad-314CB0?style=flat-square) ![Display](https://img.shields.io/badge/display-ST7789V-purple?style=flat-square) 

> A desktop device that sit on ur desktop and shows u how ur PC going, it will snow RAM,ROM,FPS,TIME etc.

![banner](assets/banner.png)

---

## What is it?

N X H is a compact HUD built around the Raspberry Pi Pico, it features a 2.4" ST7789V TFT display, USB-C and a custom PCB with on-board decapping and Rust circuitry it reads data from your system In real time Via a companion app.

## Why I built it

My system is not that awesome. Whenever I try to open something that pushes my system to the edges. In that time, I won't to be able to see my task manager, to check the status of RAM, ROM, CPU, GPU. So I made this device that will show me everything live. With near zero latency and whenever my PC gets to the edge, I will be able to see my system status. I got the opportunity to build this from Hack Club. Shout out to them!

---

## Demo

<p align="center">
  <img src="assets/3d-render.png" alt="No need to add something here. I have already named all the assets." width="48%"/>
  <img src="assets/pcb-top.png" alt="No need to add something here. I have already named all the assets." width="48%"/>
</p>

<p align="center">
  <img src="assets/schematic.png" alt="No need to add something here. I have already named all the assets." width="60%"/>
  <img src="assets/wiring.png" alt="Wiring diagram" width="36%"/>
</p>

---

## Features

- Raspberry Pi Pico as a main MCU.
- 2.4 inches ST7789V TFT display in 240x320 SPI.
- USB-C Connectivity
- Custom PCB designed in KiCad.
- C++ firmware
- Companion desktop apps, light weight
- Reset button for force reset.
- Onboard Decapping Capacitors

---

## Hardware

| Component | Qty | Purpose |
|---|---|---|
| i have made it but i will upload it manually, just tell me how to upload it. | — | — |

> Full BOM with links and prices: [`bom.csv`](bom.csv)

---

## How to use

### Flash the firmware

1. Hold  boostsel on Pico and plug in USB-C.
2. It mounts as a USB driver.
3. Copy firmware/main.py to drive.
4. The Pico reboots and runs automatically.


### Run the app

1. Open the file main.py in your command prompt.
2. run this command (pyhton main.py)


---

## Repo structure

```
n/
├── README.md
├── bom.csv
├── I have structured files already, good and structured, organized in my system. I will just upload, so I don't think there is a need.
```

---

## Zine page

[View zine page (PDF)](Design page is also ready. I will upload it manually. Just tell me how to upload it.)

---

## Credits

- I have used KiCad for PCB designing and schematic. I have used FreeCAD for designing 3D enclosure, and Hack Club is going to fund this using grant programs. In Framework, I use C++.


Made with love for [Hack Club Fallout](https://fallout.hackclub.com) by **Nabeel (broccoli 🥦)   X  Hashir**.

---

## License

This project is licensed under the [MIT License](LICENSE).

