import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    def __init__(self, life: int):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.image.fill((0, 0, 0, 128))  # 透明度128の黒い矩形
        self.rect = self.image.get_rect()
        self.life = life

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()

def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        # self.imgs = {
        #     (+1, 0): img,  # 右
        #     (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
        #     (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
        #     (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
        #     (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
        #     (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
        #     (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
        #     (-1, 0): img0,  # 左
        #     (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
        #     (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
        #     (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        #     (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
        #     (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
        #     (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        # }
        # self.dire = (+1, 0)
        # self.image = self.imgs[self.dire]
        self.image = img
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = 500

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/3.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            # self.image = self.imgs[self.dire]
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)
        screen.blit(self.image, self.rect)

        if self.state == "hyper":
            self.hyper_life -= 1
            if self.hyper_life < 0:
                self.state = "normal"


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "aaa"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = 1, 0
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 0.9)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class Shield(pg.sprite.Sprite):
    """
    防御壁に関するクラス
    """
    def __init__(self, bird: Bird, life: int):
        """
        防御壁を生成する
        引数1 bird：こうかとん
        引数2 life：防御壁の発動時間
        """
        super().__init__()
        # 空のSurfaceを作成
        self.image = pg.Surface((20,bird.rect.height * 2))
        
        # 矩形を描画
        pg.draw.rect(self.image, (0, 0, 255), (0, 0, 20, bird.rect.height * 2))
        self.rect = self.image.get_rect()

        # こうかとんの向きと位置を基に固定する
        vx, vy = bird.dire  # こうかとんの方向ベクトル
        angle = math.degrees(math.atan2(-vy, vx))  # 角度を計算
        self.rect.center = (
            bird.rect.right + 30,  # こうかとんの右端から少し離れた位置
            bird.rect.centery      # こうかとんの中央と同じ高さ
        )
        # 画像を回転
        # self.image = pg.transform.rotozoom(self.image, angle, 1.0)
        # self.image.set_colorkey((0,0,0))
        # self.rect = self.image.get_rect()

        # 防御壁をこうかとんから1体分ずらした位置に配置
        # offset_x = vx * bird.rect.width
        # offset_y = vy * bird.rect.height
        # self.rect.center = (bird.rect.centerx + offset_x, bird.rect.centery + offset_y)

        # 防御壁の寿命
        self.life = life
    
    def update(self):
        """
        防御壁の寿命を管理
        """
        self.life -= 1
        if self.life < 0:
            self.kill()  # 寿命が尽きたら消滅    


class EMP(pg.sprite.Sprite):
    """
    電磁パルス（EMP）に関するクラス
    """
    def __init__(self, bird: Bird, bombs: pg.sprite.Group, emys: pg.sprite.Group):
        """
        EMPを発動し、敵や爆弾を無効化する
        引数: bird: こうかとんインスタンス
        bombs: 爆弾のグループ
        emys: 敵機のグループ
        """
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        pg.draw.rect(self.image, (255, 255, 0, 128), (0, 0, WIDTH, HEIGHT))  # 半透明の黄色
        self.rect = self.image.get_rect()
        self.life = 10  # 時間表示
        
        for emy in emys:  # 敵を無効化し、爆弾を遅くする
            emy.interval = float("inf")  # 爆弾投下を無効化する
            emy.image = pg.transform.laplacian(emy.image)  # 敵の変更（見た目）
            emy.image.set_colorkey((0, 0, 0))
        for bomb in bombs:
            bomb.speed /= 2  # 爆弾の速度を半減する
            bomb.state = "inactive" 

    def update(self):
        """
        表示時間を管理する
        """
        self.life -= 1
        if self.life < 0:
            self.kill()

