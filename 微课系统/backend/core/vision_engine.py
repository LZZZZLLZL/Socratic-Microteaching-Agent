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
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        stats = {
            "hand_movement_score": 0,  # 手势丰富度
            "left_hand": 0,            # 左手手势
            "right_hand": 0,           # 右手手势
            "both_hands": 0,           # 双手同时
            "turn_back_frames": 0,     # 背对镜头帧数
            "movement_range": 0,       # 走动范围
            "max_hand_raise": 0,       # 最大举手高度
            "duration": 0
        }

        prev_x = None
        frame_count = 0
        error_frames = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            frame_count += 1
            # 每隔 15 帧抽样一次（10 分钟视频约抽 1200 帧）
            # 对于微格教学场景，教师动作变化慢，15 帧间隔足够捕捉关键动作
            if frame_count % 15 != 0: continue

            try:
                # 执行姿态检测
                results = self.model(frame, verbose=False, device=self.device)

                for r in results:
                    if r.keypoints is None:
                        continue
                    kpts_data = r.keypoints.data
                    if kpts_data is None or len(kpts_data) == 0:
                        continue

                    # 关键点索引: 0-鼻子, 5-左肩, 6-右肩, 7-左肘, 8-右肘, 9-左手腕, 10-右手腕
                    kpts = kpts_data[0]

                    # 1. 背对判断：如果鼻子（0）的置信度很低，但肩膀置信度高，说明在背对
                    if kpts[0][2] < 0.5 and (kpts[5][2] > 0.5 or kpts[6][2] > 0.5):
                        stats["turn_back_frames"] += 5

                    # 2. 手势分析：分别追踪左右手
                    left_up = kpts[9][2] > 0.5 and kpts[9][1] < kpts[5][1]  # 左手腕高于左肩
                    right_up = kpts[10][2] > 0.5 and kpts[10][1] < kpts[6][1]  # 右手腕高于右肩

                    if left_up and right_up:
                        stats["both_hands"] += 1
                        stats["left_hand"] += 1
                        stats["right_hand"] += 1
                    elif left_up:
                        stats["left_hand"] += 1
                    elif right_up:
                        stats["right_hand"] += 1

                    if left_up or right_up:
                        stats["hand_movement_score"] += 1
                        # 记录抬手高度（手腕到肩膀的垂直距离）
                        wrist_y = min(kpts[9][1].item() if left_up else 9999,
                                      kpts[10][1].item() if right_up else 9999)
                        shoulder_y = min(kpts[5][1].item(), kpts[6][1].item())
                        raise_height = shoulder_y - wrist_y
                        if raise_height > stats["max_hand_raise"]:
                            stats["max_hand_raise"] = raise_height

                    # 3. 走位判断：追踪鼻子或肩膀的横向位移
                    curr_x = kpts[0][0].item()
                    if prev_x is not None:
                        stats["movement_range"] += abs(curr_x - prev_x)
                    prev_x = curr_x
            except Exception:
                error_frames += 1
                continue

        cap.release()
        
        # 计算比例
        total_seconds = frame_count / fps
        if error_frames > 0:
            print(f"[Vision] {error_frames} 帧处理出错已跳过")
        movement_val = round(stats["movement_range"], 1)
        total_gestures = stats["left_hand"] + stats["right_hand"]
        # 手势幅度等级: 综合频率 + 高度
        freq = stats["hand_movement_score"] / max(total_seconds, 1)
        if freq > 1.0 and stats["max_hand_raise"] > 30:
            gesture_level = "活跃"
        elif freq > 0.3:
            gesture_level = "适度"
        else:
            gesture_level = "偏少"
        # 左右均衡度 (0~100, 越接近50越均衡)
        if total_gestures > 0:
            balance = round(min(stats["left_hand"], stats["right_hand"]) / total_gestures * 100)
        else:
            balance = 50
        return {
            "back_ratio": round(stats["turn_back_frames"] / frame_count, 2) if frame_count > 0 else 0,
            "gesture_intensity": stats["hand_movement_score"],
            "gesture_level": gesture_level,
            "hand_balance": balance,
            "both_hands_ratio": round(stats["both_hands"] / max(stats["hand_movement_score"], 1), 2),
            "is_stiff": movement_val < 50,
            "movement_range": movement_val,
            "total_duration": round(total_seconds, 1)
        }

vision_analyzer = VisionAnalyzer()