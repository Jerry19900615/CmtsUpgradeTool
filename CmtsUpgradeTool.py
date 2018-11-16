import Tkinter as tk
import ttk
from tkFileDialog import *
import tkMessageBox
import os
import sys
import requests
import threading
import winpexpect
import paramiko
from paramiko_expect import SSHClientInteraction
import win32process
import logging
import socket
import ipaddress
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from subprocess import Popen, PIPE
import time
import ConfigParser
#
from tkStatusbar import *
from cmtsHelper import *





class App(tk.Frame):
	def __init__(self, master=None):
		tk.Frame.__init__(self, master)
		self.grid(sticky="we")
		self.createUI()
		self.upgradeInProcess = False
		self.upgradeSuccess = 0
		self.upgradeStatusMsg = ""
		self.tmpStatusMsg = []
		self.logger = logging.getLogger()
		self.logger.debug("App Startup")
		self.ftpd_running = False
		self.localip = ""
	
	def open3228File(self):
		f = askopenfilename(parent=self, 
						title="select file", 
						defaultextension=".bin")
		self.e_3228_file.delete(0, tk.END)
		self.e_3228_file.insert(0, f)
		
	def openSystemFile(self):
		f = askopenfilename(parent=self, 
						title="select file", 
						defaultextension=".bin")
		self.e_system_file.delete(0, tk.END)
		self.e_system_file.insert(0, f)
		
	def startFtpServer(self):
		authorizer = DummyAuthorizer()
		authorizer.add_anonymous("./files/")

		handler = FTPHandler
		handler.authorizer = authorizer

		server = FTPServer((self.localip, 21), handler)
		self.ftpd_running = True
		while self.ftpd_running:
			server.serve_forever(timeout=1, blocking=False)
	
	def logStat(self, msg):
		self.text.insert(tk.END, msg+"\n")
	
	def upgrade(self):
		msg = "upgrading start"
		self.logStat(msg)
		self.logger.info(msg)
		self.upgradeInProcess = True
		self.prg_bar.start()
		self.upgradeStatusMsg = "upgrading ...."
		#start upgrade
		self.upgrade_single_cmts(self.localip, self.fpga_file, self.system_file)
		
		self.upgradeInProcess = False
		self.upgradeStatusMsg = "finish"
		
	def upgrade_single_cmts(self, ftpdip, fpga_file, system_file):		
		cmts = Cmts(ftpdip, fpga_file, "./files/%s"%system_file)
		if cmts.startupOk() == False:
			msg = "cmts not startup ok"
			self.logStat(msg)
			self.logger.error(msg)
			return 
		msg = "upgrading 3228 fpga"
		self.logStat("upgrading 3228 fpga")
		self.logger.info(msg)
		if cmts.upgrade3228Fpga() == False:
			msg = "upgrade 3228 fpga failed"
			self.logStat("upgrade 3228 fpga failed")
			self.logger.error(msg)
			self.upgradeStatusMsg = msg
			return 
		msg = "upgrading 3228 fpga success.\nstart upgrading system"
		self.logger.info(msg)
		self.logStat(msg)
		if cmts.upgradeSystem() == False:
			msg = "upgrading system failed"
			self.logger.error(msg)
			self.logStat(msg)
			self.upgradeStatusMsg = msg
			return 
		msg = "upgrading cmts success"
		self.logger.info(msg)
		self.logStat(msg)
		self.upgradeStatusMsg = msg
		
	def do_upgrade(self):
		#self.logger.info("do_upgrade")
		if self.upgradeInProcess:
			self.tmpStatusMsg.append("upgrading in process")
			return 
		if self.localip == "":
			addrs = socket.getaddrinfo(socket.gethostname(),None)
			for item in addrs:
				#print(item)
				e = re.search("192\.168\.2\.\d+",item[4][0])
				if None != e:
					self.localip = e.group(0)
					break
			
			if self.localip == "":
				tkMessageBox.showerror("Error", "No ip of network 192.168.2.0/24")
				return 
		try:
			files_ini = ConfigParser.ConfigParser()
			files_ini.read("files.ini")
			self.fpga_file = files_ini.get("global", "fpga")
			self.system_file = files_ini.get("global", "system")	
		except ConfigParser.NoSectionError:
			tkMessageBox.showerror("Error", "files.ini error")
			return		
		if not self.ftpd_running:
			self.ftpd = threading.Thread(target=self.startFtpServer)
			self.ftpd.start()
		#self.logger.info("do_upgrade33333")
		threading.Thread(target=self.upgrade).start()
		
		
	def do_clear(self):
		#print self.text.index(tk.INSERT)
		self.text.delete(1.0, tk.END)
	
	def statusMonitor(self):
		try:
			msg = self.tmpStatusMsg.pop()
			self.stat_bar.set(msg)
		except IndexError:
			self.stat_bar.set(self.upgradeStatusMsg)
		if self.upgradeInProcess == False:
			self.prg_bar.stop()
			self.prg_bar.grid_forget()
		else:
			self.prg_bar.grid(self.prg_grid_info)
		self.master.after(500, self.statusMonitor)
		
	def createUI(self):
		self.text = tk.Text(self, height=10, width=50)
		self.text.grid(padx=5, pady=5, columnspan=2)
		self.btn_start = tk.Button(self, text="start upgrade", command=self.do_upgrade)
		self.btn_start.grid(padx=5,pady=5, sticky="e")
		self.btn_clear = tk.Button(self, text="clear", command=self.do_clear)
		self.btn_clear.grid(row=1,column=1, padx=5,pady=5, sticky="w")
		self.prg_bar = ttk.Progressbar(self, mode="indeterminate")
		self.prg_bar.grid(sticky="we",padx=5, pady=5,columnspan=2)
		self.prg_grid_info = self.prg_bar.grid_info()
		self.stat_bar = Statusbar(self)
		self.stat_bar.grid(sticky="we",padx=5, pady=5, columnspan=2)
		#timer monitor
		self.master.after(0, self.statusMonitor)
		self.master.protocol("WM_DELETE_WINDOW", self.quit)
		
	def quit(self):
		if self.ftpd_running:
			self.ftpd_running = False
			while self.ftpd.is_alive():
				pass
		self.master.quit()
		
		
	
version = "v1.2"
		
if __name__ == "__main__":
	logging.basicConfig(filename="%s.log"%sys.argv[0], level=logging.INFO)
	app = App()
	app.master.title("Upgrade Tool %s" % (version))
	app.master.resizable(False, False)
	app.mainloop()
	
