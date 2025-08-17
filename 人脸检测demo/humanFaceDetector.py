import cv2

# 加载人脸检测器对象 括号内为模型的路径
face_cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")

# 打开电脑自带摄像头 0表示第一个摄像头
cap=cv2.VideoCapture(0) 

while True:
    # 读取一帧图像
    ret, frame=cap.read()#read()返回boolean和numpy
    if not ret:
        break

    # 转为灰度图（人脸检测用灰度更快更准）
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)

    # 检测人脸
    faces=face_cascade.detectMultiScale(
        gray,             # 灰度图
        scaleFactor=1.1,  # 每次图像缩小比例（越小检测越精细）
        minNeighbors=8,   # 每个候选矩形需要保留的邻居数（越大越严格） 测试下来8比较合适
        minSize=(50,80)  # 最小人脸尺寸
    )

    # 在人脸区域画矩形框 （x,y）为左上角坐标，（x+w,y+h）为右下角坐标，（0,255,0）bgr颜色，2为线宽
    for (x,y,w,h) in faces:
        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)

    cv2.imshow("Face Detection",frame)
    
    # 按'q'键退出
    if cv2.waitKey(1)&0xFF==ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
