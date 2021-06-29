import pyRTOS


# User defined message types start at 128
REQUEST_DATA = 128
SENT_DATA = 129


# self is the thread object this runs in
def sample_task(self):

	### Setup code here


	### End Setup code

	# Pass control back to RTOS
	yield

	# Thread loop
	while True:

		# Check messages
		msgs = self.recv()
		for msg in msgs:

			### Handle messages by adding elifs to this
			if msg.type == pyRTOS.QUIT:  # This allows you to
			                             # terminate a thread.
			                             # This condition may be removed if
			                             # the thread should never terminate.

				### Tear down code here
				print("Terminating task:", self.name)
				print("Terminated by:", msg.source)

				### End of Tear down code
				return
			elif msg.type == REQUEST_DATA: # Example message, using user
			                               # message types
				self.send(pyRTOS.Message(SENT_DATA,
				                         self,
				                         msg.source,
				                         "This is data"))
			### End Message Handler

		### Work code here
		# If there is significant code here, yield periodically
		# between instructions that are not timing dependent.
		# Also, it is generally a good idea to yield after
		# I/O commands that return instantly but will require
		# some time to complete (like I2C data requests).
		# Each task must yield at least one per iteration,
		# or it will hog all of the CPU, preventing any other
		# task from running.



		### End Work code

		yield [pyRTOS.timeout(0.5)]

		if self.name == "task1":
			target = "task2"
		else:
			target = "task1"

		print(self.name, "sending quit message to:", target)
		self.send(pyRTOS.Message(pyRTOS.QUIT, self, target))

		# Testing message passing system
		print(self.name, "sending quit message to:", "task3 (does not exist)")
		print("This should silently fail")
		self.send(pyRTOS.Message(pyRTOS.QUIT, self, "task3"))

		yield [pyRTOS.wait_for_message(self)]


pyRTOS.add_task(pyRTOS.Task(sample_task, name="task1", mailbox=True))
pyRTOS.add_task(pyRTOS.Task(sample_task, name="task2", mailbox=True))
pyRTOS.add_service_routine(lambda: print("Service Routine Executing"))


pyRTOS.start()
