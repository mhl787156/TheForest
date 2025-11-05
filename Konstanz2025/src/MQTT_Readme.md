#Installing Mosquitto Broker on Raspberry Pi OS

1) Open a new Raspberry Pi terminal window
2) Run the following command to upgrade and update your system:
```bash
sudo apt update && sudo apt upgrade
```
3) To install the Mosquitto Broker, enter these next commands:
```bash
sudo apt install -y mosquitto mosquitto-clients
```
5) To make Mosquitto auto-start when the Raspberry Pi boots, you need to run the following command (this means that the Mosquitto broker will automatically start when the Raspberry Pi starts):
```bash
sudo systemctl enable mosquitto.service
```
6) 6) Now, test the installation by running the following command:
```bash
mosquitto -v
```
This returns the Mosquitto version that is currently running on your Raspberry Pi. It will be 2.0.11 or above.
It will prompt the following message: 
```
Starting in local only mode. Connections will only be possible from clients running on this machine. Create a configuration file that defines a listener to allow remote access.
```
This means that by default, you can’t communicate with the Mosquitto broker from another device (other than your Raspberry Pi). This applies to Mosquitto version 2. 
In Mosquitto 2.0 and later, you must explicitly choose your authentication options before clients can connect. In earlier versions, the default is to allow clients to connect without authentication.

#Enable Remote Access/ Authentication
##Mosquitto Broker Enable Remote Access (No Authentication)
1) Run the following command to open the mosquitto.conf file.
```bash
sudo nano /etc/mosquitto/mosquitto.conf
```
2) Move to the end of the file using the arrow keys and paste the following two lines:
```bash
listener 1883
allow_anonymous true
```
3) Then, press CTRL-X to exit and save the file. Press Y and Enter.
4) Restart Mosquitto for the changes to take effect.
```bash
sudo systemctl restart mosquitto
```
#Raspberry Pi IP Address
To use Mosquitto broker later in your projects, you’ll need to know the Raspberry Pi IP address. To retrieve your Raspberry Pi IP address, type the next command in your Pi Terminal window:
```bash
hostname -I
```
#Testing Mosquitto Broker and MQTT Client
##Subscribing to testTopic Topic
To subscribe to an MQTT topic with Mosquitto Client, open a terminal in Raspi #1 and enter the command:
```bash
mosquitto_sub -h [HOST/BROKER IP] -d -t testTopic
```
##Publishing “Hello World!” Message to testTopic Topic
To publish a sample message to testTopic, open a terminal Window #2 and run the following command:
```bash
mosquitto_pub -h [HOST/BROKER IP] -d -t testTopic -m "Hello world!"
```
