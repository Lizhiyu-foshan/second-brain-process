from PIL import Image, ImageDraw
import numpy as np
import math

# 加载原图
img = Image.open('/root/openclaw/kimi/downloads/19c8ed91-55f2-86d6-8000-00005d88e78b_论文配图转Visio图1.png')
img_array = np.array(img)
height, width = img_array.shape[:2]

# 定义颜色
black = (0, 0, 0)
white = (255, 255, 255)

# 更精确地清除原箭头 - 使用多边形区域覆盖
# 原箭头从复合人才目标矩形左下角指向能力结构椭圆右上角
# 起点约 (1050, 320)，终点约 (450, 550)

# 创建一个覆盖原箭头的白色多边形区域
def clear_arrow_area(img_array):
    h, w = img_array.shape[:2]
    
    # 定义覆盖原箭头的多边形顶点
    # 原箭头的大致路径区域
    cover_polygon = [
        (850, 250),   # 左上
        (1150, 250),  # 右上
        (1150, 400),  # 右下外
        (550, 650),   # 底部
        (300, 650),   # 左下
        (300, 450),   # 左外
    ]
    
    # 创建掩码
    from PIL import Image, ImageDraw
    mask = Image.new('L', (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.polygon(cover_polygon, fill=255)
    mask_array = np.array(mask)
    
    # 应用掩码 - 将掩码区域内的深色像素替换为白色
    for y in range(h):
        for x in range(w):
            if mask_array[y, x] > 0:
                pixel = img_array[y, x]
                # 如果是深色（可能是箭头），替换为白色
                if pixel[0] < 150 and pixel[1] < 150 and pixel[2] < 150:
                    img_array[y, x] = [255, 255, 255]
    
    return img_array

# 清除原箭头
img_array = clear_arrow_area(img_array)

# 转换回PIL进行绘制
img_pil = Image.fromarray(img_array)
draw = ImageDraw.Draw(img_pil)

# 绘制新箭头：从能力结构指向复合人才目标
# 起点：能力结构椭圆右上（约480, 530）
# 终点：复合人才目标矩形左下（约950, 320）

start = (480, 530)
end = (950, 320)

def draw_thick_arrow(draw, start, end, color, thickness=14):
    x1, y1 = start
    x2, y2 = end
    
    # 绘制主线
    draw.line([(x1, y1), (x2, y2)], fill=color, width=thickness)
    
    # 计算箭头角度
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_length = 35
    arrow_angle = math.pi / 6  # 30度
    
    # 箭头两翼
    x3 = x2 - arrow_length * math.cos(angle - arrow_angle)
    y3 = y2 - arrow_length * math.sin(angle - arrow_angle)
    x4 = x2 - arrow_length * math.cos(angle + arrow_angle)
    y4 = y2 - arrow_length * math.sin(angle + arrow_angle)
    
    # 绘制箭头（填充三角形）
    draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)
    
    # 加粗箭头边缘
    draw.line([(x2, y2), (x3, y3)], fill=color, width=5)
    draw.line([(x2, y2), (x4, y4)], fill=color, width=5)
    draw.line([(x3, y3), (x4, y4)], fill=color, width=5)

# 绘制新箭头
draw_thick_arrow(draw, start, end, black, thickness=14)

# 保存结果
output_path = '/root/.openclaw/workspace/论文配图_修改后.png'
img_pil.save(output_path, quality=95)
print(f"修改完成，已保存到: {output_path}")
