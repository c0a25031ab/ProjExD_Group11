import os
import pygame as pg
import random
import sys

WIDTH = 1100
HEIGHT = 650
FPS = 60

# ↓追記部分
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # ファイルの基準ディレクトリを取得
os.chdir(BASE_DIR)  # カレントディレクトリの変更（必須記述）
# ↑追記部分

pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("こうかとんの杭打ち機回避ゲーム")
clock = pg.time.Clock()


def load_image_with_fallback(filenames):
    """実行環境に合わせて画像を探索"""
    for fname in filenames:
        # ↓追記部分
        candidates = [
            os.path.join(BASE_DIR, "fig", fname),  # 絶対パス指定で画像の探索精度向上
            os.path.join(BASE_DIR, fname),
            fname
        ]
        # ↑追記部分
        for path in candidates:
            if os.path.exists(path):
                try:
                    return pg.image.load(path)
                except Exception:
                    pass
    return None


# ----------------------------------------------------
# プレイヤー（こうかとん）クラス
# ----------------------------------------------------
class Player:
    """プレイヤーの移動・ジャンプ・しゃがみ状態を管理するクラス"""

    def __init__(self) -> None:
        self.w: int = 65
        # ↓追記部分
        self.base_h: int = 65                # 通常時の高さを保持（しゃがみ解除用）
        self.h: int = self.base_h
        self.x: float = WIDTH // 2 - self.w // 2
        self.base_y: float = HEIGHT - 115    # 地上の初期Y座標を保持（着地用）
        self.y: float = self.base_y
        # ↑追記部分
        self.normal_speed: float = 7.5
        self.boost_speed: float = 14.0

        # ↓追記部分
        # ジャンプ・しゃがみ用パラメータ
        self.is_jumping: bool = False        # ジャンプ中かどうか
        self.jump_power: float = -20.0       # ジャンプした瞬間の上方向への速度
        self.gravity: float = 1.2            # 毎フレームかかる重力加速度
        self.vy: float = 0.0                 # 現在のY軸方向の速度

        self.is_crouching: bool = False      # しゃがみ中かどうか
        # ↑追記部分

        self.rect: pg.Rect = pg.Rect(self.x, self.y, self.w, self.h)
        self.facing_right: bool = True

        raw_img = load_image_with_fallback(["3.png"])
        if raw_img:
            base_img = raw_img.convert_alpha()
            try:
                base_img = pg.transform.smoothscale(base_img, (self.w, self.base_h))
            except Exception:
                base_img = pg.transform.scale(base_img, (self.w, self.base_h))
        else:
            base_img = pg.Surface((self.w, self.base_h))
            base_img.fill((255, 200, 0))

        self.img_left = base_img
        self.img_right = pg.transform.flip(base_img, True, False)

    def update(self, shift_pressed: bool) -> None:
        """キー入力に応じて移動・ジャンプ・しゃがみ状態を更新する"""
        keys = pg.key.get_pressed()
        spd = self.boost_speed if shift_pressed else self.normal_speed

        # 左右移動
        if keys[pg.K_a] or keys[pg.K_LEFT]:
            self.x -= spd
            self.facing_right = False
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            self.x += spd
            self.facing_right = True

        self.x = max(0, min(self.x, WIDTH - self.w))

        # ↓追記部分
        # しゃがみ処理 (Sキー / ↓キー)
        if (keys[pg.K_s] or keys[pg.K_DOWN]) and not self.is_jumping:
            self.is_crouching = True
            self.h = 30                      # 身長を小さくする
            self.y = self.base_y + (self.base_h - self.h)  # 足元が浮かないようY座標を下方に調整
        else:
            self.is_crouching = False
            self.h = self.base_h
            if not self.is_jumping:
                self.y = self.base_y

        # ジャンプ開始 (Wキー / ↑キー / Spaceキー)
        if (keys[pg.K_w] or keys[pg.K_UP] or keys[pg.K_SPACE]) and not self.is_jumping and not self.is_crouching:
            self.is_jumping = True
            self.vy = self.jump_power        # 上方向の速度を設定

        # ジャンプ物理処理
        if self.is_jumping:
            self.y += self.vy
            self.vy += self.gravity          # 重力で下降速度を加速
            if self.y >= self.base_y:        # 地面に達したら着地
                self.y = self.base_y
                self.is_jumping = False
                self.vy = 0.0
        # ↑追記部分

        self.rect = pg.Rect(self.x, self.y, self.w, self.h)

    def draw(self, target_surf: pg.Surface) -> None:
        """プレイヤー描画"""
        img = self.img_right if self.facing_right else self.img_left
        # ↓追記部分
        if self.is_crouching:
            scaled_img = pg.transform.scale(img, (self.w, self.h))  # しゃがみ用に縦幅を縮小して描画
            target_surf.blit(scaled_img, self.rect)
        else:
            target_surf.blit(img, self.rect)
        # ↑追記部分


