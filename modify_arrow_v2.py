from PIL import Image, ImageDraw
import numpy as np
import math

# 加载原图
img = Image.open('/root/openclaw/kimi/downloads/19c8ed91-55f2-86d6-8000-00005d88e78b_论文配图转Visio图1.png')
img_array = np.array(img)
height, width = img_array.shape[:2]

# 转换为PIL进行绘制
img_pil = Image.fromarray(img_array)
draw = ImageDraw.Draw(img_pil)

# 定义颜色
black = (0, 0, 0)
white = (255, 255, 255)

# 原箭头分析：
# - 从复合人才目标矩形（上方中央，约x=900-1300, y=150-350）
# - 指向能力结构椭圆（左侧，约x=200-600, y=450-700）
# - 箭头方向：从右上到左下

# 清除原箭头的区域（更精确的范围）
# 原箭头路径大致从 (1050, 350) 到 (450, 550)
def clear_original_arrow(img_array):
    h, w = img_array.shape[:2]
    
    # 定义要清除的多边形区域（原箭头的覆盖区域）
    # 基于观察，原箭头在左侧，从上方矩形左下角指向椭圆右上角
    for y in range(300, 650):
        for x in range(350, 1150):
            # 检查点是否在原箭头路径附近
            # 原箭头大致从 (950, 320) 到 (450, 550)
            # 使用点到线段的距离
            x1, y1 = 950, 320  # 原箭头起点（矩形左下）
            x2, y2 = 450, 550  # 原箭头终点（椭圆右上）
            
            # 计算点到线段的距离
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0 and dy == 0:
                continue
            
            t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
            closest_x = x1 + t * dx
            closest_y = y1 + t * dy
            dist = math.sqrt((x - closest_x) ** 2 + (y - closest_y) ** 2)
            
            # 如果距离足够近，且颜色接近黑色（箭头颜色），则替换为白色
            if dist < 30:
                # 检查当前像素是否是黑色或深色（箭头）
                pixel = img_array[y, x]
                if pixel[0] < 100 and pixel[1] < 100 and pixel[2] < 100:  # 深色
                    img_array[y, x] = [255, 255, 255]
    
    return img_array

# 清除原箭头
img_array = clear_original_arrow(img_array)

# 转换回PIL
img_pil = Image.fromarray(img_array)
draw = ImageDraw.Draw(img_pil)

# 绘制新箭头：从能力结构指向复合人才目标
# 起点：能力结构椭圆右上（约450, 550）
# 终点：复合人才目标矩形左下（约950, 320）
start = (450, 550)
end = (950, 320)

def draw_thick_arrow(draw, start, end, color, thickness=12):
    x1, y1 = start
    x2, y2 = end
    
    # 绘制主线
    draw.line([(x1, y1), (x2, y2)], fill=color, width=thickness)
    
    # 计算箭头角度
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_length = 30
    arrow_angle = math.pi / 6  # 30度
    
    # 箭头两翼
    x3 = x2 - arrow_length * math.cos(angle - arrow_angle)
    y3 = y2 - arrow_length * math.sin(angle - arrow_angle)
    x4 = x2 - arrow_length * math.cos(angle + arrow_angle)
    y4 = y2 - arrow_length * math.sin(angle + arrow_angle)
    
    # 绘制箭头（填充三角形）
    draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)
    
    # 加粗箭头边缘
    draw.line([(x2, y2), (x3, y3)], fill=color, width=4)
    draw.line([(x2, y2), (x4, y4)], fill=color, width=4)
    draw.line([(x3, y3), (x4, y4)], fill=color, width=4)

# 绘制新箭头
draw_thick_arrow(draw, start, end, black, thickness=12)

# 保存结果
output_path = '/root/.openclaw/workspace/论文配图_修改后.png'
img_pil.save(output_path, quality=95)
print(f"修改完成，已保存到: {output_path}")
