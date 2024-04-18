# python 3.11

import subprocess
import yaml
import time
from paho.mqtt import client as mqtt_client
import logging
import sys
import json

with open('settings.yml', 'r') as file:
    settings = yaml.safe_load(file)

with open(settings['descriptor'], 'r') as file:
    descriptor = json.load(file)

descriptor['unique_id'] = settings['unique_id']
descriptor['name'] = settings['unique_id']
descriptor['device']['name'] = settings['unique_id']
descriptor['state_topic'] = settings['topics']['state']
descriptor['command_topic'] = settings['topics']['command']
descriptor['device']['identifiers'].clear()
descriptor['device']['identifiers'].append(settings['unique_id'])
descriptor['availability'].clear()
avail = {}
avail['topic'] = settings['topics']['availability']

descriptor['availability'].append(avail)


gpio_enabled = False

switch1_state = "off"

try:
    import RPi.GPIO as GPIO
    gpio_enabled = True
except RuntimeError:
    print("Error importing RPi.GPIO!  This is probably because you need superuser privileges.  You can achieve this by using 'sudo' to run your script")

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
    logging.info("Publish " + switch1_state + " on " + settings['topics']['state'])
    client.publish(settings['topics']['state'], switch1_state, qos=2, retain=True)

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
        result = client.publish(settings['topics']['availability'], "online", qos=2, retain=True)
        result = client.publish(settings['topics']['advertise'], json.dumps(descriptor), qos=2, retain=True)
        publish_state(client)
    else:
        logging.info("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, message, properties=None):
    logging.info(" Received message " + str(message.payload)
        + " on topic '" + message.topic
        + "' with QoS " + str(message.qos))
    
    topic = message.topic.split("/")
    if message.topic == settings['topics']['command']:
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
    result = client.publish(settings['topics']['availability'], "offline", qos=2, retain=True)

def subscribe(client: mqtt_client):
    for topic in settings['to_sub']:
        logging.info("Subscribe to " + topic)
        client.subscribe(topic)

def run():
    logging.basicConfig(format='%(asctime)s %(message)s')
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Start Application")

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
    client.will_set(settings['topics']['availability'],"offline",qos=2, retain=True)
    client.on_log = on_log
    logging.info("Connect to %s:%s", settings['mqtt']['broker'], settings['mqtt']['port'])
    result = client.connect(settings['mqtt']['broker'], settings['mqtt']['port'])
    if result != 0:
        logging.info("Failed")    
    logging.info("Subscribe")
    subscribe(client)
    logging.info("Loop")
    client.loop_forever()
    logging.info(f"Received the following message: {client.user_data_get()}")


if __name__ == '__main__':
    run()