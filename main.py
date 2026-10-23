__version__ = "12.0.0"
GITHUB_REPO = "devzerox113-crypto/BilimUp"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
import base64, datetime, hashlib, json, math, os, random, re, time
import urllib.parse, urllib.request, threading, webbrowser
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import escape_markup
from kivy.utils import get_color_from_hex as hx

BG, CARD, BLUE, GREEN, RED, GRAY = "#07070D", "#171735", "#5B5CE2", "#0F9F8F", "#E5486D", "#30304B"
Window.clearcolor = hx(BG)
THEMES = {"Түнгі көк": (BG, CARD), "Қара": ("#000000", "#171722"), "Жасыл": ("#071A18", "#123B36"), "Күлгін": ("#090817", "#211A48")}
AV = ["#5B5CE2", "#E5486D", "#0F9F8F", "#F59E0B", "#8B5CF6", "#D946EF", "#06B6D4", "#84CC16"]
PROFILES = [("Физика – Математика", ["Физика", "Математика"]), ("Информатика – Математика", ["Информатика", "Математика"]),
            ("Биология – Химия", ["Биология", "Химия"]), ("Биология – География", ["Биология", "География"]),
            ("География – Математика", ["География", "Математика"]), ("Химия – Физика", ["Химия", "Физика"])]
T = dict(bg=BG, card=CARD)

def apply_theme(name):
    bg, card = THEMES.get(name, THEMES["Түнгі көк"]); T.update(bg=bg, card=card); Window.clearcolor = hx(bg)
HERE = os.path.dirname(os.path.abspath(__file__))
ALL, MISTAKES, PER_TEST = "Барлық пәндер", "Қателермен жұмыс", 15
DAILY, DAILY_MODE = 30, "Күнделікті 30 сұрақ"


CALC_ERR = (ValueError, ZeroDivisionError, OverflowError, RecursionError)
TOK = re.compile(r"\s*(\d+\.?\d*|\.\d+|asin|acos|atan|sin|cos|tan|ln|log|ANS|π|e|[-+×÷^()%√!])")
FUNCS = ("sin", "cos", "tan", "asin", "acos", "atan", "ln", "log")
STARTS = set(FUNCS) | {"(", "π", "e", "ANS", "√"}


def tokenize(s):
    s, out, pos = s.strip(), [], 0
    while pos < len(s):
        m = TOK.match(s, pos)
        if not m: raise ValueError("bad")
        out.append(m.group(1)); pos = m.end()
    return out


def fmt(v):
    if v != v or v in (float("inf"), float("-inf")): raise ValueError("nan")
    if abs(v) < 1e-12: v = 0.0
    if v == int(v) and abs(v) < 1e15: return str(int(v))
    return f"{v:.10g}"


class Ev:
    """Қауіпсіз өрнек есептегіш (eval қолданылмайды)."""
    def __init__(self, toks, deg=True, ans=0.0): self.t, self.i, self.deg, self.ans = toks, 0, deg, ans
    def peek(self): return self.t[self.i] if self.i < len(self.t) else None
    def eat(self): t = self.peek(); self.i += 1; return t
    def parse(self):
        v = self.expr()
        if self.peek() is not None: raise ValueError("tail")
        return v
    def expr(self):
        v = self.term()
        while self.peek() in ("+", "-"):
            v = v + self.term() if self.eat() == "+" else v - self.term()
        return v
    def term(self):
        v = self.unary()
        while True:
            t = self.peek()
            if t == "×": self.eat(); v *= self.unary()
            elif t == "÷": self.eat(); v /= self.unary()
            elif t is not None and (t[0].isdigit() or t[0] == "." or t in STARTS): v *= self.unary()
            else: return v
    def unary(self):
        t = self.peek()
        if t == "-": self.eat(); return -self.unary()
        if t == "+": self.eat(); return self.unary()
        return self.power()
    def power(self):
        b = self.post()
        if self.peek() == "^":
            self.eat(); r = b ** self.unary()
            if isinstance(r, complex): raise ValueError("complex")
            return r
        return b
    def post(self):
        v = self.prim()
        while self.peek() in ("%", "!"):
            if self.eat() == "%": v /= 100
            else:
                if v < 0 or v != int(v) or v > 170: raise ValueError("fact")
                v = float(math.factorial(int(v)))
        return v
    def close(self, v):
        if self.peek() == ")": self.eat()
        elif self.peek() is not None: raise ValueError("paren")
        return v
    def prim(self):
        t = self.eat()
        if t is None: raise ValueError("end")
        if t[0].isdigit() or t[0] == ".": return float(t)
        if t == "(": return self.close(self.expr())
        if t == "π": return math.pi
        if t == "e": return math.e
        if t == "ANS": return self.ans
        if t == "√": return math.sqrt(self.prim())
        if t in FUNCS:
            if self.eat() != "(": raise ValueError("fn")
            return self.fn(t, self.close(self.expr()))
        raise ValueError("tok")
    def fn(self, t, v):
        d = self.deg
        if t in ("sin", "cos", "tan"):
            a = math.radians(v) if d else v
            if t == "tan" and ((d and v % 180 == 90) or (not d and abs(math.cos(a)) < 1e-12)): raise ValueError("tan")
            r = getattr(math, t)(a)
        elif t in ("asin", "acos", "atan"):
            r = getattr(math, t)(v); r = math.degrees(r) if d else r
        elif t == "ln": r = math.log(v)
        else: r = math.log10(v)
        return 0.0 if abs(r) < 1e-12 else r


GUEST_MAX = 3
WA = [("+7 707 715 3750", "77077153750"), ("+7 707 454 8249", "77074548249")]  # WhatsApp нөмірлері
ADMIN_PUB = bytes.fromhex("6a68f2c60c0c31289dfe6fa3667f89feda2c724a3f20efe1a6632f613c50928c")

