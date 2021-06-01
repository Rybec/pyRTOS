#pyRTOS


## Introduction

pyRTOS is a real-time operating system (RTOS), written in Python.  The primary goal of pyRTOS is to provide a pure Python RTOS that will work in CircuitPython.  The secondary goal is to provide an educational tool for advanced CircuitPython users who want to learn to use an RTOS.  pyRTOS should also work in MicroPython, and it can be used in standard Python as well.

pyRTOS was modeled after FreeRTOS, with some critical differences.  The biggest difference is that it uses a voluntary task preemption model, where FreeRTOS generally enforces preemption through timer interrupts.  This means there is a greater onus on the user to ensure that all tasks are well behaved.  pyRTOS also uses different naming conventions, and tasks have built in message passing.

To the best of my knowledge, aside from voluntary preemption, the task scheduling is identical to that found in FreeRTOS.  Tasks are assigned numerical priorities, the lower the number the higher the priority, and the highest priority ready task is given CPU time, where ties favor the currently running task.  Alternative scheduling algorithms may be added in the future.

## Basic Usage

See sample.py for an example task and usage.  A task is similar to a thread in a desktop operating system, except that in pyRTOS tasks cannot be migrated to other processors or cores.  This is due to limitations with CircuitPython.  In theory, though, it should be possible to write a scheduler with thread migration, for MicroPython, which does support hardware multithreading.

### Tasks

A pyRTOS task is composed of a Task object combined with a function containing the task code.  A task function takes a single argument, a reference to the Task object containing it.  Task functions are Python generators.  Any code before the first yield is setup code.  Anything returned by this yield will be ignored.  The main task loop should follow this yield.  This is the code that will be executed when the scheduler gives the task CPU time.

The main task loop is typically an infinite loop.  If the task needs to terminate, a return call should be used, and any teardown that is necessary should be done directly before returning.  Typically though, tasks never return.

Preemption in pyRTOS is completely voluntary.  This means that all tasks _must_ periodically yield control back to the OS, or no other task will get CPU time, messages cannot be passed between tasks, and other administrative duties of the OS will never get done.  Yields have to functions in pyRTOS.  One is merely to pass control back to the OS.  This allows the OS to reevaluate task priorities and pass control to a higher priority ready task, and it allows the OS to take care of administration like message passing, lock handling, and such.  Yields should be fairly frequent.  For small tasks, once per main loop may be sufficient.  For larger tasks, yields should be placed between subsections.  If a task has a section of timing dependent code though, do not place yields in places where they could interrupt timing critial processes.  There is no guarantee a yield will return within the required time.

Yields are also used to make certain blocking API calls.  The most common will likely be delays.  Higher priority processes need to be especially well behaved, because even frequent yields will not give lower priority processes CPU time.  The default scheduler always gives the highest priority ready task the CPU time.  The only way lower priority tasks _ever_ get time, is if higher priority tasks block when they do not need the CPU time.  Typically this means blocking delays, which are accomplished in pyRTOS by yielding with a timeout generator.  When the timeout generator expires, the task will become ready again, but until then, lower priority tasks will be allowed to have CPU time.  Tasks can also block when waiting for messages or mutual exclusion locks.  In the future, more forgiving non-real-time schedulers may be available.

There are also some places tasks _should_ always yield.  Whenever a message is passed, it is placed on a local queue.  Messages in the local task outgoing queue are delivered when that task yields.  Other places where yielding is necessary for an action to resolve will be noted with the documentation on those actions.

### Messages

Message passing mechanics are built directly into tasks in pyRTOS.  Each task has its own incoming and outgoing mailbox.  Messages are delivered when the currently running task yields.  This message passing system is fairly simple.  Each message has a single sender and a single recipient.  Messages also have a type, which can be pyRTOS.QUIT or a user defined type (see sample.py).  User defined types start with integer values of 128 and higher.  Types below 128 are reserved for future use by the pyRTOS API.  Messages can also contain a message, but this is not required.  If the type field is sufficient to convey the necessary information, it is better to leave the message field empty, to save memory.  The message field can contain anything, including objects and lists.  If you need to pass arguments into a new task, one way to do this is to call deliver() on the newly created task object, with a message containing a list or tuple of arguments.  This will add the message to the task's message queue, allowing it to access that message and thus the arguments once it begins execution.

Checking messages is a critical part of any task that may receive messages.  Unchecked message queues can accumulate so many messages that your system runs out of memory.  If your task may receive messages, it is important to check the messages every loop.  Also be careful not to send low priority tasks too many messages without periodically blocking all higher priority tasks, so they can have time to process their message queues.  If a task that is receiving messages never gets CPU time, that is another way to run out of memory.

