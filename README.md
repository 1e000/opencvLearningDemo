# OpenCV Learning Demo

这是一个基于OpenCV和MediaPipe的手掌检测与距离测量项目，支持iPhone和Mac之间的实时数据传输。

## 项目结构

```
pyandc++learning/
├── 手部距离/                    # 手掌检测与距离测量项目
│   ├── demo.py                  # Mac端主程序
│   ├── iPhone_ViewController.swift  # iPhone端应用
│   └── requirements.txt         # Python依赖
├── 人脸检测demo/                # 人脸检测相关项目
├── opencv图像基本操作/          # OpenCV基础操作示例
└── README.md                   # 项目说明文档
```

## 功能特性

### 🖐️ 手掌检测与距离测量
- **实时手掌检测**: 使用MediaPipe进行高精度手掌识别
- **深度数据获取**: 从iPhone LiDAR雷达获取深度信息
- **距离计算**: 实时计算手掌到摄像头的距离
- **可视化显示**: RGB图像和深度雷达图同步显示

### 📱 iPhone端功能
- ARKit集成，支持LiDAR深度数据
- 实时RGB图像采集和传输
- 网络连接管理，支持自动重连
- 图像格式优化和压缩

### 💻 Mac端功能
- TCP服务器接收iPhone数据
- MediaPipe手掌检测和关键点识别
- 深度数据处理和距离计算
- 实时可视化界面

## 安装和运行

### 环境要求
- Python 3.7+
- OpenCV 4.x
- MediaPipe
- NumPy
- iPhone (支持LiDAR的设备)

### Mac端设置
```bash
# 安装依赖
pip install -r 手部距离/requirements.txt

# 运行主程序
cd 手部距离
python demo.py
```

### iPhone端设置
1. 使用Xcode打开`iPhone_ViewController.swift`
2. 配置网络连接参数
3. 部署到支持LiDAR的iPhone设备
4. 确保Mac和iPhone在同一网络

## 使用说明

1. **启动Mac端程序**: 运行`demo.py`，等待iPhone连接
2. **启动iPhone应用**: 运行iOS应用，自动连接到Mac
3. **手掌检测**: 在摄像头前展示手掌
4. **查看结果**: 
   - RGB图像显示手掌骨架
   - 深度雷达图显示距离信息
   - 右上角显示实时距离数值

## 技术细节

### 网络通信
- 协议: TCP
- 端口: 9999
- 数据格式: 大小前缀 + 二进制数据

### 图像处理
- RGB格式: BGRA (iPhone) → BGR (Mac)
- 分辨率: 640x480
- 深度数据: Float32格式

### 手掌检测
- 检测置信度: 0.3
- 最大检测数量: 2只手
- 关键点: 手腕、食指指尖、中指指尖

## 项目特色

- ✅ **实时性能**: 低延迟数据传输和处理
- ✅ **高精度**: 基于LiDAR的精确距离测量
- ✅ **鲁棒性**: 自动错误恢复和重连机制
- ✅ **可视化**: 直观的实时显示界面
- ✅ **跨平台**: iPhone + Mac协同工作

## 开发说明

### 调试工具
- 详细的日志输出
- 数据统计信息
- 错误处理和恢复

### 扩展功能
- 支持多手掌检测
- 距离趋势分析
- 手势识别扩展

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进项目！

---

**注意**: 本项目需要支持LiDAR的iPhone设备才能获取深度数据。