# ---------- Ed25519 (RFC 8032, таза Python): тіркеу кодтарын офлайн тексеру ----------
_p = 2 ** 255 - 19
_d = -121665 * pow(121666, _p - 2, _p) % _p
_q = 2 ** 252 + 27742317777372353535851937790883648493
_I = pow(2, (_p - 1) // 4, _p)
_inv = lambda x: pow(x, _p - 2, _p)
_H = lambda m: hashlib.sha512(m).digest()


def _xrec(y, sign):
    x2 = (y * y - 1) * _inv(_d * y * y + 1) % _p
    x = pow(x2, (_p + 3) // 8, _p)
    if (x * x - x2) % _p: x = x * _I % _p
    if (x * x - x2) % _p: return None
    return _p - x if (x & 1) != sign else x


_By = 4 * _inv(5) % _p
_Bx = _xrec(_By, 0)
_B = (_Bx, _By, 1, _Bx * _By % _p)


def _add(P, Q):
    A, B = (P[1] - P[0]) * (Q[1] - Q[0]) % _p, (P[1] + P[0]) * (Q[1] + Q[0]) % _p
    C, D = 2 * P[3] * Q[3] * _d % _p, 2 * P[2] * Q[2] % _p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _p, G * H % _p, F * G % _p, E * H % _p)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s:
        if s & 1: Q = _add(Q, P)
        P = _add(P, P); s >>= 1
    return Q


def _enc(P):
    zi = _inv(P[2]); x, y = P[0] * zi % _p, P[1] * zi % _p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _dec(b):
    y = int.from_bytes(b, "little"); sign = y >> 255; y &= (1 << 255) - 1
    x = _xrec(y, sign)
    if x is None: raise ValueError("pt")
    return (x, y, 1, x * y % _p)


def _clamp(h): return (int.from_bytes(h[:32], "little") & ((1 << 254) - 8)) | (1 << 254)
def ed_pub(seed): return _enc(_mul(_clamp(_H(seed)), _B))


def ed_sign(seed, msg):
    h = _H(seed); a = _clamp(h); A = _enc(_mul(a, _B))
    r = int.from_bytes(_H(h[32:] + msg), "little") % _q; R = _enc(_mul(r, _B))
    k = int.from_bytes(_H(R + A + msg), "little") % _q
    return R + int.to_bytes((r + k * a) % _q, 32, "little")


def ed_verify(pub, msg, sig):
    try:
        A, R, S = _dec(pub), _dec(sig[:32]), int.from_bytes(sig[32:], "little")
        if S >= _q: return False
        k = int.from_bytes(_H(sig[:32] + pub + msg), "little") % _q
        return _enc(_mul(S, _B)) == _enc(_add(R, _mul(k, A)))
    except Exception: return False


LOGIN_RE = r"[a-z0-9_]{3,20}"


def make_token(seed, login):
    return login + "." + base64.b32encode(ed_sign(seed, b"UBT1|" + login.encode())).decode().rstrip("=")


def verify_token(tok):
    try:
        lg, _, s = tok.strip().rpartition(".")
        if not re.fullmatch(LOGIN_RE, lg): return ""
        sig = base64.b32decode(s.upper() + "=" * (-len(s) % 8))
        return lg if len(sig) == 64 and ed_verify(ADMIN_PUB, b"UBT1|" + lg.encode(), sig) else ""
    except Exception: return ""


def open_url(url):
    try:
        from kivy.utils import platform
        if platform == "android":
            from jnius import autoclass
            Intent, Uri = autoclass("android.content.Intent"), autoclass("android.net.Uri")
            autoclass("org.kivy.android.PythonActivity").mActivity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            return
    except Exception: pass
    import webbrowser; webbrowser.open(url)


# ---------- тілдер: қазақша / русский / English ----------
LANG = ["kk"]
ITEMS = [
 ("ҰБТ ДАЙЫНДЫҚ", "ПОДГОТОВКА К ЕНТ", "UNT PREP"), ("Аралас тест (барлық пәндер)", "Смешанный тест (все предметы)", "Mixed test (all subjects)"),
 ("ҰБТ профильдері (2 пән)", "Профили ЕНТ (2 предмета)", "UNT profiles (2 subjects)"), ("ҰБТ профильдері", "Профили ЕНТ", "UNT profiles"),
 ("Тест: Қазақстан тарихы + Математика + 2 профиль пәні, әрқайсысынан 10 сұрақ.", "Тест: История Казахстана + Математика + 2 профильных предмета, по 10 вопросов.", "Test: History of Kazakhstan + Math + 2 profile subjects, 10 questions each."),
 ("Калькулятор", "Калькулятор", "Calculator"), ("Калк.", "Калькул.", "Calc"), ("Статистиканы тазалау", "Сбросить статистику", "Reset statistics"),
 ("Қателермен жұмыс", "Работа над ошибками", "Review mistakes"), ("Бүгінгі мақсат:", "Цель на сегодня:", "Today's goal:"), ("Қатар:", "Серия:", "Streak:"),
 ("Бүгінгі 30 сұрақ орындалды!", "Вопросы на сегодня выполнены!", "Today's questions completed!"), ("Бүгінгі жоспар орындалды!", "План на сегодня выполнен!", "Today's plan completed!"),
 ("Бүгінгі 30 сұрақ (қалды:", "Вопросы на сегодня (осталось:", "Today's questions (left:"), ("Тесттер:", "Тестов:", "Tests:"), ("Жауап:", "Ответов:", "Answers:"),
 ("Дұрыс жауап!", "Верно!", "Correct!"), ("Дұрыс:", "Верно:", "Correct:"), ("Қате.", "Неверно.", "Wrong."), ("Ұпай:", "Счёт:", "Score:"), ("Шығу", "Выход", "Exit"),
 ("Келесі", "Далее", "Next"), ("Аяқтау", "Завершить", "Finish"), ("Тест аяқталды!", "Тест завершён!", "Test finished!"), ("Нәтиже:", "Результат:", "Result:"),
 ("Уақыт:", "Время:", "Time:"), ("Бүгін:", "Сегодня:", "Today:"), ("Тамаша!", "Отлично!", "Great!"), ("Жақсы, жалғастыр!", "Хорошо, продолжай!", "Good, keep going!"),
 ("Қайталау керек", "Нужно повторить", "Needs review"), ("Қайта тапсыру", "Пройти заново", "Retry"), ("Басты бет", "Главная", "Home"), ("Артқа", "Назад", "Back"),
 ("Профиль және баптаулар", "Профиль и настройки", "Profile & settings"), ("Есімің:", "Твоё имя:", "Your name:"), ("Аватар түсі:", "Цвет аватара:", "Avatar color:"),
 ("Тақырып (фон):", "Тема (фон):", "Theme (background):"), ("Админ панель", "Админ-панель", "Admin panel"), ("Профильді баптау", "Настроить профиль", "Set up profile"),
 ("Баптау", "Настройки", "Settings"), ("Сұрақ жоқ.", "Вопросов нет.", "No questions."), ("Қателер әзірше жоқ!", "Ошибок пока нет!", "No mistakes yet!"),
 ("Қосымша тест үшін пәнді таңдаңыз.", "Для дополнительного теста выберите предмет.", "Pick a subject for an extra test."),
 ("Аккаунт", "Аккаунт", "Account"), ("Қонақ", "Гость", "Guest"), ("Кіру / Тіркелу", "Войти / Регистрация", "Log in / Register"), ("Кіру", "Войти", "Log in"),
 ("Аккаунттан шығу", "Выйти из аккаунта", "Log out"), ("Сіз кірдіңіз:", "Вы вошли как:", "Logged in as:"), ("Тіркеу коды", "Код регистрации", "Registration code"),
 ("Код дұрыс емес", "Неверный код", "Invalid code"), ("Атыңыз", "Ваше имя", "Your name"), ("Алдымен атыңызды жазыңыз", "Сначала введите имя", "Enter your name first"),
 ("Тіркелу тек админ арқылы жүреді. Атыңызды жазып, төмендегі түймені басыңыз - WhatsApp ашылып, хабарлама дайын болады.", "Регистрация только через администратора. Введите имя и нажмите кнопку ниже - откроется WhatsApp с готовым сообщением.", "Registration is only through the administrator. Enter your name and tap a button below - WhatsApp opens with a ready message."),
 ("Тегін 3 тест аяқталды. Жалғастыру үшін тіркеліңіз немесе аккаунтқа кіріңіз.", "Бесплатные 3 теста закончились. Зарегистрируйтесь или войдите в аккаунт.", "The 3 free tests are used up. Register or log in to continue."),
 ("Тіл:", "Язык:", "Language:"), ("WhatsApp-қа жазу", "Написать в WhatsApp", "Message on WhatsApp"),
 ("Қазақстан тарихы", "История Казахстана", "History of Kazakhstan"), ("Математика", "Математика", "Mathematics"), ("Информатика", "Информатика", "Computer science"),
 ("Физика", "Физика", "Physics"), ("Химия", "Химия", "Chemistry"), ("Биология", "Биология", "Biology"), ("География", "География", "Geography"),
 ("Ағылшын тілі", "Английский язык", "English"), ("Орыс тілі", "Русский язык", "Russian")]
ITEMS.sort(key=lambda t: -len(t[0]))


def L(s):
    lg = LANG[0]
    if lg == "kk" or not isinstance(s, str): return s
    i = 1 if lg == "ru" else 2
    for t in ITEMS:
        if t[0] in s: s = s.replace(t[0], t[i])
    if "Серия:" in s: s = s.replace(" күн", " дн.")
    if "Streak:" in s: s = s.replace(" күн", " days")
    return s


class WLabel(Label):
    """Жолға бөлінетін, биіктігі мәтінге сай өзгеретін Label."""
    def __init__(self, **kw):
        if kw.pop("tr", True) and "text" in kw: kw["text"] = L(kw["text"])
        kw.setdefault("markup", True); kw.setdefault("halign", "left")
        kw.setdefault("valign", "top"); kw.setdefault("size_hint_y", None)
        super().__init__(**kw)
        self.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
        self.bind(texture_size=lambda i, s: setattr(i, "height", s[1] + dp(8)))


def btn(text, color=None, h=52, cb=None, tr=True):
    color = color or T["card"]
    if tr: text = L(text)
    b = Button(text=text, size_hint_y=None, height=dp(h), background_normal="",
               background_color=hx(color), color=(1, 1, 1, 1), halign="center", valign="middle")
    b.bind(width=lambda i, w: setattr(i, "text_size", (w - dp(20), None)))
    b.bind(texture_size=lambda i, s: setattr(i, "height", max(dp(h), s[1] + dp(24))))
    if cb: b.bind(on_release=cb)
    return b


def vbox(**kw):
    b = BoxLayout(orientation="vertical", size_hint_y=None, **kw)
    b.bind(minimum_height=b.setter("height"))
    return b


class UBTApp(App):
    def build(self):
        self.title = "BilimUp"
        qs = self.read_json(os.path.join(HERE, "questions.json"), [])
        self.questions = [q for q in qs if isinstance(q, dict) and q.get("options") and "question" in q]
        self.custom_path = os.path.join(self.user_data_dir, "custom_questions.json")
        self.custom = [q for q in self.read_json(self.custom_path, []) if isinstance(q, dict) and q.get("options") and "question" in q]
        self.questions += self.custom
        self.stats_path = os.path.join(self.user_data_dir, "stats.json")
        st = self.read_json(self.stats_path, {})
        for k, v in (("tests", 0), ("total", 0), ("correct", 0), ("subjects", {}), ("wrong", []), ("today", 0), ("day", ""), ("streak", 0), ("last_day", ""), ("theme", "Түнгі көк"), ("name", ""), ("avatar", 0), ("pin", ""), ("user", ""), ("guest", 0), ("lang", "kk"), ("adm", "")):
            st.setdefault(k, v)
        self.stats, self.timer = st, None
        self.roll_day()
        apply_theme(st["theme"]); LANG[0] = st["lang"]; self.acc_note = ""
        self.cx = self.cres = ""; self.cdeg, self.cinv, self.cans, self.cfresh, self.cpop = True, False, 0.0, False, None
        self.sm = ScreenManager()
        for n in ("home", "quiz", "res", "set", "adm", "prof", "calc", "acc", "cod"): self.sm.add_widget(Screen(name=n))
        Window.bind(on_keyboard=self.on_key)
        self.show_home()
        Clock.schedule_once(lambda _dt: self.check_github_update(), 3)
        return self.sm

    # ---------- BilimUp автообнова (GitHub Releases) ----------
    def check_github_update(self, *_):
        """GitHub Releases-тегі соңғы нұсқаны фондық ағынмен тексереді."""
        def worker():
            try:
                req = urllib.request.Request(
                    GITHUB_RELEASES_API,
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "BilimUp-Updater"},
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    release = json.loads(response.read().decode("utf-8"))
                tag = str(release.get("tag_name", "")).strip().lstrip("vV")
                if not tag or release.get("draft") or release.get("prerelease"):
                    return
                def version_tuple(value):
                    nums = re.findall(r"\d+", value)
                    return tuple(int(n) for n in nums) if nums else (0,)
                if version_tuple(tag) > version_tuple(__version__):
                    url = release.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases/latest"
                    notes = (release.get("body") or "").strip()
                    Clock.schedule_once(lambda _dt: self.show_update_popup(tag, url, notes), 0)
            except Exception:
                # Интернет болмаса немесе Release жарияланбаса, қолданба қалыпты ашыла береді.
                return
        threading.Thread(target=worker, daemon=True).start()

    def show_update_popup(self, version, release_url, notes=""):
        body = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        msg = f"BilimUp {version} нұсқасы шықты.\n\nҚазір орнатылған нұсқа: {__version__}"
        if notes:
            msg += "\n\n" + notes[:500]
        body.add_widget(Label(text=msg, halign="center", valign="middle"))
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        later = Button(text="Кейінірек")
        update = Button(text="Жаңартуды ашу", background_normal="", background_color=hx(BLUE))
        popup = Popup(title="BilimUp жаңартуы", content=body, size_hint=(.9, .55), auto_dismiss=True)
        def open_release(*_):
            popup.dismiss()
            try:
                webbrowser.open(release_url)
            except Exception:
                self.popup("GitHub Releases бетін ашыңыз: " + release_url)
        later.bind(on_release=popup.dismiss)
        update.bind(on_release=open_release)
        buttons.add_widget(later); buttons.add_widget(update)
        body.add_widget(buttons)
        popup.open()

    # ---------- қызметші ----------
    @staticmethod
    def read_json(path, default):
        try:
            with open(path, encoding="utf-8") as f: return json.load(f)
        except (OSError, ValueError): return default

    def save_stats(self):
        try:
            with open(self.stats_path, "w", encoding="utf-8") as f: json.dump(self.stats, f, ensure_ascii=False)
        except OSError: pass

    def put(self, name, widget):
        s = self.sm.get_screen(name); s.clear_widgets(); s.add_widget(widget); self.sm.current = name

    def popup(self, text):
        Popup(title="", separator_height=0, content=Label(text=L(text)), size_hint=(.8, .25)).open()

    def on_key(self, window, key, *a):
        if key == 27 and self.cpop: self.cpop.dismiss(); return True
        if key == 27 and self.sm.current != "home":  # Android «Артқа»
            self.show_home(); return True
        return False

    def stop_timer(self):
        if self.timer: self.timer.cancel(); self.timer = None

    def fmt(self, sec): return f"{int(sec)//60:02d}:{int(sec)%60:02d}"

    def wrong_questions(self):
        w = set(self.stats["wrong"]); return [q for q in self.questions if q["question"] in w]

    def roll_day(self):
        today = datetime.date.today().isoformat()
        if self.stats["day"] != today:
            self.stats["day"], self.stats["today"] = today, 0

    def streak(self):
        y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        return self.stats["streak"] if self.stats["last_day"] in (self.stats["day"], y) else 0

    @staticmethod
    def mixed(pool, n):
        groups = {}
        for q in pool: groups.setdefault(q.get("subject", "Басқа"), []).append(q)
        for g in groups.values(): random.shuffle(g)
        out = []
        while len(out) < n and any(groups.values()):
            for g in groups.values():
                if g and len(out) < n: out.append(g.pop())
        random.shuffle(out)
        return out

    # ---------- басты бет ----------
    def show_home(self, *_):
        self.stop_timer()
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        root.add_widget(self.top_bar())
        root.add_widget(Label(text=L("[b]ҰБТ ДАЙЫНДЫҚ[/b]"), markup=True, font_size="26sp",
                              size_hint_y=None, height=dp(56), color=hx("#A5A4FF")))
        t, c = self.stats["total"], self.stats["correct"]
        root.add_widget(WLabel(text=f"Тесттер: {self.stats['tests']}  |  Жауап: {t}  |  Дұрыс: {round(c*100/t) if t else 0}%",
                               halign="center", color=hx("#9CA3AF")))
        self.roll_day(); td = self.stats["today"]; left = max(DAILY - td, 0)
        root.add_widget(WLabel(text=f"Бүгінгі мақсат: [b]{min(td, DAILY)}/{DAILY}[/b]  |  Қатар: {self.streak()} күн", halign="center"))
        root.add_widget(ProgressBar(max=DAILY, value=min(td, DAILY), size_hint_y=None, height=dp(10)))
        sv, box = ScrollView(), vbox(spacing=dp(8))
        box.add_widget(btn(f"Бүгінгі {DAILY} сұрақ (қалды: {left})" if left else "Бүгінгі жоспар орындалды!",
                           "#D97706" if left else GREEN, 56, lambda *_: self.start(DAILY_MODE)))
        box.add_widget(btn("Аралас тест (барлық пәндер)", BLUE, cb=lambda *_: self.start(ALL)))
        box.add_widget(btn("ҰБТ профильдері (2 пән)", "#7C3AED", cb=self.show_profiles))
        box.add_widget(btn("Калькулятор", "#0E7490", cb=self.show_calc))
        box.add_widget(btn(f"Аккаунт: {self.stats['user']}" if self.stats["user"] else "Кіру / Тіркелу", "#16A34A", cb=self.show_account))
        for s in sorted({q.get("subject", "Басқа") for q in self.questions}):
            n = sum(1 for q in self.questions if q.get("subject", "Басқа") == s)
            sc = self.stats["subjects"].get(s)
            tail = f"  ·  {round(sc[0]*100/sc[1])}%" if sc and sc[1] else ""
            box.add_widget(btn(f"{s} ({n}){tail}", cb=lambda *_, s=s: self.start(s)))
        box.add_widget(btn(f"{MISTAKES} ({len(self.wrong_questions())})", "#92400E", cb=lambda *_: self.start(MISTAKES)))
        box.add_widget(btn("Статистиканы тазалау", GRAY, 44, self.reset_stats))
        sv.add_widget(box); root.add_widget(sv)
        self.put("home", root)

    def reset_stats(self, *_):
        self.stats.update(tests=0, total=0, correct=0, subjects={}, wrong=[], today=0, streak=0, last_day="")
        self.save_stats(); self.show_home()

    # ---------- профиль, баптау, админ ----------
    def set_stat(self, k, v, refresh=False):
        self.stats[k] = v; self.save_stats()
        if refresh: self.show_settings()

    def top_bar(self):
        st = self.stats; row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
        av = btn((st["name"] or "?")[:1].upper(), AV[st["avatar"] % len(AV)], 48, self.show_settings)
        av.size_hint_x, av.width = None, dp(52)
        row.add_widget(av)
        who = escape_markup(st["name"]) if st["name"] else "Профильді баптау"
        sub = f"Аккаунт: {escape_markup(st['user'])}" if st["user"] else f"Қонақ: {st['guest']}/{GUEST_MAX}"
        row.add_widget(WLabel(text=f"{who}\n[size=13sp]{sub}[/size]", valign="middle"))
        b = btn("Баптау", GRAY, 46, self.show_settings); b.size_hint_x, b.width = None, dp(96)
        row.add_widget(b)
        return row

    def show_settings(self, *_):
        st = self.stats; root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(WLabel(text="[b]Профиль және баптаулар[/b]", font_size="22sp"))
        sv, box = ScrollView(), vbox(spacing=dp(8))
        ti = TextInput(text=st["name"], hint_text="Атың", multiline=False, size_hint_y=None, height=dp(46), font_size="18sp")
        ti.bind(text=lambda i, v: self.set_stat("name", v.strip()[:20]))
        box.add_widget(WLabel(text="Есімің:")); box.add_widget(ti)
        box.add_widget(WLabel(text="Аватар түсі:"))
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        for i, c in enumerate(AV):
            row.add_widget(btn("•" if st["avatar"] == i else "", c, 48, lambda *_, i=i: self.set_stat("avatar", i, True)))
        box.add_widget(row)
        box.add_widget(WLabel(text="Тақырып (фон):"))
        for name, (bg, card) in THEMES.items():
            box.add_widget(btn(("• " if st["theme"] == name else "") + name, card, 46, lambda *_, n=name: self.pick_theme(n)))
        box.add_widget(btn("Аккаунт", "#16A34A", 50, self.show_account))
        box.add_widget(WLabel(text="Тіл:")); box.add_widget(self.lang_row(self.show_settings))
        box.add_widget(btn("Админ панель", "#92400E", 50, self.show_admin))
        sv.add_widget(box); root.add_widget(sv)
        root.add_widget(btn("Артқа", GRAY, 50, self.show_home))
        self.put("set", root)

    def pick_theme(self, name):
        self.stats["theme"] = name; self.save_stats(); apply_theme(name); self.show_settings()

    def show_profiles(self, *_):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(WLabel(text="[b]ҰБТ профильдері[/b]", font_size="22sp"))
        root.add_widget(WLabel(text="Тест: Қазақстан тарихы + Математика + 2 профиль пәні, әрқайсысынан 10 сұрақ.", font_size="14sp", color=hx("#9CA3AF")))
        sv, box = ScrollView(), vbox(spacing=dp(8))
        for name, _s in PROFILES:
            box.add_widget(btn(name, "#7C3AED", cb=lambda *_, n=name: self.start("prof:" + n)))
        sv.add_widget(box); root.add_widget(sv)
        root.add_widget(btn("Артқа", GRAY, 50, self.show_home))
        self.put("prof", root)

    def start_profile(self, name):
        need = {"Қазақстан тарихы", "Математика", *dict(PROFILES)[name]}; qs = []
        for sj in need:
            pool = [q for q in self.questions if q.get("subject") == sj]
            qs += random.sample(pool, min(10, len(pool)))
        if not qs: return self.popup("Сұрақ жоқ.")
        random.shuffle(qs); self.begin(qs, "prof:" + name)

    def begin(self, qs, mode):
        self.run = dict(qs=qs, i=0, score=0, wrong=[], right=[], per={}, t0=time.time(), mode=mode)
        self.stop_timer(); self.timer = Clock.schedule_interval(self.tick, 1); self.show_question()

    def write_custom(self):
        try:
            with open(self.custom_path, "w", encoding="utf-8") as f: json.dump(self.custom, f, ensure_ascii=False)
        except OSError: pass

    def _old_admin(self, *_):
        st = self.stats; root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        root.add_widget(WLabel(text="[b]Админ панель[/b]\n" + ("PIN енгіз:" if st["pin"] else "Жаңа PIN ойлап тап (кемінде 4 сан):"), font_size="20sp"))
        ti = TextInput(multiline=False, password=True, input_filter="int", size_hint_y=None, height=dp(46), font_size="20sp")
        root.add_widget(ti); msg = WLabel(text="", color=hx("#FCA5A5")); root.add_widget(msg)
        def go(*_):
            v = ti.text.strip()
            if not st["pin"]:
                if len(v) < 4: msg.text = "Кемінде 4 сан"; return
                st["pin"] = v; self.save_stats(); self.admin_panel()
            elif v == st["pin"]: self.admin_panel()
            else: msg.text = "PIN қате"
        root.add_widget(btn("Кіру", BLUE, 50, go)); root.add_widget(btn("Артқа", GRAY, 46, self.show_settings)); root.add_widget(Label())
        self.put("adm", root)

    def admin_panel(self):
        subs = sorted({q.get("subject", "Басқа") for q in self.questions})
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6))
        root.add_widget(WLabel(text=f"[b]Админ панель[/b]  |  Өз сұрақтарым: {len(self.custom)}", font_size="18sp"))
        sv, box = ScrollView(), vbox(spacing=dp(6))
        sp = Spinner(text=subs[0] if subs else "Басқа", values=subs, size_hint_y=None, height=dp(46)); box.add_widget(sp)
        mk = lambda h: TextInput(hint_text=h, multiline=False, size_hint_y=None, height=dp(46))
        q = mk("Сұрақ мәтіні"); o = [mk(f"{'ABCD'[i]} нұсқасы") for i in range(4)]
        a = mk("Дұрыс жауап: 1-4 (A=1)"); a.input_filter = "int"
        for w in [q] + o + [a]: box.add_widget(w)
        msg = WLabel(text="", color=hx("#FCA5A5")); box.add_widget(msg)
        def save(*_):
            try: k = int(a.text) - 1
            except ValueError: k = -1
            opts = [x.text.strip() for x in o]
            if not q.text.strip() or not all(opts) or len(set(opts)) < 4 or not 0 <= k < 4:
                msg.text = "Барлық өрісті толтыр, нұсқалар әртүрлі болсын, жауап 1-4"; return
            d = {"subject": sp.text, "question": q.text.strip(), "options": opts, "answer": k}
            self.custom.append(d); self.questions.append(d); self.write_custom(); self.admin_panel()
        def undo(*_):
            if self.custom:
                d = self.custom.pop(); self.questions.remove(d); self.write_custom(); self.admin_panel()
        def newpin(*_): self.stats["pin"] = ""; self.save_stats(); self.show_admin()
        box.add_widget(btn("Сұрақты сақтау", GREEN, 48, save))
        box.add_widget(btn("Соңғы қосқан сұрағымды өшіру", RED, 44, undo))
        box.add_widget(btn("Тіркеу коды жасау", "#0E7490", 48, self.show_codegen))
        box.add_widget(btn("Админнен шығу", GRAY, 44, self.admin_logout))
        sv.add_widget(box); root.add_widget(sv); root.add_widget(btn("Артқа", GRAY, 46, self.show_settings))
        self.put("adm", root)

    # ---------- калькулятор ----------
    LONG = ("asin(", "acos(", "atan(", "sin(", "cos(", "tan(", "ln(", "log(", "√(", "ANS")

    def show_calc(self, *_): self.put("calc", self.calc_widget(self.show_home))

    def open_calc(self, *_):
        pop = Popup(title="Калькулятор", size_hint=(.97, .93), auto_dismiss=False)
        pop.content = self.calc_widget(pop.dismiss); self.cpop = pop
        pop.bind(on_dismiss=lambda *_: setattr(self, "cpop", None)); pop.open()

    def calc_widget(self, close):
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        self.cd = Label(font_size="26sp", halign="right", valign="bottom", size_hint_y=None, height=dp(90))
        self.cr_lbl = Label(font_size="20sp", halign="right", valign="middle", size_hint_y=None, height=dp(34), color=hx("#9CA3AF"))
        for w in (self.cd, self.cr_lbl):
            w.bind(size=lambda i, sz: setattr(i, "text_size", (sz[0] - dp(8), sz[1]))); root.add_widget(w)
        g, self.ckeys = GridLayout(cols=5, spacing=dp(4)), {}
        for k in "DEG INV sin cos tan ln log √ x² ^ π e ( ) ! C DEL % 1/x ÷ 7 8 9 ANS × 4 5 6 . - 1 2 3 0 +".split():
            col = "#B91C1C" if k == "C" else "#92400E" if k == "DEL" else BLUE if k in ("÷", "×", "-", "+", "^") else T["card"] if (k.isdigit() or k == ".") else GRAY
            b = Button(text=k, font_size="18sp", background_normal="", background_color=hx(col))
            b.bind(on_release=lambda *_, k=k: self.ckey(k)); g.add_widget(b); self.ckeys[k] = b
        root.add_widget(g)
        bot = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        bot.add_widget(btn("Артқа", GRAY, 50, lambda *_: close())); bot.add_widget(btn("=", GREEN, 50, lambda *_: self.ckey("=")))
        root.add_widget(bot)
        self.ckeys["DEG"].text = "DEG" if self.cdeg else "RAD"
        for f in ("sin", "cos", "tan"): self.ckeys[f].text = ("a" if self.cinv else "") + f
        self.refresh_calc(); return root

    def refresh_calc(self): self.cd.text, self.cr_lbl.text = self.cx, self.cres

    def ceval(self): return Ev(tokenize(self.cx), self.cdeg, self.cans).parse()

    def ckey(self, k):
        if k == "=":
            try: v = self.ceval(); self.cres, self.cans, self.cfresh = "= " + fmt(v), v, True
            except CALC_ERR: self.cres = "Қате"
            return self.refresh_calc()
        if k == "DEG": self.cdeg = not self.cdeg; self.ckeys["DEG"].text = "DEG" if self.cdeg else "RAD"
        elif k == "INV":
            self.cinv = not self.cinv
            for f in ("sin", "cos", "tan"): self.ckeys[f].text = ("a" if self.cinv else "") + f
        elif k == "C": self.cx, self.cres, self.cfresh = "", "", False
        elif k == "DEL":
            for t in self.LONG:
                if self.cx.endswith(t): self.cx = self.cx[:-len(t)]; break
            else: self.cx = self.cx[:-1]
            self.cfresh = False
        elif k == "1/x": self.cx = f"1÷({self.cx})" if self.cx else ""; self.cfresh = False
        else:
            ins = ("a" if self.cinv else "") + k + "(" if k in ("sin", "cos", "tan") else k + "(" if k in ("ln", "log", "√") else "^2" if k == "x²" else k
            if self.cfresh: self.cx = "ANS" if ins in ("+", "-", "×", "÷", "^", "^2", "%", "!", ")") else ""
            self.cx += ins; self.cfresh = False
        try: self.cres = "= " + fmt(self.ceval()) if self.cx else ""
        except CALC_ERR: self.cres = ""
        self.refresh_calc()

    # ---------- аккаунт, тіл, админ ----------
    def on_pause(self): return True

    def allowed(self):
        if self.stats["user"] or self.stats["guest"] < GUEST_MAX: return True
        self.acc_note = "Тегін 3 тест аяқталды. Жалғастыру үшін тіркеліңіз немесе аккаунтқа кіріңіз."
        self.show_account(); return False

    def lang_row(self, refresh):
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        for code, name in (("kk", "Қазақша"), ("ru", "Русский"), ("en", "English")):
            row.add_widget(btn(("• " if LANG[0] == code else "") + name, BLUE if LANG[0] == code else GRAY, 46, lambda *_, c=code: self.set_lang(c, refresh), tr=False))
        return row

    def set_lang(self, c, refresh): LANG[0] = c; self.stats["lang"] = c; self.save_stats(); refresh()

    def logout(self, *_): self.stats["user"] = ""; self.save_stats(); self.show_account()

    def wa_register(self, digits, name, msg):
        name = name.strip()
        if not name: msg.text = L("Алдымен атыңызды жазыңыз"); return
        self.set_stat("name", name[:20])
        texts = {"kk": "Сәлеметсізбе! Мен ҰБТ ға дайындықта тіркелгім келген. Атым: ",
                 "ru": "Здравствуйте! Я хочу зарегистрироваться на подготовку к ЕНТ. Меня зовут: ",
                 "en": "Hello! I would like to register for UNT (ҰБТ) preparation. My name is: "}
        open_url("https://wa.me/" + digits + "?text=" + urllib.parse.quote(texts[LANG[0]] + name))

    def show_account(self, *_):
        st = self.stats; root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        sv, box = ScrollView(), vbox(spacing=dp(8))
        box.add_widget(WLabel(text="[b]Аккаунт[/b]", font_size="22sp"))
        if self.acc_note: box.add_widget(WLabel(text=self.acc_note, color=hx("#FCA5A5"))); self.acc_note = ""
        msg = WLabel(text="", color=hx("#FCA5A5"))
        if st["user"]:
            box.add_widget(WLabel(text=f"Сіз кірдіңіз: [b]{escape_markup(st['user'])}[/b]"))
            box.add_widget(btn("Аккаунттан шығу", RED, 50, self.logout))
        else:
            box.add_widget(WLabel(text=f"Қонақ: {st['guest']}/{GUEST_MAX}"))
            ti = TextInput(hint_text=L("Тіркеу коды"), multiline=False, size_hint_y=None, height=dp(46)); box.add_widget(ti)
            def login(*_):
                u = verify_token(ti.text)
                if u: st["user"] = u; self.save_stats(); self.show_home()
                else: msg.text = L("Код дұрыс емес")
            box.add_widget(btn("Кіру", BLUE, 50, login)); box.add_widget(msg)
            box.add_widget(WLabel(text="Тіркелу тек админ арқылы жүреді. Атыңызды жазып, төмендегі түймені басыңыз - WhatsApp ашылып, хабарлама дайын болады.", font_size="14sp", color=hx("#9CA3AF")))
            nm = TextInput(text=st["name"], hint_text=L("Атыңыз"), multiline=False, size_hint_y=None, height=dp(46)); box.add_widget(nm)
            for label, digits in WA:
                box.add_widget(btn(f"WhatsApp-қа жазу: {label}", "#16A34A", 50, lambda *_, d=digits: self.wa_register(d, nm.text, msg)))
        box.add_widget(WLabel(text="Тіл:")); box.add_widget(self.lang_row(self.show_account))
        sv.add_widget(box); root.add_widget(sv); root.add_widget(btn("Артқа", GRAY, 50, self.show_home))
        self.put("acc", root)

    def admin_ok(self):
        try: return ed_pub(bytes.fromhex(self.stats["adm"])) == ADMIN_PUB
        except Exception: return False

    def admin_logout(self, *_): self.stats["adm"] = ""; self.save_stats(); self.show_settings()

    def show_admin(self, *_):
        if self.admin_ok(): return self.admin_panel()
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        root.add_widget(WLabel(text="[b]Админ панель[/b]\nАдмин кілті (64 таңба):", font_size="20sp"))
        ti = TextInput(multiline=False, password=True, size_hint_y=None, height=dp(46)); root.add_widget(ti)
        msg = WLabel(text="", color=hx("#FCA5A5")); root.add_widget(msg)
        def go(*_):
            self.stats["adm"] = ti.text.strip().lower()
            if self.admin_ok(): self.save_stats(); self.admin_panel()
            else: self.stats["adm"] = ""; msg.text = "Кілт қате"
        root.add_widget(btn("Кіру", BLUE, 50, go)); root.add_widget(btn("Артқа", GRAY, 46, self.show_settings)); root.add_widget(Label())
        self.put("adm", root)

    def show_codegen(self, *_):
        if not self.admin_ok(): return self.show_admin()
        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        root.add_widget(WLabel(text="[b]Тіркеу коды жасау[/b]\nЛогин (латын әріп, сан, _ ; 3-20 таңба):", font_size="18sp"))
        ti = TextInput(multiline=False, size_hint_y=None, height=dp(46))
        out = TextInput(readonly=True, multiline=True, size_hint_y=None, height=dp(150), font_size="13sp")
        msg = WLabel(text="", color=hx("#FCA5A5"))
        def gen(*_):
            lg = ti.text.strip().lower()
            if not re.fullmatch(LOGIN_RE, lg): msg.text = "Логин қате"; return
            out.text = make_token(bytes.fromhex(self.stats["adm"]), lg); msg.text = ""
        def copy(*_):
            from kivy.core.clipboard import Clipboard; Clipboard.copy(out.text)
        def share(*_):
            if out.text: open_url("https://wa.me/?text=" + urllib.parse.quote(out.text))
        for w in (ti, btn("Код жасау", BLUE, 48, gen), out, msg, btn("Көшіру", GRAY, 46, copy), btn("WhatsApp-қа жіберу", "#16A34A", 48, share), btn("Артқа", GRAY, 46, self.admin_panel)):
            root.add_widget(w)
        self.put("adm", root)

    # ---------- тест ----------
    def start(self, mode):
        if not self.allowed(): return
        self.roll_day()
        if mode.startswith("prof:"): return self.start_profile(mode[5:])
        if mode == DAILY_MODE and self.stats["today"] >= DAILY:
            return self.popup("Бүгінгі жоспар орындалды!\nҚосымша тест үшін пәнді таңдаңыз.")
        if mode == MISTAKES: pool = self.wrong_questions()
        else: pool = [q for q in self.questions if mode in (ALL, DAILY_MODE) or q.get("subject", "Басқа") == mode]
        if not pool:
            return self.popup("Сұрақ жоқ." if mode != MISTAKES else "Қателер әзірше жоқ!")
        n = DAILY - self.stats["today"] if mode == DAILY_MODE else PER_TEST
        qs = self.mixed(pool, n) if mode in (ALL, DAILY_MODE) else random.sample(pool, min(n, len(pool)))
        self.run = dict(qs=qs, i=0, score=0, wrong=[], right=[], per={}, t0=time.time(), mode=mode)
        self.stop_timer()
        self.timer = Clock.schedule_interval(self.tick, 1)
        self.show_question()

    def tick(self, dt):
        if hasattr(self, "time_lbl"): self.time_lbl.text = self.fmt(time.time() - self.run["t0"])

    def show_question(self):
        r = self.run; q = r["qs"][r["i"]]; n = len(r["qs"]); opts = q["options"]
        if r["i"] == 0 and not self.stats["user"]: self.stats["guest"] += 1; self.save_stats()
        self.answered = False
        order = list(range(len(opts))); random.shuffle(order)
        self.right = order.index(int(q.get("answer", 0)))
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        top = BoxLayout(size_hint_y=None, height=dp(30))
        self.prog_lbl = Label(text=L(f"{r['i']+1}/{n}  |  Ұпай: {r['score']}"))
        self.time_lbl = Label(text=self.fmt(time.time() - r["t0"]), color=hx("#9CA3AF"))
        top.add_widget(self.prog_lbl); top.add_widget(self.time_lbl)
        root.add_widget(top)
        root.add_widget(ProgressBar(max=n, value=r["i"] + 1, size_hint_y=None, height=dp(8)))
        sv, box = ScrollView(), vbox(spacing=dp(8), padding=(0, dp(8)))
        box.add_widget(WLabel(text=q.get("subject", ""), font_size="13sp", color=hx("#A5A4FF")))
        box.add_widget(WLabel(text=f"[b]{q['question']}[/b]", font_size="20sp", tr=False))
        self.opt_btns = []
        for k, idx in enumerate(order):
            b = btn(f"{chr(65+k)}. {opts[idx]}", cb=lambda *_, k=k: self.answer(k), tr=False)
            b.markup = False
            self.opt_btns.append(b); box.add_widget(b)
        self.fb = WLabel(text="", font_size="16sp"); box.add_widget(self.fb)
        sv.add_widget(box); root.add_widget(sv)
        last = r["i"] + 1 == n
        self.next_btn = btn("Аяқтау" if last else "Келесі", GREEN, 50, self.next)
        self.next_btn.disabled = True
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        row.add_widget(btn("Шығу", GRAY, 50, self.show_home)); row.add_widget(btn("Калк.", "#0E7490", 50, self.open_calc)); row.add_widget(self.next_btn)
        root.add_widget(row)
        self.put("quiz", root)

    def answer(self, k):
        if self.answered: return
        self.answered = True
        r = self.run; q = r["qs"][r["i"]]; ok = k == self.right
        per = r["per"].setdefault(q.get("subject", "Басқа"), [0, 0]); per[1] += 1
        self.opt_btns[self.right].background_color = hx(GREEN)
        if ok:
            r["score"] += 1; per[0] += 1; r["right"].append(q["question"])
        else:
            self.opt_btns[k].background_color = hx(RED); r["wrong"].append(q["question"])
        msg = L("[color=34D399]Дұрыс жауап![/color]" if ok else "[color=FCA5A5]Қате.[/color]")
        if q.get("explain"): msg += f"\n{q['explain']}"
        self.fb.text = msg
        self.prog_lbl.text = L(f"{r['i']+1}/{len(r['qs'])}  |  Ұпай: {r['score']}")
        st = self.stats; st["today"] += 1
        if st["today"] == DAILY:
            y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            st["streak"] = st["streak"] + 1 if st["last_day"] == y else 1
            st["last_day"] = st["day"]
            self.fb.text += L(f"\n\n[b]Бүгінгі {DAILY} сұрақ орындалды![/b]")
        self.save_stats()
        self.next_btn.disabled = False

    def next(self, *_):
        r = self.run; r["i"] += 1
        self.show_question() if r["i"] < len(r["qs"]) else self.finish()

    def finish(self):
        self.stop_timer()
        r, st = self.run, self.stats; n = len(r["qs"]); sc = r["score"]
        st["tests"] += 1; st["total"] += n; st["correct"] += sc
        for s, (c, t) in r["per"].items():
            a = st["subjects"].setdefault(s, [0, 0]); a[0] += c; a[1] += t
        st["wrong"] = sorted((set(st["wrong"]) - set(r["right"])) | set(r["wrong"]))
        self.save_stats()
        pct = round(sc * 100 / n) if n else 0
        verdict = "Тамаша!" if pct >= 85 else "Жақсы, жалғастыр!" if pct >= 60 else "Қайталау керек"
        root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(12))
        root.add_widget(WLabel(text=f"[b]Тест аяқталды![/b]\n\nНәтиже: {sc}/{n}  ({pct}%)\nУақыт: {self.fmt(time.time() - r['t0'])}\nБүгін: {self.stats['today']}/{DAILY}\n\n{verdict}",
                               font_size="22sp"))
        root.add_widget(Label())
        root.add_widget(btn("Қайта тапсыру", BLUE, 52, lambda *_: self.start(r["mode"])))
        root.add_widget(btn("Басты бет", GRAY, 52, self.show_home))
        self.put("res", root)


if __name__ == "__main__":
    UBTApp().run()
