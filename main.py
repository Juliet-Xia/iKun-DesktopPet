import sys
import os
import random

from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QLabel, QMenu
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QPoint

def resource_path(relative_path):
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)


class DesktopPet(QLabel):
    def __init__(self):
        super().__init__()

        # =========================
        # 1. 窗口设置
        # =========================
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        # =========================
        # 2. 加载坤坤图片
        # =========================
        self.original_pixmap = QPixmap(resource_path("assets/pet.png"))

        if self.original_pixmap.isNull():
            print("图片加载失败，请检查 assets/pet.png")
            sys.exit()

        self.current_width = 250

        self.min_width = 80
        self.max_width = 700

        # 白边粗细
        self.outline_width = 2

        # =========================
        # 3. 状态
        # =========================
        self.selected = False

        self.drag_position = QPoint()
        self.is_dragging = False

        # 显示图片
        self.update_pet_size()

        # 初始位置
        self.move(1000, 500)

        # =========================
        # 音频播放器
        # =========================
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()

        self.player.setAudioOutput(self.audio_output)

        # 音量 0.0 ~ 1.0
        self.audio_output.setVolume(0.8)

        # 不循环播放
        self.player.setLoops(QMediaPlayer.Loops.Once)
        
    # =========================
    # 创建白色轮廓
    # =========================
    def add_white_outline(self, pixmap):
        """
        给透明 PNG 中的人物轮廓添加细白边
        """

        w = self.outline_width

        # 创建比原图稍大的透明画布
        result = QPixmap(
            pixmap.width() + w * 2,
            pixmap.height() + w * 2
        )

        result.fill(Qt.transparent)

        # =========================
        # 制作白色人物剪影
        # =========================
        silhouette = QPixmap(pixmap.size())
        silhouette.fill(Qt.transparent)

        painter = QPainter(silhouette)

        # 先画人物
        painter.drawPixmap(0, 0, pixmap)

        # 只保留人物透明度，
        # 并把人物全部染成白色
        painter.setCompositionMode(
            QPainter.CompositionMode_SourceIn
        )

        painter.fillRect(
            silhouette.rect(),
            QColor(255, 255, 255)
        )

        painter.end()

        # =========================
        # 把白色剪影向四周偏移
        # 形成轮廓
        # =========================
        painter = QPainter(result)

        for dx in range(-w, w + 1):
            for dy in range(-w, w + 1):

                # 中心位置不用画
                if dx == 0 and dy == 0:
                    continue

                painter.drawPixmap(
                    w + dx,
                    w + dy,
                    silhouette
                )

        # 最后把原人物盖在上面
        painter.drawPixmap(
            w,
            w,
            pixmap
        )

        painter.end()

        return result
    
    # =========================
    # 更新坤坤大小
    # =========================
    def update_pet_size(self):

        pixmap = self.original_pixmap.scaledToWidth(
            self.current_width,
            Qt.SmoothTransformation
        )

        # 被选中才增加白边
        if self.selected:
            pixmap = self.add_white_outline(pixmap)

        self.setPixmap(pixmap)
        self.resize(pixmap.size())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.selected:
                self.selected = False
                self.update_pet_size()

    # =========================
    # 鼠标按下
    # =========================
    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            # 第一次点击 → 选中
            if not self.selected:
                self.selected = True
                self.update_pet_size()

            self.setFocus()

            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

            self.is_dragging = True

        elif event.button() == Qt.RightButton:

            self.show_menu(
                event.globalPosition().toPoint()
            )

    # =========================
    # 鼠标拖动
    # =========================
    def mouseMoveEvent(self, event):

        if (
            self.is_dragging
            and event.buttons() & Qt.LeftButton
        ):

            self.move(
                event.globalPosition().toPoint()
                - self.drag_position
            )

    # =========================
    # 鼠标松开
    # =========================
    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.is_dragging = False

    # =========================
    # 滚轮缩放
    # =========================
    def wheelEvent(self, event):

        if not self.selected:
            return

        old_center = self.frameGeometry().center()

        delta = event.angleDelta().y()

        if delta > 0:

            self.current_width = int(
                self.current_width * 1.1
            )

        elif delta < 0:

            self.current_width = int(
                self.current_width * 0.9
            )

        self.current_width = max(
            self.min_width,
            min(
                self.current_width,
                self.max_width
            )
        )

        self.update_pet_size()

        new_rect = self.frameGeometry()

        self.move(
            old_center.x() - new_rect.width() // 2,
            old_center.y() - new_rect.height() // 2
        )

    # =========================
    # 右键菜单
    # =========================
    def show_menu(self, position):

        menu = QMenu()

        play_action = menu.addAction("播放音频")

        stop_action = menu.addAction("停止播放")

        menu.addSeparator()

        exit_action = menu.addAction("退出坤坤")

        selected_action = menu.exec(position)

        if selected_action == play_action:
            self.play_random_audio()

        elif selected_action == stop_action:
            self.stop_audio()

        elif selected_action == exit_action:
            QApplication.quit()

    def play_random_audio(self):

        # 三个音频及其权重
        audio_files = ["sound1.mp3", "sound2.mp3", "sound3.mp3"]

        weights = [  40,   40,   20]

        # 按 40% / 40% / 20% 随机选择
        selected_audio = random.choices(
            audio_files,
            weights=weights,
            k=1
        )[0]

        audio_path = resource_path(os.path.join("assets", selected_audio))

        # 如果之前正在播放，先停掉
        self.player.stop()

        self.player.setSource(
        QUrl.fromLocalFile(audio_path)
        )

        self.player.play()

    def stop_audio(self):
        self.player.stop()

# =========================
# 主程序
# =========================

app = QApplication(sys.argv)

pet = DesktopPet()
pet.show()

sys.exit(app.exec())