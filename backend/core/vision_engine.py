import cv2
from ultralytics import YOLO
import torch

class VisionAnalyzer:
    def __init__(self):
        # 1. 自动调用你的 3070 Ti
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"👁️ 视觉引擎初始化 | 运行设备: {self.device}")
        
        # 加载 YOLOv8 姿态估计模型 (初次运行会自动下载，约 12MB)
        self.model = YOLO('yolov8n-pose.pt').to(self.device)

    def analyze_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        
        stats = {
            "hand_movement_score": 0,  # 手势丰富度
            "turn_back_frames": 0,     # 背对镜头帧数
            "movement_range": 0,       # 走动范围
            "duration": 0
        }
        
        prev_x = None
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            frame_count += 1
            # 每隔 5 帧抽样一次，节省 3070 Ti 算力，提高处理速度
            if frame_count % 5 != 0: continue

            # 执行姿态检测
            results = self.model(frame, verbose=False, device=self.device)
            
            for r in results:
                if r.keypoints is not None:
                    # 获取关键点坐标 (x, y, confidence)
                    # 5: 左肩, 6: 右肩, 9: 左手腕, 10: 右手腕, 0: 鼻子
                    kpts = r.keypoints.data[0] 
                    
                    # 1. 背对判断：如果鼻子（0）的置信度很低，但肩膀置信度高，说明在背对
                    if kpts[0][2] < 0.5 and (kpts[5][2] > 0.5 or kpts[6][2] > 0.5):
                        stats["turn_back_frames"] += 5
                    
                    # 2. 手势判断：手腕高于肩膀
                    if kpts[9][1] < kpts[5][1] or kpts[10][1] < kpts[6][1]:
                        stats["hand_movement_score"] += 1
                    
                    # 3. 走位判断：追踪鼻子或肩膀的横向位移
                    curr_x = kpts[0][0].item()
                    if prev_x is not None:
                        stats["movement_range"] += abs(curr_x - prev_x)
                    prev_x = curr_x

        cap.release()
        
        # 计算比例
        total_seconds = frame_count / fps
        return {
            "back_ratio": round(stats["turn_back_frames"] / frame_count, 2) if frame_count > 0 else 0,
            "gesture_intensity": stats["hand_movement_score"],
            "is_stiff": stats["movement_range"] < 50, # 如果位移太小，说明站得太僵硬
            "total_duration": round(total_seconds, 1)
        }

vision_analyzer = VisionAnalyzer()