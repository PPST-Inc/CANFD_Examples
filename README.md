# Python CAN Test Program

This Python CAN test program is designed to facilitate testing and validation of a CAN USB interface. It allows for sending and validating messages defined in a provided CAN-DB database. The program offers features for calculating and displaying message transmission times and delays, as well as saving all relevant data to a log file.

### Requirements
To run the Python CAN test program, you'll need the following:

- Python 3.x
- Install cantools 38.0.2 ( `pip install cantools==38.0.2` )
- A CAN-DB database file
- CAN USB interface and necessary drivers

### Steps to run CAN Test Program
1. Install Python for Windows. Make sure to check "Add python.exe to PATH"
   ![imagen](https://github.com/PPST-Inc/CANFD_Examples/assets/20909874/947cdb7b-8d3c-4bd8-a477-be91968bdd63)

2. Open a Windows Console and run the command:\
`pip install cantools==38.0.2`
3. Connect one of the USB/CAN adapters to the unit and the other to the PC
4. Interconnect both CAN adapters with a CAN BUS cable.
5. Load to the unit the file "01_FullTestCAN.dbc", located in the example folder.\
   Open the Web interface, go to **SYSTEM -> INTERFACE SETUP -> CANFD CONFIGURATION -> DBC FILE** and click on **UPLOAD**
7. Set the **NODE NAME** to **PPS_First_1**
8. Enable the CANFD interface by clicking on the swith
9. Open a Windows Console in the example folder and run the example executing: `python.exe .\01_FullTestCAN.py`
