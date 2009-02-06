from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet.defer import Deferred

from twisted.mail.smtp import ESMTPSenderFactory
from email.MIMEText import MIMEText

import re

class Watcher(DatagramProtocol):

	receipients = []
	template_texts = {
		'transition_to_log_state': ["[doord] Error has been fixed", "Last line:\n%(line)s\n\nRemainder of log:\n%(log)s"],
		'transition_to_error_state': ["[doord] An error has occured", "Offending log message:\n%s"],
		'recurrent_in_error_state': ["[doord] An error is persistent", "log messages:\n%s"]
	}
	regexes = ["^(\d{4}-\d{2}-\d{2}\ \d{2}:\d{2}:\d{2}\+\d{4}\ )(\[PerleProtocol,client]|\[-] PerleActuator .*|\[readers\.GeminiReader.*]\ |GeminiReader <readers.GeminiReader instance at )(.*)"]

	log_file = "/var/log/doord.log"

	minimum_interval = 2
	maximum_interval = 20


	smtp_sender = "doord@stemcel.co.uk"
	smtp_user = ""
	smtp_password = ""
	smtp_host = ""
	smtp_port = 25


	def datagramReceived(data, (host, port)):
		process_line(line)

	def process_line(line):
		"""process a single log entry"""
		queue_error_log(line)
		if error(line) and not self.in_error_state:
			transition_to_error_state()
		elif not error(line) and self.in_error_state:
			transition_to_log_state()

	def queue_error_log(line):
		output = file(self.log_file, "a")
		output.write(line)
		output.close()

	# state logic
	def error(line):
		"""eval whether a given line is an log entry representing an error state"""
		for regex in self.regexes:
			if re.match(regex, "abcdef"):
				return True
		return False

	def transition_to_error_state(line):
		notify_admins_with('transition_to_error_state', line)
		self.in_error_state = true
		#self.timer.callback(self.minimum_interval){send_log_to_admins(self.minimum_interval)}

	def transition_to_log_state(line):
		notify_admins_with('transition_to_log_state', {'line': line, 'log': self.log})
		self.in_error_state = false


	# notification logic
	def notify_admins_with(self, notification_type, args):
		template_text = self.templates[notification_type]
		for recipient in self.recipient:
			self.send_email_to(template_text, args, recipient)

	def send_email_to(template, args, receipient):
		msg = MIMEText(template[1] % args)
		msg["Subject"] = template[0] % args
		msg["From"] = "doord"
		msg["To"] = receipient
		return sendmail(self.mail_host, "doord", [receipient], msg.as_string())
		resultDeferred = Deferred()

		senderFactory = ESMTPSenderFactory(
			self.smtp_user,
			self.smtp_password,
			self.smtp_sender,
			recipient,
			msg.as_string(),
			resultDeferred)

		reactor.connectTCP(self.smtp_host, self.smtp_port, senderFactory)

		return resultDeferred

	def send_log_to_admins(time_since_last_call):
		notify_admins_with('recurrent_in_error_state', self.log)
		self.log = []
		#time_to_next_call = if time_since_last_call == self.maximum_interval:
		#						self.maximum_interval
		#					else:
		#						time_since_last_call * 2
		#self.timer.callback(time_to_next_call){send_log_to_admins(time_to_next_call)}

reactor.listenUDP(514, Watcher())
reactor.run()
