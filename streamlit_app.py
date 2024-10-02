import streamlit as st
import os
from pydub import AudioSegment
from pydub.utils import which
from docx import Document
from io import BytesIO
import tempfile
import re


import streamlit as st
from helpers import (
    format_audio,
    transcribe_audio,
    create_outline,
    write_chapters,
    save_transcription_to_docx,
    save_report_to_docx
)

# Show title and description.
st.title("📄 つくる君2.0")
st.write(
    "音声データからレポートを作成します。"
    "ご利用にはOpenAIのAPIキーが必要です。 APIキーは[ここから](https://platform.openai.com/account/api-keys)取得できます。 "
)

# Set your OpenAI API key
openai_api_key = st.text_input("OpenAI APIキー", type="password")
if not openai_api_key:
    st.info("APIキーを入力後、Enter/Returnキーを押下。", icon="🗝️")
else:
    os.environ["OPENAI_API_KEY"] = openai_api_key
    #openai.api_key = openai_api_key  # Set the API key for OpenAI

    # Let the user upload a file via `st.file_uploader`.
    upload_files = st.file_uploader(
        '文字起こしする音声データをアップロード',
        type=['m4a', 'mp3', 'webm', 'mp4', 'mpga', 'wav'],
        accept_multiple_files=True
    )

    if upload_files:

        # Button to start transcription
        trans_start = st.button('文字起こし開始')

        if trans_start:
            all_transcriptions = ""
            for upload_file in upload_files:
                with st.spinner(f'***文字起こし中： {upload_file.name}***'):
                    try:
                        # Save the uploaded file to a temporary file
                        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                            tmp_file.write(upload_file.read())
                            tmp_file_path = tmp_file.name

                        # Process the audio: transcribe
                        formatted_audio = format_audio(tmp_file_path)
                        formatted_transcript = transcribe_audio(formatted_audio)

                        st.success(f'***{upload_file.name} の文字起こしを完了しました***')
                        st.write(f"***{upload_file.name} の文字起こし結果***")
                        st.write(formatted_transcript)#【要修正】文字お越しの一部のみを表示
                        all_transcriptions += formatted_transcript + "\n\n"

                        os.remove(tmp_file_path)  # Remove the temporary file
                    except Exception as e:
                        st.error(f"エラー：{upload_file.name} の文字起こし中に問題が発生しました: {e}")

            if all_transcriptions:
                 # Store transcription in session_state
                st.session_state['all_transcriptions'] = all_transcriptions

                # Automatically show the download button for the transcription
                docx_transcription = save_transcription_to_docx(all_transcriptions)
                st.download_button(
                    label="文字起こしをダウンロード (.docx)",
                    data=docx_transcription,
                    file_name="transcription.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_transcription"
                )

                # Proceed to create the outline
                with st.spinner('アウトラインを生成中...'):
                    outline = create_outline(all_transcriptions)

                # Store outline in session_state
                st.session_state['outline'] = outline

                # Provide a text area for the user to input or edit the outline
                st.write("### アウトラインを確認")
                user_outline = st.text_area("必要に応じて修正してください", value=outline, height=300)
                st.session_state['user_outline'] = user_outline

        # If the transcription and outline are available in the session state, show the report generation button
        if st.session_state['outline']:
            
            if st.button('レポートを作成'):
                # Retrieve variables from session_state
                all_transcriptions = st.session_state['all_transcriptions']
                user_outline = st.session_state['user_outline']

                # Determine number of chapters
                chapter_titles = re.findall(r'章\s*([^\n]+)', user_outline)
                num_chapters = len(chapter_titles)

                if num_chapters == 0:
                    st.error("アウトラインに章を特定できませんでした。各章を「第1章」のように記載をしてください。")
                else:
                    with st.spinner('レポートを作成中...'):
                        written_chapters = write_chapters(all_transcriptions, user_outline, num_chapters)
                    st.success('レポートの作成が完了しました。')

                    # Prepare the report for download
                    docx_file = save_report_to_docx("レポート", user_outline, written_chapters)
                    st.download_button(
                        label="レポートをダウンロード (.docx)",
                        data=docx_file,
                        file_name="report.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="download_report"
                    )