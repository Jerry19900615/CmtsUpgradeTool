
import ping
import paramiko
from paramiko_expect import SSHClientInteraction
import sys
import os
import socket
import logging
import requests

class Cmts:
	def __init__(self, ftpdip, fpga_file="BCM3228_20180730.bin", system_file="./files/CMC30-1.0.4-zhangzhibin-r4796.bin"):
		self.ip = "192.168.2.200"
		self.ftpdip = ftpdip
		self.fpga_file = fpga_file
		self.system_file = system_file
		self.logger = logging.getLogger("cmtsHelper.Cmts")
		self.username = "admin"
		self.password = "bluelink"

	def startupOk(self):
		if None == ping.do_one(self.ip, 3, 64):
			self.logger.warn("ping %s failed", self.ip)
			return False
		try:
			client = paramiko.SSHClient()
			client.load_system_host_keys()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

			client.connect(self.ip, username=self.username, password=self.password)

			with SSHClientInteraction(client, timeout=10, display=True) as exp:
				exp.expect([".*#\s+", ".*\$\s+"])
				exp.send("proxy_stdio_client docsiscore\n")
				exp.expect(".*CMTS>\s+", timeout=2)
			return True
		except socket.timeout:
			self.logger.error("docsiscore not startup")
			return False
		finally:
			try:
				client.close()
			except:
				pass

	def upgrade3228Fpga(self):
		try:
			client = paramiko.SSHClient()
			client.load_system_host_keys()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

			client.connect(self.ip, username=self.username, password=self.password)

			with SSHClientInteraction(client, timeout=10, display=True) as exp:
				exp.expect([".*#\s+", ".*\$\s+"])
				exp.send("wget -c -O /tmp/bcm3228.bin ftp://%s/%s"%(  self.ftpdip, self.fpga_file ))
#				exp.send("tftp -g -l /tmp/bcm3228.bin -r %s %s"%(   self.fpga_file , self.ftpdip ))
				exp.expect([".*#\s+", ".*\$\s+"])
				exp.send("proxy_stdio_client docsiscore\n")
				exp.send("cd /\n")
				exp.expect("CMTS>\s+")
				exp.send("/hal/download_3228_fpga /tmp/bcm3228.bin\n")
				exp.expect(".*Success.*",timeout=180)
			return True
		except socket.timeout:
			self.logger.error("upgrade 3228 fpga error")
			return False
		finally:
			try:
				client.close()
			except:
				pass

	def upgradeSystem(self):
		filename = os.path.basename(self.system_file)
		#print filename
		url = "http://%s/upload/appbin"%(self.ip)
		#print url
		try:
			files = {'file': (filename, open(self.system_file, 'rb'), 'application/docsis-cfg-file')}
			#print files
		except IOError:
			self.logger.error("file %s not exists"%(self.system_file))
			return False
			
		r = requests.post(url, files=files)
		#print r.json()
		return r.json()["success"]


if __name__ == "__main__":
	logging.basicConfig(filename="test.log")
	cmts = Cmts()
	if not cmts.startupOk():
		pass

