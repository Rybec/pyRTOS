
# FreeRTOS states are
#
# Running - Currently executing
# Ready - Ready to run but task of higher or equal priority is currently in Running state
# Blocked - Task is waiting for some event, for example, a delay
#           Other reasons for blocks include waiting for a queue, semaphore, or message.
# Suspended - Task was explicitly suspended and will only be resumed by another task.

# For Blocked states, some condition must be met to unblock.  Is it possible that this
# condition could be represented as a function that is called on the task object, that
# will return True if the condition is met?  This would allow the construction of
# lamba or inner functions, that have built in references to any data required to
# determine whether the unblocking condition is met.

# See https://www.freertos.org/RTOS-task-states.html for state transition graph


# Task states
RUNNING   = 0   # Currently executing on the processor
READY     = 1   # Ready to run but task of higher or equal priority is currently running
BLOCKED   = 2   # Task is waiting for some condition to be met to move to READY state
SUSPENDED = 3   # Task is waiting for some other task to unsuspend
				# Why do we need this, since BLOCKED could be used? Creating an
				# unblocking condition for this would require the API to know
				# that the condition is a suspension, and if it already knows
				# it is a suspension, it can just remove it, instead of running
				# the test function.  Thus there is no point in having a
				# function and we might as well just use a flag, since it is
				# cheaper.


class Task(object):
	def __init__(self, func, priority=255, name=None):
		self.func = func
		self.priority = priority
		self.name = name
		self.state = READY
		self.ready_conditions = []
		self.thread = None  # This is for the generator object
		self._in_messages = []
		self._out_messages = []

	# If the thread function is well behaved, this will get the generator
	# for it, then it will start it, it will run its initialization code,
	# and then it will yield.
	def initialize(self):
		self.thread = self.func(self)
		next(self.thread)

	# Run task until next yield
	def run_next(self):
		state_change = next(self.thread)

		if state_change != None:
			print("Blocking", self.name, "for", state_change)
			self.ready_conditions = state_change
			self.state = BLOCKED

		msgs = self._out_messages
		self._out_messages = []

		return msgs

	def send(self, msg):
		self._out_messages.append(msg)

	def recv(self):
		msgs = self._in_messages
		self._in_messages = []
		return msgs

	def message_count(self):
		return len(self._in_messages)

	def deliver(self, msg):
		self._in_messages.append(msg)

	def suspend(self):
		self.state = SUSPENDED
		self.ready_conditions = []

	def resume(self):
		self.state = READY
		self.ready_conditions = []

