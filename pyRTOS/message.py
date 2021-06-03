import pyRTOS

# Message Types
QUIT = 0
# 1-127 are reserved for future use
# 128+ may be used for user defined message types


class Message(object):
	def __init__(self, type, source, target, message=None):
		self.type = type
		self.source = source
		self.target = target
		self.message = message


def deliver_messages(messages, tasks):
	for message in messages:
		if type(message.target) == pyRTOS.Task:
			message.target.deliver(message)
		else:
			targets = filter(lambda t: message.target == t.name, tasks)
			try:
				next(targets).deliver(message)
			except StopIteration:
				pass


class MessageQueue(object):
	def __init__(self, capacity=10):
		self.capacity = capacity
		self.buffer = []

	# This is a blocking condition
	def send(self, msg):
		sent = False

		while True:
			if sent:
				yield True
			elif len(self.buffer) < self.capacity:
				self.buffer.append(msg)
				yield True
			else:
				yield False

	def nb_send(self, msg):
		if len(self.buffer) < self.capacity:
			self.buffer.append(msg)
			return True
		else:
			return False


	# This is a blocking condition.
	# out_buffer should be a list
	def recv(self, out_buffer):
		received = False
		while True:
			if received:
				yield True
			elif len(self.buffer) > 0:
				received = True
				out_buffer.append(self.buffer.pop(0))
				yield True
			else:
				yield False

	
	def nb_recv(self):
		if len(self.buffer) > 0:
			return self.buffer.pop(0)
		else:
			return None

