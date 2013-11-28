import hou
import threading
import hdefereval as hd


def startTimer():
    timer = threading.Timer(0.5, setViewport)
    timer.start()


def setViewport():
    cam = hou.node('/obj/ipr_camera')
    desk = hou.ui.curDesktop()
    tab = desk.findTabByType(hou.paneTabType.SceneViewer)
    v = tab.curViewport()
    mat = v.viewTransform()
    cam.setWorldTransform(mat)
    startTimer()


@hd.do_work_in_background_thread
def deferViewport():
    cam = hou.node('/obj/ipr_camera')
    yield
    desk = hou.ui.curDesktop()
    tab = desk.paneTabOfType(hou.paneTabType.SceneViewer)
    v = tab.curViewport()
    mat = v.viewTransform()
    if cam.worldTransform != mat:
        cam.setWorldTransform(mat)
    yield
    hd.executeDeferredAfterWaiting(deferViewport, 25)


def start():
    hd.executeDeferred(deferViewport)