Messages can be addressed with a reference to the target task object or with the name of the object.  Names can be any sort of comparable data, but numbers are the most efficient, while strings are the most readable.  Object reference addressing _must_ target an object that actually exists, otherwise the OS will crash.  Also note that keeping references of terminated tasks will prevent those tasks from being garbage collected, creating a potential memory leak.  Object references are the _fastest_ message addressing method, and they may provide some benefits when debugging, but its up to the user to understand and avoid the associated hazards.  Name addressing is much safer, however messages addressed to names that are not among the existing tasks will silently fail to be delivered, making certain bugs harder to find.  In addition, because name addresses require finding the associated object, name addressed messages will consume significantly more CPU time to deliver.

sample.py has several examples of message passing.

## pyRTOS API

### Main API

```add_task(task)```

This adds a task to the scheduler.  Tasks that have been created but not added will never run.  This can be useful, if you want to create a task and then add it at some time in the future, but in general, tasks are created and then added to the scheduler before the scheduler is started.

`task` - a Task object, with an appropriatly designed task generator function.

Note that `add_task()` will automatically initialize any task that has not previously been initialized.  This is important to keep in mind, because initializing a task manually after adding it to the scheduler may cause serious problems, if the initialization code cannot safely be run more than once.

```start(scheduler=None)```

This begins execution.  This function will only return when all tasks have terminated.  In most cases, tasks will not teriminate and this will never return.

`scheduler` - When this argument is left with its default value, the default scheduler is used since no other schedulers currently exist, this is really only useful if you want to write your own scheduler.  Otherwise, just call `start()` without an argument.  This should be called only after you have added all tasks.  Additional tasks can be added while the scheduler is running (within running tasks), but this should generally be avoided if necessary.  (A better option, if you need to have a task that is only activated once some condition is met, is to create the task and then immediately suspend it.  This will not prevent the initialization code from running though.  If you need to prevent intialization code from running until the task is unsuspended, you can place the first yield before it instead of after.)

### Task API

```Task(func, priority=255, name=None)```

Task functions must be wrapped in `Task` objects that hold some context data.  This object keeps track of task state, priority, name, blocking conditions, and ingoing and outgoing message queues.  It also handles initialization, transition to blocking state, and message queues.  The Task object also provides some utility functions for tasks.

`func` - This is the actual task function.  This function must have the signature `func_name(self)`.  The `self` arguement is a reference to the Task object wrapping the function, and it will be passed in when the Task is initialized.  See sample.py for an example task function.

`priority` - This is the task priority.  The lower the value, the higher priority the task.  The range of possible values depends on the system, but typically priority values are generally kept between 0 and 8 to 32, depending on the number of tasks.  The default of 255 is assumed to be far lower priority than any sane developer would ever use, making the default the lowest possible priority.  Ideally, each task should have a unique priority, but there may be cases where a group of tasks should allow the currently running task within the group to continue running until it blocks, without any task in the group having higher priority than the others.  In this case, it is acceptable to give these tasks the same priority.

`name` - Naming tasks can make message passing easier.  See Basic Usage > Messages above for the pros and cons of using names.  If you do need to use names, using integer values will use less memory and give better performance than strings, but use what works best for you.

#### Task Methods

These are the methods of the `Task` object that are useful to the task and user.  Other methods should be treated as internal OS methods that should never be used outside of OS code.

```Task.initialize()```

This will initialize the task function, to obtain the generator and run any setup code (code before the first yield).  Note that this passes `self` into the task function, to make the following methods of `Task` available to the task.  This can be run explicitly.  If it is not, it will be run when the task is added to the scheduler using `add_task()`.  In most cases, it is not necessary to manually initialize tasks, but if there are strict ordering and timing constraints between several tasks, manual initialization can be used to guarantee that these constraints are met.  If a task is manually initialized, `add_task()` will not attempt to initialize it again.

```Task.send(msg)```

Put a `Message` object in the outgoing message queue.  Note that while it is possible to call this with any kind of data without an immediate exception, the message passing code in the OS will throw an exception if it cannot find a `target` member within the data, and well behaved tasks will throw an exception if there is no `type` member.  Just stick to passing `Message` objects, unless there is a critical reason not to.  Also note that sent messages will remaining in the outgoing message queue, until the next yield.  Unless there is some good reason not to, it is probably a good idea to yield immediately after any message is sent.  (The exception is, if the task needs to send out messages to multiple targets before giving up the CPU, send all of the messages, then yield.)

