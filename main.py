import sys
import os
import random

from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QLabel, QMenu
from PySide6.QtGui import QPixmap, QPainter, QColor, QMovie
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImageReader

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
        self.black_outline_width = 1

        # =========================
        # 3. 状态
        # =========================
        self.selected = False

        self.drag_position = QPoint()
        self.is_dragging = False

                # 区分单击与拖动
        self.press_position = QPoint()
        self.drag_started = False

        # 保存静态图片
        self.static_pixmap = self.original_pixmap

        # GIF 播放状态
        self.gif_playing = False
        self.last_gif_frame = -1

        self.movie = QMovie(self)
        self.movie.setFileName(resource_path("assets/pet.gif"))
        self.gif_size = QImageReader(resource_path("assets/pet.gif")).size()
        self.movie.frameChanged.connect(self.update_gif_frame)
        self.movie.finished.connect(self.restore_static_pet)
        self.movie.error.connect(self.on_gif_error)

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
        white_width = self.outline_width
        total_width = white_width + self.black_outline_width

        result = QPixmap(
            pixmap.width() + total_width * 2,
            pixmap.height() + total_width * 2
        )
        result.fill(Qt.transparent)

        def make_silhouette(color):
            silhouette = QPixmap(pixmap.size())
            silhouette.fill(Qt.transparent)

            painter = QPainter(silhouette)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(
                QPainter.CompositionMode_SourceIn
            )
            painter.fillRect(silhouette.rect(), color)
            painter.end()

            return silhouette

        black = make_silhouette(QColor(0, 0, 0))
        white = make_silhouette(QColor(255, 255, 255))

        painter = QPainter(result)

        # 先画外层黑色，再画内层白色
        for silhouette, radius in (
            (black, total_width),
            (white, white_width),
        ):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    painter.drawPixmap(
                        total_width + dx,
                        total_width + dy,
                        silhouette
                    )

        # 最后覆盖原图
        painter.drawPixmap(total_width, total_width, pixmap)
        painter.end()

        return result

    def play_gif_once(self):
        # 正在播放时，重复点击不打断动画
        if self.gif_playing:
            return

        if not self.movie.isValid():
            print("GIF 加载失败，请检查 assets/pet.gif")
            return

        self.movie.stop()
        self.last_gif_frame = -1
        self.gif_playing = True
        self.movie.start()

    def update_pet_size(self):
        target_height = max(
            1,
            round(
                self.current_width
                * self.static_pixmap.height()
                / self.static_pixmap.width()
            )
        )

        # 无论显示 PNG 还是 GIF，都预留相同的画布宽度
        gif_width = self.current_width
        if self.gif_size.isValid():
            gif_width = round(
                target_height
                * self.gif_size.width()
                / self.gif_size.height()
            )

        # 根据当前素材第一帧，向右补偿约 35 个原图像素
        gif_offset = 0
        if self.gif_size.isValid():
            gif_offset = round(
                35 * target_height / self.gif_size.height()
            )

        # 始终保留描边空间，选中时也不改变窗口尺寸
        padding = self.outline_width + self.black_outline_width

        canvas_width = (
            max(
                self.current_width,
                gif_width + 2 * abs(gif_offset)
            )
            + padding * 2
        )
        canvas_height = target_height + padding * 2

        if self.gif_playing:
            pixmap = self.original_pixmap.scaledToHeight(
                target_height,
                Qt.SmoothTransformation
            )
        else:
            pixmap = self.original_pixmap.scaledToWidth(
                self.current_width,
                Qt.SmoothTransformation
            )

        if self.selected:
            pixmap = self.add_white_outline(pixmap)

        canvas = QPixmap(canvas_width, canvas_height)
        canvas.fill(Qt.transparent)

        # 图片在固定画布内居中、底部对齐
        x = (canvas_width - pixmap.width()) // 2
        if self.gif_playing:
            x += gif_offset

        bottom_padding = 0 if self.selected else padding
        y = canvas_height - bottom_padding - pixmap.height()

        painter = QPainter(canvas)
        painter.drawPixmap(x, y, pixmap)
        painter.end()

        # 只有滚轮缩放等导致画布大小变化时才调整窗口
        if self.size() != canvas.size():
            old_rect = self.geometry()
            anchor_x = old_rect.x() + old_rect.width() // 2
            anchor_y = old_rect.y() + old_rect.height()

            self.setGeometry(
                anchor_x - canvas_width // 2,
                anchor_y - canvas_height,
                canvas_width,
                canvas_height
            )

        self.setPixmap(canvas)

    def update_gif_frame(self, frame_number):
        if not self.gif_playing:
            return

        # 帧号回到开头，说明第一遍已经完整播放完毕
        if frame_number <= self.last_gif_frame:
            self.restore_static_pet()
            return

        self.last_gif_frame = frame_number

        frame = self.movie.currentPixmap()
        if not frame.isNull():
            self.original_pixmap = frame
            self.update_pet_size()

    def restore_static_pet(self):
        self.gif_playing = False
        self.movie.stop()
        self.last_gif_frame = -1

        self.original_pixmap = self.static_pixmap
        self.update_pet_size()

    def on_gif_error(self, error):
        print("GIF 播放失败：", self.movie.lastErrorString())
        self.restore_static_pet()

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
            if not self.selected:
                self.selected = True
                self.update_pet_size()

            self.setFocus()

            self.press_position = event.globalPosition().toPoint()
            self.drag_position = (
                self.press_position
                - self.frameGeometry().topLeft()
            )

            self.is_dragging = True
            self.drag_started = False

        elif event.button() == Qt.RightButton:
            self.show_menu(event.globalPosition().toPoint())
    # =========================
    # 鼠标拖动
    # =========================
    def mouseMoveEvent(self, event):
        if (
            self.is_dragging
            and event.buttons() & Qt.LeftButton
        ):
            current_position = event.globalPosition().toPoint()
            distance = (
                current_position - self.press_position
            ).manhattanLength()

            # 容许单击时手指轻微抖动
            if distance >= QApplication.startDragDistance():
                self.drag_started = True

            if self.drag_started:
                self.move(current_position - self.drag_position)

    # =========================
    # 鼠标松开
    # =========================
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            distance = (
                event.globalPosition().toPoint()
                - self.press_position
            ).manhattanLength()

            was_click = (
                self.is_dragging
                and not self.drag_started
                and distance < QApplication.startDragDistance()
            )

            self.is_dragging = False
            self.drag_started = False

            if was_click:
                self.play_gif_once()

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