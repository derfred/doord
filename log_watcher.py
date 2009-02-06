from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet.defer import Deferred

from twisted.mail.smtp import ESMTPSenderFactory
from email.MIMEText import MIMEText

import re, StringIO


class Watcher(DatagramProtocol):

	receipients = []
	template_texts = {
		'transition_to_log_state': ["[doord] Error has been fixed", "Last line:\n%(line)s\n\nRemainder of log:\n%(log)s"],
		'transition_to_error_state': ["[doord] An error has occured", "Offending log message:\n%s"],
		'recurrent_in_error_state': ["[doord] An error is persistent", "log messages:\n%s"]
	}
	regexes = [
		"\[-\] ReportedHealthCheck no errors",
		"\[-\] Pipeline .* opening door for authentication result success"
	]

	log_file = "/var/log/doord.log"

	smtp_sender = "doord@stemcel.co.uk"
	smtp_user = ""
	smtp_password = ""
	smtp_host = ""
	smtp_port = 25


	minimum_interval = 2
	maximum_interval = 20
	log = []

	in_error_state = False

	def datagramReceived(self, data, (host, port)):
		self.process_line(data[4:])

	def process_line(self, line):
		"""process a single log entry"""
		self.queue_error_log(line)

		if self.error(line[16:]) and not self.in_error_state:
			print "have error %s" % line
			self.transition_to_error_state(line)
		elif not self.error(line[16:]) and self.in_error_state:
			print "end error"
			self.transition_to_log_state(line)

	def queue_error_log(self, line):
		output = file(self.log_file, "a")
		output.write(line + "\n")
		output.close()

	# state logic
	def error(self, line):
		"""eval whether a given line is an log entry representing an error state"""
		if not "doord" in line:
			return False

		line = line[7:]

		for regex in self.regexes:
			if re.match(regex, line):
				return False
		return True

	def transition_to_error_state(self, line):
		self.notify_admins_with('transition_to_error_state', line)
		self.in_error_state = True
		#self.timer.callback(self.minimum_interval){send_log_to_admins(self.minimum_interval)}

	def transition_to_log_state(self, line):
		self.notify_admins_with('transition_to_log_state', {'line': line, 'log': self.log})
		self.in_error_state = False


	# notification logic
	def notify_admins_with(self, notification_type, args):
		template_text = self.template_texts[notification_type]
		for receipient in self.receipients:
			self.send_email_to(template_text, args, receipient)

	def send_email_to(self, template, args, receipient):
		msg = MIMEText(template[1] % args)
		msg["Subject"] = template[0]
		msg["From"] = "doord"
		msg["To"] = receipient

		resultDeferred = Deferred()

		senderFactory = ESMTPSenderFactory(
			self.smtp_user,
			self.smtp_password,
			self.smtp_sender,
			receipient,
			StringIO.StringIO(msg.as_string()),
			resultDeferred)

		reactor.connectTCP(self.smtp_host, self.smtp_port, senderFactory)

		return resultDeferred

	def send_log_to_admins(self, time_since_last_call):
		notify_admins_with('recurrent_in_error_state', self.log)
		self.log = []
		#time_to_next_call = if time_since_last_call == self.maximum_interval:
		#						self.maximum_interval
		#					else:
		#						time_since_last_call * 2
		#self.timer.callback(time_to_next_call){send_log_to_admins(time_to_next_call)}

reactor.listenUDP(514, Watcher())
reactor.run()
