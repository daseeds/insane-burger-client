# python 3.11

import subprocess
import yaml
import time
from paho.mqtt import client as mqtt_client
import paho.mqtt.publish as publish
import logging
import sys
import json
import threading
from time import sleep
import io


class MQTTHandler(logging.Handler):
    """
    A handler class which writes logging records, appropriately formatted,
    to a MQTT server to a topic.
    """
    def __init__(self, hostname, topic, qos=0, retain=False,
            port=1883, client_id='', keepalive=60, will=None, auth=None,
            tls=None, protocol=mqtt_client.MQTTv31, transport='tcp'):
        logging.Handler.__init__(self)
        self.topic = topic
        self.qos = qos
        self.retain = retain
        self.hostname = hostname
        self.port = port
        self.client_id = client_id
        self.keepalive = keepalive
        self.will = will
        self.auth = auth
        self.tls = tls
        self.protocol = protocol
        self.transport = transport

    def emit(self, record):
        """
        Publish a single formatted logging record to a broker, then disconnect
        cleanly.
        """
        msg = self.format(record)
        publish.single(self.topic, msg, self.qos, self.retain,
            hostname=self.hostname, port=self.port,
            client_id=self.client_id, keepalive=self.keepalive,
            will=self.will, auth=self.auth, tls=self.tls,
            protocol=self.protocol, transport=self.transport)

with open('settings.yml', 'r') as file:
    settings = yaml.safe_load(file)