```Task.recv()```

This returns the incoming message queue and clears it.  This should be called regularly by any task that messages may be sent to, to prevent the queue from accumulating so many messages that the devices runs out of memory.  Note that because messages are distributed by the OS, once a task has called this, no new messages will be added to the incoming queue until a yield has allowed some other task to run.  (This means that if this is the highest priority task, and it issues a non-blocking yield, no other task will have a chance to sent a message.  Thus high priority tasks should issue blocking yields, typically timeouts, periodically, to allow lower priority tasks some CPU time.)

```Task.message_count()```

This returns the number of messages in the incoming queue.

```Task.deliver(msg)```

This adds a message to the incoming queue.  This should _almost_ never be called directly.  The one exception is that this can be used to pass arguments into a task, in the main thread, before the scheduler is started.  Once the scheduler is started, messages should be passed exclusively through the OS, and this should never be called directly.  Note also that a message passed this way does not need to be a message object.  If you are using this to pass in arguments, use whatever sort of data structure you want, but make sure that the task expects it.  (If you deliver your arguments to the task before initialization, you can use `self.recv()` in the initialization code to retreive them.)

```Task.suspend()```

Puts the task into the suspended state.  Suspended tasks do not run while they are suspended.  Unlike blocked tasks, there are no conditions for resuming a suspended task.  Suspended tasks are only returned to a ready state when they are explicitly resumed.  Note that suspension is cheaper than blocking, because suspended tasks do not have conditions that need to be evaluated regularly.  Also note that suspending a blocked task will clear all blocking conditions.

```Task.resume()```

Resumes the task from a suspended state.  This can also be used to resume a blocked task.  Note that using this on a blocked task will clear all blocking conditions.  `resume()` should not be used on the running task.  Doing so will change the state to ready, telling the OS that the task is not running when it _is_ running.  Under the default scheduler, this is unlikely to cause serious problems, but the behavior of a running task that is in the ready state is undefined and may cause issues with other schedulers.

### Task Block Conditions

Task block conditions are generators that yield True if their conditions are met or False if they are not.  When a block condition returns True, the task blocked by it is unblocked and put into the ready state.

A task is blocked when a yield returns a list of block conditions.  When any condition in that list returns True, the task is unblocked.  This allows any blocking condition to be paired with a `timeout()` condition, to unblock it when the timeout expires, even if the main condition is not met.  For example, `yield [wait_for_message(self), timeout(5)]` will block until there is a message in the incoming message queue, but it will timeout after 5 seconds and return to ready state, even if no message arrives.

Note that blocking conditions _must_ be returned as lists, even if there is only one condition.  Thus, for a one second blocking delay, use `yield [timeout(1)]`.

```timeout(seconds)```

By itself, this blocks the current task for the specified amount of time.  This does not guarantee that the task will begin execution as soon as the time has elasped, but it does guarantee that it will not resume until that time has passed.  If this is higher priority than the running task and all other ready tasks, then this task will resume as soon as control is passed back to the scheduler, and it has completed its maintenance.

When combined with other blocking conditions, this will act as a timeout.  Because only one condition must be met to unblock, when this evaluates to true, the task will unblock even if other blocking conditions are not met.

`seconds` - The number of seconds, as a floating point value, to delay.

```timeout_ns(nanoseconds)```

This is exactly like `timeout()`, except the argument specifies the delay in nanoseconds.  Note that the precision of this condition is dependent on the clock speed of your CPU, in addition to the limitations affecting `timeout()`.

`nanoseconds` - The number of nanoseconds, as an integer value, to delay.

```delay(cycles)```

This delay is based on OS cycles rather than time.  This allows for delays that are guaranteed to allow a specific number of cycles for other tasks to run.  This can be especially useful in cases where it is known that a specific task will take priority during the delay and that task is doing something that will require a known number of cycles to complete.  (Note that a cycle lasts from one yield to the next, rather than going through the full loop of a task.)

*UFunction*

It is also possible to create your own blocking conditions.  User defined blocking conditions must follow the same pattern as API defined conditions.  Blocking conditions are generator functions that return True or False.  They must be infinite loops, so they never throw a StopIteration exception.  The initial call to the function can take one or more arguments.  Subsequent calls to the generator _may_ take arguments (using the generator `send()` function) but must not _require_ arguments.  The scheduler will never pass arguments when testing blocking conditions.  In general, it is probably better to use global variables or passed in objects for tracking and controlling state than it is to create conditions that can take arguments in the generator calls.

