from core.analyzers.profiler import analyze_profile
from core.schemas import CustomerProfile, LanguagePreference


def test_profile_extracts_edutech_fields(fake_llm):
    fake_llm.expect(
        CustomerProfile,
        CustomerProfile(
            occupation_background="传统行业运营人员",
            core_pain_point="薪资瓶颈,想转行数据分析",
            budget_sensitivity="High",
            deal_intent="Medium",
            language_preference=LanguagePreference.ZH,
            language_reason="聊天记录全部为中文",
        ),
    )
    profile = analyze_profile(fake_llm, "客户:你好,我想转行数据分析。")
    assert profile.occupation_background == "传统行业运营人员"
    assert profile.budget_sensitivity in ("High", "Medium", "Low")
    assert profile.deal_intent in ("High", "Medium", "Low")
    assert profile.language_preference == LanguagePreference.ZH


def test_profile_uses_actual_chat_language_not_guessing(fake_llm):
    fake_llm.expect(
        CustomerProfile,
        CustomerProfile(
            occupation_background="foreign company analyst",
            core_pain_point="wants to learn AI tools to boost efficiency",
            budget_sensitivity="Medium",
            deal_intent="Medium",
            language_preference=LanguagePreference.EN,
            language_reason="客户全程使用英文提问,自述在外企工作",
        ),
    )
    profile = analyze_profile(fake_llm, "Customer: Hi, what tech stack does the course cover?")
    assert profile.language_preference == LanguagePreference.EN
    assert "外企" in profile.language_reason or "english" in profile.language_reason.lower()
