import UIKit
import ARKit
import Network
import CoreImage

class ViewController: UIViewController, ARSessionDelegate {
    var connection: NWConnection?
    var isConnected = false
    var depthImageView: UIImageView!
    var rgbImageView: UIImageView!
    var arSession: ARSession!
    var lastUpdateTime: TimeInterval = 0
    let updateInterval: TimeInterval = 1.0/10.0  // 降低到10 FPS，大幅减少网络压力
    var isSendingData = false  // 防止重复发送
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        // 设置UI
        setupUI()
        
        // 启动 TCP 连接到 Mac
        setupNetworkConnection()
        
        // 配置 ARKit
        let config = ARWorldTrackingConfiguration()
        config.frameSemantics = .sceneDepth // 打开深度
        
        // 检查设备是否支持深度
        if ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) {
            print("设备支持深度数据")
        } else {
            print("设备不支持深度数据")
            return
        }
        
        arSession = ARSession()
        arSession.delegate = self
        arSession.run(config)
        
        print("ARKit会话已启动")
    }
    
    func setupUI() {
        // 创建RGB图像显示视图
        rgbImageView = UIImageView()
        rgbImageView.contentMode = .scaleAspectFit
        rgbImageView.backgroundColor = .black
        rgbImageView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(rgbImageView)
        
        // 创建深度图像显示视图
        depthImageView = UIImageView()
        depthImageView.contentMode = .scaleAspectFit
        depthImageView.backgroundColor = .black
        depthImageView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(depthImageView)
        
        // 设置约束 - 左右分屏显示
        NSLayoutConstraint.activate([
            // RGB图像视图 - 左侧
            rgbImageView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 20),
            rgbImageView.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 10),
            rgbImageView.widthAnchor.constraint(equalTo: view.widthAnchor, multiplier: 0.48),
            rgbImageView.heightAnchor.constraint(equalTo: rgbImageView.widthAnchor, multiplier: 0.75),
            
            // 深度图像视图 - 右侧
            depthImageView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 20),
            depthImageView.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -10),
            depthImageView.widthAnchor.constraint(equalTo: view.widthAnchor, multiplier: 0.48),
            depthImageView.heightAnchor.constraint(equalTo: depthImageView.widthAnchor, multiplier: 0.75)
        ])
        
        // 添加标签
        let rgbLabel = UILabel()
        rgbLabel.text = "RGB相机"
        rgbLabel.textAlignment = .center
        rgbLabel.textColor = .white
        rgbLabel.backgroundColor = .black
        rgbLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(rgbLabel)
        
        let depthLabel = UILabel()
        depthLabel.text = "深度雷达"
        depthLabel.textAlignment = .center
        depthLabel.textColor = .white
        depthLabel.backgroundColor = .black
        depthLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(depthLabel)
        
        // 添加状态标签
        let statusLabel = UILabel()
        statusLabel.text = "等待连接..."
        statusLabel.textAlignment = .center
        statusLabel.textColor = .white
        statusLabel.backgroundColor = .black
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(statusLabel)
        
        NSLayoutConstraint.activate([
            // RGB标签
            rgbLabel.topAnchor.constraint(equalTo: rgbImageView.bottomAnchor, constant: 5),
            rgbLabel.leadingAnchor.constraint(equalTo: rgbImageView.leadingAnchor),
            rgbLabel.trailingAnchor.constraint(equalTo: rgbImageView.trailingAnchor),
            
            // 深度标签
            depthLabel.topAnchor.constraint(equalTo: depthImageView.bottomAnchor, constant: 5),
            depthLabel.leadingAnchor.constraint(equalTo: depthImageView.leadingAnchor),
            depthLabel.trailingAnchor.constraint(equalTo: depthImageView.trailingAnchor),
            
            // 状态标签
            statusLabel.topAnchor.constraint(equalTo: rgbLabel.bottomAnchor, constant: 20),
            statusLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            statusLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20)
        ])
        
        print("UI设置完成，左右分屏显示RGB和深度图像")
    }
    
    func setupNetworkConnection() {
        // 尝试多个可能的IP地址
        let possibleHosts = [
            "192.168.2.100",  // 原来的IP
            "192.168.1.100",  // 常见的路由器网段
            "192.168.0.100",  // 另一个常见网段
            "localhost",       // 本地测试
            "127.0.0.1"       // 本地回环
        ]
        
        let port = NWEndpoint.Port(rawValue: 9999)!
        
        // 尝试连接第一个IP
        tryConnect(host: possibleHosts[0], port: port)
    }
    
    func tryConnect(host: String, port: NWEndpoint.Port) {
        print("尝试连接到: \(host):\(port)")
        
        let endpoint = NWEndpoint.Host(host)
        connection = NWConnection(host: endpoint, port: port, using: .tcp)
        
        // 设置连接状态监听
        connection?.stateUpdateHandler = { [weak self] state in
            DispatchQueue.main.async {
                switch state {
                case .ready:
                    print("连接已建立到 \(host)")
                    self?.isConnected = true
                    self?.isSendingData = false
                case .failed(let error):
                    print("连接到 \(host) 失败: \(error)")
                    self?.isConnected = false
                    self?.isSendingData = false
                    // 尝试下一个IP地址
                    self?.tryNextHost()
                case .cancelled:
                    print("连接已取消")
                    self?.isConnected = false
                    self?.isSendingData = false
                case .waiting(let error):
                    print("连接等待中: \(error)")
                default:
                    print("连接状态: \(state)")
                }
            }
        }
        
        connection?.start(queue: .global())
    }
    
    func tryNextHost() {
        let possibleHosts = [
            "192.168.2.100",
            "192.168.1.100", 
            "192.168.0.100",
            "localhost",
            "127.0.0.1"
        ]
        
        // 这里可以实现轮询逻辑，暂时只重试第一个
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
            self.tryConnect(host: possibleHosts[0], port: NWEndpoint.Port(rawValue: 9999)!)
        }
    }
    
    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        let currentTime = CACurrentMediaTime()
        
        // 控制更新频率，减少帧丢失
        guard currentTime - lastUpdateTime >= updateInterval else { return }
        lastUpdateTime = currentTime
        
        // 获取RGB图像
        let rgbImage = frame.capturedImage
        print("RGB图像尺寸: \(CVPixelBufferGetWidth(rgbImage)) x \(CVPixelBufferGetHeight(rgbImage))")
        
        // 获取深度数据
        guard let depthMap = frame.sceneDepth?.depthMap else {
            print("没有深度数据")
            return
        }
        
        print("深度图尺寸: \(CVPixelBufferGetWidth(depthMap)) x \(CVPixelBufferGetHeight(depthMap))")
        
        // 在iPhone上显示RGB和深度图像
        displayRGBImage(rgbImage)
        displayDepthImage(depthMap)
        
        // 如果连接了Mac且没有正在发送数据，则发送数据
        if isConnected && !isSendingData {
            sendFrameData(rgbImage: rgbImage, depthMap: depthMap)
        }
    }
    
    func displayRGBImage(_ pixelBuffer: CVPixelBuffer) {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let context = CIContext()
        
        if let cgImage = context.createCGImage(ciImage, from: ciImage.extent) {
            let uiImage = UIImage(cgImage: cgImage)
            DispatchQueue.main.async {
                self.rgbImageView.image = uiImage
            }
        }
    }
    
    func displayDepthImage(_ depthMap: CVPixelBuffer) {
        let width = CVPixelBufferGetWidth(depthMap)
        let height = CVPixelBufferGetHeight(depthMap)
        
        CVPixelBufferLockBaseAddress(depthMap, .readOnly)
        let baseAddr = CVPixelBufferGetBaseAddress(depthMap)!
        let data = Data(bytes: baseAddr, count: width * height * MemoryLayout<Float32>.size)
        CVPixelBufferUnlockBaseAddress(depthMap, .readOnly)
        
        // 转换为UIImage显示
        if let image = depthDataToImage(data, width: width, height: height) {
            DispatchQueue.main.async {
                self.depthImageView.image = image
            }
        }
    }
    
    func depthDataToImage(_ data: Data, width: Int, height: Int) -> UIImage? {
        // 将Float32数据转换为UInt8用于显示
        let floatData = data.withUnsafeBytes { $0.bindMemory(to: Float32.self) }
        var uint8Data = [UInt8](repeating: 0, count: width * height)
        
        // 找到最小值和最大值进行归一化
        let minDepth = floatData.min() ?? 0
        let maxDepth = floatData.max() ?? 1
        
        for i in 0..<floatData.count {
            if maxDepth > minDepth {
                let normalized = (floatData[i] - minDepth) / (maxDepth - minDepth)
                uint8Data[i] = UInt8(normalized * 255)
            }
        }
        
        // 创建CGImage
        let colorSpace = CGColorSpaceCreateDeviceGray()
        let bitmapInfo = CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue)
        
        guard let context = CGContext(data: &uint8Data,
                                    width: width,
                                    height: height,
                                    bitsPerComponent: 8,
                                    bytesPerRow: width,
                                    space: colorSpace,
                                    bitmapInfo: bitmapInfo.rawValue) else {
            return nil
        }
        
        guard let cgImage = context.makeImage() else {
            return nil
        }
        
        return UIImage(cgImage: cgImage)
    }
    
    func sendFrameData(rgbImage: CVPixelBuffer, depthMap: CVPixelBuffer) {
        guard isConnected && !isSendingData else { return }
        
        isSendingData = true
        
        // 先发送RGB数据
        sendRGBData(rgbImage) { [weak self] success in
            if success {
                // RGB发送成功，再发送深度数据
                self?.sendDepthData(depthMap) { depthSuccess in
                    DispatchQueue.main.async {
                        self?.isSendingData = false
                        if depthSuccess {
                            print("完整帧数据发送成功")
                        } else {
                            print("深度数据发送失败")
                        }
                    }
                }
            } else {
                DispatchQueue.main.async {
                    self?.isSendingData = false
                    print("RGB数据发送失败")
                }
            }
        }
    }
    
    func sendDepthData(_ depthMap: CVPixelBuffer, completion: @escaping (Bool) -> Void) {
        let width = CVPixelBufferGetWidth(depthMap)
        let height = CVPixelBufferGetHeight(depthMap)
        CVPixelBufferLockBaseAddress(depthMap, .readOnly)
        let baseAddr = CVPixelBufferGetBaseAddress(depthMap)!
        let data = Data(bytes: baseAddr, count: width * height * MemoryLayout<Float32>.size)
        CVPixelBufferUnlockBaseAddress(depthMap, .readOnly)
        
        print("准备发送深度数据: \(data.count) 字节")
        
        // 发送数据大小信息
        let sizeData = withUnsafeBytes(of: UInt32(data.count).littleEndian) { Data($0) }
        connection?.send(content: sizeData, completion: .contentProcessed { [weak self] error in
            if let error = error {
                print("发送深度数据大小失败: \(error)")
                completion(false)
                return
            }
            
            // 发送实际数据
            self?.connection?.send(content: data, completion: .contentProcessed { error in
                if let error = error {
                    print("发送深度数据失败: \(error)")
                    completion(false)
                } else {
                    print("成功发送 \(data.count) 字节深度数据")
                    // 等待服务器确认
                    self?.waitForAck { ackSuccess in
                        completion(ackSuccess)
                    }
                }
            })
        })
    }
    
    func sendRGBData(_ pixelBuffer: CVPixelBuffer, completion: @escaping (Bool) -> Void) {
        // 缩放图像到640x480
        let targetWidth: Int32 = 640
        let targetHeight: Int32 = 480
        
        // 检查原始像素格式
        let pixelFormat = CVPixelBufferGetPixelFormatType(pixelBuffer)
        print("原始RGB像素格式: \(pixelFormat)")
        
        // 检查像素格式，如果不是BGRA则记录警告
        if pixelFormat != kCVPixelFormatType_32BGRA {
            print("警告: 像素格式不是BGRA，当前格式: \(pixelFormat)")
            print("将尝试继续处理，但可能影响图像质量")
        }
        
        guard let scaledBuffer = resizePixelBuffer(pixelBuffer, to: CGSize(width: Int(targetWidth), height: Int(targetHeight))) else {
            print("图像缩放失败")
            completion(false)
            return
        }
        
        let width = CVPixelBufferGetWidth(scaledBuffer)
        let height = CVPixelBufferGetHeight(scaledBuffer)
        let scaledFormat = CVPixelBufferGetPixelFormatType(scaledBuffer)
        
        print("缩放后RGB图像: \(width)x\(height), 格式: \(scaledFormat)")
        
        // 验证缩放后的格式
        guard scaledFormat == kCVPixelFormatType_32BGRA else {
            print("错误: 缩放后像素格式不是BGRA")
            completion(false)
            return
        }
        
        CVPixelBufferLockBaseAddress(scaledBuffer, .readOnly)
        let baseAddr = CVPixelBufferGetBaseAddress(scaledBuffer)!
        let bytesPerRow = CVPixelBufferGetBytesPerRow(scaledBuffer)
        let expectedBytes = width * height * 4 // BGRA格式，4字节/像素
        
        print("RGB数据信息: 宽度=\(width), 高度=\(height), 每行字节数=\(bytesPerRow), 期望字节数=\(expectedBytes)")
        
        // 检查是否有padding
        if bytesPerRow > width * 4 {
            print("警告: 检测到行padding，需要特殊处理")
            // 逐行复制数据，跳过padding
            var data = Data()
            for row in 0..<height {
                let rowData = Data(bytes: baseAddr.advanced(by: row * bytesPerRow), count: width * 4)
                data.append(rowData)
            }
            CVPixelBufferUnlockBaseAddress(scaledBuffer, .readOnly)
            
            print("准备发送RGB数据: \(data.count) 字节 (处理padding后)")
            sendRGBDataWithSize(data, completion: completion)
        } else {
            // 没有padding，直接复制
            let data = Data(bytes: baseAddr, count: expectedBytes)
            CVPixelBufferUnlockBaseAddress(scaledBuffer, .readOnly)
            
            print("准备发送RGB数据: \(data.count) 字节")
            sendRGBDataWithSize(data, completion: completion)
        }
    }
    
    func sendRGBDataWithSize(_ data: Data, completion: @escaping (Bool) -> Void) {
        // 发送RGB数据大小信息
        let sizeData = withUnsafeBytes(of: UInt32(data.count).littleEndian) { Data($0) }
        connection?.send(content: sizeData, completion: .contentProcessed { [weak self] error in
            if let error = error {
                print("发送RGB数据大小失败: \(error)")
                completion(false)
                return
            }
            
            // 发送实际RGB数据
            self?.connection?.send(content: data, completion: .contentProcessed { error in
                if let error = error {
                    print("发送RGB数据失败: \(error)")
                    completion(false)
                } else {
                    print("成功发送 \(data.count) 字节RGB数据")
                    // 等待服务器确认
                    self?.waitForAck { ackSuccess in
                        completion(ackSuccess)
                    }
                }
            })
        })
    }
    
    func resizePixelBuffer(_ pixelBuffer: CVPixelBuffer, to size: CGSize) -> CVPixelBuffer? {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let scaleX = size.width / CGFloat(CVPixelBufferGetWidth(pixelBuffer))
        let scaleY = size.height / CGFloat(CVPixelBufferGetHeight(pixelBuffer))
        
        let scaledImage = ciImage.transformed(by: CGAffineTransform(scaleX: scaleX, y: scaleY))
        
        let context = CIContext()
        var scaledPixelBuffer: CVPixelBuffer?
        
        // 确保创建BGRA格式的像素缓冲区
        let status = CVPixelBufferCreate(kCFAllocatorDefault,
                                       Int(size.width),
                                       Int(size.height),
                                       kCVPixelFormatType_32BGRA, // 强制使用BGRA格式
                                       nil,
                                       &scaledPixelBuffer)
        
        guard status == kCVReturnSuccess, let scaledBuffer = scaledPixelBuffer else {
            print("创建缩放像素缓冲区失败")
            return nil
        }
        
        // 锁定缓冲区进行渲染
        CVPixelBufferLockBaseAddress(scaledBuffer, [])
        context.render(scaledImage, to: scaledBuffer)
        CVPixelBufferUnlockBaseAddress(scaledBuffer, [])
        
        // 验证格式
        let finalFormat = CVPixelBufferGetPixelFormatType(scaledBuffer)
        print("缩放后像素格式: \(finalFormat)")
        
        return scaledBuffer
    }
    
    func waitForAck(completion: @escaping (Bool) -> Void) {
        // 接收4字节的确认消息
        connection?.receive(minimumIncompleteLength: 4, maximumLength: 4) { [weak self] data, _, isComplete, error in
            if let error = error {
                print("接收确认消息失败: \(error)")
                completion(false)
                return
            }
            
            if let data = data, data.count == 4 {
                let ackValue = data.withUnsafeBytes { $0.load(as: UInt32.self) }
                let success = ackValue == 1
                print("收到确认消息: \(success ? "成功" : "失败")")
                completion(success)
            } else {
                print("确认消息格式错误")
                completion(false)
            }
        }
    }
    
    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        connection?.cancel()
    }
    
    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        arSession?.pause()
    }
    
    deinit {
        arSession?.pause()
        connection?.cancel()
    }
}
