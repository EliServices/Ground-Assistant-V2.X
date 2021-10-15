#Get the opional path from sys.argv
import sys
from os import path as op

if len(sys.argv) > 2:
    path = op.abspath(".")
elif len(sys.argv) < 2:
    path = op.abspath(".")
else:
    path = sys.argv[1]

#Set the process name
from setproctitle import setproctitle
setproctitle("ga_daemon")

stdout = sys.stdout
from time import sleep
from controller import Controller
from ground_assistant.load import ReadConfig
from ground_assistant.logger import Logger

d = Controller(path)
configs = ReadConfig(path)
p = configs.getconfig("ci")
logging = Logger(config_obj = configs, path = path, name = "ipc.log")
logging.append("\n" + d.status("dual"))

ipc = d.ipc(p["port"],p["password"])
if ipc == False:
    d.close()
    exit()

while True:
    with ipc.accept() as connection:
        logging.append("IPC Connection accepted from " + str(ipc.last_accepted))
        msg = connection.recv()
        logging.append("Got " + msg)
        if msg == "stop":
            logging.append("Received Stop from " + str(ipc.last_accepted))
            d.stop()
        elif msg == "continue":
            logging.append("Received Continue from " + str(ipc.last_accepted))
            d.run()
        elif msg == "restart":
            logging.append("Received Restart from " + str(ipc.last_accepted))
            status = d.restart()
            connection.send(status)
        elif msg == "refresh_ndb":
            logging.append("Received Refresh_ndb from " + str(ipc.last_accepted))
            status = d.refresh_ndb()
            connection.send(status)
        elif msg == "status":
            logging.append("Received Status request from " + str(ipc.last_accepted))
            status = d.status()
            logging.append(status)
            connection.send(status)
        elif msg == "show":
            logging.append("Received Show request from " + str(ipc.last_accepted))
            d.show()
        elif msg == "close":
            logging.append("Received Close from " + str(ipc.last_accepted))
            ipc.close()
            logging.append(d.status("dual") + "\n")
            d.close()
            break

logging.append("Bye\n")
logging.close()
