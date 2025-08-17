import socket
import numpy as np
import cv2
import signal
import sys
import mediapipe as mp
import struct
import time

HOST = "0.0.0.0"
PORT = 9999

# 全局变量用于清理
server = None
conn = None



# MediaPipe 手掌检测
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.3,  # 降低检测置信度阈值
    min_tracking_confidence=0.3,   # 降低跟踪置信度阈值
    model_complexity=1             # 使用更复杂的模型
)

def cleanup():
    """清理socket连接"""
    global server, conn
    if conn:
        try:
            conn.close()
            print("连接已关闭")
        except:
            pass
    if server:
        try:
            server.close()
            print("服务器已关闭")
        except:
            pass
    if hands:
        hands.close()

def signal_handler(sig, frame):
    """信号处理器，用于优雅退出"""
    print("\n正在退出...")
    cleanup()
    sys.exit(0)

def detect_hands_and_calculate_distance(rgb_image, depth_image):
    """检测手掌并计算距离"""
    # 转换BGR到RGB
    rgb_rgb = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)
    
    # 检测手掌
    results = hands.process(rgb_rgb)
    
    hand_distances = []
    
    # 添加调试信息
    if results.multi_hand_landmarks:
        print(f"检测到 {len(results.multi_hand_landmarks)} 个手掌")
        
        for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
            # 获取手掌中心点（手腕）
            wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            
            # 转换到图像坐标
            h, w = rgb_image.shape[:2]
            wrist_x = int(wrist.x * w)
            wrist_y = int(wrist.y * h)
            
            print(f"手掌 {i+1} 位置: ({wrist_x}, {wrist_y})")
            
            # 确保坐标在有效范围内
            print(f"手掌 {i+1} 坐标检查: RGB坐标({wrist_x}, {wrist_y}), 深度图尺寸{depth_image.shape}")
            
            # 计算对应的深度图坐标
            depth_x = int(wrist_x * depth_image.shape[1] / rgb_image.shape[1])
            depth_y = int(wrist_y * depth_image.shape[0] / rgb_image.shape[0])
            
            print(f"手掌 {i+1} 映射到深度图坐标: ({depth_x}, {depth_y})")
            
            if 0 <= depth_x < depth_image.shape[1] and 0 <= depth_y < depth_image.shape[0]:
                # 从雷达的相应位置获取深度值
                depth_value = depth_image[depth_y, depth_x]
                
                print(f"手掌 {i+1} 雷达深度值: {depth_value}")
                
                # 过滤无效深度值
                if not np.isnan(depth_value) and not np.isinf(depth_value) and depth_value > 0:
                    hand_distances.append({
                        'distance': depth_value,
                        'position': (wrist_x, wrist_y),
                        'depth_position': (depth_x, depth_y)
                    })
                    print(f"手掌 {i+1} 距离: {depth_value:.3f}m - 从雷达位置({depth_x}, {depth_y})获取成功")
                else:
                    print(f"手掌 {i+1} 雷达深度值无效: {depth_value}")
                    # 尝试获取周围点的深度值
                    print("尝试获取雷达周围点的深度值...")
                    valid_neighbors = []
                    for dy in [-3, -2, -1, 0, 1, 2, 3]:
                        for dx in [-3, -2, -1, 0, 1, 2, 3]:
                            new_x = depth_x + dx
                            new_y = depth_y + dy
                            if 0 <= new_x < depth_image.shape[1] and 0 <= new_y < depth_image.shape[0]:
                                neighbor_depth = depth_image[new_y, new_x]
                                if not np.isnan(neighbor_depth) and not np.isinf(neighbor_depth) and neighbor_depth > 0:
                                    valid_neighbors.append(neighbor_depth)
                                    print(f"  有效雷达周围点({new_x}, {new_y}): {neighbor_depth}")
                    
                    # 如果有有效的周围点，使用平均值
                    if valid_neighbors:
                        avg_depth = np.mean(valid_neighbors)
                        hand_distances.append({
                            'distance': avg_depth,
                            'position': (wrist_x, wrist_y),
                            'depth_position': (depth_x, depth_y)
                        })
                        print(f"手掌 {i+1} 使用雷达周围点平均距离: {avg_depth:.3f}m")
                    else:
                        print(f"手掌 {i+1} 雷达周围没有有效深度数据")
            else:
                print(f"手掌 {i+1} 深度图坐标超出范围: ({depth_x}, {depth_y})")
                print(f"深度图有效范围: 0-{depth_image.shape[1]} x 0-{depth_image.shape[0]}")
            
            # 在RGB图像上绘制手掌关键点
            mp_drawing.draw_landmarks(rgb_image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
    else:
        print("未检测到手掌")
    
    return rgb_image, hand_distances, results

def receive_data_with_size(connection, timeout=10):
    """接收带大小信息的数据，增加超时和错误处理"""
    try:
        # 设置接收超时
        connection.settimeout(timeout)
        
        # 接收数据大小（4字节）
        size_data = connection.recv(4)
        if not size_data or len(size_data) < 4:
            print(f"接收数据大小失败: 收到 {len(size_data) if size_data else 0} 字节")
            return None
        
        data_size = struct.unpack('<I', size_data)[0]
        print(f"期望接收数据大小: {data_size} 字节")
        
        # 检查数据大小是否合理
        if data_size > 10 * 1024 * 1024:  # 10MB限制
            print(f"数据大小过大: {data_size} 字节")
            return None
        
        # 接收实际数据
        data = b""
        start_time = time.time()
        
        while len(data) < data_size:
            remaining = data_size - len(data)
            chunk = connection.recv(min(remaining, 8192))  # 每次最多接收8KB
            
            if not chunk:
                print(f"连接中断，已接收 {len(data)}/{data_size} 字节")
                return None
            
            data += chunk
            
            # 检查是否超时
            if time.time() - start_time > timeout:
                print(f"接收数据超时，已接收 {len(data)}/{data_size} 字节")
                return None
        
        print(f"成功接收数据: {len(data)} 字节")
        return data
        
    except socket.timeout:
        print("接收数据超时")
        return None
    except Exception as e:
        print(f"接收数据时出错: {e}")
        return None

def send_ack(connection, success=True):
    """发送确认消息给客户端"""
    try:
        ack = struct.pack('<I', 1 if success else 0)
        connection.send(ack)
        print(f"发送确认: {'成功' if success else '失败'}")
    except Exception as e:
        print(f"发送确认失败: {e}")

def debug_image_data(data, name="image"):
    """调试图像数据"""
    if len(data) > 0:
        print(f"{name} 数据统计:")
        print(f"  总字节数: {len(data)}")
        print(f"  前10个字节: {data[:10]}")
        print(f"  数据类型: {type(data)}")
        
        # 转换为numpy数组检查
        try:
            arr = np.frombuffer(data, dtype=np.uint8)
            print(f"  数组形状: {arr.shape}")
            print(f"  数组范围: {arr.min()} - {arr.max()}")
            print(f"  数组均值: {arr.mean():.2f}")
            
            # 检查数据是否全为0或全为255（可能的数据问题）
            if arr.min() == arr.max():
                print(f"  警告: 数据全为 {arr.min()}")
            elif arr.std() < 1.0:
                print(f"  警告: 数据变化很小 (标准差: {arr.std():.2f})")
        except Exception as e:
            print(f"  数组转换失败: {e}")
    else:
        print(f"{name} 数据为空")

def process_rgb_data(rgb_data, expected_width=640, expected_height=480):
    """处理RGB数据，支持多种格式"""
    try:
        rgb_array = np.frombuffer(rgb_data, dtype=np.uint8)
        total_pixels = len(rgb_array)
        
        print(f"RGB数据处理: 总像素数 {total_pixels}")
        
        # 检查不同的格式可能性
        if total_pixels == expected_width * expected_height * 4:  # BGRA/RGBA
            print("检测到4通道格式 (BGRA/RGBA)")
            rgb_image = rgb_array.reshape((expected_height, expected_width, 4))
            
            # 尝试BGRA格式
            try:
                bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGRA2BGR)
                print("成功转换为BGR (BGRA格式)")
                return bgr_image
            except:
                pass
            
            # 尝试RGBA格式
            try:
                bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGBA2BGR)
                print("成功转换为BGR (RGBA格式)")
                return bgr_image
            except:
                pass
                
        elif total_pixels == expected_width * expected_height * 3:  # BGR/RGB
            print("检测到3通道格式 (BGR/RGB)")
            rgb_image = rgb_array.reshape((expected_height, expected_width, 3))
            
            # 尝试RGB格式
            try:
                bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
                print("成功转换为BGR (RGB格式)")
                return bgr_image
            except:
                pass
            
            # 假设已经是BGR格式
            print("假设为BGR格式")
            return rgb_image
            
        else:
            print(f"未知格式: 期望 {expected_width}x{expected_height} 的3或4通道图像")
            print(f"实际像素数: {total_pixels}")
            return None
            
    except Exception as e:
        print(f"RGB数据处理失败: {e}")
        return None

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)

