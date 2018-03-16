# -*- coding: utf-8 -*-
##################################################
#
# 文件锁类,考虑到不同爬虫使用同一文件锁的情况
#
##################################################

from os import path as os_path
from platform import system as get_os

if 'Windows' == get_os():
    import psutil
    import win32con
    import win32gui
    from filelock import FileLock
    from win32process import GetWindowThreadProcessId

    file_name = 'temp_file.lock'
    current_path = os_path.dirname(os_path.abspath(__file__))
    file_path = os_path.join(current_path, file_name)


    class FilelockUtil(object):
        """
        文件锁工具类
        """

        def __init__(self):
            self.flock = FileLock(file_path)

        def acquire(self):
            """
            文件加锁
            """
            self.flock.acquire()

        def release(self):
            """
            文件锁释放
            """
            self.flock.release()

        def _get_child_pid(self, ppid):
            """
            获取ppid的子进程ID号
            :param ppid: 父进程PID号
            :return    : 子进程PID号
            """
            pids = psutil.pids()
            for pid in pids:
                try:
                    parent_id = psutil.Process(pid).ppid()
                    if parent_id == ppid:
                        return pid
                except Exception:
                    continue
            return None

        def _get_hwnds_for_pid(self, pid):
            """
            获取对应pid进程的所有句柄
            :param pid: 进程号
            :return   : 句柄列表
            """

            def callback(hwnd, hwnds):
                if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                    _, found_pid = GetWindowThreadProcessId(hwnd)
                    if found_pid == pid:
                        hwnds.append(hwnd)
                    return True

            hwnds = []
            win32gui.EnumWindows(callback, hwnds)
            return hwnds

        def get_hwnds(self, ppid):
            """
            获取ppid的子进程句柄
            :param ppid: 父进程ID
            :return    : 句柄列表
            """
            cpid = self._get_child_pid(ppid)
            hwnds = self._get_hwnds_for_pid(cpid)
            return hwnds

        def hwnd_top_most(self, hwnds):
            """
            根据句柄置顶窗口
            :param hwnds: 句柄列表
            :return     : None
            """
            for hwnd in hwnds:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                      win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE | win32con.SWP_NOOWNERZORDER | win32con.SWP_SHOWWINDOW)

        def hwnd_not_top_most(self, hwnds):
            """
            根据句柄取消窗口的置顶
            :param hwnds: 句柄列表
            :return     : None
            """
            for hwnd in hwnds:
                win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                      win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
else:
    class FilelockUtil(object):
        pass

if __name__ == '__main__':
    fl = FilelockUtil()
    fl.hwnd_top_most(6852)
