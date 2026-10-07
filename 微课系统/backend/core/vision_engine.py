import cv2
from ultralytics import YOLO
import torch

class VisionAnalyzer:
    def __init__(self):
        # 1. 自动调用你的 3070 Ti
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[Vision] 视觉引擎初始化 | 运行设备: {self.device}")

        # 加载 YOLOv8 姿态估计模型 (初次运行会自动下载，约 12MB)
        self.model = YOLO('yolov8n-pose.pt').to(self.device)

    def analyze_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920

        # 每 0.5 秒抽一帧，适配不同帧率的视频
        sample_interval = max(1, round(fps * 0.5))

        stats = {
            "hand_movement_score": 0,
            "left_hand": 0,
            "right_hand": 0,
            "both_hands": 0,
            "turn_back_frames": 0,
            "movement_range": 0,
            "max_hand_raise": 0,
            "duration": 0
        }

        prev_x = None
        frame_count = 0
        error_frames = 0
        timeline = []  # 逐采样点的时间轴数据

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % sample_interval != 0:
                continue

            timestamp = round(frame_count / fps, 1)
            is_back = False
            has_gesture = False

            try:
                results = self.model(frame, verbose=False, device=self.device)

                for r in results:
                    if r.keypoints is None:
                        continue
                    kpts_data = r.keypoints.data
                    if kpts_data is None or len(kpts_data) == 0:
                        continue

                    # 关键点索引: 0-鼻子, 5-左肩, 6-右肩, 7-左肘, 8-右肘, 9-左手腕, 10-右手腕
                    kpts = kpts_data[0]

                    # 1. 背对判断：鼻子置信度低但肩膀置信度高 → 背对镜头
                    if kpts[0][2] < 0.5 and (kpts[5][2] > 0.5 or kpts[6][2] > 0.5):
                        stats["turn_back_frames"] += sample_interval
                        is_back = True

                    # 2. 手势分析：分别追踪左右手
                    left_up = kpts[9][2] > 0.5 and kpts[9][1] < kpts[5][1]
                    right_up = kpts[10][2] > 0.5 and kpts[10][1] < kpts[6][1]

                    if left_up and right_up:
                        stats["both_hands"] += 1
                        stats["left_hand"] += 1
                        stats["right_hand"] += 1
                        has_gesture = True
                    elif left_up:
                        stats["left_hand"] += 1
                        has_gesture = True
                    elif right_up:
                        stats["right_hand"] += 1
                        has_gesture = True

                    if left_up or right_up:
                        stats["hand_movement_score"] += 1
                        wrist_y = min(kpts[9][1].item() if left_up else 9999,
                                      kpts[10][1].item() if right_up else 9999)
                        shoulder_y = min(kpts[5][1].item(), kpts[6][1].item())
                        raise_height = shoulder_y - wrist_y
                        if raise_height > stats["max_hand_raise"]:
                            stats["max_hand_raise"] = raise_height

                    # 3. 走位判断：追踪鼻子横向位移，归一化后累加
                    #
                    # norm_distance 累计的是「位移路径总长 ÷ 画面宽度」，
                    # 它是一个无量纲的路径长度（0.5 表示横穿了半个画面宽的距离总和）。
                    # 注意：该值会随视频时长增长，因此最终展示与判定时
                    # 一律换算成「每分钟位移」再使用（见下方 movement_rate）。
                    #
                    # ultralytics 的 keypoints.data 返回原图像素坐标，
                    # 因此这里用 frame_width 归一化是正确的。
                    curr_x = kpts[0][0].item()
                    if prev_x is not None:
                        stats["movement_range"] += abs(curr_x - prev_x) / frame_width
                    prev_x = curr_x

            except Exception as e:
                error_frames += 1
                print(f"[Vision] 第 {frame_count} 帧处理异常: {e}")
                continue

            # 记录该采样点的时间轴事件
            timeline.append({
                "t": timestamp,
                "back": is_back,
                "gesture": has_gesture
            })

        cap.release()

        # 计算比例
        total_seconds = frame_count / fps
        if error_frames > 0:
            print(f"[Vision] {error_frames}/{frame_count // sample_interval} 抽样帧处理出错已跳过")

        # ── 位移指标 ──
        # stats["movement_range"] 是「位移路径总长 ÷ 画面宽度」，会随时长增长，
        # 直接展示既不稳定也无法跨视频比较。因此统一换算为：
        #   movement_rate = 每分钟位移路径长度（单位：画面宽度 / 分钟）
        # 这个值对时长不敏感，3 分钟和 30 分钟的课可以放在同一把尺子上衡量。
        total_minutes = max(total_seconds / 60.0, 1e-6)
        movement_rate = stats["movement_range"] / total_minutes

        # 判定阈值基于「每分钟」而不是全程累计
        #   < 0.8 画面宽 / 分钟 → 站位偏固定
        #   >= 0.8              → 站位灵活
        MOVEMENT_STIFF_RATE = 0.8

        is_stiff = (movement_rate < MOVEMENT_STIFF_RATE) and total_seconds > 30
        movement_val = round(movement_rate, 2)

        total_gestures = stats["left_hand"] + stats["right_hand"]

        freq = stats["hand_movement_score"] / max(total_seconds, 1)
        if freq > 1.0 and stats["max_hand_raise"] > 30:
            gesture_level = "活跃"
        elif freq > 0.3:
            gesture_level = "适度"
        else:
            gesture_level = "偏少"

        if total_gestures > 0:
            balance = round(min(stats["left_hand"], stats["right_hand"]) / total_gestures * 100)
        else:
            balance = 50

        # ── 教态智能预警 ──
        alerts = []
        back_ratio = stats["turn_back_frames"] / max(frame_count, 1)

        if back_ratio > 0.25:
            alerts.append({"level": "error", "msg": f"背对学生时间占比 {round(back_ratio * 100)}%，超过 25%，建议减少背对板书时间，多用侧身或半转身"})
        elif back_ratio > 0.15:
            alerts.append({"level": "warning", "msg": f"背对学生时间占比 {round(back_ratio * 100)}%，建议控制在 15% 以内"})

        if gesture_level == "偏少":
            alerts.append({"level": "info", "msg": "手势动作偏少，适当增加手势可以增强表达感染力和课堂互动感"})

        if is_stiff:
            alerts.append({"level": "info", "msg": "站位较为固定，建议在讲解不同内容时适当走动，拉近与学生的距离"})

        if balance < 30 and total_gestures > 5:
            alerts.append({"level": "info", "msg": f"左右手使用不均衡（左手 {balance}%），建议双手并用，让教态更自然"})

        if total_gestures == 0 and total_seconds > 30:
            alerts.append({"level": "warning", "msg": "全程未检测到明显手势动作，微课教学中适当的手势有助于强调重点和吸引注意力"})

        if back_ratio <= 0.15 and gesture_level in ("活跃", "适度") and not is_stiff:
            alerts.append({"level": "success", "msg": "教态整体表现良好，背对控制得当，手势丰富，站位灵活 👍"})

        return {
            "back_ratio": round(back_ratio, 2),
            "gesture_intensity": stats["hand_movement_score"],
            "gesture_level": gesture_level,
            "hand_balance": balance,
            "both_hands_ratio": round(stats["both_hands"] / max(stats["hand_movement_score"], 1), 2),
            "is_stiff": is_stiff,
            # movement_range：每分钟位移路径长度（单位：画面宽度 / 分钟）
            # 已按视频时长归一化，可直接跨视频比较，也用于 is_stiff 判定。
            "movement_range": movement_val,
            # movement_total：全程位移路径总长（画面宽度），保留原始值以便追溯
            "movement_total": round(stats["movement_range"], 2),
            "movement_unit": "画面宽度/分钟",
            "total_duration": round(total_seconds, 1),
            "timeline": timeline,
            "alerts": alerts
        }

vision_analyzer = VisionAnalyzer()
