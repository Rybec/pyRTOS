import time

import pyRTOS

version = 0.1


tasks = []


def add_task(task):
	if task.thread == None:
		task.initialize()

	tasks.append(task) 

	tasks.sort(key=lambda t: t.priority)



def start(scheduler=None):
	global tasks

	if scheduler == None:
		scheduler = pyRTOS.default_scheduler


	run = True
	while run:
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

class Mutex(object):
	def __init__(self):
		self.locked = False

	# This returns a task block condition generator.  It should
	# only be called using something like "yield [mutex.lock()]"
	# or "yield [mutex.lock(), timeout(1)]"
	def lock(self):
		has_lock = False

		while True:
			if has_lock:
				yield True
			elif self.locked:
				yield False
			else:
				self.locked = True
				has_lock = True
				yield True

	def nb_lock(self):
		if self.locked:
			return False
		else:
			self.locked = True
			return True

	def unlock(self):
		self.locked = False


