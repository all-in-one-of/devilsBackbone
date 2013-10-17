import hou
import threading
import toolutils as ut
import hdefereval as hd


def startTimer():
    timer = threading.Timer(0.5, setViewport)
    timer.start()


def setViewport():
    cam = hou.node('/obj/ipr_camera')
    mat = ut.sceneViewer().curViewport().viewTransform()
    cam.setWorldTransform(mat)
    startTimer()


def deferViewport():
    cam = hou.node('/obj/ipr_camera')
    mat = ut.sceneViewer().curViewport().viewTransform()
    if cam.worldTransform != mat:
        cam.setWorldTransform(mat)
    hd.executeDeferredAfterWaiting(deferViewport, 25)
