"""customer_no 店家識別鍵規則。

承辦 2026-05-30 定案：統編不可靠（部分是音響廠商統編），改用「店名 + 使用地址」判斷：
同店名 + 同地址 = 同一家。
"""
from app.services.customer_no import holder_key, norm_address, norm_holder_name, valid_tax


class TestValidTax:
    """valid_tax 仍保留（辨識/顯示用），但不參與客戶編號分組。"""

    def test_eight_digits_ok(self):
        assert valid_tax("13476725") == "13476725"

    def test_dirty_value_rejected(self):
        assert valid_tax("二聯") is None

    def test_blank_rejected(self):
        assert valid_tax("") is None
        assert valid_tax(None) is None

    def test_fullwidth_digits_normalized(self):
        assert valid_tax("１２３４５６７８") == "12345678"


class TestNormHolderName:
    def test_strips_trailing_paren_halfwidth(self):
        assert norm_holder_name("翊麟餐廳(JOJO)") == "翊麟餐廳"

    def test_strips_trailing_paren_fullwidth(self):
        assert norm_holder_name("翊麟餐廳（JOJO）") == "翊麟餐廳"

    def test_strips_multiple_trailing_parens(self):
        assert norm_holder_name("介芳餐廳(晴)（介芳餐廳）") == "介芳餐廳"

    def test_all_paren_name_kept(self):
        assert norm_holder_name("(無店名)") == "(無店名)"

    def test_no_paren_unchanged(self):
        assert norm_holder_name("玉亭餐廳") == "玉亭餐廳"


class TestNormAddress:
    def test_fullwidth_and_taiwan_char(self):
        assert norm_address("臺北市信義區信義路五段５號") == "台北市信義區信義路五段5號"

    def test_strips_floor(self):
        # 同棟不同樓 → 視為同址
        a = norm_address("高雄市三民區河北二路101號1樓")
        b = norm_address("高雄市三民區河北二路101號3樓")
        c = norm_address("高雄市三民區河北二路101號1、3樓")
        d = norm_address("高雄市三民區河北二路101號")
        assert a == b == c == d == "高雄市三民區河北二路101號"

    def test_first_door_number_and_drop_note(self):
        # 多門牌/括號備註 → 取第一段
        a = norm_address("高雄市鳳山區善政街39號/華興街35號")
        b = norm_address("高雄市鳳山區善政街39號（含2樓）")
        assert a == b == "高雄市鳳山區善政街39號"

    def test_zhi_dash_equivalent(self):
        assert norm_address("新竹縣竹北市新社197之11號") == norm_address(
            "新竹縣竹北市新社197-11號"
        )

    def test_drop_neighbor_number(self):
        # 只剝安全的「N鄰」；里/村名不剝（避免吃到區/鄉名）
        assert norm_address("苗栗縣南庄鄉員林村4鄰小南埔19號") == norm_address(
            "苗栗縣南庄鄉員林村小南埔19號"
        )

    def test_blank(self):
        assert norm_address(None) == ""
        assert norm_address("  ") == ""


class TestHolderKey:
    def test_paren_variants_same_address_merge(self):
        # 承辦原意：同店、只差括號別名，且同址 → 同一家
        a = holder_key("翊麟餐廳", "台北市中山區A路1號")
        b = holder_key("翊麟餐廳(JOJO)", "台北市中山區A路1號1樓")
        assert a == b

    def test_same_name_different_address_separate(self):
        # 音響廠商案例：同公司名跨不同場地 → 各自獨立（地址不同）
        a = holder_key("金嗓電腦科技股份有限公司", "台北市信義區信義路五段5號")
        b = holder_key("金嗓電腦科技股份有限公司", "台中市烏日區中山路三段1號")
        assert a != b

    def test_tax_is_ignored_same_name_addr_merge(self):
        # 統編不參與：同店名同地址，即使一筆填了音響廠商統編、一筆沒填 → 仍同一家
        # （holder_key 根本不收統編參數，這裡證明只靠名+址即合一）
        a = holder_key("快樂小吃店", "高雄市三民區九如二路596號")
        b = holder_key("快樂小吃店", "高雄市三民區九如二路596號2樓")
        assert a == b

    def test_unidentifiable_returns_none(self):
        assert holder_key(None, "台北市A路1號") is None
        assert holder_key("", "台北市A路1號") is None

    def test_key_shape(self):
        assert holder_key("翊麟餐廳(JOJO)", "台北市A路1號1樓") == "翊麟餐廳|台北市A路1號"
