import os
import random
import sys
import pygame as pg

# スクリプトの保存先フォルダをカレントディレクトリに変更
os.chdir(os.path.dirname(os.path.abspath(__file__)))

WIDTH = 1100
HEIGHT = 650
FPS = 60

pg.init()
pg.mixer.init()  # ← 【重要】サウンド機能を初期化

screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("こうかとんの杭打ち機回避ゲーム")
clock = pg.time.Clock()

# ==================== 【追加】BGM・効果音の読み込みと設定 ====================
pg.mixer.music.load("sound/bgm.mp3")
pg.mixer.music.play(-1)  # BGMループ再生
pg.mixer.music.set_volume(0.3)

impact_se = pg.mixer.Sound("sound/impact.mp3")
impact_se.set_volume(0.7)

score_se = pg.mixer.Sound("sound/score.mp3")
score_se.set_volume(0.4)

dash_se = pg.mixer.Sound("sound/dash.mp3")
dash_se.set_volume(1.0)
# ===========================================================================


def load_image_with_fallback(filenames):
    """実行環境に合わせて画像を探索"""
    for fname in filenames:
        candidates = [os.path.join("fig", fname), fname]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return pg.image.load(path)
                except Exception:
                    pass
    return None


# プレイヤー（こうかとん: 3.png / 人間: man.png）
class Player:

    def __init__(self, char_type="koukaton"):
        self.w = 65
        self.h = 65
        self.x = WIDTH // 2 - self.w // 2
        self.y = HEIGHT - 140
        self.normal_speed = 7.5
        self.boost_speed = 14.0
        self.rect = pg.Rect(self.x, self.y, self.w, self.h)
        self.facing_right = True

        filenames = ["man.png"] if char_type == "man" else ["3.png"]
        raw_img = load_image_with_fallback(filenames)
        if raw_img:
            base_img = raw_img.convert_alpha()
            try:
                base_img = pg.transform.smoothscale(base_img, (self.w, self.h))
            except Exception:
                base_img = pg.transform.scale(base_img, (self.w, self.h))
        else:
            base_img = pg.Surface((self.w, self.h))
            base_img.fill(
                (200, 200, 200) if char_type == "man" else (255, 200, 0)
            )

        if char_type == "man":
            self.img_right = base_img
            self.img_left = pg.transform.flip(base_img, True, False)
        else:
            self.img_left = base_img
            self.img_right = pg.transform.flip(base_img, True, False)

    def update(self, shift_pressed):
        keys = pg.key.get_pressed()
        spd = self.boost_speed if shift_pressed else self.normal_speed

        if keys[pg.K_a] or keys[pg.K_LEFT]:
            self.x -= spd
            self.facing_right = False
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            self.x += spd
            self.facing_right = True

        self.x = max(0, min(self.x, WIDTH - self.w))
        self.rect.x = self.x

    def draw(self, target_surf):
        img = self.img_right if self.facing_right else self.img_left
        target_surf.blit(img, self.rect)


# 杭打ち機の壁（上からの登場スピード強化版）
class HammerWall:

    def __init__(self, base_speed):
        self.h = 165
        self.y = -self.h
        self.gap_w = 135
        self.gap_x = random.randint(80, WIDTH - 80 - self.gap_w)

        self.base_down_speed = base_speed
        self.down_speed = base_speed
        self.rise_speed = 12

        self.state = "warning"
        self.warning_speed = 3.2
        self.warning_target_y = 15
        self.hold_timer = 25
        self.ground_hold_timer = 20
        self.update_rects()

    def update_rects(self):
        self.left_rect = pg.Rect(0, self.y, self.gap_x, self.h)
        self.right_rect = pg.Rect(
            self.gap_x + self.gap_w,
            self.y,
            WIDTH - (self.gap_x + self.gap_w),
            self.h,
        )

    def update(self):
        passed = False

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

            land_y = HEIGHT - self.h
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
                self.gap_x = random.randint(80, WIDTH - 80 - self.gap_w)

        self.update_rects()
        return passed

    def draw(self, target_surf):
        top_wall_height = max(0, int(self.y))
        if top_wall_height > 0:
            pg.draw.rect(
                target_surf, (80, 85, 100), (0, 0, WIDTH, top_wall_height)
            )

        if self.y + self.h > 0:
            pg.draw.rect(target_surf, (80, 85, 100), self.left_rect)
            pg.draw.rect(target_surf, (80, 85, 100), self.right_rect)

            line_color = (
                (255, 200, 0)
                if self.state in ["warning", "hold"]
                else (220, 60, 60)
            )
            pg.draw.rect(
                target_surf,
                line_color,
                (0, self.left_rect.bottom - 8, self.gap_x, 8),
            )
            pg.draw.rect(
                target_surf,
                line_color,
                (
                    self.gap_x + self.gap_w,
                    self.right_rect.bottom - 8,
                    WIDTH - (self.gap_x + self.gap_w),
                    8,
                ),
            )

            if self.y > 0:
                pg.draw.line(
                    target_surf,
                    (50, 55, 70),
                    (self.gap_x, self.y),
                    (self.gap_x + self.gap_w, self.y),
                    3,
                )

    def collide(self, player_rect):
        return self.left_rect.colliderect(player_rect) or self.right_rect.colliderect(
            player_rect
        )


