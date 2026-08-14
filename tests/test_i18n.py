from app import i18n


def test_supported_languages_and_default():
    assert i18n.DEFAULT_LANG == "zh-CN"
    assert set(i18n.SUPPORTED) == {"zh-CN", "zh-HK", "en-US"}


def test_all_languages_have_same_keys():
    key_sets = [set(m) for m in i18n.TRANSLATIONS.values()]
    assert key_sets[0] == key_sets[1] == key_sets[2]


def test_t_returns_value_for_existing_key():
    assert isinstance(i18n.t("nav.analysis", "zh-CN"), str)
    assert i18n.t("nav.analysis", "en-US") != ""


def test_t_falls_back_to_zh_cn_then_key():
    en_only_key = "only_en_key"
    assert i18n.t(en_only_key, "zh-CN") == en_only_key
    assert i18n.t(en_only_key, "en-US") == en_only_key


def test_t_defaults_to_zh_cn_when_lang_none():
    assert i18n.t("nav.analysis") == i18n.t("nav.analysis", "zh-CN")


def test_is_supported():
    assert i18n.is_supported("en-US")
    assert not i18n.is_supported("fr-FR")
    assert not i18n.is_supported("")
    assert not i18n.is_supported(None)


def test_get_lang_parses_cookie():
    class FakeRequest:
        cookies = {"lang": "en-US"}
    assert i18n.get_lang(FakeRequest()) == "en-US"


def test_get_lang_falls_back_on_invalid():
    class FakeRequest:
        cookies = {"lang": "fr-FR"}
    assert i18n.get_lang(FakeRequest()) == "zh-CN"

    class EmptyRequest:
        cookies = {}
    assert i18n.get_lang(EmptyRequest()) == "zh-CN"


def test_set_lang_cookie():
    class FakeResp:
        def __init__(self):
            self.cookies = {}

        def set_cookie(self, key, value, **kw):
            self.cookies[key] = value
    response = FakeResp()
    i18n.set_lang_cookie(response, "zh-HK")
    assert response.cookies["lang"] == "zh-HK"


def test_t_filter_is_context_aware():
    from app.templating import templates

    tmpl = templates.env.from_string("{{ t('nav.analysis') }}")
    assert tmpl.render(lang="en-US") == "Analysis"
    assert tmpl.render(lang="zh-HK") == "分析"
    assert tmpl.render(lang="zh-CN") == "分析"
    assert tmpl.render(lang="fr-FR") == "分析"  # 非法 lang 回退 zh-CN