import copy
import sys
import ctypes
import time
import threading
from logic import WIDTH, HEIGHT
from solarsystem import solar_system
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


def update_position(celestial_object, temp_sys, new_solar):
    celestial_object.update_position(temp_sys)
    new_solar.append(celestial_object)


def update_solar_system(system_sol: list):
    new_solar = []
    threads = []

    for celestial_object in system_sol:
        temp = copy.copy(system_sol)
        thread = threading.Thread(target=update_position, args=(celestial_object, temp, new_solar))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return new_solar

class main_application(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon("images/icon.png"))
        my_app_id = 'by_Müller_Willi.Solarsystem'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)

        self.setWindowTitle('Solarsystem')

        self.height = HEIGHT
        self.width = WIDTH
        self.full_screen = False

        self.resize(self.width, self.height)
        self.setMinimumSize(self.width, self.height)

        self.game = QLabel(self)
        self.update_game = QLabel(self)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animation)
        self.speed = 0
        self.timer.start(self.speed)

        self.day = 1
        self.zoom = 1.0
        self.solar_system = solar_system

        self.first_draw()

    def first_draw(self):
        canvas = QPixmap(self.width, self.height)
        canvas.fill(Qt.black)
        self.game.setPixmap(canvas)
        self.game.setGeometry(0, 0, self.width, self.height)

        pen = QPen()
        pen.setWidth(2)
        pen.setColor(Qt.white)

    def animation(self):
        time.sleep(0.02)
        self.update()

    def paintEvent(self, event):
        canvas = QPixmap(self.width, self.height)
        canvas.fill(QColor(0, 0, 0, 0))
        self.update_game.setPixmap(canvas)
        self.update_game.setGeometry(0, 0, self.width, self.height)

        painter_update_game = QPainter(self.update_game.pixmap())
        painter_update_game.setFont(QFont("times", 16))

        new_solar = update_solar_system(self.solar_system)

        for i in new_solar:
            color = QColor(i.color[0], i.color[1], i.color[2])
            painter_update_game.setPen(color)
            painter_update_game.setBrush(color)

            size = int(i.radius * i.SCALE_RAD * self.zoom) 
            x = int(i.x * i.SCALE * self.zoom + self.width / 2 - size // 2) 
            y = int(i.y * i.SCALE * self.zoom + self.height / 2 - size // 2)  

            painter_update_game.drawEllipse(x, y, size, size)

        self.solar_system = new_solar

        painter_update_game.setPen(Qt.white)
        painter_update_game.drawText(40, 40, f"Day: {self.day}")
        painter_update_game.drawText(40, 80, f"Zoom: {round(self.zoom, 2)}x")

        self.day += 1

    def wheelEvent(self, event):  
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom *= 1.1  
        else:
            self.zoom /= 1.1 
        self.zoom = max(0.04, min(self.zoom, 5)) 
        self.update()

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key_Escape:
            sys.exit()

        if key == Qt.Key_R:
            self.zoom = 1.0
            self.update()

        if key == Qt.Key_F11:
            if not self.full_screen:
                self.showFullScreen()
                self.full_screen = True
            else:
                self.showNormal()
                self.full_screen = False


def main():
    app = QApplication(sys.argv)
    application = main_application()
    application.show()
    sys.exit(app.exec_())


main()