# ----------------------------------------------------
# 杭打ち機の壁クラス
# ----------------------------------------------------
class HammerWall:
    """色ごとに異なる回避方法を迫る壁クラス"""

    def __init__(self, base_speed: float) -> None:
        self.h: int = 165
        self.y: float = -self.h
        self.gap_w: int = 135
        self.gap_x: int = random.randint(80, WIDTH - 80 - self.gap_w)

        self.base_down_speed: float = base_speed
        self.down_speed: float = base_speed
        self.rise_speed: float = 12.0

        # ↓追記部分
        self.wall_type: str = random.choice(["normal", "crouch", "jump"])  # 壁の種類（通常/しゃがみ回避/ジャンプ回避）をランダムに設定
        self.dodged: bool = False            # 今回の壁の回避に成功したかどうかのフラグ
        # ↑追記部分

        self.state: str = "warning"
        self.warning_speed: float = 3.2
        self.warning_target_y: float = 15.0
        self.hold_timer: int = 25
        self.ground_hold_timer: int = 20

        self.update_rects()

    def update_rects(self) -> None:
        """壁のタイプに応じたRectサイズの設定"""
        # ↓追記部分
        if self.wall_type == "normal":
            self.left_rect = pg.Rect(0, self.y, self.gap_x, self.h)
            self.right_rect = pg.Rect(self.gap_x + self.gap_w, self.y, WIDTH - (self.gap_x + self.gap_w), self.h)
        elif self.wall_type == "crouch":
            self.left_rect = pg.Rect(0, self.y, WIDTH, 120)       # 画面全体を覆う高い壁
            self.right_rect = pg.Rect(0, 0, 0, 0)
        elif self.wall_type == "jump":
            self.left_rect = pg.Rect(0, self.y, WIDTH, 60)        # 画面全体を覆う低い壁
            self.right_rect = pg.Rect(0, 0, 0, 0)
        # ↑追記部分

    def update(self) -> bool:
        """壁の落下・上昇アニメーション更新"""
        passed: bool = False

        if self.state == "warning":
            self.y += self.warning_speed
            if self.y >= self.warning_target_y:
                self.state = "hold"
                self.timer = self.hold_timer

        elif self.state == "hold":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "falling"
                self.down_speed = self.base_down_speed

        elif self.state == "falling":
            self.y += self.down_speed
            self.down_speed += 2.5

            # ↓追記部分
            # 壁の種類ごとに止まる高さ（足元の隙間）を変更
            if self.wall_type == "crouch":
                land_y = HEIGHT - 220         # 隙間を50pxにし、しゃがみ(30px)でのみ通れるように調整（棒立ち65pxは激突）
            elif self.wall_type == "jump":
                land_y = HEIGHT - 115         # ジャンプで飛び越える高さで停止
            else:
                land_y = HEIGHT - self.h
            # ↑追記部分

            if self.y >= land_y:
                self.y = land_y
                self.state = "ground_hold"
                self.timer = self.ground_hold_timer
                passed = True

        elif self.state == "ground_hold":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "rising"

        elif self.state == "rising":
            self.y -= self.rise_speed
            if self.y <= -self.h:
                self.state = "warning"
                self.timer = self.hold_timer
                # ↓追記部分
                self.wall_type = random.choice(["normal", "crouch", "jump"])  # 次に降ってくる壁の種類を選び直す
                self.gap_x = random.randint(80, WIDTH - 80 - self.gap_w)
                self.dodged = False           # 次の壁用に回避フラグをリセット
                # ↑追記部分

        self.update_rects()
        return passed

    def draw(self, target_surf: pg.Surface) -> None:
        """壁の描画"""
        # ↓追記部分
        # 壁のタイプごとに配色を変更
        if self.wall_type == "crouch":
            wall_color = (200, 60, 60)        # 赤色（しゃがみ回避）
            line_color = (255, 120, 120)
        elif self.wall_type == "jump":
            wall_color = (60, 100, 220)       # 青色（ジャンプ回避）
            line_color = (120, 180, 255)
        else:
            wall_color = (80, 85, 100)        # グレー（隙間移動回避）
            line_color = (255, 200, 0) if self.state in ["warning", "hold"] else (220, 60, 60)
        # ↑追記部分

        top_wall_height = max(0, int(self.y))
        if top_wall_height > 0 and self.wall_type == "normal":
            pg.draw.rect(target_surf, wall_color, (0, 0, WIDTH, top_wall_height))

        if self.y + self.h > 0:
            pg.draw.rect(target_surf, wall_color, self.left_rect)
            if self.wall_type == "normal":
                pg.draw.rect(target_surf, wall_color, self.right_rect)
                pg.draw.rect(target_surf, line_color, (0, self.left_rect.bottom - 8, self.gap_x, 8))
                pg.draw.rect(target_surf, line_color, (self.gap_x + self.gap_w, self.right_rect.bottom - 8, WIDTH - (self.gap_x + self.gap_w), 8))
            else:
                # ↓追記部分
                pg.draw.rect(target_surf, line_color, (0, self.left_rect.bottom - 8, WIDTH, 8))  # 全幅の警告ラインを描画
                # ↑追記部分

    # ↓追記部分
    def collide(self, player: Player) -> bool:
        """衝突判定
        
        - 判定対象を player.rect から Player オブジェクト全体に変更
        - 一度回避に成功した壁は dodged = True にして、壁が上昇するまで当たり判定を無効化
        """
        if self.dodged:
            return False                      # すでに回避成功していれば当たり判定をスルー

        if self.wall_type == "crouch":
            if player.is_crouching:
                self.dodged = True            # しゃがんでいれば回避成功フラグON
                return False
            return self.left_rect.colliderect(player.rect)

        elif self.wall_type == "jump":
            if player.is_jumping:
                self.dodged = True            # ジャンプしていれば回避成功フラグON
                return False
            return self.left_rect.colliderect(player.rect)

        else:
            hitbox = player.rect.inflate(-8, -8)  # すれ違い時の当たり判定調整
            return self.left_rect.colliderect(hitbox) or self.right_rect.colliderect(hitbox)
    # ↑追記部分


