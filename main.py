import pygame
import sys
import random
import math
from enum import Enum

# 初始化pygame
pygame.init()

# 初始化字体系统
pygame.font.init()

# 游戏常量
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600
FPS = 60

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
BROWN = (139, 69, 19)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# 食物类型枚举
class FoodType(Enum):
    BURGER = "burger"
    FRIES = "fries"
    COLA = "cola"

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("FOOD FLINGER")
        self.clock = pygame.time.Clock()
        self.running = True
        # 持久化最高分
        self.high_score = 0
        self.all_scores = []  # 记录每一局结束时的分数
        try:
            with open("highscore.txt", "r") as f:
                self.high_score = int(f.read().strip())
        except Exception:
            self.high_score = 0
        self.game_over_message = None

        # 游戏状态
        self.counter_height = 120
        self.counter_width = 600
        self.counter_x = 0
        self.counter_y = SCREEN_HEIGHT - self.counter_height
        # 玩家和食物框尺寸更大
        self.player_width = 150  # 从120增大到150
        self.player_height = 150  # 从120增大到150
        self.player_y = self.counter_y - 75  # 玩家站在柜台正上方（调整位置以适应更大的员工）

        # 加载食物图片（转换为更好的格式）
        self.food_images = {}
        food_files = {
            FoodType.BURGER: "Image/Burger.jpg",
            FoodType.FRIES: "Image/Fries.jpg",
            FoodType.COLA: "Image/Cola.jpg"
        }
        # 使用更好的加载和缩放方法
        for food_type, file_path in food_files.items():
            img = pygame.image.load(file_path).convert()
            # 食物图片尺寸更大
            self.food_images[food_type] = pygame.transform.smoothscale(img, (100, 100))

        # 加载店员图片（转换为更好的格式）
        staff_img = pygame.image.load("Image/Staff.jpg").convert()
        # 使用smoothscale获得更好的质量
        self.staff_image = pygame.transform.smoothscale(staff_img, (self.player_width, self.player_height))

        # 加载背景图片
        background_img = pygame.image.load("Image/Background.png").convert()
        # 缩放背景图片以适应屏幕尺寸
        self.background_image = pygame.transform.smoothscale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))

        self.current_food_box = 0  # 当前选择的食物框索引
        # 食物框放在柜台上方（而不是悬空）
        food_box_y = self.counter_y + 10  # 放在柜台顶部
        food_box_gap = self.counter_width // 4
        self.food_boxes = [
            {"x": self.counter_x + food_box_gap * 1, "y": food_box_y, "type": FoodType.BURGER, "color": BROWN},
            {"x": self.counter_x + food_box_gap * 2, "y": food_box_y, "type": FoodType.FRIES, "color": YELLOW},
            {"x": self.counter_x + food_box_gap * 3, "y": food_box_y, "type": FoodType.COLA, "color": RED}
        ]

        # 按键状态
        self.keys_pressed = pygame.key.get_pressed()
        self.key_delay = 0  # 按键延迟计数器

        # 顾客系统
        self.customers = [None, None, None]  # 3个固定位置
        self.customer_spawn_timer = 0
        self.customers_served = 0  # 已服务的顾客数量
        self.giant_customer = None  # 巨人顾客（特殊）

        # 顾客位置定义
        self.customer_positions = [
            {"x": 800, "y": 450},   # 位置1
            {"x": 900, "y": 450},   # 位置2
            {"x": 1000, "y": 450}   # 位置3
        ]

        # 投掷系统
        self.thrown_foods = []

        # 分数
        self.score = 0
        self.money = 10  # 初始10元
        
        # 连击系统
        self.combo = 0  # 当前连击数
        self.max_combo = 0  # 最高连击数
        self.combo_timer = 0  # 连击计时器（一段时间不操作连击消失）
        
        # 难度系统
        self.difficulty_level = 1  # 难度等级
        self.base_customer_spawn_delay = 180  # 基础生成延迟
        self.base_customer_patience = 300  # 基础耐心值
        
        # 店铺评分系统
        self.rating = 5.0  # 当前评分（0-5星）
        self.success_count = 0  # 成功出餐计数（每3次加半颗星）
        self.fail_count = 0  # 失败计数（每次扣半颗星）
        
        # 特效系统
        self.effects = []  # 存储所有特效（钞票和文字）
        
    def handle_events(self):
        # 更新按键状态
        self.keys_pressed = pygame.key.get_pressed()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    self.throw_food()
    
    def move_player(self):
        # 使用连续按键检测，添加延迟避免切换太快
        if self.key_delay <= 0:
            if self.keys_pressed[pygame.K_a]:
                self.current_food_box = max(0, self.current_food_box - 1)
                self.key_delay = 15  # 15帧延迟
            elif self.keys_pressed[pygame.K_d]:
                self.current_food_box = min(len(self.food_boxes) - 1, self.current_food_box + 1)
                self.key_delay = 15  # 15帧延迟
        else:
            self.key_delay -= 1
    
    def throw_food(self):
        # 从当前选择的食物框投掷食物
        box = self.food_boxes[self.current_food_box]
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # 计算投掷方向
        dx = mouse_x - box["x"]
        dy = mouse_y - (self.player_y - 20)
        distance = math.sqrt(dx*dx + dy*dy)

        if distance > 0:
            # 标准化方向向量
            dx /= distance
            dy /= distance

            # 创建投掷的食物
            food = {
                "x": box["x"],
                "y": self.player_y - 20,
                "dx": dx * 17,
                "dy": dy * 17,
                "type": box["type"]
            }
            self.thrown_foods.append(food)

            # 每次出餐扣除3元
            self.money -= 3
            # 显示扣除成本的文字特效
            cost_effect = {
                "x": box["x"],
                "y": self.player_y - 60,
                "dy": -2,
                "life": 40,
                "text": "- $3 (cost)",
                "type": "text"
            }
            self.effects.append(cost_effect)

    def create_money_effect(self, x, y, combo_multiplier=1):
        """创建金钱特效：飞出的钞票和文字"""
        # 创建3-5张飞出的钞票
        num_bills = random.randint(3, 5)
        for i in range(num_bills):
            bill = {
                "x": x,
                "y": y,
                "dx": random.uniform(-3, 3),  # 随机水平速度
                "dy": random.uniform(-8, -4),  # 向上飞
                "life": 60,  # 生命周期（帧数）
                "type": "bill"  # 钞票类型
            }
            self.effects.append(bill)
        
        # 计算实际得分和金钱（分数受combo影响，金钱不受影响）
        score_gained = 10 * combo_multiplier
        money_gained = 5
        # 创建文字特效（显示连击倍率）
        if combo_multiplier > 1:
            text = f"+{score_gained} Score  +$5  {combo_multiplier}x COMBO!"
        else:
            text = f"+{score_gained} Score  +$5"
        text_effect = {
            "x": x,
            "y": y - 20,
            "dy": -2,  # 向上漂浮
            "life": 60,  # 生命周期（帧数）
            "text": text,
            "type": "text"  # 文字类型
        }
        self.effects.append(text_effect)
    
    def create_angry_effect(self, x, y):
        """创建生气特效：飞出的生气符号和扣分文字"""
        # 创建3-4个生气符号（愤怒emoji）
        num_emojis = random.randint(3, 4)
        for i in range(num_emojis):
            emoji = {
                "x": x,
                "y": y,
                "dx": random.uniform(-4, 4),  # 随机水平速度
                "dy": random.uniform(-9, -5),  # 向上飞
                "life": 60,  # 生命周期（帧数）
                "rotation": random.uniform(0, 360),  # 随机旋转角度
                "type": "angry_emoji"  # 生气表情类型
            }
            self.effects.append(emoji)
        
        # 创建扣分文字特效
        text_effect = {
            "x": x,
            "y": y - 20,
            "dy": -2,  # 向上漂浮
            "life": 60,  # 生命周期（帧数）
            "text": "-5 Score",
            "type": "angry_text"  # 生气文字类型
        }
        self.effects.append(text_effect)
    
    def update_effects(self):
        """更新所有特效"""
        for effect in self.effects[:]:
            effect["life"] -= 1
            
            if effect["type"] == "bill":
                # 钞票运动
                effect["x"] += effect["dx"]
                effect["y"] += effect["dy"]
                effect["dy"] += 0.3  # 重力
            elif effect["type"] == "text":
                # 文字向上漂浮
                effect["y"] += effect["dy"]
            elif effect["type"] == "angry_emoji":
                # 生气表情运动
                effect["x"] += effect["dx"]
                effect["y"] += effect["dy"]
                effect["dy"] += 0.3  # 重力
                effect["rotation"] += 10  # 旋转
            elif effect["type"] == "angry_text":
                # 扣分文字向上漂浮
                effect["y"] += effect["dy"]
            
            # 移除生命周期结束的特效
            if effect["life"] <= 0:
                self.effects.remove(effect)

    def spawn_customer(self):
        # 如果巨人顾客存在，不生成普通顾客
        if self.giant_customer is not None:
            return
        
        if self.customer_spawn_timer <= 0:
            # 检查预设的三个位置中是否有空位
            empty_positions = []
            for i in range(len(self.customer_positions)):
                if i >= len(self.customers) or self.customers[i] is None:
                    empty_positions.append(i)

            # 如果有空位，在随机空位上生成新顾客
            if empty_positions:
                position_index = random.choice(empty_positions)
                position = self.customer_positions[position_index]

                # 计算当前难度的生成延迟和耐心值
                current_spawn_delay = max(60, self.base_customer_spawn_delay - (self.difficulty_level - 1) * 15)  # 最少1秒
                current_patience = max(120, self.base_customer_patience - (self.difficulty_level - 1) * 20)  # 最少2秒

                # 创建新顾客（尺寸扩大到1.5倍）
                customer = {
                    "x": position["x"],
                    "y": position["y"],
                    "width": 45,  # 从30扩大到45
                    "height": 75,  # 从50扩大到75
                    "desired_food": random.choice(list(FoodType)),
                    "color": BLUE,
                    "patience": current_patience  # 根据难度调整耐心值
                }

                # 确保customers列表有足够的长度
                while len(self.customers) <= position_index:
                    self.customers.append(None)

                # 在指定位置放置顾客
                self.customers[position_index] = customer
                self.customer_spawn_timer = current_spawn_delay
        else:
            self.customer_spawn_timer -= 1
    
    def spawn_giant_customer(self):
        """生成巨人顾客"""
        self.giant_customer = {
            "x": 1000,  # 在右侧中央
            "y": SCREEN_HEIGHT - 100,  # 站在地面
            "width": 120,  # 超大尺寸
            "height": 200,  # 超大尺寸
            "color": ORANGE,  # 橙色表示特殊
            "timer": 600,  # 存在10秒（60fps * 10）
            "hits": 0,  # 被击中次数
            "desired_food": random.choice(list(FoodType))  # 当前想要的食物
        }
    
    def update_giant_customer(self):
        """更新巨人顾客"""
        if self.giant_customer is not None:
            self.giant_customer["timer"] -= 1
            # 检查投掷的食物是否击中巨人顾客
            for food in self.thrown_foods[:]:
                giant = self.giant_customer
                giant_center_x = giant["x"]
                giant_center_y = giant["y"] - giant["height"] // 2
                if (abs(food["x"] - giant_center_x) < (giant["width"]//2 + 50) and 
                    abs(food["y"] - giant_center_y) < (giant["height"]//2 + 50)):
                    if food["type"] == giant["desired_food"]:
                        # 巨人吃到正确食物，加分加钱
                        self.score += 20
                        self.money += 5  # 现在每个只加5元
                        self.giant_customer["hits"] += 1
                        self.create_giant_money_effect(giant["x"], giant["y"] - giant["height"])
                    self.thrown_foods.remove(food)
                    break
            # 吃满10个食物后离开并奖励50元
            if self.giant_customer["hits"] >= 10:
                self.money += 50
                self.giant_customer = None
            # 时间到了也离开（保留原有机制）
            elif self.giant_customer["timer"] <= 0:
                self.giant_customer = None
    
    def create_giant_money_effect(self, x, y):
        """创建巨人顾客的金钱特效：更少钞票，不卡顿"""
        # 创建2-3张飞出的钞票（大幅减少）
        num_bills = random.randint(2, 3)
        for i in range(num_bills):
            bill = {
                "x": x,
                "y": y,
                "dx": random.uniform(-4, 4),
                "dy": random.uniform(-8, -4),
                "life": 40,  # 更短寿命
                "type": "bill"
            }
            self.effects.append(bill)
        # 只显示一次文字特效
        text_effect = {
            "x": x,
            "y": y - 30,
            "dy": -2,
            "life": 40,
            "text": "+20 Score  +$10",
            "type": "text"
        }
        self.effects.append(text_effect)
    
    def show_game_over(self):
        # 记录本局分数
        self.all_scores.append(self.score)
        # 计算历史最高分
        if self.score > self.high_score:
            self.high_score = self.score
            try:
                with open("highscore.txt", "w") as f:
                    f.write(str(self.high_score))
            except Exception:
                pass
        font = pygame.font.Font(None, 64)
        small_font = pygame.font.Font(None, 36)
        self.screen.fill(BLACK)
        if self.game_over_message:
            text = font.render(self.game_over_message, True, RED)
            self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - 100))
        score_text = small_font.render(f"Your Score: {self.score}", True, WHITE)
        high_score_text = small_font.render(f"High Score: {self.high_score}", True, YELLOW)
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2))   
        self.screen.blit(high_score_text, (SCREEN_WIDTH//2 - high_score_text.get_width()//2, SCREEN_HEIGHT//2 + 50))
        tip = small_font.render("Press ESC to exit", True, GRAY)
        self.screen.blit(tip, (SCREEN_WIDTH//2 - tip.get_width()//2, SCREEN_HEIGHT//2 + 120))
        pygame.display.flip()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        waiting = False
    # ...existing code...

    def update(self):
        # 破产判定
        if self.money < 0 and self.running:
            self.running = False
            self.game_over_message = "You are bankrupt! Game over."
        # 更新玩家移动
        self.move_player()
        
        # 更新投掷的食物
        for food in self.thrown_foods[:]:
            food["x"] += food["dx"]
            food["y"] += food["dy"]
            food["dy"] += 0.3  # 重力
            
            # 检查食物是否落地或出界
            if food["y"] > SCREEN_HEIGHT or food["x"] > SCREEN_WIDTH or food["x"] < 0:
                self.thrown_foods.remove(food)
        
        # 更新特效
        self.update_effects()
        
        # 更新顾客
        self.spawn_customer()
        
        for i, customer in enumerate(self.customers):
            if customer is not None:  # 检查顾客是否存在
                customer["patience"] -= 1
                
                # 检查投掷的食物是否击中顾客
                for food in self.thrown_foods[:]:
                    # 计算顾客的实际中心位置（顾客矩形从 y-height 到 y）
                    customer_center_x = customer["x"]
                    customer_center_y = customer["y"] - customer["height"] // 2  # 顾客的垂直中心
                    
                    # 碰撞检测：检查食物是否在顾客全身范围内
                    if (abs(food["x"] - customer_center_x) < (customer["width"]//2 + 40) and 
                        abs(food["y"] - customer_center_y) < (customer["height"]//2 + 40) and
                        food["type"] == customer["desired_food"]):
                        
                        # 增加连击
                        self.combo += 1
                        self.combo_timer = 180  # 3秒内如果没有新的成功，连击清零
                        if self.combo > self.max_combo:
                            self.max_combo = self.combo
                        
                        # 计算连击倍率（1x, 2x, 3x...）
                        combo_multiplier = min(self.combo, 10)  # 最多10倍
                        
                        # 顾客满意，付钱离开（分数随连击增加）
                        base_score = 10
                        base_money = 5
                        self.score += base_score * combo_multiplier
                        self.money += base_money  # 金钱不受combo影响
                        self.customers_served += 1  # 增加已服务顾客计数
                        
                        # 店铺评分系统：每成功3次加半颗星
                        self.success_count += 1
                        if self.success_count >= 3:
                            self.rating = min(5.0, self.rating + 0.5)  # 最多5星
                            self.success_count = 0
                        
                        # 生成特效：飞出的钞票和文字（显示连击倍率）
                        self.create_money_effect(customer["x"], customer["y"] - customer["height"], combo_multiplier)
                        
                        self.customers[i] = None  # 将位置设置为空
                        self.thrown_foods.remove(food)
                        break
                
                # 顾客失去耐心离开
                if customer["patience"] <= 0:
                    # 连击清零
                    self.combo = 0
                    self.combo_timer = 0
                    
                    # 扣除分数
                    self.score -= 5
                    
                    # 店铺评分系统：失败扣半颗星
                    self.fail_count += 1
                    self.rating = max(0.0, self.rating - 0.5)  # 最少0星
                    self.success_count = 0  # 重置成功计数
                    
                    # 生成生气特效
                    self.create_angry_effect(customer["x"], customer["y"] - customer["height"])
                    
                    self.customers[i] = None  # 将位置设置为空
        
        # 更新巨人顾客
        self.update_giant_customer()

        # 检查是否需要生成巨人顾客
        if self.customers_served >= 15 and self.giant_customer is None:
            self.spawn_giant_customer()
            self.customers_served = 0  # 重置计数器

        # 更新连击计时器
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer <= 0:
                self.combo = 0  # 连击清零

        # 难度递增系统：每服务10个顾客，难度等级+1
        total_served = self.customers_served
        new_difficulty = (total_served // 10) + 1
        if new_difficulty > self.difficulty_level:
            self.difficulty_level = new_difficulty

        # 游戏结束判定
        if self.rating <= 0 and self.running:
            self.running = False
            self.game_over_message = "Too many bad reviews, your shop is forced to close."
    
    def draw(self):
        # 绘制背景图片
        self.screen.blit(self.background_image, (0, 0))

        # 绘制玩家（在选中的食物框位置）- 先绘制，这样会在柜台和食物框后面
        player_x = self.food_boxes[self.current_food_box]["x"]
        # 计算店员图片的位置（居中显示）
        staff_rect = self.staff_image.get_rect()
        staff_rect.center = (player_x, self.player_y)
        self.screen.blit(self.staff_image, staff_rect)

        # 绘制柜台（左下大区域）
        pygame.draw.rect(self.screen, BROWN, (self.counter_x, self.counter_y, self.counter_width, self.counter_height))

        # 绘制食物框
        for i, box in enumerate(self.food_boxes):
            # 高亮当前选择的食物框
            color = box["color"]
            if i == self.current_food_box:
                # 添加白色边框表示选中
                pygame.draw.rect(self.screen, WHITE, 
                               (box["x"] - 35, box["y"] - 10, 70, 60), 4)
            pygame.draw.rect(self.screen, color, 
                           (box["x"] - 30, box["y"], 60, 40))

        # 绘制投掷的食物
        for food in self.thrown_foods:
            # 使用图片而不是色块
            food_image = self.food_images[food["type"]]
            # 计算图片中心位置
            image_rect = food_image.get_rect()
            image_rect.center = (int(food["x"]), int(food["y"]))
            self.screen.blit(food_image, image_rect)

        # 绘制顾客（调整位置以适应1.5倍尺寸）
        for customer in self.customers:
            if customer is not None:  # 检查顾客是否存在
                # 顾客矩形，居中对齐（width=45, height=75）
                pygame.draw.rect(self.screen, customer["color"], 
                               (customer["x"] - customer["width"]//2, customer["y"] - customer["height"], 
                                customer["width"], customer["height"]))
        
        # 绘制巨人顾客
        if self.giant_customer is not None:
            giant = self.giant_customer
            # 绘制巨大的矩形
            pygame.draw.rect(self.screen, giant["color"], 
                           (giant["x"] - giant["width"]//2, giant["y"] - giant["height"], 
                            giant["width"], giant["height"]))
            # 绘制边框表示特殊
            pygame.draw.rect(self.screen, YELLOW, 
                           (giant["x"] - giant["width"]//2, giant["y"] - giant["height"], 
                            giant["width"], giant["height"]), 5)
            
            # 绘制倒计时
            timer_seconds = giant["timer"] // 60
            font = pygame.font.Font(None, 48)
            timer_text = font.render(f"{timer_seconds}s", True, WHITE)
            self.screen.blit(timer_text, (giant["x"] - 20, giant["y"] - giant["height"] - 50))
            
            # 绘制"GIANT BONUS!"文字
            bonus_font = pygame.font.Font(None, 36)
            bonus_text = bonus_font.render("GIANT BONUS!", True, YELLOW)
            self.screen.blit(bonus_text, (giant["x"] - 80, giant["y"] - giant["height"] - 90))
            
            # 绘制巨人想要的食物
            food_font = pygame.font.Font(None, 42)
            food_text = food_font.render(giant["desired_food"].value.upper(), True, WHITE)
            self.screen.blit(food_text, (giant["x"] - 50, giant["y"] - giant["height"]//2 - 10))
            
            # 绘制还能吃几个食物
            left = max(0, 10 - giant['hits'])
            left_text = bonus_font.render(f"Left: {left}", True, WHITE)
            self.screen.blit(left_text, (giant["x"] - 40, giant["y"] + 10))
        
        # 绘制特效（钞票和文字）
        for effect in self.effects:
            if effect["type"] == "bill":
                # 绘制钞票（绿色矩形）
                alpha = int(255 * (effect["life"] / 60))  # 根据生命周期计算透明度
                bill_color = (0, min(255, 150 + alpha // 3), 0)  # 绿色
                pygame.draw.rect(self.screen, bill_color, 
                               (int(effect["x"]) - 8, int(effect["y"]) - 4, 16, 8))
                # 绘制钞票上的"$"符号
                font = pygame.font.Font(None, 16)
                dollar_text = font.render("$", True, WHITE)
                self.screen.blit(dollar_text, (int(effect["x"]) - 4, int(effect["y"]) - 6))
            elif effect["type"] == "text":
                # 绘制文字特效（加分）
                alpha = int(255 * (effect["life"] / 60))  # 根据生命周期计算透明度
                font = pygame.font.Font(None, 32)
                # 创建带阴影的文字效果
                shadow_text = font.render(effect["text"], True, BLACK)
                self.screen.blit(shadow_text, (int(effect["x"]) - 58, int(effect["y"]) + 2))
                color_text = font.render(effect["text"], True, YELLOW)
                self.screen.blit(color_text, (int(effect["x"]) - 60, int(effect["y"])))
            elif effect["type"] == "angry_emoji":
                # 绘制生气表情（红色圆圈 + 愤怒符号）
                alpha = int(255 * (effect["life"] / 60))
                # 绘制红色圆形背景
                pygame.draw.circle(self.screen, (255, 50, 50), 
                                 (int(effect["x"]), int(effect["y"])), 15)
                # 绘制愤怒的眼睛（两个小三角形）
                pygame.draw.polygon(self.screen, BLACK, 
                                  [(int(effect["x"]) - 8, int(effect["y"]) - 3),
                                   (int(effect["x"]) - 3, int(effect["y"]) - 3),
                                   (int(effect["x"]) - 5, int(effect["y"]) + 2)])
                pygame.draw.polygon(self.screen, BLACK, 
                                  [(int(effect["x"]) + 3, int(effect["y"]) - 3),
                                   (int(effect["x"]) + 8, int(effect["y"]) - 3),
                                   (int(effect["x"]) + 5, int(effect["y"]) + 2)])
                # 绘制愤怒的嘴巴（弧线）
                pygame.draw.arc(self.screen, BLACK, 
                              (int(effect["x"]) - 8, int(effect["y"]) + 2, 16, 10),
                              3.14, 0, 2)
            elif effect["type"] == "angry_text":
                # 绘制扣分文字特效（红色）
                alpha = int(255 * (effect["life"] / 60))
                font = pygame.font.Font(None, 36)
                # 创建带阴影的文字效果
                shadow_text = font.render(effect["text"], True, BLACK)
                self.screen.blit(shadow_text, (int(effect["x"]) - 48, int(effect["y"]) + 2))
                color_text = font.render(effect["text"], True, RED)
                self.screen.blit(color_text, (int(effect["x"]) - 50, int(effect["y"])))
        
        # 绘制投掷轨迹预览
        if len(self.customers) > 0:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            box = self.food_boxes[self.current_food_box]
            
            # 计算投掷方向
            dx = mouse_x - box["x"]
            dy = mouse_y - (self.player_y - 20)
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 0:
                dx /= distance
                dy /= distance
                
                # 绘制投掷轨迹
                start_x, start_y = box["x"], self.player_y - 20
                for i in range(20):
                    t = i * 0.5
                    x = start_x + dx * 10 * t
                    y = start_y + dy * 10 * t + 0.3 * t * t / 2
                    
                    if 0 <= x <= SCREEN_WIDTH and 0 <= y <= SCREEN_HEIGHT:
                        pygame.draw.circle(self.screen, GRAY, (int(x), int(y)), 2)
                    else:
                        break
        
        # === 所有文字绘制在最后，确保显示在最前面 ===
        
        # 绘制食物框标签（黑色）
        for i, box in enumerate(self.food_boxes):
            font = pygame.font.Font(None, 24)
            text = font.render(box["type"].value.upper(), True, BLACK)
            self.screen.blit(text, (box["x"] - 25, box["y"] - 25))
        
        # 绘制顾客的文字信息
        for customer in self.customers:
            if customer is not None:
                # 显示顾客想要的食物（字体放大到30）
                font = pygame.font.Font(None, 30)
                text = font.render(customer["desired_food"].value.upper(), True, WHITE)
                self.screen.blit(text, (customer["x"] - 30, customer["y"] - customer["height"] - 25))
                
                # 显示耐心条（放大到60宽度）
                patience_width = int((customer["patience"] / 300) * 60)
                pygame.draw.rect(self.screen, RED, 
                               (customer["x"] - 30, customer["y"] - customer["height"] - 10, 60, 8))
                pygame.draw.rect(self.screen, GREEN, 
                               (customer["x"] - 30, customer["y"] - customer["height"] - 10, patience_width, 8))
        
        # 绘制分数和金钱
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self.score}", True, WHITE)
        money_text = font.render(f"Money: ${self.money}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        self.screen.blit(money_text, (10, 50))
        
        # 绘制连击系统
        if self.combo > 0:
            combo_font = pygame.font.Font(None, 48)
            combo_text = combo_font.render(f"COMBO: {self.combo}x", True, YELLOW)
            self.screen.blit(combo_text, (10, 90))
            # 绘制连击计时条
            combo_bar_width = int((self.combo_timer / 180) * 150)
            pygame.draw.rect(self.screen, YELLOW, (10, 135, combo_bar_width, 8))
            pygame.draw.rect(self.screen, WHITE, (10, 135, 150, 8), 2)
        
        # 绘制店铺评分系统（5颗星）
        rating_font = pygame.font.Font(None, 32)
        rating_text = rating_font.render("Rating:", True, WHITE)
        self.screen.blit(rating_text, (10, 150))
        
        # 绘制星星
        star_x = 100
        star_y = 155
        full_stars = int(self.rating)
        half_star = (self.rating - full_stars) >= 0.5
        
        for i in range(5):
            if i < full_stars:
                # 满星（黄色）
                pygame.draw.polygon(self.screen, YELLOW, [
                    (star_x + i*25 + 10, star_y),
                    (star_x + i*25 + 12, star_y + 7),
                    (star_x + i*25 + 20, star_y + 7),
                    (star_x + i*25 + 14, star_y + 12),
                    (star_x + i*25 + 16, star_y + 20),
                    (star_x + i*25 + 10, star_y + 15),
                    (star_x + i*25 + 4, star_y + 20),
                    (star_x + i*25 + 6, star_y + 12),
                    (star_x + i*25 + 0, star_y + 7),
                    (star_x + i*25 + 8, star_y + 7)
                ])
            elif i == full_stars and half_star:
                # 半星（灰+黄）
                pygame.draw.polygon(self.screen, GRAY, [
                    (star_x + i*25 + 10, star_y),
                    (star_x + i*25 + 12, star_y + 7),
                    (star_x + i*25 + 20, star_y + 7),
                    (star_x + i*25 + 14, star_y + 12),
                    (star_x + i*25 + 16, star_y + 20),
                    (star_x + i*25 + 10, star_y + 15),
                    (star_x + i*25 + 4, star_y + 20),
                    (star_x + i*25 + 6, star_y + 12),
                    (star_x + i*25 + 0, star_y + 7),
                    (star_x + i*25 + 8, star_y + 7)
                ])
                # 左半边涂黄色
                pygame.draw.polygon(self.screen, YELLOW, [
                    (star_x + i*25 + 10, star_y),
                    (star_x + i*25 + 10, star_y + 15),
                    (star_x + i*25 + 4, star_y + 20),
                    (star_x + i*25 + 6, star_y + 12),
                    (star_x + i*25 + 0, star_y + 7),
                    (star_x + i*25 + 8, star_y + 7)
                ])
            else:
                # 空星（灰色）
                pygame.draw.polygon(self.screen, GRAY, [
                    (star_x + i*25 + 10, star_y),
                    (star_x + i*25 + 12, star_y + 7),
                    (star_x + i*25 + 20, star_y + 7),
                    (star_x + i*25 + 14, star_y + 12),
                    (star_x + i*25 + 16, star_y + 20),
                    (star_x + i*25 + 10, star_y + 15),
                    (star_x + i*25 + 4, star_y + 20),
                    (star_x + i*25 + 6, star_y + 12),
                    (star_x + i*25 + 0, star_y + 7),
                    (star_x + i*25 + 8, star_y + 7)
                ])
        
        # 绘制难度等级
        difficulty_font = pygame.font.Font(None, 28)
        difficulty_text = difficulty_font.render(f"Difficulty: Lv.{self.difficulty_level}", True, RED)
        self.screen.blit(difficulty_text, (10, 190))
        
        # 绘制顾客服务进度（距离巨人顾客还差几个）
        customers_until_giant = 15 - self.customers_served
        if self.giant_customer is None:
            progress_font = pygame.font.Font(None, 28)
            progress_text = progress_font.render(f"Giant in: {customers_until_giant} customers", True, YELLOW)
            self.screen.blit(progress_text, (10, 220))
        
        # 绘制最高连击记录
        if self.max_combo > 0:
            max_combo_font = pygame.font.Font(None, 24)
            max_combo_text = max_combo_font.render(f"Max Combo: {self.max_combo}x", True, ORANGE)
            self.screen.blit(max_combo_text, (10, 250))
        
        # 绘制控制说明
        font = pygame.font.Font(None, 24)
        controls_text = font.render("Move: AD | Aim: mouse | Throw: left click", True, WHITE)
        self.screen.blit(controls_text, (SCREEN_WIDTH - 350, 10))
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        # Game over
        self.show_game_over()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
