#MPY_CROSS = ./mpy-cross.static-amd64-linux-6.3.0
MPY_CROSS = ./mpy-cross-linux-amd64-8.2.0-69-gfb57c0801.static

# Order matters here.  Dependencies must come
# before files that depend on them.
SOURCES = pyRTOS/task.py pyRTOS/message.py pyRTOS/scheduler.py pyRTOS/pyRTOS.py


build/pyRTOS.mpy: build/pyRTOS.py
	$(MPY_CROSS) build/pyRTOS.py -o build/pyRTOS.mpy

build/pyRTOS.py: $(SOURCES)
	cat $(SOURCES) > build/pyRTOS.py



clean:
	-rm build/*