User defined blocking conditions are used exactly like API blocking conditions.  They are passed into a yield within a task, in a list.

### Message API

```Message(type, source, target, message=None)```

The `Message` object is merely a container with some header data and a message.  The message element is optional, as in many cases the type can be used to convey everything necessary.

`type` - Currently only one built in type exists: QUIT.  Types are used to convey what the message is about.  In many cases, `type` may convey sufficient information to make the `message` element unnecessary.  Type values from 0 to 127 are reserved for future use, while higher numbered types are available for user defined types.  Note that `type` can also be used to communicate the format of the data passed in the `message` element.

`source` - This communicates the source task of the message.  It is essentially a "from" field.  This is critical in messages requesting data from another task, so that task will know where to send that data.  When no response is expected, and the target task does not need to know the source, this is less important, but it is probably good practice to be honest about the source anyway, just in case it is eventually needed.  This can be set to `self` or `self.name`.

`target` - This specifies the target task.  This is essentially the "to" field for the message.  This can be a direct object reference or the name of the target object.  See Basic Usage > Messages above for the pros and cons of using names versus objects. 

```MessageQueue(capacity=10)```

The `MessageQueue` object is a FIFO queue for tasks to communicate with each other.  And task with a reference to a `MessageQueue` can add messages to the queue and take messages from it.  Both pushing and popping can be done with blocking and non-blocking calls.

`capacity` - By default, the maximum number of messages allowed on the queue is 10.  If the queue is full and a task attempts to push another onto it, it will block if the blocking call is used, otherwise it will just fail.  This can be used to limit how much memory is being used keeping track of messages.

#### MessageQueue Methods

```MessageQueue.push(msg)```

This is a blocking push.  If the queue is full, this will block until the message can be added.

`msg` - The message can be any kind of data.  No destination or source needs to be specified, but messages can contain that information if necessary.

Keep in mind that blocking functions return generators that must be passed into a yield in a list.


```MessageQueue.nonblocking_push(msg)```

This is nonblocking push.  If the queue is full, this will return False.  Otherwise the message will be added to the queue and this will return True.

`msg` - The data to be put on the queue.


```MessageQueue.pop(out_buffer)```

This is a blocking pop.  If the queue is empty it will block until a message is added.  When a message is available, it will append that message to `out_buffer`.

`out_buffer` - This should be a list or some data container with an `append()` method.  When this method unblocks, the message will be deposited in this buffer.

```MessageQueue.nonblocking_pop()```

This is the nonblocking pop.  It will return a message, if there is one in the queue, or it will return None otherwise.

## Future Additions

### Mutual Exclusion

We currently have a Mutex object, but this isn't really a complete set of mutual exclusion tools.  FreeRTOS has Binary Semaphores, Counting Semaphoes, and Recursive Mutexes.  Because this uses voluntary preemption, these are not terribly high priority, as tasks can just _not yield_ during critical sections, rather than needing to use mutual exclusion.  There are still cases where mutual exclusion is necessary though.  This includes things like locking external hardware that has time consuming I/O, where we might want to yield for some time to allow the I/O to complete, without allowing other tasks to tamper with that hardware while we are waiting.  In addition, some processors have vector processing and/or floating point units that are slow enough to warrant yielding while waiting, without giving up exclusive access to those units.  The relevance of these is not clear in the context of Python, but we definitely want some kind of mutual exclusion.

In FreeRTOS, Mutexes have a priority inheritance mechanic.  By default, this is also true in pyRTOS, because blocking conditions are checked in task priority order.  Binary semaphores are effectively mutexes without priority inheritance.  How would we handle request order based locks?  I suppose we could have a queue in the semaphore that keeps track of who asked first and prioritizes in that order.  This would be significantly more expensive than priority inheritance, but it shouldn't be too hard to do.

Would spinlocks be relevant/useful in a single threaded, voluntary preemption system?

### FreeRTOS

We need to look through the FreeRTOS documentation, to see what other things a fully featured RTOS could have.

## Notes

This needs more extensive testing.  The Mutex class has not been tested.  We also need more testing on block conditions.  `sample.py` uses `wait_for_message()` twice, successfully.  `timeout()` is also tested in sample.py.

What we really need is a handful of example problems, including some for actual CircuitPython devices.  When the Trinkey RP2040 comes out, there will be some plenty of room for some solid CircuitPython RTOS example programs.  I have a NeoKey Trinkey and a Rotary Trinkey.  Neither of these have much going on, so they are really only suitable for very simple examples.