def draw_background(target_surf, bg_img):
    if bg_img:
        target_surf.blit(bg_img, (0, 0))
    else:
        target_surf.fill((20, 24, 38))
        for x in range(0, WIDTH, 50):
            pg.draw.line(target_surf, (32, 38, 58), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 50):
            pg.draw.line(target_surf, (32, 38, 58), (0, y), (WIDTH, y))


def main():
    player = Player()
    wall = HammerWall(base_speed=15.0)
    score = 0
    game_over = False

    canvas = pg.Surface((WIDTH, HEIGHT))
    big_shake_timer = 0

    raw_bg = load_image_with_fallback(["pg_bg.jpg", "background.jpg", "background.png"])
    if raw_bg:
        try:
            bg_img = pg.transform.smoothscale(raw_bg.convert(), (WIDTH, HEIGHT))
        except Exception:
            bg_img = pg.transform.scale(raw_bg.convert(), (WIDTH, HEIGHT))
    else:
        bg_img = None

    font = pg.font.SysFont(["meiryo", "hiraginosans", "yu gothic", "msgothic"], 36)

    while True:
        clock.tick(FPS)
        shift_pressed = pg.key.get_pressed()[pg.K_LSHIFT] or pg.key.get_pressed()[pg.K_RSHIFT]

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()

        if not game_over:
            player.update(shift_pressed)

            if wall.update():
                score += 1
                wall.base_down_speed = 15.0 + score * 0.5
                big_shake_timer = 10

            # ↓追記部分
            if wall.collide(player):          # 判定処理にPlayerオブジェクト自体を渡すように修正
                game_over = True
            # ↑追記部分

        draw_background(canvas, bg_img)
        wall.draw(canvas)
        player.draw(canvas)

        text_color = (30, 30, 30) if bg_img else (255, 255, 255)
        score_surf = font.render(f"Score: {score}", True, text_color)
        canvas.blit(score_surf, (20, 20))

        offset_x = 0
        offset_y = 0

        if wall.state == "warning":
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)
        elif wall.state == "hold":
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)
        elif big_shake_timer > 0:
            big_shake_timer -= 1
            offset_x = random.randint(-8, 8)
            offset_y = random.randint(-8, 8)

        screen.fill((0, 0, 0))
        screen.blit(canvas, (offset_x, offset_y))

        pg.display.flip()


if __name__ == "__main__":
    main()