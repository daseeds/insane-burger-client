# python 3.11

import yaml
import random
import time
from paho.mqtt import client as mqtt_client


topic = "devices"
client_id = f'insane-burger-toulon1'
with open('settings.yml', 'r') as file:
    settings = yaml.safe_load(file)

def connect_mqtt():

    # Set Connecting Client ID
    client = mqtt_client.Client(settings['mqtt']['clientid'])
    # client.tls_set(ca_certs='./broker.emqx.io-ca.crt')

    # For paho-mqtt 2.0.0, you need to set callback_api_version.
    # client = mqtt_client.Client(client_id=client_id, callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)

    client.username_pw_set(settings['mqtt']['username'], settings['mqtt']['password'])
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.will_set("clients/"+settings['mqtt']['clientid'],"offline",qos=2, retain=True)
    client.connect(settings['mqtt']['broker'], settings['mqtt']['port'])
    return client

def on_connect(client, userdata, flags, rc):
# For paho-mqtt 2.0.0, you need to add the properties parameter.
# def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT Broker!")
        result = client.publish("clients/"+settings['mqtt']['clientid'], "online", qos=2, retain=True)
    else:
        print("Failed to connect, return code %d\n", rc)


FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

def on_disconnect(client, userdata, rc):
    result = client.publish("clients/"+settings['mqtt']['clientid'], "offline", qos=2, retain=True)
    logging.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            return
        except Exception as err:
            logging.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)

def subscribe(client: mqtt_client):
    client.subscribe(topic)
    client.on_message = on_message

def on_message(client, userdata, message, properties=None):
    print(" Received message " + str(message.payload)
        + " on topic '" + message.topic
        + "' with QoS " + str(message.qos))

def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


if __name__ == '__main__':
    run()