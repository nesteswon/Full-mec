
# ------------------------------------------------------------------------------
# Copyright (c) 2024 EncodingHouse Team. All Rights Reserved.
# ------------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import requests
from generate_mec import generate_mec_xml_from_dataframe, is_valid_xml_structure, validate_summary_length

st.set_page_config(page_title="CSV → MEC XML 변환기", page_icon="🎬", layout="centered")

# ---------- Slack 알림 함수 ----------
slack_webhook_url = "https://hooks.slack.com/services/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"

def notify_slack_of_xml_error(error_message, filename="(알 수 없음)"):
    payload = {
        "text": f"""🚨 *MEC XML 유효성 검사 실패!*
📄 파일명: `{filename}`
```{error_message}```"""
    }
    try:
        response = requests.post(slack_webhook_url, json=payload)
        if response.status_code != 200:
            st.warning(f"Slack 전송 실패: {response.text}")
    except Exception as e:
        st.warning(f"Slack 알림 실패: {e}")

# ---------- 탭 구분 ----------
tab1, tab2 = st.tabs(["📄 MEC XML 생성", "🧩 XML 구조 비교"])

# ---------- 탭 1: MEC 생성 ----------
with tab1:
    st.markdown("""
        <h1 style='text-align: center; color: #4CAF50;'>🎬 MEC Metadata Generator</h1>
        <p style='text-align: center; font-size: 16px;'>Amazon Prime Video용 MEC 메타데이터를 쉽고 정확하게 생성하세요.</p>
        <hr>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("📁 CSV 파일을 업로드하세요", type=["csv"])

    if uploaded_file:
        filename = uploaded_file.name
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ {len(df)}개의 언어 행 로딩 완료!")

        # ---------- Summary 글자 수 검사 ----------
        summary_errors = validate_summary_length(df)
        if summary_errors:
            st.error(f"❌ Summary 글자 수 제한 초과 항목 발견 ({len(summary_errors)}건)")
            error_df = pd.DataFrame(summary_errors, columns=["행 번호", "컬럼명", "글자수"])
            st.dataframe(error_df)
            notify_slack_of_xml_error(f"Summary 글자 수 초과 항목 감지됨!\n{error_df.to_string(index=False)}", filename)
            st.stop()

        # ---------- XML 생성 ----------
        xml = generate_mec_xml_from_dataframe(df)

        # ---------- 유효성 검사 ----------
        is_valid = is_valid_xml_structure(xml)
        if is_valid:
            st.success("✅ XML 구조 유효성 검사 통과!")
        else:
            st.error("❌ XML 구조 오류 발생! 다운로드 전에 확인이 필요합니다.")
            notify_slack_of_xml_error("XML 구조 유효성 검사 실패", filename)

        # ---------- 미리보기 ----------
        with st.expander("🔍 XML 내용 미리보기", expanded=True):
            st.code(xml, language="xml")

        # ---------- 다운로드 ----------
        if is_valid:
            st.download_button(
                label="📥 MEC XML 다운로드",
                data=xml,
                file_name="MEC_Metadata.xml",
                mime="application/xml"
            )

# ---------- 탭 2: XML 비교 ----------
with tab2:
    st.header("🧩 XML 구조 비교기")

    sample_file = st.file_uploader("📁 샘플 MEC XML 업로드", type=["xml"], key="sample")
    generated_file = st.file_uploader("📁 생성된 XML 업로드", type=["xml"], key="generated")

    def parse_xml_structure(xml_string):
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_string)
            structure = []

            def recurse(node, path=""):
                tag_path = f"{path}/{node.tag}"
                structure.append((tag_path, sorted(node.attrib.keys())))
                for child in node:
                    recurse(child, tag_path)

            recurse(root)
            return structure
        except Exception as e:
            return f"Parse Error: {e}"

    if sample_file and generated_file:
        sample_str = sample_file.read().decode("utf-8")
        generated_str = generated_file.read().decode("utf-8")

        sample_structure = parse_xml_structure(sample_str)
        generated_structure = parse_xml_structure(generated_str)

        if isinstance(sample_structure, str) or isinstance(generated_structure, str):
            st.error("❌ XML 파싱 오류 발생")
        else:
            sample_set = set((tag, tuple(attrs)) for tag, attrs in sample_structure)
            generated_set = set((tag, tuple(attrs)) for tag, attrs in generated_structure)

            missing = sorted(sample_set - generated_set)
            extra = sorted(generated_set - sample_set)

            if not missing and not extra:
                st.success("🎉 XML 구조가 완전히 일치합니다!")
            else:
                if missing:
                    st.warning("🔻 생성 XML에 누락된 항목:")
                    st.dataframe(missing, use_container_width=True)

                if extra:
                    st.info("🔺 생성 XML에 추가된 항목:")
                    st.dataframe(extra, use_container_width=True)

# ---------- 제작자 서명 ----------
st.markdown("""
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: rgba(0,0,0,0.7);
    color: white;
    text-align: center;
    padding: 12px;
    font-size: 13px;
    font-family: 'Helvetica Neue', sans-serif;
    z-index: 100;
}
</style>

<div class="footer">
    Made with ❤️ by <strong>Encodinghouse Team</strong>
    Ⓒ 2024 EncodingHouse Team. Unauthorized use is prohibited.
</div>
""", unsafe_allow_html=True)
