from PIL import Image, ImageDraw, ImageFont
import math

# 加载原图
img = Image.open('/root/openclaw/kimi/downloads/19c8ed91-55f2-86d6-8000-00005d88e78b_论文配图转Visio图1.png')
width, height = img.size

# 创建可绘制对象
draw = ImageDraw.Draw(img)

# 定义颜色
black = (0, 0, 0)
white = (255, 255, 255)

# 原图中箭头的坐标（基于观察）
# 复合人才目标在上方中央，能力结构在左下方
# 原箭头从复合人才目标指向能力结构（从右上到左下）
# 需要反转为从能力结构指向复合人才目标（从左下到右上）

# 根据图像分析，确定关键位置（基于2364x1773的原图尺寸）
# 复合人才目标矩形区域大致在上方中央
center_top_x = width // 2  # ~1182
center_top_y = 280  # 矩形底部附近

# 能力结构椭圆区域大致在左下方
left_oval_x = 380  # 椭圆右侧附近
left_oval_y = 580  # 椭圆顶部附近

# 箭头起点（能力结构椭圆右上）
start_x = 520
start_y = 520

# 箭头终点（复合人才目标矩形左下）
end_x = 520
end_y = 320

# 绘制箭头函数
def draw_arrow(draw, start, end, color, width=8):
    x1, y1 = start
    x2, y2 = end
    
    # 绘制主线
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    
    # 计算箭头角度
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_length = 25
    arrow_angle = math.pi / 6  # 30度
    
    # 箭头两翼
    x3 = x2 - arrow_length * math.cos(angle - arrow_angle)
    y3 = y2 - arrow_length * math.sin(angle - arrow_angle)
    x4 = x2 - arrow_length * math.cos(angle + arrow_angle)
    y4 = y2 - arrow_length * math.sin(angle + arrow_angle)
    
    # 绘制箭头（填充三角形）
    draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)

# 首先用白色覆盖原箭头区域（擦除原箭头）
# 原箭头大致从 (1182, 380) 到 (380, 580)
cover_draw = ImageDraw.Draw(img)

# 覆盖原箭头的白色区域（稍微大一点确保完全覆盖）
for i in range(-15, 16):
    for j in range(-15, 16):
        # 沿原箭头路径覆盖
        t = i / 30.0
        if 0 <= t <= 1:
            x = int(1182 + (380 - 1182) * t + j)
            y = int(380 + (580 - 380) * t + i)
            if 0 <= x < width and 0 <= y < height:
                img.putpixel((x, y), white)

# 使用更大的矩形区域覆盖原箭头
cover_draw.rectangle([350, 350, 1250, 620], fill=white)

# 重新加载原图以获取干净的背景（因为上面覆盖可能不够精确）
img = Image.open('/root/openclaw/kimi/downloads/19c8ed91-55f2-86d6-8000-00005d88e78b_论文配图转Visio图1.png')
draw = ImageDraw.Draw(img)

# 更精确的方法：只覆盖原箭头的黑色线条
# 原箭头从复合人才目标（上方中央矩形）指向能力结构（左侧椭圆）
# 起点大致在矩形左下角，终点在椭圆右上方

# 覆盖原箭头 - 使用白色线条
# 原箭头路径：从 (约520, 320) 到 (约380, 580)
# 但方向是从上到下，现在需要反向

# 先用白色粗线覆盖原箭头区域
cover_width = 20
# 原箭头大致从上方中央偏左位置到左侧椭圆
cover_draw = ImageDraw.Draw(img)

# 覆盖区域：从复合人才目标矩形左下到能力结构椭圆右上
cover_draw.polygon([(480, 280), (580, 280), (450, 600), (350, 600)], fill=white)

# 更精确的覆盖：使用矩形覆盖原箭头路径
import numpy as np

# 重新加载原图
img = Image.open('/root/openclaw/kimi/downloads/19c8ed91-55f2-86d6-8000-00005d88e78b_论文配图转Visio图1.png')
img_array = np.array(img)

# 找到黑色箭头区域并替换为白色
# 原箭头在图像左侧，从上方矩形指向下方椭圆
height, width = img_array.shape[:2]

# 定义要清除的区域（原箭头的位置）
# 基于观察，原箭头从上方中央偏左指向左下方
for y in range(280, 620):
    for x in range(300, 650):
        # 检查是否在箭头区域内（简单的区域判断）
        # 原箭头大致沿对角线从 (520, 320) 到 (380, 580)
        # 清除这个区域
        if 280 <= y <= 600 and 320 <= x <= 600:
            # 计算到箭头的距离
            # 箭头线：从 (520, 320) 到 (380, 580)
            t = ((x - 520) * (380 - 520) + (y - 320) * (580 - 320)) / ((380 - 520)**2 + (580 - 320)**2)
            t = max(0, min(1, t))
            closest_x = 520 + t * (380 - 520)
            closest_y = 320 + t * (580 - 320)
            dist = math.sqrt((x - closest_x)**2 + (y - closest_y)**2)
            if dist < 25:  # 箭头宽度
                img_array[y, x] = [255, 255, 255]

# 转换回PIL Image
img = Image.fromarray(img_array)
draw = ImageDraw.Draw(img)

# 现在绘制新的箭头：从能力结构指向复合人才目标
# 起点：能力结构椭圆右上 (约380, 580)
# 终点：复合人才目标矩形左下 (约520, 320)

start = (380, 580)
end = (520, 320)

# 绘制新箭头
def draw_thick_arrow(draw, start, end, color, thickness=8):
    x1, y1 = start
    x2, y2 = end
    
    # 绘制主线
    draw.line([(x1, y1), (x2, y2)], fill=color, width=thickness)
    
    # 计算箭头角度
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_length = 25
    arrow_angle = math.pi / 6  # 30度
    
    # 箭头两翼
    x3 = x2 - arrow_length * math.cos(angle - arrow_angle)
    y3 = y2 - arrow_length * math.sin(angle - arrow_angle)
    x4 = x2 - arrow_length * math.cos(angle + arrow_angle)
    y4 = y2 - arrow_length * math.sin(angle + arrow_angle)
    
    # 绘制箭头（填充三角形）
    draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)

draw_thick_arrow(draw, start, end, black, thickness=10)

# 保存结果
output_path = '/root/.openclaw/workspace/论文配图_修改后.png'
img.save(output_path)
print(f"修改完成，已保存到: {output_path}")