class GuidedBeam(pg.sprite.Sprite):
    """
    誘導ビームに関するクラス
    """
    def __init__(self, bird: Bird, emys: pg.sprite.Group):
        """
        誘導ビーム画像Surfaceを生成する
        引数1 bird：ビームを放つこうかとん
        引数2 emys：敵機のグループ
        """
        super().__init__()
        self.vx, self.vy = 1, 0
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), 0, 0.9)
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery
        self.rect.centerx = bird.rect.centerx + bird.rect.width
        self.speed = 10
        
        # 最も近い敵を特定
        nearest_emy = None
        min_dist = float('inf')
        for emy in emys:
            dx = emy.rect.centerx - self.rect.centerx
            dy = emy.rect.centery - self.rect.centery
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                nearest_emy = emy
        
        # 誘導対象となる敵がいる場合、その方向をターゲットとする
        if nearest_emy:
            dx = nearest_emy.rect.centerx - self.rect.centerx
            dy = nearest_emy.rect.centery - self.rect.centery
            norm = math.sqrt(dx**2 + dy**2)
            self.vx = dx/norm if norm > 0 else 1
            self.vy = dy/norm if norm > 0 else 0
            angle = math.degrees(math.atan2(-self.vy, self.vx))
            self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 0.9)

    def update(self):
        """
        誘導ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class Item(pg.sprite.Sprite):
    """
    アイテムに関するクラス
    """
    def __init__(self, x: int, y: int, type: str):
        """
        アイテムSurfaceを生成する
        引数1 x：アイテムのx座標
        引数2 y：アイテムのy座標
        引数3 type：アイテムの種類（"gravity", "shield", "emp", "hyper"）
        """
        super().__init__()
        self.type = type
        self.image = pg.Surface((30, 30))
        
        # アイテムの種類に応じて色を設定
        colors = {
            "gravity": (255, 0, 0),      # 赤
            "shield": (0, 0, 255),       # 青
            "emp": (255, 165, 0),        # オレンジ
            "hyper": (0, 255, 0),         # 緑
            "guided": (255, 0, 255)      # 紫（誘導ビーム用）
        }
        
        # 円形のアイテムを描画
        pg.draw.rect(self.image, colors[type], (5, 5, 20, 20))
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH + 15, y
        self.vx = -5  # 左方向への速度

    def update(self):
        """
        アイテムを落下させる
        """
        self.rect.centerx += self.vx
        if self.rect.right < 0:  # 左端から出たら消える
            self.kill()

class ItemStock:
    """
    アイテムの所持数を管理するクラス
    """
    def __init__(self):
        self.items = {
            "gravity": 0,  # 重力場の所持数
            "shield": 0,   # 防御壁の所持数
            "emp": 0,      # EMPの所持数
            "hyper": 0,     # 無敵モードの所持数
            "guided": 0    # 誘導ビームの所持数
        }
        # フォントの設定
        self.font = pg.font.Font(None, 30)
        
    def add_item(self, item_type: str):
        """
        アイテムを追加する
        """
        self.items[item_type] += 1
        
    def use_item(self, item_type: str) -> bool:
        """
        アイテムを使用する
        戻り値：使用可能な場合True、使用できない場合False
        """
        if self.items[item_type] > 0:
            self.items[item_type] -= 1
            return True
        return False
    
    def draw(self, screen: pg.Surface):
        """
        アイテムの所持数を画面に表示
        """
        colors = {
            "gravity": (255, 0, 0),      # 赤
            "shield": (0, 0, 255),       # 青
            "emp": (255, 165, 0),        # オレンジ
            "hyper": (0, 255, 0),         # 緑
            "guided": (255, 0, 255)      # 紫（誘導ビーム用）
        }
        keys = {
            "gravity": "Enter",
            "shield": "S",
            "emp": "E",
            "hyper": "RShift",
            "guided": "LShift"  # 左シフトキーで誘導ビーム
        }
        for i, (item_type, count) in enumerate(self.items.items()):
            # アイテムアイコンの表示
            icon = pg.Surface((20, 20))
            pg.draw.rect(icon, colors[item_type], (5, 5, 20, 20))
            icon.set_colorkey((0, 0, 0))
            screen.blit(icon, (10, 10 + i * 30))
            
            # 所持数の表示
            text = self.font.render(f"x{count} ({keys[item_type]}", True, (255, 255, 255))
            screen.blit(text, (35, 10 + i * 30))

def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    flip_bg_img = pg.transform.flip(bg_img, True, False)
    score = Score()
    item_stock = ItemStock()  # アイテム所持管理クラスのインスタンス化

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    shields = pg.sprite.Group()  # 防御壁グループを追加
    emps = pg.sprite.Group()  # EMPのグループ
    items = pg.sprite.Group()  # アイテムグループを追加
    gravity_group = pg.sprite.Group()

    tmr = 0
    emps.update()# EMPの更新と描画を追加
    emps.draw(screen)
      
    clock = pg.time.Clock()
    gravity_group = pg.sprite.Group()  # Gravityインスタンスを管理するグループ

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))
                # アイテム使用の判定（スコア条件を削除）
                elif event.key == pg.K_RETURN:  # 重力場
                    if item_stock.use_item("gravity"):
                        gravity_group.add(Gravity(400))
                elif event.key == pg.K_s:  # 防御壁
                    if item_stock.use_item("shield"):
                        shields.add(Shield(bird, 400))
                elif event.key == pg.K_e:  # EMP
                    if item_stock.use_item("emp"):
                        emps.add(EMP(bird, bombs, emys))
                elif event.key == pg.K_RSHIFT:  # 無敵モード
                    if item_stock.use_item("hyper"):
                        bird.state = "hyper"
                        bird.hyper_life = 500
                elif event.key == pg.K_LSHIFT:  # 誘導ビーム
                    if item_stock.use_item("guided"):
                        beams.add(GuidedBeam(bird, emys))
        # for event in pg.event.get():
        #     if event.type == pg.QUIT:
        #         return 0
        #     if event.type == pg.KEYDOWN:  # 必ず KEYDOWN のチェックを行う
        #         if event.key == pg.K_SPACE:
        #             beams.add(Beam(bird))
        #         if event.key == pg.K_s and score.value >= 50 and len(shields) == 0:
        #             score.value -= 50  # スコアを消費
        #             shields.add(Shield(bird, 400))  # 防御壁を生成
        #     if event.type == pg.KEYDOWN and event.key == pg.K_RETURN and score.value >= 200:
        #             # リターンキー押下で重力場を発動
        #             gravity_group.add(Gravity(400))
        #             score.value -= 200  # スコアを200減らす
        #     if event.type == pg.KEYDOWN and event.key == pg.K_e and score.value >= 20:
        #         score.value -= 20  # スコアを消費
        #         emps.add(EMP(bird, bombs, emys))  # EMPを発動 

        #     if key_lst[pg.K_RSHIFT] and score.value >= 100:
        #         score.value -= 100
        #         bird.state = "hyper"
        #         bird.hyper_life = 500
        
        # アイテムとの衝突判定
        for item in pg.sprite.spritecollide(bird, items, True):
            item_stock.add_item(item.type)  # アイテムをストックに追加

        X = tmr%3200
        screen.blit(bg_img, [-X*3, 0])
        screen.blit(flip_bg_img, [-X*3+1600, 0])
        screen.blit(bg_img, [-X*3+3200, 0])
        screen.blit(flip_bg_img, [-X*3+4800, 0])

        # ランダムなタイミングでアイテムを出現させる
        if tmr % 300 == 0:  # 300フレームごとに
            item_type = random.choice(["gravity", "shield", "emp", "hyper", "guided"])
            y = random.randint(0, HEIGHT)  # y座標をランダムに設定
            items.add(Item(WIDTH + 15, y, item_type))

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ# こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        # 重力場と爆弾、敵機の衝突判定
        for gravity in gravity_group:
            for bomb in pg.sprite.spritecollide(gravity, bombs, True):
                exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            for emy in pg.sprite.spritecollide(gravity, emys, True):
                exps.add(Explosion(emy, 100))  # 爆発エフェクト

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bomb.state == "inactive":
                continue
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))
                score.value += 1  # 1点アップ
                continue
            else:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
        # アイテムとの衝突判定
        for item in pg.sprite.spritecollide(bird, items, True):
            if item.type == "gravity" and score.value >= 200:
                gravity_group.add(Gravity(400))
                score.value -= 200
            elif item.type == "shield" and score.value >= 50:
                shields.add(Shield(bird, 400))
                score.value -= 50
            elif item.type == "emp" and score.value >= 20:
                emps.add(EMP(bird, bombs, emys))
                score.value -= 20
            elif item.type == "hyper" and score.value >= 100:
                bird.state = "hyper"
                bird.hyper_life = 500
                score.value -= 100

        gravity_group.update()
        gravity_group.draw(screen)
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        shields.update()
        shields.draw(screen)
        items.update()  # アイテムの更新
        items.draw(screen)  # アイテムの描画
        score.update(screen)
        item_stock.draw(screen)  # アイテムの所持数を表示
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
