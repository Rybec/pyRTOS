import time

import pyRTOS

version = 0.1


tasks = []
service_routines = []


def add_task(task):
	if task.thread == None:
		task.initialize()

	tasks.append(task) 

	tasks.sort(key=lambda t: t.priority)


def add_service_routine(service_routine):
	service_routines.append(service_routine)


def start(scheduler=None):
	global tasks

	if scheduler == None:
		scheduler = pyRTOS.default_scheduler

	run = True
	while run:
		for service in service_routines:
			service()

		messages = scheduler(tasks)
		pyRTOS.deliver_messages(messages, tasks)

		if len(tasks) == 0:
			run = False



# Task Block Conditions

# Timeout   - Task is delayed for no less than the specified time.
def timeout(seconds):
		start = time.monotonic()

		while True:
			yield time.monotonic() - start >= seconds

def timeout_ns(nanoseconds):
		start = time.monotonic_ns()

		while True:
			yield time.monotonic_ns() - start >= nanoseconds

# Cycle Delay - Task is delayed for no less than the number OS loops specified.
def delay(cycles):
	ttl = cycles
	while True:
		if ttl > 0:
			ttl -= 1
			yield False
		else:
			yield True

# Message   - Task is waiting for a message.
def wait_for_message(self):
	while True:
		yield self.message_count() > 0

# Notification - Task is waiting for a notification
def wait_for_notification(task, index=0, state=1):
	task.notes[0][index] = 0
	while task.notes[0][index] != state:
		yield False

	while True:
		yield True



# API I/O   - I/O done by the pyRTOS API has completed.
#             This blocking should be automatic, but API
#             functions may want to provide a timeout
#             arguement.
# API Defined

# UFunction - A user provided function that returns true
#             or false, allowing for complex, user defined
#             conditions.
#
#             UFunctions must be infinite generators.  They can
#             take take any initial arguments, but they must
#             must yield False if the condition is not met and
#             True if it is.  Arguments may be passed into the
#             generator iterations, but pyRTOS should not be
#             expected to pass arguments in when checking. In
#             most cases, it would probably be better to
#             communicate with Ufunctions through globals.
# User Defined


# Blocking is achieved by yielding with a list argument.  Each time pyRTOS
# tests the task for readiness, it will iterate through the list, running
# each generator function, checking the truth value of its output.  If the
# truth value of any element of the list is true, the task will unblock.
# This allows for conditions to effectively be "ORed" together, such that it
# is trivial to add a timeout to any other condition.  If you need to "AND"
# conditions together, write a UFunction that takes a list of conditions and
# yields the ANDed output of those conditions.



# API Elements

# Mutex with priority inheritance
# (highest priority waiting task gets the lock)
class Mutex(object):
	def __init__(self):
		self.locked = False

	# This returns a task block condition generator.  It should
	# only be called using something like "yield [mutex.lock(self)]"
	# or "yield [mutex.lock(self), timeout(1)]"
	def lock(self, task):
		while True:
			if self.locked == False or self.locked == task:
				self.locked = task
				yield True
			else:
				yield False

	def nb_lock(self, task):
		if self.locked == False or self.locked == task:
			self.locked = task
			return True
		else:
			return False

	def unlock(self):
		self.locked = False


# Mutex with request order priority
# (first-come-first-served priority for waiting tasks)
class BinarySemaphore(object):
	def __init__(self):
		self.wait_queue = []
		self.owner = None
		
	# This returns a task block condition generator
	def lock(self, task):
		self.wait_queue.append(task)

		try:
			while True:
				if self.owner == None and self.wait_queue[0] == task:
					self.owner = self.wait_queue.pop(0)
					yield True
				elif self.owner == self:
					yield True
				else:
					yield False
		finally:
			# If this is combined with other block conditions,
			# for example timeout, and one of those conditions
			# unblocks before this, we need to prevent this
			# from taking the lock and never releasing it.
			if task in self.wait_queue:
				self.wait_queue.remove(task)

	def nb_lock(self, task):
		if self.owner == None or self.owner == task:
			self.owner = task
			return True
		else:
			return False

	def unlock(self):
		self.owner = None



