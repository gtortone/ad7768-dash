from celery import Celery
from lib.ad7768 import DataFormat, Filter, DecRate
import lib.ad7768 as ad7768

#queue = Celery('sched.tasks', broker='redis://localhost', backend='redis://localhost')
queue = Celery('sched.tasks', broker='redis://localhost', backend='db+sqlite:///results.db')

ad = ad7768.AD7768_iio("ip:enc01")
ad.init()
print("AD7768 init OK")

@queue.task
def selectChannel(ch):
    ad.selectChannel(ch)

@queue.task
def getChannel():
    return ad.getChannel()

@queue.task
def setLength(n):
    ad.setLength(n)

@queue.task
def getLength():
    return ad.getLength()

@queue.task
def setFilter(flt, drate):
    ad.setFilter(flt, drate)

@queue.task
def setMasterClockDiv(div):
    ad.setMasterClockDiv(div)

@queue.task
def setModulatorDiv(group, div):
    ad.setModulatorDiv(group, div)

@queue.task
def readRegister(reg):
    return ad.readRegister(reg)

@queue.task
def writeRegister(reg, value):
    ad.writeRegister(reg,value)

@queue.task
def getWaveform(*args, fmt=DataFormat.RAW):         # for celery.chord arguments
    return ad.getWaveform(fmt=fmt)

@queue.task
def storeWaveform():
    ad.storeWaveform()

@queue.task
def fetchWaveform(fmt=DataFormat.RAW):
    return ad.fetchWaveform(fmt=fmt)
