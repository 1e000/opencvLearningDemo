import cv2
import numpy as np  #2x2操作的时候需要numpy库
img=cv2.imread("ROBOCON-GREAT-SMALL.png")


#if img is None:
#    print("Error: Image not found")
#    exit()
#cv2.imshow("img1.png",img) #显示图片

#k=cv2.waitKey(0) #等待键盘输入
#if k==27:cv2.destroyAllWindows() #如果按下esc键，关闭窗口
#elif k==ord('s'): #如果按下s键，保存图片
#    output_path="img1.png" #保存路径
#    cv2.imwrite(output_path,img) #保存图片
#print(img.shape)
#print(img[100,100]) #返回100，100处的颜色
#roi = img[50:250,50:250] #切片
#img[100:200,100:200]=[255,255,255]   #修改img的pixel
#cv2.imwrite("roi.png",roi)       #为什么这里修改img而不是修改roi？因为roi是img的引用，修改roi会修改img



#下面进行resize操作 我会尝试不同算法 放大16倍

#模版：dst = cv2.resize(src, dsize=None, fx=None, fy=None, interpolation=cv2.INTER_LINEAR)
#                           尺寸 宽，高   x倍率     y倍率                  插值方法
big_NEAREST=cv2.resize(img,None,fx=4,fy=4,interpolation=cv2.INTER_NEAREST)
big_BICUBIC=cv2.resize(img,None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)
big_AREA=cv2.resize(img,None,fx=4,fy=4,interpolation=cv2.INTER_AREA)
big_LANCZOS4=cv2.resize(img,None,fx=4,fy=4,interpolation=cv2.INTER_LANCZOS4)
big_LINEAR=cv2.resize(img,None,fx=4,fy=4,interpolation=cv2.INTER_LINEAR)
big_LINEAR_EXACT=cv2.resize(img,None,fx=4,fy=4,interpolation=cv2.INTER_LINEAR_EXACT)
big_NEAREST_EXACT=cv2.resize(img,None,fx=4,fy=4,interpolation=cv2.INTER_NEAREST_EXACT)
big_CUBIC=cv2.resize(img,None,fx=4,fy=4,interpolation=cv2.INTER_CUBIC)
cv2.imwrite("big_NEAREST.png",big_NEAREST)
cv2.imwrite("big_BICUBIC.png",big_BICUBIC)
cv2.imwrite("big_AREA.png",big_AREA)
cv2.imwrite("big_LANCZOS4.png",big_LANCZOS4)
cv2.imwrite("big_LINEAR.png",big_LINEAR)
cv2.imwrite("big_LINEAR_EXACT.png",big_LINEAR_EXACT)
cv2.imwrite("big_NEAREST_EXACT.png",big_NEAREST_EXACT)
cv2.imwrite("big_CUBIC.png",big_CUBIC)

#看来LANCZOS4是坠吊的 一共8张，可以进行两次2*2
row1_1=np.hstack((big_NEAREST,big_BICUBIC))
row1_2=np.hstack((big_AREA,big_LANCZOS4))
row2_1=np.hstack((big_LINEAR,big_LINEAR_EXACT))
row2_2=np.hstack((big_NEAREST_EXACT,big_CUBIC))

imgbig1=np.vstack((row1_1,row1_2))
imgbig2=np.vstack((row2_1,row2_2))

cv2.imwrite("imgbig1.png",imgbig1)
cv2.imwrite("imgbig2.png",imgbig2)


#现在对imgbig进行平滑操作 使用高斯模糊 理解了一下高斯模糊
imgbig1_smooth=cv2.GaussianBlur(imgbig1,(5,5),0)
imgbig2_smooth=cv2.GaussianBlur(imgbig2,(5,5),0)
cv2.imwrite("imgbig1_smooth.png",imgbig1_smooth)
cv2.imwrite("imgbig2_smooth.png",imgbig2_smooth)

#处理成灰度图
imgbig1_gray=cv2.cvtColor(imgbig1_smooth,cv2.COLOR_BGR2GRAY)
imgbig2_gray=cv2.cvtColor(imgbig2_smooth,cv2.COLOR_BGR2GRAY)
cv2.imwrite("imgbig1_gray.png",imgbig1_gray)
cv2.imwrite("imgbig2_gray.png",imgbig2_gray)

#处理成梯度图 使用Sobel算子
imgbig1_grad=cv2.Sobel(imgbig1_smooth,cv2.CV_64F,1,1,ksize=3)  #这里转换成64位浮点数
imgbig2_grad=cv2.Sobel(imgbig2_smooth,cv2.CV_64F,1,1,ksize=3)
cv2.imwrite("imgbig1_grad.png",imgbig1_grad)
cv2.imwrite("imgbig2_grad.png",imgbig2_grad)

#对灰度图进行色彩映射
imgbig1_color=cv2.applyColorMap(imgbig1_gray,cv2.COLORMAP_RAINBOW)
imgbig2_color=cv2.applyColorMap(imgbig2_gray,cv2.COLORMAP_RAINBOW)
cv2.imwrite("imgbig1_color.png",imgbig1_color)
cv2.imwrite("imgbig2_color.png",imgbig2_color)

#对梯度图进行色彩映射
imgbig1_grad_color=cv2.applyColorMap(cv2.convertScaleAbs(imgbig1_grad),cv2.COLORMAP_RAINBOW)  #这里用convertScaleAbs转换成8位无符号整数
imgbig2_grad_color=cv2.applyColorMap(cv2.convertScaleAbs(imgbig2_grad),cv2.COLORMAP_RAINBOW)
cv2.imwrite("imgbig1_grad_color.png",imgbig1_grad_color)
cv2.imwrite("imgbig2_grad_color.png",imgbig2_grad_color)