logging.basicConfig(format='%(asctime)s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
auth = {}
auth["username"] = settings['mqtt']['username']
auth["password"] = settings['mqtt']['password']
tls = {}
tls["ca_certs"] = None
tls["insecure"] = True

myHandler = MQTTHandler(hostname=settings['mqtt']['broker'],
                        topic=settings['mqtt']['logs'], 
                        port=settings['mqtt']['port'],
                        auth=auth, tls=tls)
myHandler.setLevel(logging.INFO)
myHandler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
logger.addHandler(myHandler)

logger.info("Start Application")




  

gpio_enabled = False

switch1_state = "off"


def is_raspberrypi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False

try:
    import RPi.GPIO as GPIO
    gpio_enabled = True
except RuntimeError:
    print("Error importing RPi.GPIO!  This is probably because you need superuser privileges.  You can achieve this by using 'sudo' to run your script")

if is_raspberrypi:
    try:
        import adafruit_dht
        import board
        dht_enabled = True
        dht_device = adafruit_dht.DHT22(board.D17)
    except RuntimeError:
        print("Error importing adafruit_dht! ")


def publish_descriptors(client):
    for metric in settings['device']['metrics']:
        logging.info("Publish " + metric['unique_id'])
        message = {}
        avail = {}
        avail['topic'] = settings['device']['availability']
        message['availability'] = []
        message['availability'].append(avail)
        message['device'] = {}
        message['device']['identifiers'] = []
        message['device']['identifiers'].append(settings['device']['identifier'])
        message['device']['manufacturer'] = settings['device']['manufacturer']
        message['device']['model'] = settings['device']['model']
        message['device']['name'] = settings['device']['name']
        message['device']['sw_version'] = settings['device']['sw_version']
        message['device_class'] = metric['device_class']
        message['json_attribute_topic'] = metric['json_attribute_topic']
        message['name'] = metric['name']
        message['state_topic'] = metric['state_topic']
        message['unique_id'] = metric['unique_id']
        message['value_template'] = metric['value_template']
        if "command_topic" in metric:
            message['command_topic'] = metric['command_topic']
        if "payload_off" in metric:
            message['payload_off'] = metric['payload_off']
        if "payload_on" in metric:
            message['payload_on'] = metric['payload_on']
        if "unit_of_measurement" in metric:
            message['unit_of_measurement'] = metric['unit_of_measurement']
        if "retain" in metric:
            message['retain'] = metric['retain']
        advertise_topic = "homeassistant/"+metric['advertise']+"/"+settings['device']['identifier']+"/"+metric['device_class']+"/config"
        logging.info("On " + advertise_topic)
        result = client.publish(advertise_topic, json.dumps(message), qos=2, retain=True)


def start_secondary(stop_event, client):
  global dht_enabled
  logging.info("thread start")
  last_temp = dht_device.temperature
  last_humid = dht_device.humidity
  topic = settings['device']['metrics'][1]['state_topic']
  message = {}
  message['temperature'] = str(last_temp)
  message['humidity'] = str(last_humid)
  client.publish(topic, json.dumps(message), qos=0, retain=True)

  while not stop_event.is_set():
    logging.debug("thread loop")
    if dht_enabled:
        try:
            message.clear()
            temperature_c = dht_device.temperature
            humidity = dht_device.humidity
            logging.debug("temp="+str(temperature_c)+"hum="+str(humidity))

            if temperature_c != last_temp:
                message['temperature'] = str(temperature_c)
                last_temp = temperature_c
            if humidity != last_humid:
                message['humidity'] = str(humidity)
                last_humid = humidity

            if len(message.keys()) > 0:
                logging.debug("Publish on " + topic)
                client.publish(topic, json.dumps(message), qos=0, retain=True)

        except Exception: pass
    sleep(60.0)

def switch_on(client):
    global switch1_state
    logging.info("Switch on")
    if gpio_enabled:
        GPIO.output(4, GPIO.HIGH)    
    switch1_state = "on"
    publish_state(client)

def switch_off(client):
    global switch1_state
    logging.info("Switch off")
    if gpio_enabled:
        GPIO.output(4, GPIO.LOW)
    switch1_state = "off"
    publish_state(client)

def publish_state(client):
    global switch1_state
    topic = settings['device']['metrics'][0]['state_topic']
    logging.info("Publish " + switch1_state + " on " + topic)
    client.publish(topic, switch1_state, qos=2, retain=True)

def on_log(client, userdata, paho_log_level, messages):
    if paho_log_level == mqtt_client.LogLevel.MQTT_LOG_ERR:
        logging.info(messages)

def on_subscribe(client, userdata, mid, reason_code_list, properties):
    # Since we subscribed only for a single channel, reason_code_list contains
    # a single entry
    if reason_code_list[0].is_failure:
        logging.info(f"Broker rejected you subscription: {reason_code_list[0]}")
    else:
        logging.info(f"Broker granted the following QoS: {reason_code_list[0].value}")

def on_connect(client, userdata, flags, rc, properties):
    
    if rc == 0:
        logging.info("Connected to MQTT Broker!")
        result = client.publish(settings['device']['availability'], "online", qos=2, retain=True)
        publish_descriptors(client)
        publish_state(client)
    else:
        logging.info("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, message, properties=None):
    logging.info(" Received message " + str(message.payload)
        + " on topic '" + message.topic
        + "' with QoS " + str(message.qos))
    
    topic = message.topic.split("/")
    if message.topic == settings['device']['metrics'][0]['command_topic']:
        if message.payload == b'on':
            logging.info("Command switch1 HIGH yo")
            switch_on(client)
        if message.payload == b'off':
            logging.info("Command switch1 LOW")
            switch_off(client)
    if topic[-1] == "command":
        if message.payload == b"update":
            logging.info("Update")
            subprocess.run(["bash", "-c", "echo update.sh > /shared/host_executor_queue"])
            

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    result = client.publish(settings['device']['availability'], "offline", qos=2, retain=True)

def subscribe(client: mqtt_client):
    for metric in settings['device']['metrics']:
        if "command_topic" in metric:
            topic = metric['command_topic']
            logging.info("Subscribe to " + topic)
            client.subscribe(topic)

def run():

    if gpio_enabled:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(4, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(7, GPIO.OUT, initial=GPIO.LOW)

    logging.info("Start Connection")
    client = mqtt_client.Client(client_id=settings['mqtt']['clientid'], callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)
    client.tls_set()

    client.username_pw_set(settings['mqtt']['username'], settings['mqtt']['password'])
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.user_data_set([])
    client.will_set(settings['device']['availability'],"offline",qos=2, retain=True)
    client.on_log = on_log
    logging.info("Connect to %s:%s", settings['mqtt']['broker'], settings['mqtt']['port'])
    result = client.connect(settings['mqtt']['broker'], settings['mqtt']['port'])
    if result != 0:
        logging.info("Failed")    
    logging.info("Subscribe")
    subscribe(client)
    stop_event = threading.Event()
    secondary_thread = threading.Thread(target=start_secondary, args=(stop_event,client,))
    secondary_thread.daemon = True
    secondary_thread.start()    
    logging.info("Loop")
    client.loop_forever()
    stop_event.set()
    logging.info(f"Received the following message: {client.user_data_get()}")


if __name__ == '__main__':
    run()