MPY_CROSS = ./mpy-cross.static-x64-windows-6.3.0.exe

# Order matters here.  Dependencies must come
# before files that depend on them.
SOURCES = pyRTOS/task.py pyRTOS/message.py pyRTOS/scheduler.py pyRTOS/pyRTOS.py


build/pyRTOS.mpy: build/pyRTOS.py
	$(MPY_CROSS) build/pyRTOS.py -o build/pyRTOS.mpy

build/pyRTOS.py: $(SOURCES)
	cat $(SOURCES) > build/pyRTOS.py



clean:
	-rm build/*