# 背景描画
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
    score = 0
    state = "TITLE"
    char_types = ["koukaton", "man"]
    selected_char_idx = 0

    player = Player(char_types[selected_char_idx])
    wall = HammerWall(base_speed=15.0)
    prev_state = wall.state  # 音のタイミング検知用

    canvas = pg.Surface((WIDTH, HEIGHT))
    big_shake_timer = 0

    raw_bg = load_image_with_fallback(
        ["pg_bg.jpg", "background.jpg", "background.png"]
    )
    bg_img = (
        pg.transform.smoothscale(raw_bg.convert(), (WIDTH, HEIGHT))
        if raw_bg
        else None
    )

    font = pg.font.SysFont(
        ["meiryo", "hiraginosans", "yu gothic", "msgothic"], 36
    )
    font_large = pg.font.SysFont(
        ["meiryo", "hiraginosans", "yu gothic", "msgothic"], 50
    )

    while True:
        clock.tick(FPS)
        shift_pressed = pg.key.get_pressed()[pg.K_LSHIFT] or pg.key.get_pressed()[
            pg.K_RSHIFT
        ]

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()

            if event.type == pg.KEYDOWN:
                # 【追加】ダッシュ音（Shiftキーを押した瞬間）
                if event.key == pg.K_LSHIFT or event.key == pg.K_RSHIFT:
                    dash_se.play()

                if state == "TITLE":
                    # 矢印キーでキャラ切り替え
                    if event.key in (pg.K_LEFT, pg.K_RIGHT, pg.K_a, pg.K_d):
                        selected_char_idx = (selected_char_idx + 1) % 2
                        player = Player(char_types[selected_char_idx])
                    elif event.key == pg.K_SPACE:
                        state = "GAME"
                        player = Player(char_types[selected_char_idx])
                        wall = HammerWall(base_speed=15.0)
                        score = 0
                        pg.mixer.music.play(-1)  # ゲーム開始時にもBGMを再生

                elif state == "GAMEOVER" and event.key == pg.K_SPACE:
                    state = "TITLE"
                    player = Player(char_types[selected_char_idx])
                    pg.mixer.music.play(-1)  # タイトルに戻ったときもBGM再生

        draw_background(canvas, bg_img)

        # 1. スタート画面
        if state == "TITLE":
            t_surf = font_large.render(
                "こうかとんの杭打ち機回避ゲーム", True, (0, 200, 200)
            )
            s_surf = font.render(
                "◀ 矢印キーでキャラ選択 ▶  /  SPACE START", True, (255, 0, 0)
            )
            canvas.blit(t_surf, t_surf.get_rect(center=(WIDTH // 2, 200)))
            canvas.blit(s_surf, s_surf.get_rect(center=(WIDTH // 2, 280)))
            player.draw(canvas)

        # 2. プレイ画面
        elif state == "GAME":
            player.update(shift_pressed)

            if wall.update():
                score += 1
                wall.base_down_speed = 15.0 + score * 0.5
                big_shake_timer = 10
                score_se.play()  # 【追加】スコアアップ音

            # 【追加】壁が落下し始めた瞬間のインパクト音
            if wall.state == "falling" and prev_state != "falling":
                impact_se.play()

            prev_state = wall.state

            if wall.collide(player.rect):
                state = "GAMEOVER"
                pg.mixer.music.stop()  # ゲームオーバー時にBGM停止

            wall.draw(canvas)
            player.draw(canvas)

            text_color = (30, 30, 30) if bg_img else (255, 255, 255)
            score_surf = font.render(f"Score: {score}", True, text_color)
            canvas.blit(score_surf, (20, 20))

        # 3. ゲームオーバー画面
        elif state == "GAMEOVER":
            go_surf = font_large.render("しんだ", True, (255, 50, 50))
            sc_surf = font.render(f"Score: {score}", True, (255, 255, 255))
            rt_surf = font.render(
                "SPACEでタイトルに戻る", True, (255, 0, 0)
            )

            canvas.blit(go_surf, go_surf.get_rect(center=(WIDTH // 2, 220)))
            canvas.blit(sc_surf, sc_surf.get_rect(center=(WIDTH // 2, 300)))
            canvas.blit(rt_surf, rt_surf.get_rect(center=(WIDTH // 2, 370)))

        # ---------------- 画面振動 ----------------
        offset_x, offset_y = 0, 0
        if state == "GAME":
            if wall.state == "warning":
                offset_x, offset_y = random.randint(-2, 2), random.randint(
                    -2, 2
                )
            elif wall.state == "hold":
                offset_x, offset_y = random.randint(-10, 10), random.randint(
                    -10, 10
                )
            elif big_shake_timer > 0:
                big_shake_timer -= 1
                offset_x, offset_y = random.randint(-8, 8), random.randint(
                    -8, 8
                )

        screen.fill((0, 0, 0))
        screen.blit(canvas, (offset_x, offset_y))
        pg.display.flip()


if __name__ == "__main__":
    main()