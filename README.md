# pyRTOS


## Introduction

pyRTOS is a real-time operating system (RTOS), written in Python.  The primary goal of pyRTOS is to provide a pure Python RTOS that will work in CircuitPython.  The secondary goal is to provide an educational tool for advanced CircuitPython users who want to learn to use an RTOS.  pyRTOS should also work in MicroPython, and it can be used in standard Python as well.

pyRTOS was modeled after FreeRTOS, with some critical differences.  The biggest difference is that it uses a voluntary task preemption model, where FreeRTOS generally enforces preemption through timer interrupts.  This means there is a greater onus on the user to ensure that all tasks are well behaved.  pyRTOS also uses different naming conventions, and tasks have built in message passing.

To the best of my knowledge, aside from voluntary preemption, the task scheduling is identical to that found in FreeRTOS.  Tasks are assigned numerical priorities, the lower the number the higher the priority, and the highest priority ready task is given CPU time, where ties favor the currently running task.  Alternative scheduling algorithms may be added in the future.

## Table of Contents

[Basic Usage](#basic-usage)
- [Tasks](#tasks)
- [Notifications](#notifications)
- [Messages](#messages)
- [Error Handling](#error-handling)

[pyRTOS API](#pyrtos-api)
- [Main API](#main-api)
- [Mutual Exclusion & Synchronization](#mutual-exclusion--synchronization)

[Task API](#task-api)

[Task Block Conditions](#task-block-conditions)

[Message API](#message-api)

[OS API](#os-api)
- [Service Routines](#service-routines)

[Templates & Examples](#templates--examples)
- [Task Template](#task-template)
- [Message Handling Example Template](#message-handling-example-template)
- [Timeout & Delay Examples](#timeout--delay-examples)
- [Messages Passing Examples](#message-passing-examples)
- [Notification Examples](#notification-examples)
- [Message Queue Exmaples](#message-queue-examples)
- [Mutex Examples](#mutex-examples)
- [Service Routine Examples](#service-routine-examples)
- [Communication Setup Examples](#communication-setup-examples)

[Future Additions](#future-additions)

[Notes](#notes)

## Basic Usage

pyRTOS separates functionality into tasks.  A task is similar to a thread in a desktop operating system, except that in pyRTOS tasks cannot be migrated to other processors or cores.  This is due to limitations with CircuitPython.  In theory, though, it should be possible to write a scheduler with thread migration, for MicroPython, which does support hardware multithreading.

A simple pyRTOS program will define some task functions, wrap them in `Task` objects, and then register them with the OS using the `add_task()` API function.  Once all tasks are added, the `start()` function is used to start the RTOS.

Once started, the RTOS will schedule time for tasks, giving tasks CPU time based on a priority scheduling algorithm.  When the tasks are well behaved, designed to work together, and given the right priorities, the operating system will orchestrate them so they work together to accomplish whatever goal the program was designed for.

See sample.py for an example task and usage.

### Tasks

A pyRTOS task is composed of a `Task` object combined with a function containing the task code.  A task function takes a single argument, a reference to the `Task` object containing it.  Task functions are Python generators.  Any code before the first yield is setup code.  Anything returned by this yield will be ignored.  The main task loop should follow this yield.  This is the code that will be executed when the scheduler gives the task CPU time.

The main task loop is typically an infinite loop.  If the task needs to terminate, a return call should be used, and any teardown that is necessary should be done directly before returning.  Typically though, tasks never return.

Preemption in pyRTOS is completely voluntary.  This means that all tasks _must_ periodically yield control back to the OS, or no other task will get CPU time, messages cannot be passed between tasks, and other administrative duties of the OS will never get done.  Yields have two functions in pyRTOS.  One is merely to pass control back to the OS.  This allows the OS to reevaluate task priorities and pass control to a higher priority ready task, and it allows the OS to take care of administration like message passing, lock handling, and such.  Yields should be fairly frequent but not so frequent that the program spends more time in the OS than in tasks.  For small tasks, once per main loop may be sufficient.  For larger tasks, yields should be placed between significant subsections.  If a task has a section of timing dependent code though, do not place yields in places where they could interrupt timing critical processes.  There is no guarantee a yield will return within the required time.

Yields are also used to make certain blocking API calls.  The most common will likely be delays.  Higher priority processes need to be especially well behaved, because even frequent yields will not give lower priority processes CPU time.  The default scheduler always gives the highest priority ready task the CPU time.  The only way lower priority tasks _ever_ get time, is if higher priority tasks block when they do not need the CPU time.  Typically this means blocking delays, which are accomplished in pyRTOS by yielding with a timeout generator.  When the timeout generator expires, the task will become ready again, but until then, lower priority tasks will be allowed to have CPU time.  Tasks can also block when waiting for messages or mutual exclusion locks.  In the future, more forgiving non-real-time schedulers may be available.

There are also some places tasks _should_ always yield.  Whenever a message is passed, it is placed on a local queue.  Messages in the local task outgoing queue are delivered when that task yields.  Other places where yielding is necessary for an action to resolve will be noted with the documentation on those actions.

### Notifications

Notifications are a lightweight message passing mechanic native to tasks.  When a task is created, a number of notifications can be specified.  These notifications can be used by other tasks or by Service Routines to communicate with the task.

Notifications have a state and a value.  The state is an 8-bit (signed) value used to communicate the state of the notification.  The meaning of the state is user defined, but the default values for the notification functions assume 0 means the notification is not currently active and 1 means it is active.  Notifications also have a 32 bit value (also signed), which can be used as a counter or to communicate a small amount of data.  A series of functions are provided to send, read, and otherwise interact with notifications.

A notification wait is provided as a Task Block Condition, allowing a task to wait for a notification to be set to a specific state.  This blocking wait can even be used on other tasks, to wait for a notification to be set to a particular value, for example, a task may want to send a notification, but only once that notification is inactive for the target task, and thus it might block to wait for that notification state to be set to 0, before it sends.

Notifications are designed for lightweight message passing, both when full messages are not necessary and for Service Routines to communicate with tasks in a very fast and lightweight manner.  To communicate via notification, it is necessary to have a reference to the task you want to communicate with.

### Messages

Message passing mechanics are built directly into tasks in pyRTOS, in the form of mailboxes.  By default tasks are lightweight, without mailboxes, but a constructor argument can be used to give a task has its own incoming mailbox.  Messages are delivered when the currently running task yields.  This message passing system is fairly simple.  Each message has a single sender and a single recipient.  Messages also have a type, which can be pyRTOS.QUIT or a user defined type (see sample.py).  User defined types start with integer values of 128 and higher.  Types below 128 are reserved for future use by the pyRTOS API.  Messages can also contain a message, but this is not required.  If the type field is sufficient to convey the necessary information, it is better to leave the message field empty, to save memory.  The message field can contain anything, including objects and lists.  If you need to pass arguments into a new task that has a mailbox, one way to do this is to call `deliver()` on the newly created task object, with a list or tuple of arguments.   This will add the arguments to the task's mailbox, allowing it to access the arguments during initialization.

Checking messages is a critical part of any task that may receive messages.  Unchecked mailboxes can accumulate so many messages that your system runs out of memory.  If your task may receive messages, it is important to check the mailbox every loop.  Also be careful not to send low priority tasks too many messages without periodically blocking all higher priority tasks, so they can have time to process their messages.  If a task that is receiving messages never gets CPU time, that is another way to run out of memory.

Messages can be addressed with a reference to the target task object or with the name of the object.  Names can be any sort of comparable data, but numbers are the most efficient, while strings are the most readable.  Object reference addressing _must_ target an object that actually exists, otherwise the OS will crash.  Also note that keeping references of terminated tasks will prevent those tasks from being garbage collected, creating a potential memory leak.  Object references are the _fastest_ message addressing method, and they may provide some benefits when debugging, but its up to the user to understand and avoid the associated hazards.  Name addressing is much safer, however messages addressed to names that are not among the existing tasks will silently fail to be delivered, making certain bugs harder to find.  In addition, because name addresses require finding the associated object, name addressed messages will consume significantly more CPU time to deliver.

sample.py has several examples of message passing.

### Error Handling

The error handling philosophy of pyRTOS is: Write good code.  The OS operates on the assumption that the user will write good code that does not cause issues for the OS.  If this assumption is broken, the OS _will_ crash when it comes across the broken elements, and it probably will not give you very meaningful error messages.  For example, attempting to send a notification to a `Task` that does not have notifications will cause a crash, with a message about the `Task` object having no `notifications` attribute (which is actually somewhat meaningful, in this particular case...).

pyRTOS is designed to be used with CircuitPython, on devices that may have _very_ limited resources.  Adding OS level error handling would require significantly more code, using more flash and RAM space, as well as requiring more processing.  This is unacceptable.  As such, we will _not_ be adding OS error handling code to gracefully handle OS exceptions caused by incorrect use of the OS.  We will also not add special OS exceptions to throw when errors occur, nor will we add preemptive error detection.  These are all expensive, requiring significantly more code and processing time.  This means that errors that occur within the OS may not produce high quality error messages.  Users are encouraged to _write good code_, so that errors in the OS do not occur, and barring that, users can add error handling in their own code (but note that we do not condone writing poor code and then covering up the errors with error handling).  Please do not file issues for crashes caused by failures to use the APIs provided correctly.  Instead, fix your own code.

That said, if there is a bug in the OS itself, please _do_ file an issue.  Users should not have to work around bugs in pyRTOS.  We apply the same standard, "Write good code" to ourselves, and if we have failed to do that, please let us know, so we can fix it.  If you are having a crash, and you are not sure where the error is occurring, please do your best to check your own code first, and if you cannot find the bug in your own code, feel free to file an issue.  We will do our best to track down the issue, as we have time (at the time of writing, this is a one man operation, and I am not getting paid for this, so it will likely not be immediate).  Do not be offended if we find the error in your code and inform you of that.  If the error is on our end, we will do our best to fix it in a timely manner (but again, one man team working for free, so no promises; this _is_ open source, so if it is urgent, please consider fixing it yourself).

Similarly, if you find it difficult to correctly use the APIs, because the documentation is lacking or poorly written, please do file an issue, and we will try to improve it.  Our philosophy of "Write good code" also applies to our documentation.

If this sounds harsh, we sincerely apologize.  We understand that this is not ideal.  Unfortunately, sacrifices must be made when working on systems with extremely limited resources.  Limited flash means our code has to be very small.  Limited RAM means we are limited in what we can keep track of.  Limited processing power means we have to weigh the value of every command we issue.  The purpose of an OS is to facilitate the tasks _the user_ deems important, and the more resources the OS uses, the fewer resources are available for the user's tasks.  Given such limited resources, keeping the OS as small and streamlined as possible takes precedence over error handling and debugging convenience.  If your application _needs_ the error handling, and you are confident your device has the resources, you can always create a fork of pyRTOS and add error handling yourself.  pyRTOS is pretty small, and it is not terribly difficult to understand, if you are familiar with Python, so this should not be very hard.

## pyRTOS API

### Main API

**```add_task(task)```**

<ul>

This adds a task to the scheduler.  Tasks that have been created but not added will never run.  This can be useful, if you want to create a task and then add it at some time in the future, but in general, tasks are created and then added to the scheduler before the scheduler is started.

</ul><ul>

`task` - a `Task` object

</ul><ul>

Note that `add_task()` will automatically initialize any task that has not previously been initialized.  This is important to keep in mind, because initializing a task manually _after_ adding it to the scheduler may cause serious problems, if the initialization code cannot safely be run more than once.

</ul>

**```start(scheduler=None)```**

<ul>

This begins execution.  This function will only return when all tasks have terminated.  In most cases, tasks will not terminate and this will never return.  Note that this means no code after this will ever be run.

</ul><ul>

`scheduler` - When this argument is left with its default value, the default scheduler is used.  Since no other schedulers currently exist, this is really only useful if you want to write your own scheduler.  Otherwise, just call `start()` without an argument.  This should be called only after you have added all tasks.  Additional tasks can be added while the scheduler is running (within running tasks), but this should generally be avoided.  (A better option, if you need to have a task that is only activated once some condition is met, is to create the task and then immediately suspend it.  This will not prevent the initialization code from running though.  If you need to prevent initialization code from running until the task is unsuspended, you can place the first yield in the task before initialization instead of after.)

</ul>

### Mutual Exclusion & Synchronization

**```class Mutex()```**

<ul>

This is a simple mutex with priority inheritance.

</ul>

<ul>

**```Mutex.lock(task)```**

<ul>

This will attempt to acquire the lock on the mutex, with a blocking call.  Note that because this is a blocking call, the returned generator must be passed to a yield in a list, eg. `yield [mutex.lock(self)]`.

</ul>
<ul>

`task` - The task requesting the lock.

</ul>
</ul>

<ul>

**```Mutex.nb_lock(task)```**

<ul>

This nonblocking lock will attempt to acquire the lock on the mutex.  It will return `True` if the lock is successfully acquired, otherwise it will immediately return `False`.

</ul>
<ul>

`task` - The task requesting the lock.

</ul>
</ul>

<ul>

**```Mutex.unlock()```**

<ul>

Use this to release the lock on the mutex.  If the mutex is not locked, this will have no effect.  Note that there is no guard to prevent a mutex from being unlocked by some task other than the one that acquired it, so it is up to the user to make sure a mutex locked in one task is not accidentally unlocked in some other task.

</ul>
</ul>

**```class BinarySemaphore()```**

<ul>

This is another simple mutex, but unlike `Mutex()`, it uses request order priority.  Essentially, this is a first-come-first-served mutex.

</ul>

<ul>

**```BinarySemaphore.lock(task)```**

<ul>

This will attempt to acquire the lock on the mutex, with a blocking call.  Note that because this is a blocking call, the returned generator must be passed to a yield in a list, eg. `yield [mutex.lock(task)]`.

</ul>
<ul>

`task` - The task requesting the lock.

</ul>
</ul>

<ul>

**```BinarySemaphore.nb_lock(task)```**

<ul>

This nonblocking lock will attempt to acquire the lock on the mutex.  It will return `True` if the lock is successfully acquired, otherwise it will immediately return `False`.

</ul>
<ul>

`task` - The task requesting the lock.

</ul>
</ul>

<ul>

**```BinarySemaphore.unlock()```**

<ul>

Use this to release the lock on the mutex.  If the mutex is not locked, this will have no effect.  Note that there is no guard to prevent a `BinarySemaphore()` from being unlocked by some task other than the one that acquired it, so it is up to the user to make sure a binary semaphore locked in one task is not accidentally unlocked in some other task.  When this is called, if there are other tasks waiting for this lock, the first of those to have requested it will acquire the lock.

</ul>
</ul>

### Task API

**```class Task(func, priority=255, name=None, notifications=None, mailbox=False)```**

<ul>

Task functions must be wrapped in `Task` objects that hold some context data.  This object keeps track of task state, priority, name, blocking conditions, and ingoing and outgoing message queues.  It also handles initialization, transition to blocking state, and message queues.  The Task object also provides some utility functions for tasks.

</ul><ul>

`func` - This is the actual task function.  This function must have the signature `func_name(self)`, and the function must be a generator.  The `self` argument is a reference to the `Task` object wrapping the function, and it will be passed in when the task is initialized.  See sample.py for an example task function.

</ul><ul>

`priority` - This is the task priority.  The lower the value, the higher priority the task.  The range of possible values depends on the system, but typically priority values are generally kept between 0 and 8 to 32, depending on the number of tasks.  The default of 255 is assumed to be far lower priority than any sane developer would ever use, making the default the lowest possible priority.  Normally, each task should have a unique priority.  If multiple tasks have the same priority, and no higher priority task is ready, whichever is already running will be treated as the higher priority task so long as it remains the running task.  Tasks may be given the same priority, if this behavior is useful.

</ul><ul>

`name` - Naming tasks can make message passing easier.  See Basic Usage > Messages above for the pros and cons of using names.  If you do need to use names, using integer values will use less memory and give better performance than strings, but strings can be used for readability, if memory and performance are not an issue.

</ul><ul>

`notifications` - This sets the number of notifications a task has.  By default, tasks are lightweight and have no notifications.  Attempting to interact with notifications when this is not set will cause a crash, and attempting to access notifications above the number that exist will also cause a crash.

</ul><ul>

`mailbox` - When set to true, the task is given a mailbox that can be accessed with `Task.deliver()`, `Task.recv()`, and `Task.message_count()`.  When set to False (the default), the task cannot receive messages (and attempting to send the task messages will crash the OS), but it can still use `Task.send()` to send messages to other tasks.

</ul>

<ul>

**```Task.initialize()```**

<ul>

This will initialize the task function, to obtain the generator and run any setup code (code before the first yield).  Note that this passes `self` into the task function, to make the following methods of `Task` available to the task.  This can be run explicitly.  If it is not, it will be run when the task is added to the scheduler using `add_task()`.  In most cases, it is not necessary to manually initialize tasks, but if there are strict ordering and timing constraints between several tasks, manual initialization can be used to guarantee that these constraints are met.  If a task is manually initialized, `add_task()` will not attempt to initialize it again.

</ul>
</ul>

<ul>

**```Task.notify_set_value(index=0, state=1, value=0)```**

<ul>

This sets a notification state and value.  By default, this sets notification 0 to state 1 and value 0.  The main use case for this is when a notification needs to provide some data to the task, for example an input sampled by an ADC or states of an array of buttons or digital pins.

</ul><ul>

`index` - The index of the notification to be set.  If the task only has one notification, this argument can be omitted (as the default index is 0).

</ul><ul>

`state` - The new state value of the notification.  A state of 0 means the notification is inactive.  A state of 1 means the notification is active and needs attention, which is why 1 is the default value.  Aside from default values, the state value actually has no special meaning to pyRTOS, so if needed, the state value can be treated as having whatever meaning is desired.  This is a signed byte type, and thus it can take a value anywhere in the range 127 to -128.

</ul><ul>

`value` - The value to set the notification to.  The meaning of the value is purely user defined.  It can be used as a counter, to keep track of how many times a given notification has been sent or as a data field to send integer data up to 32 bits.  This allows the sender to provide anything from temperature data to one pixel of 24 or 32 bit color data through a notification.  As with state, this is a signed type.

</ul>
</ul>

<ul>

**```Task.notify_inc_value(index=0, state=1, step=1)```**

<ul>

Similar the `Task.notify_set_value()`, this increments the value instead of setting it.  If the value of this notification is being used to keep track of how many notifications of this type have been received, use this to send the notification.  (See `Task.notify_set_value()` for more detailed information on the first two arguments.)

</ul><ul>

`index` - The index of the notification to be set.  If the task only has one notification, this argument can be omitted (as the default index is 0).

</ul><ul>

`state` - The new state value of the notification.

</ul><ul>

`step` - The increment step for the value.  This can be set to a negative value to decrement.  The default is to increment the value by 1.

</ul>
</ul>

<ul>

**```Task.notify_get_value(index=0)```**

<ul>

Returns the value of a notification.

</ul><ul>

`index` - The index of the notification to retrieve the value of.  If the task only has one notification, this argument can be omitted (as the default index is 0).

</ul>
</ul>

<ul>

**```Task.notify_set_state(index=0, state=1)```**

<ul>

In some cases it may be desirable to send a notification while retaining the current value, or it may be necessary to change the state without changing the value.  This is especially useful in cases where the state value is used by the task to keep track of things like accesses.  For example, a state of 2 might be used to indicate that a notification has not been read, and after reading the notification, the task might change the state to 1, to indicate that it has read the notification but is not ready for it to be overwritten with a new notification.

</ul><ul>

`index` - The index of the notification to be set.  If the task only has one notification, this argument can be omitted (as the default index is 0).

</ul><ul>

`state` - The new state value of the notification.

</ul>
</ul>

<ul>

**```Task.notify_inc_state(index=0, step=1)```**

<ul>

Instead of setting the state, it may be desirable to increment it.  This can be used make a task block until it has received a particular notification a specific number of times.  It is possible to create something like a lightweight semaphore using this mechanic.  Using a Service Routine, this mechanic can also be used to wake up a task when a button or other input has been activated a specific number of times.  It is even possible to build certain types of state machines around this mechanic.

</ul><ul>

`index` - The index of the notification to be set.  If the task only has one notification, this argument can be omitted (as the default index is 0).

</ul><ul>

`step` - The increment step for the value.  This can be set to a negative value to decrement.  The default is to increment the value by 1.

</ul>
</ul>

<ul>

**```Task.notify_get_state(index=0)```**

<ul>

In some cases it may be necessary to check the state of a notification.  For example, if a notification should only be sent if the notification is inactive, this can be used to check if the state is 0.  If a program is using a state of 2 to indicate an unread notification and a 1 to indicate a read one that should be preserved, the task can use this to check the state.

</ul><ul>

`index` - The index of the notification to be set.  If the task only has one notification, this argument can be omitted (as the default index is 0).

</ul>
</ul>

<ul>

**```Task.send(msg)```**

<ul>

Put a `Message` object in the outgoing message queue.  Note that while it is possible to call this with any kind of data without an immediate exception, the message passing code in the OS will throw an exception if it cannot find a `target` member within the data, and well behaved tasks will throw an exception if there is no `type` member.  Also note that sent messages will remain in the outgoing message queue until the next yield.  Unless there is some good reason not to, it is probably a good idea to yield immediately after any message is sent.  (The exception is, if the task needs to send out messages to multiple targets before giving up the CPU, send all of the messages, then yield.)

</ul>
</ul>

<ul>

**```Task.recv()```**

<ul>

This returns the incoming message queue and clears it.  This should be called regularly by any task that messages may be sent to, to prevent the queue from accumulating so many messages that the devices runs out of memory.  Note that because messages are distributed by the OS, once a task has called this, no new messages will be added to the incoming queue until a yield has allowed some other task to run.  (This means that if this is the highest priority task, and it issues a non-blocking yield, no other task will have a chance to send a message.  Thus high priority tasks should issue blocking yields, typically timeouts, periodically, to allow lower priority tasks some CPU time.)

</ul>
</ul>

<ul>

**```Task.message_count()```**

<ul>

This returns the number of messages in the incoming queue.

</ul>

**```Task.deliver(msg)```**

<ul>

This adds a message to the incoming queue.  This should _almost_ never be called directly.  The one exception is that this can be used to pass arguments into a task, in the main thread, before the scheduler is started.  Once the scheduler is started, messages should be passed exclusively through the OS, and this should never be called directly.  Note also that a message passed this way does not need to be a message object.  If you are using this to pass in arguments, use whatever sort of data structure you want, but make sure that the task expects it.  (If you deliver your arguments to the task before initialization, you can use `self.recv()` in the initialization code to retrieve them.)

</ul>
</ul>

<ul>

**```Task.suspend()```**

<ul>

Puts the task into the suspended state.  Suspended tasks do not run while they are suspended.  Unlike blocked tasks, there are no conditions for resuming a suspended task.  Suspended tasks are only returned to a ready state when they are explicitly resumed.  Note that suspension is cheaper than blocking, because suspended tasks do not have conditions that need to be evaluated regularly.  Also note that suspending a blocked task will clear all blocking conditions.

</ul>
</ul>

<ul>

**```Task.resume()```**

<ul>

Resumes the task from a suspended state.  This can also be used to resume a blocked task.  Note that using this on a blocked task will clear all blocking conditions.  `resume()` should not be used on the running task.  Doing so will change the state to ready, telling the OS that the task is not running when it _is_ running.  Under the default scheduler, this is unlikely to cause serious problems, but the behavior of a running task that is in the ready state is undefined and may cause issues with other schedulers.

</ul>
</ul>

### Task Block Conditions

Task block conditions are generators that yield True if their conditions are met or False if they are not.  When a block condition returns True, the task blocked by it is unblocked and put into the ready state.

A task is blocked when a yield returns a list of block conditions.  When any condition in that list returns True, the task is unblocked.  This allows any blocking condition to be paired with a `timeout()` condition, to unblock it when the timeout expires, even if the main condition is not met.  For example, `yield [wait_for_message(self), timeout(5)]` will block until there is a message in the incoming message queue, but it will timeout after 5 seconds and return to ready state, even if no message arrives.

Note that blocking conditions _must_ be returned as lists, even if there is only one condition.  Thus, for a one second blocking delay, use `yield [timeout(1)]`.

**```timeout(seconds)```**

<ul>

By itself, this blocks the current task for the specified amount of time.  This does not guarantee that the task will begin execution as soon as the time has elapsed, but it does guarantee that it will not resume until that time has passed.  If this task is higher priority than the running task and all other ready tasks, then this task will resume as soon as control is passed back to the scheduler and the OS has completed its maintenance.

</ul><ul>

When combined with other blocking conditions, this will act as a timeout.  Because only one condition must be met to unblock, when this evaluates to true, the task will unblock even if other blocking conditions are not met.

</ul><ul>

`seconds` - The number of seconds, as a floating point value, to delay.

</ul>

**```timeout_ns(nanoseconds)```**

<ul>

This is exactly like `timeout()`, except the argument specifies the delay in nanoseconds.  Note that the precision of this condition is dependent on the clock speed of your CPU, in addition to the limitations affecting `timeout()`.

</ul><ul>

`nanoseconds` - The number of nanoseconds, as an integer value, to delay.

</ul>

**```delay(cycles)```**

<ul>

This delay is based on OS cycles rather than time.  This allows for delays that are guaranteed to allow a specific number of cycles for other tasks to run.  This can be especially useful in cases where it is known that a specific task will take priority during the delay and that task is doing something that will require a known number of cycles to complete.  (Note that a cycle lasts from one yield to the next, rather than going through the full loop of a task.)

</ul>

**```wait_for_message(self)```**

<ul>

This blocks until a message is added to the incoming message queue for this task.  `self` should be the `Task` object of the calling task.

</ul>

**```wait_for_notification(task, index=0, state=1)```**

<ul>

This blocks until the notification of number `index` for `task` is equal to `state`.  `task` does not necessarily have to be the caller.  This can be used to have the caller wait for another entity to send it a notification, or this can be used to have another entity wait for a notification on a particular `Task` to be set to a particular value (for example, wait for a notification to be inactive (set to 0), before sending a new notification to the same index).

</ul>

***UFunction***

<ul>

It is also possible to create your own blocking conditions.  User defined blocking conditions must follow the same pattern as API defined conditions.  Blocking conditions are generator functions that yield True or False.  They must be infinite loops, so they never throw a StopIteration exception.  The initial call to the function can take one or more arguments.  Subsequent calls to the generator _may_ take arguments (using the generator `send()` function) but must not _require_ arguments.  The scheduler will never pass arguments when testing blocking conditions.  In general, it is probably better to use global variables or passed in objects for tracking and controlling state than it is to create conditions that can take arguments in the generator calls.

</ul><ul>

User defined blocking conditions are used exactly like API blocking conditions.  They are passed into a yield, in a list.

</ul>

### Message API

**```class Message(type, source, target, message=None)```**

<ul>

The `Message` object is merely a container with some header data and a message.  The message element is optional, as in many cases the type can be used to convey everything necessary.

</ul><ul>

`type` - Currently only one built in type exists: `QUIT`.  Types are used to convey what the message is about.  In many cases, `type` may convey sufficient information to make the `message` element unnecessary.  Type values from 0 to 127 are reserved for future use, while higher values are available for user defined types.  Note that `type` can also be used to communicate the format of the data passed in the `message` element.

</ul><ul>

`source` - This is the sender of the message.  It is essentially a "from" field.  This is critical in messages requesting data from another task, so that task will know where to send that data.  When no response is expected, and the target task does not need to know the source, this is less important, but it is probably good practice to be honest about the source anyway, just in case it is eventually needed.  This can be set to `self` or `self.name`.

</ul><ul>

`target` - This specifies the target task.  This is essentially the "to" field for the message.  This can be a direct object reference or the name of the target object.  See Basic Usage > Messages above for the pros and cons of using names versus objects. 

</ul><ul>

`message` - This is the message to be passed.  By default this is `None`, because in many cases `type` is sufficient to convey the desired information.  `message` can be any kind of data or data structure.  If type is not empty, `type` may be used to communicate the structure or format of the data contained in `message`.

</ul>

**```class MessageQueue(capacity=10)```**

<ul>

The `MessageQueue` object is a FIFO queue for tasks to communicate with each other.  Any task with a reference to a `MessageQueue` can add messages to the queue and take messages from it.  Both blocking and nonblocking calls are provided for these.

</ul><ul>

`capacity` - By default, the maximum number of messages allowed on the queue is 10.  If the queue is full and a task attempts to push another onto it, it will block if the blocking call is used, otherwise it will just fail.  This can be used to limit how much memory is being used keeping track of messages.

</ul>

<ul>

**```MessageQueue.send(msg)```**

<ul>

This is a blocking send.  If the queue is full, this will block until the message can be added.

</ul><ul>

`msg` - The message can be any kind of data.  No destination or source needs to be specified, but messages can contain that information if necessary.

</ul><ul>

Keep in mind that blocking functions return generators that must be passed into a yield in a list, thus a message would be sent with `yield [queue.send(msg)]`.

</ul>
</ul>

<ul>

**```MessageQueue.nb_send(msg)```**

<ul>

This is nonblocking send.  If the queue is full, this will return False.  Otherwise the message will be added to the queue and this will return True.

</ul><ul>

`msg` - The data to be put on the queue.

</ul>
</ul>

<ul>

**```MessageQueue.recv(out_buffer)```**

<ul>

This is a blocking receive.  If the queue is empty it will block until a message is added.  When a message is available, it will append that message to `out_buffer`.

</ul><ul>

`out_buffer` - This should be a list or some list-like data container with an `append()` method.  When this method unblocks, the message will be deposited in this buffer.

</ul>
</ul>

<ul>

**```MessageQueue.nb_recv()```**

<ul>

This is the nonblocking receive.  It will return a message, if there is one in the queue, or it will return None otherwise.

</ul>
</ul>

## OS API

The OS API provides tools for extending pyRTOS.  Some things just do not make sense to use tasks to do.  Some things need higher reliability than tasks.

For the most part, messing around inside the OS is not a great idea.  While part of the pyRTOS project policy is to not break userspace within a given major version, this policy does not hold for the OS API.  So when deciding whether to use the OS API, keep in mind that you may be creating a dependency on a specific release or even commit.

### Service Routines

Service routines are OS extensions that run every OS loop.  An OS loop occurs every time a task yields.  Service routines have no priority mechanic, and they run in the order they are registered.  Registered service routines are intended to be permanent.  While it is possible to remove them, this is part of the OS implementation that may change without warning, and there is no formal mechanic for removing a service routine.  Likewise, while service routines can technically be added from within tasks, it is generally better practice to add them in the main initialization code before calling `pyRTOS.start()`†.  Starting service routines outside of the main initialization code may make performance problems related to the service routine extremely difficult to debug.

Service routines are simple functions, which take no arguments and return nothing.  Because they run every OS loop, service routines should be small and fast, much like ISRs in RTOSs that use real-time preemption.  Normally, service routines should also be stateless.  Service routines that need to communicate with tasks can be created with references to global `MessageQueue` or `Task` objects.  As OS extensions, it is appropriate for service routines to call `Task.deliver()` to send tasks messages, however note that creating message objects is expensive.  Sending lighter messages in `MessageQueue`s is cheaper, and future features may provide even better options.

Service routines that absolutely need internal state _can be_ created by wrapping a generator in a lambda function.  Note that this will produce much heavier service routines than normal, so this should be used sparingly and only when necessary.  To do this, first create a generator function.  The function itself can take arguments, but the yield cannot.  Ideally, there should be a single yield, within an infinite loop, that takes no arguments and returns nothing.  Each OS loop, the service routine will begin execution directly after the yield, and it will end when it gets back to the yield.  The generator must never return, or a StopIteration exception will be thrown, crashing the OS\*.  Once the generator has been created by calling the function, wrap it in a lambda function like this: `lambda: next(gen)`.  This lambda function is your service routine, which should be registered with `add_service_routine()`.

Use cases for service routines start with the kind of things ISRs are normally used for.  In CircuitPython (as of 6.3.0), there are no iterrupts.  If you need to regularly check the state of a pin normally used as an interrupt source, a service routine is a good place to do that.  Just like with an ISR, you should not handle the program business in the service routine.  Instead, the service routine should notify a task that will handle the business associated with the iterrupt.  Service routines can also be used to handle things that multiple tasks care about, to avoid the need for semaphores.  For example, if multiple tasks need network communication (generally avoid this if possible), a service routine can handle routing traffic between the network and the tasks.  Note though, that putting a large network stack in a service routine is a terrible idea that will starve your tasks of CPU time.  If you need something bigger than a very slim traffic routing routine, it should be put into a task rather than a service routine.

\* No, we will not wrap the service routine OS code in a try/except statement.  This would increase the size of the OS and make it run more slowly.  Instead, write good code and follow the instructions in this document, and no errors will ever get to the OS.

† Attempting to start a service routine in the main initialization _after_ `pyRTOS.start()` will fail, as this function does not return in normal usage and thus no code after it will ever run. 

**```add_service_routine(service_routine)```**

<ul>

This adds a service routine to the OS, to be called every OS loop.

</ul><ul>

`service_routine` - A simple function that takes no argument and returns nothing.  If necessary, this can also be a wrapped generator, however stateful service routines like this will tie up memory and take a little longer to run and thus should be used sparingly.

</ul>


## Templates & Examples

### Task Template

```
def task(self):

	# Uncomment this to get argument list passed in with Task.deliver()
	# (If you do this, it will crash if no arguments are passed in
	# prior to initialization.)
	# args = self.recv()[0]

	### Setup code here



	### End Setup code

	# Pass control back to RTOS
	yield

	# Main Task Loop
	while True:
		### Work code here



		### End Work code
		yield # (Do this at least once per loop)
```

### Message Handling Example Template


```
msgs = self.recv()
for msg in msgs:
	if msg.type == pyRTOS.QUIT:
		# If your task should never return, remove this section
		### Tear Down code here



		### End Tear Down Code
		return
	elif msg.type == TEMP:
		# TEMP is a user defined integer constant larger than 127
		# Temperature data will be in msg.message
		### Code here



		### End Code

# This will silently throw away messages that are not
# one of the specified types, unless you add an else.
```

### Timeout & Delay Examples

Delay for 0.5 seconds

`yield [pyRTOS.timeout(0.5)]`

Delay for 100 nanoseconds

`yield [pyRTOS.timeout_ns(100)]`

Delay for 10 OS cycles (other tasks must yield 10 times, unless all other tasks are suspended or blocked)

`yield [pyRTOS.delay(10)]`

### Message Passing Examples

#### Send Message

Send temperature of 45 degrees to display task (TEMP constant is set to some value > 127)

`self.send(pyRTOS.Message(TEMP, self, "display", 45))`

This message will be delivered at the next yield.

#### Read Message

Instruct hum_read task to read the humidity sensor and send back the result, when wait for a message to arrive (READ_HUM constant is set to some value > 127)

```
self.send(pyRTOS.Message(READ_HUM, self, "hum_read"))
yield [wait_for_message(self)]
```

### Message Queue Examples

#### Create MessageQueue

Create a `MessageQueue` and pass it into some newly created tasks, so it can be retrived during initialization of the tasks

```
display = pyRTOS.Task(display_task, priority=1, "display")
tsensor = pyRTOS.Task(tsensor_task, priority=2, "tsensor")

temp_queue = MessageQueue(capacity=4)

display.deliver(temp_queue)
tsensor.deliver(temp_queue)

pyRTOS.add_task(display)
pyRTOS.add_task(tsensor)
```

#### Write MessageQueue

Write the temperature to a `MessageQueue` (if the queue is full, this will block until it has room)

`yield [temp_queue.send(current_temp)]`

#### Read MessageQueue

Read the temperature from a `MessageQueue` (if the queue is empty, this will block until a message is added)

```
temp_buffer = []
yield [temp_queue.recv(temp_buffer)]

temp = temp_buffer.pop()
```

### Notification Examples

#### Example Task with Notification

Task that runs one step each time it receives a notification at index 0

```
# This task uses one notification
def task_w_notification(self):
	# No setup
	yield

	# Main Task Loop
	while True:
		self.wait_for_notification(index=0, state=1)

		# Task code here
		# self.notify_get_value(0) returns the value of notification 0


# Create task instance
task = Task(task_w_notification, notifications=1)
```

#### Set Notification with Increment

Set notification 0 to a state of 1 and increment its value as a counter

```
task.notify_inc_value(index=0, step=1)
```

#### Set Notification to Value

Set notification 0 to a state of 1 and value of 27

```
task.notify_set_value(index=0, value=27)
```

### Mutex Examples

#### Create Mutex

Create a `Mutex` and pass it into some newly created tasks

```
temp_printer = pyRTOS.Task(temp_task, priority=3, "temp_printer")
hum_printer = pyRTOS.Task(hum_task, priority=3, "hum_printer")

print_mutex = pyRTOS.Mutex()

temp_printer.deliver(print_mutex)
hum_printer.deliver(print_mutex)
```

#### Use Mutex

Use a mutex to avoid collisions when printing multiple lines of data  (Note that it should never be necessary to actually do this, since no preemption occurs without a yield.  This should only be necessary when at least one task yields _within_ the code that needs lock protection.)

```
yield [print_mutex.lock()]

print("The last five temperature readings were:")

for temp in temps:
	print(temp, "C")

print_mutex.unlock()
```

### Service Routine Examples

#### Scheduler Delay (Simple Service Routine)

When using pyRTOS within an OS, instead of as _the_ OS of an embedded microcontroller, it will likely use significantly more CPU time than expected.  This is because it assumes it is the only thing running and needs to run as fast as the hardware will allow.  While there are several ways to solve this, the simplest is probably to just create a service routine that introduces a delay to the scheduler.  The delay probably does not need to be very long to reduce the CPU time consumed by the scheduler to almost nothing (but note that if your tasks do a lot between yields, _they_ may still use a lot of CPU time).

Service routines are simple functions that do not take any arguments or return anything.  If a service routine needs outside data or communication, it will need to be done through global variables.  (More complex service routines can be made with generators, if internal state needs to be preserved.)


```
scheduler_delay = 0.001 # Scheduler delay in seconds (0.001 is 1 millisecond; adjust as needed)

# Service Routine function
def delay_sr():
	global scheduler_delay
	time.sleep(scheduler_delay)  # Don't forget to import time


pyRTOS.add_service_routine(delay_sr)  # Register service routine to run every scheduler loop
```

### Communication Setup Examples

Before tasks can communicate with each other, they have to know about each other.  Giving tasks references to other tasks can be done in a variety of ways.

#### Global Tasks

Tasks are typically going to be global variables just to start with.  This makes them automatically available to anything that can access global scope.  For this to work though, things need to be done in the correct order.  A task function cannot know about a task that does not exist yet, and a task cannot be created until the associated task function is defined.  If things are done in the right order though, this can still work.

```
# We have to create the globals before we can define the task functions
task0 = None
task1 = None

def task0_fun(self):
	global task1  # Give this task access to the task1 global variable
	# Initialization code here
	yield

	while True:
		# Task code here
		yield

def task1_fun(self):
	global task0  # Give this task access to the task0 global variable
	# Initialization code here
	yield
	
	while True:
		# Task code here
		yield
		
task0 = pyRTOS.Task(task0_fun)
task1 = pyRTOS.Task(task1_fun)

# Start tasks and then scheduler
```

#### Deliver Tasks Using Mailboxes

Tasks can be delivered to other tasks using their mailboxes.  Obviously this only works for tasks initialized with mailboxes.  Order of events is less important here, but the tasks must explicitly read their mailboxes to get the task references.  (Note that this is the accepted method for giving _any_ arguments to tasks, not just references to other tasks.)

```
def task_fun(self):
	target_task = self.recv()[0]
	yield
	
	while True:
		# Code here, including communication with target_task
		yield

task = pyRTOS.Task(task_fun, priority=3)


task.deliver(some_other_task)
```

#### Module Level Globals

If the tasks exist within a separate module, the global nature of modules can be leveraged to provide what are essentially global references to those tasks.  This can be done, simply by making the tasks global variables at the module level, and then referencing them as variables contained in the module.  This eliminates the need for using the `global` directive, however that may make the code less readable, becaues the `global` directive at the begining of a task function is a clear indicator that the task is using that global.

Excerpt from `mod_tasks.py`
```
task = pyRTOS.Task(task_fun)
```

Excert from external file
```
import mod_tasks

def task_fun(self):
	# Initialization code
	yield
	
	while True:
		# Task code
		
		# Using reference to task, without needing to declare it global
		mod_tasks.task.[etc...]
		
		yield
```



## Future Additions

### Mutual Exclusion

We currently have a Mutex object (with priority inheritance) and a Binary Semaphore object (essentially a first-come-first-served Mutex), but this isn't really a complete set of mutual exclusion tools.  FreeRTOS has Counting Semaphores and Recursive Mutexes.  Because this uses voluntary preemption, these are not terribly high priority, as tasks can just _not yield_ during critical sections, rather than needing to use mutual exclusion.  There are still cases where mutual exclusion is necessary though.  This includes things like locking external hardware that has time consuming I/O, where we might want to yield for some time to allow the I/O to complete, without allowing other tasks to tamper with that hardware while we are waiting.  In addition, some processors have vector processing and/or floating point units that are slow enough to warrant yielding while waiting, without giving up exclusive access to those units.  The relevance of these is not clear in the context of Python, but we definitely want some kind of mutual exclusion.

### FreeRTOS

We need to look through the FreeRTOS documentation, to see what other things a fully featured RTOS could have.

### Size

Because this is intended for use on microcontrollers, size is a serious concern.  The code is very well commented, but this means that comments take up a very significant fraction of the space.  We are releasing in .mpy format for Circuit Python now, which is cutting the size down to around 5KB.  Maybe we should include a source version with comments stripped out in future releases.

## Notes

This needs more extensive testing.  The Mutex class has not been tested.  We also need more testing on block conditions.  `sample.py` uses `wait_for_message()` twice, successfully.  `timeout()` is also tested in sample.py.

What we really need is a handful of example problems, including some for actual CircuitPython devices.  When the Trinkey RP2040 comes out, there will be some plenty of room for some solid CircuitPython RTOS example programs.  I have a NeoKey Trinkey and a Rotary Trinkey.  Neither of these have much going on, so they are really only suitable for very simple examples.
