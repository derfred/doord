from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor

class Watcher(DatagramProtocol):

	receipients = []
	template_texts = {
		
	}

    def datagramReceived(data, (host, port)):
        process_line(line)

	def process_line(line):
		"""process a single log entry"""
		queue_error_log(line)
		if error(line) and not self.in_error_state:
			transition_to_error_state()
		elif not error(line) and self.in_error_state:
			transition_to_log_state()

	def error(line):
		"""eval whether a given line is an log entry representing an error state"""
		self.regexes.any{line / regex}

	def transition_to_error_state(line):
		notify_admins_with(:transition_to_error_state, line)
		self.in_error_state = true
		self.timer.callback(self.minimum_interval){send_log_to_admins(self.minimum_interval)}

	def transition_to_log_state(line):
		notify_admins_with(:transition_to_log_state, {line,self.log})
		self.in_error_state = false

	def notify_admins_with(self, notification_type, |arg|):
		template_text = self.templates[notification_type]
		self.recipients.each{send_email_to((template_text % arg), receipient)}

	def send_email_to((subject, body), receipient):
		self.email_server.send(subject, body, receipient)

	def send_log_to_admins(time_since_last_call):
		notify_admins_with(:recurrent_in_error_state, self.log)
		self.log = []
		time_to_next_call = if time_since_last_call == self.maximum_interval:
								self.maximum_interval
							else:
								time_since_last_call * 2
		self.timer.callback(time_to_next_call){send_log_to_admins(time_to_next_call)}

reactor.listenUDP(514, Watcher())
reactor.run()
