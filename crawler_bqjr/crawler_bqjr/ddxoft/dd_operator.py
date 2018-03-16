# -*- coding: utf-8 -*-

"""
    需要注意的问题。
    若同时开启两个脚本，第二个脚本会调用失败。驱动会加载错误。
    这个错误可以被Python捕获。

    网络错误会成功启动脚本，但是按键不会有效果，需要重新启动脚本。
    这个错误无法被Python捕获。
    这个错误可以用dd_dll的内置函数测试是否加载成功来确定。
"""

from platform import system as get_os

if 'Windows' == get_os():
    import win32gui
    from ctypes import *
    from os import path as os_path
    from win32process import GetWindowThreadProcessId

    import psutil
    from filelock import FileLock, Timeout as LockTimeout

    this_dir = os_path.dirname(os_path.abspath(__file__))

    path = "temp_file.lock"
    flock = FileLock(path)


    def file_lock(func):
        """
        文件锁装饰器
        :param func:
        :return:
        """

        def _handle(*args, **kwargs):
            try:
                _flock = FileLock(path)
                _flock.acquire(timeout=15)
            except LockTimeout:
                pass
            else:
                try:
                    return func(*args, **kwargs)
                finally:
                    _flock.release()

        return _handle


    def get_hwnds_for_pid(pid):
        """
        获取对应PID进程的所有句柄
        :param pid:
        :return:
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


    def get_child_pid(ppid):
        """
        通过父进程ID获取子进程ID
        :param ppid:
        :return:
        """
        pids = psutil.pids()
        for pid in pids:
            try:
                parent_id = psutil.Process(pid).ppid()
                if parent_id == ppid:
                    return pid
            except Exception:
                continue


    def get_focus(pid):
        """
        将进程设置为当前窗口
        :param pid:
        :return:
        """
        # print("PPID:" + str(pid))
        curr_pid = get_child_pid(pid)
        # print("PID:" + str(curr_pid))
        for hwnd in get_hwnds_for_pid(curr_pid):
            # print(hwnd, "=>", win32gui.GetWindowText(hwnd))
            win32gui.SetForegroundWindow(hwnd)


    class Ddxoft(object):
        def __init__(self, pid=None):
            self.dll_path = os_path.join(this_dir, 'dd71800x64.64.dll')
            self.dd_dll = windll.LoadLibrary(self.dll_path)
            self.pid = pid

            # DD虚拟码，可以用DD内置函数转换。
            self.vk = {'5': 205, 'c': 503, 'n': 506, 'z': 501, '3': 203, '1': 201, 'd': 403, '0': 210,
                       'l': 409, '8': 208, 'w': 302, 'u': 307, '4': 204, 'e': 303, '[': 311, 'f': 404,
                       'y': 306, 'x': 502, 'g': 405, 'v': 504, 'r': 304, 'i': 308, 'a': 401, 'm': 507,
                       'h': 406, '.': 509, ',': 508, ']': 312, '/': 510, '6': 206, '2': 202, 'b': 505,
                       'k': 408, '7': 207, 'q': 301, "'": 411, '\\': 313, 'j': 407, '`': 200, '9': 209,
                       'p': 310, 'o': 309, 't': 305, '-': 211, '=': 212, 's': 402, ';': 410}
            # 需要组合shift的按键。
            self.vk2 = {'"': "'", '#': '3', ')': '0', '^': '6', '?': '/', '>': '.', '<': ',', '+': '=',
                        '*': '8', '&': '7', '{': '[', '_': '-', '|': '\\', '~': '`', ':': ';', '$': '4',
                        '}': ']', '%': '5', '@': '2', '!': '1', '(': '9'}

        def __enter__(self):
            flock.acquire()
            try:
                if self.pid:
                    get_focus(self.pid)
            except Exception:
                pass
            finally:
                return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            flock.release()

        # 按键按下弹起
        def down_up(self, key):
            self.dd_dll.DD_key(self.vk[key], 1)
            self.dd_dll.DD_key(self.vk[key], 2)

        # 键盘
        def dd_keyboard(self, key):
            # 500是shift键码。
            if key.isupper():
                # 如果是一个大写，按下抬起。
                self.dd_dll.DD_key(500, 1)
                self.down_up(key.lower())
                self.dd_dll.DD_key(500, 2)

            elif key in '~!@#$%^&*()_+{}|:"<>?':
                self.dd_dll.DD_key(500, 1)
                self.down_up(self.vk2[key])
                self.dd_dll.DD_key(500, 2)
            else:
                self.down_up(key)

        # tab键
        def dd_tab(self):
            self.dd_dll.DD_key(300, 1)
            self.dd_dll.DD_key(300, 2)

        # 鼠标移动到屏幕左上为原点距离x,y位置
        def dd_move(self, x, y):
            self.dd_dll.DD_mov(x, y)

        # 鼠标左键点击
        def dd_left_mouse_click(self):
            self.dd_dll.DD_btn(1)
            self.dd_dll.DD_btn(2)
else:
    class Ddxoft(object):
        def __init__(self, pid=None):
            pass

# 测试按键。
if __name__ == '__main__':
    test = Ddxoft()
    for i in '18323680105':
        test.dd_keyboard(i)