# 建立 TCP 服务器
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
server.bind((HOST, PORT))
server.listen(1)
print(f"服务器启动在 {HOST}:{PORT}")
print("等待 iPhone 连接...")

# 设置超时时间
server.settimeout(30)
try:
    conn, addr = server.accept()
    print(f"已连接: {addr}")
    # 设置TCP保活 (macOS兼容)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    # macOS使用不同的TCP保活选项名称
    try:
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except AttributeError:
        # macOS可能不支持这些选项，使用默认值
        print("使用默认TCP保活设置")
except socket.timeout:
    print("连接超时，没有设备连接")
    cleanup()
    sys.exit(1)
except Exception as e:
    print(f"接受连接时出错: {e}")
    cleanup()
    sys.exit(1)

# 深度图和RGB图的尺寸
depth_width, depth_height = 256, 192
rgb_width, rgb_height = 640, 480  # 降低分辨率，减少网络压力

try:
    frame_count = 0
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        print(f"\n等待接收第 {frame_count + 1} 帧数据...")
        
        # 接收RGB数据
        rgb_data = receive_data_with_size(conn)
        if not rgb_data:
            consecutive_errors += 1
            print(f"RGB数据接收失败 (错误 {consecutive_errors}/{max_consecutive_errors})")
            if consecutive_errors >= max_consecutive_errors:
                print("连续错误过多，退出程序")
                break
            continue
        
        # 发送RGB接收确认
        send_ack(conn, True)
        
        # 接收深度数据
        depth_data = receive_data_with_size(conn)
        if not depth_data:
            consecutive_errors += 1
            print(f"深度数据接收失败 (错误 {consecutive_errors}/{max_consecutive_errors})")
            if consecutive_errors >= max_consecutive_errors:
                print("连续错误过多，退出程序")
                break
            continue
        
        # 发送深度接收确认
        send_ack(conn, True)
        
        print(f"接收到 RGB: {len(rgb_data)} 字节, 深度: {len(depth_data)} 字节")
        
        # 调试数据
        debug_image_data(rgb_data, "RGB")
        
        try:
            # 处理RGB数据
            rgb_image = process_rgb_data(rgb_data, rgb_width, rgb_height)
            
            if rgb_image is None:
                print("RGB数据处理失败")
                consecutive_errors += 1
                continue
            
            # 验证转换后的图像
            if rgb_image.shape != (rgb_height, rgb_width, 3):
                print(f"RGB图像形状错误: {rgb_image.shape}")
                consecutive_errors += 1
                continue
            
            # 检查图像是否有效
            if np.any(np.isnan(rgb_image)) or np.any(np.isinf(rgb_image)):
                print("RGB数据包含无效值")
                consecutive_errors += 1
                continue
            
            # 检查图像是否全黑或全白
            if rgb_image.mean() < 5 or rgb_image.mean() > 250:
                print(f"RGB图像可能有问题 (均值: {rgb_image.mean():.2f})")
                consecutive_errors += 1
                continue
            
            # 处理深度数据
            depth_array = np.frombuffer(depth_data, dtype=np.float32)
            expected_depth_size = depth_height * depth_width
            
            if len(depth_array) != expected_depth_size:
                print(f"深度数据大小不匹配: 期望 {expected_depth_size}, 实际 {len(depth_array)}")
                consecutive_errors += 1
                continue
            
            depth_image = depth_array.reshape((depth_height, depth_width))
            
            # 处理无效深度值
            depth_clean = np.copy(depth_image)
            
            # 统计深度数据
            valid_depth_count = np.sum((depth_clean > 0) & ~np.isnan(depth_clean) & ~np.isinf(depth_clean))
            total_pixels = depth_clean.size
            print(f"深度数据统计: 有效像素 {valid_depth_count}/{total_pixels} ({valid_depth_count/total_pixels*100:.1f}%)")
            
            # 如果有效深度数据太少，尝试不同的处理方法
            if valid_depth_count < total_pixels * 0.1:  # 少于10%的有效数据
                print("警告: 有效深度数据太少，尝试调整处理...")
                # 尝试不同的阈值
                depth_clean[depth_clean < 0.1] = 0  # 过滤太近的距离
                depth_clean[depth_clean > 5.0] = 0  # 过滤太远的距离
            
            depth_clean[np.isnan(depth_clean)] = 0
            depth_clean[np.isinf(depth_clean)] = 0
            depth_clean[depth_clean < 0] = 0
            
            # 检查处理后的深度数据
            valid_after_clean = np.sum(depth_clean > 0)
            print(f"清理后有效深度像素: {valid_after_clean}/{total_pixels} ({valid_after_clean/total_pixels*100:.1f}%)")
            
            # 如果还是没有有效数据，显示警告
            if valid_after_clean == 0:
                print("错误: 没有有效的深度数据！")
            else:
                print(f"深度数据范围: {depth_clean[depth_clean > 0].min():.3f} - {depth_clean[depth_clean > 0].max():.3f}")
            
            # 检测手掌并计算距离
            print(f"RGB图像尺寸: {rgb_image.shape}")
            print(f"深度图像尺寸: {depth_clean.shape}")
            print(f"深度数据范围: {depth_clean.min():.3f} - {depth_clean.max():.3f}")
            
            rgb_with_hands, hand_distances, results = detect_hands_and_calculate_distance(rgb_image, depth_clean)
            

            
            # 调整图像大小以便显示
            rgb_display = cv2.resize(rgb_with_hands, (640, 480))
            
            # 归一化深度图用于显示
            depth_norm = cv2.normalize(depth_clean, None, 0, 255, cv2.NORM_MINMAX)
            depth_uint8 = depth_norm.astype(np.uint8)
            depth_display = cv2.resize(depth_uint8, (640, 480))
            
            # 在深度图上添加信息
            cv2.putText(depth_display, "Depth Radar", (10, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 显示有效深度数据比例
            valid_ratio = valid_after_clean / total_pixels * 100
            cv2.putText(depth_display, f"Valid: {valid_ratio:.1f}%", (10, 60), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 在深度图上标记手掌位置并显示距离
            for hand_info in hand_distances:
                pos = hand_info['position']
                distance = hand_info['distance']
                depth_pos = hand_info.get('depth_position', None)
                
                if depth_pos:
                    # 使用实际的深度图坐标
                    depth_x, depth_y = depth_pos
                else:
                    # 回退到坐标映射
                    depth_x = int(pos[0] * depth_width / rgb_width)
                    depth_y = int(pos[1] * depth_height / rgb_height)
                
                # 将深度图坐标映射到显示坐标
                display_depth_x = int(depth_x * 640 / depth_width)
                display_depth_y = int(depth_y * 480 / depth_height)
                
                # 在深度图上绘制圆圈和距离信息
                if 0 <= display_depth_x < depth_display.shape[1] and 0 <= display_depth_y < depth_display.shape[0]:
                    # 绘制白色圆圈
                    cv2.circle(depth_display, (display_depth_x, display_depth_y), 15, (255, 255, 255), 3)
                    
                    # 显示距离信息
                    text = f"{distance:.2f}m"
                    cv2.putText(depth_display, text, 
                              (display_depth_x + 20, display_depth_y), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    # 在RGB图像上也标记对应位置
                    display_rgb_x = int(pos[0] * 640 / rgb_width)
                    display_rgb_y = int(pos[1] * 480 / rgb_height)
                    
                    if 0 <= display_rgb_x < rgb_display_with_info.shape[1] and 0 <= display_rgb_y < rgb_display_with_info.shape[0]:
                        cv2.circle(rgb_display_with_info, (display_rgb_x, display_rgb_y), 8, (0, 255, 0), 2)
                        cv2.circle(rgb_display_with_info, (display_rgb_x, display_rgb_y), 3, (0, 255, 0), -1)
            
            # 在RGB图像右上角直接显示距离信息
            rgb_display_with_info = rgb_display.copy()
            
            # 显示手掌距离信息
            if hand_distances:
                for i, hand_info in enumerate(hand_distances):
                    distance = hand_info['distance']
                    
                    # 根据距离设置颜色
                    if distance < 0.5:
                        color = (0, 255, 0)  # 绿色
                    elif distance < 1.0:
                        color = (0, 255, 255)  # 黄色
                    else:
                        color = (0, 0, 255)  # 红色
                    
                    # 在右上角显示距离
                    text = f"Hand {i+1}: {distance:.2f}m"
                    cv2.putText(rgb_display_with_info, text, 
                              (rgb_display.shape[1] - 200, 30 + i * 25), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            else:
                # 检查是否有手掌检测但深度数据无效
                if results.multi_hand_landmarks:
                    # 有手掌检测但没有有效距离数据
                    cv2.putText(rgb_display_with_info, "Hand detected", 
                              (rgb_display.shape[1] - 200, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.putText(rgb_display_with_info, "No depth data", 
                              (rgb_display.shape[1] - 200, 55), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                else:
                    # 显示未检测到手掌
                    cv2.putText(rgb_display_with_info, "No hand detected", 
                              (rgb_display.shape[1] - 200, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)
            
            # 显示图像
            cv2.imshow("RGB Camera", rgb_display_with_info)
            cv2.imshow("Depth Radar", depth_display)
            
            # 打印检测到的手掌信息
            if hand_distances:
                for i, hand_info in enumerate(hand_distances):
                    print(f"手掌 {i+1}: 距离 {hand_info['distance']:.3f} 米, 位置 {hand_info['position']}")
            else:
                print("未检测到手掌")
            
            frame_count += 1
            consecutive_errors = 0  # 重置错误计数
            print(f"成功显示第 {frame_count} 帧")
            
        except Exception as e:
            consecutive_errors += 1
            print(f"处理图像时出错: {e}")
            print(f"错误计数: {consecutive_errors}/{max_consecutive_errors}")
            if consecutive_errors >= max_consecutive_errors:
                print("连续错误过多，退出程序")
                break
            continue
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
            
except Exception as e:
    print(f"程序出错: {e}")
    import traceback
    traceback.print_exc()
finally:
    cleanup()
    cv2.destroyAllWindows()
