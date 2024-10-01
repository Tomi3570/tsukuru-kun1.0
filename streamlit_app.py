import streamlit as st
import openai
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
                with st.spinner(f'***文字起こし中: {upload_file.name}***'):
                    try:
                        # Save the uploaded file to a temporary file
                        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                            tmp_file.write(upload_file.read())
                            tmp_file_path = tmp_file.name

                        # Split the audio file into chunks
                        formatted_audio = format_audio(tmp_file_path)

                        # Transcribe the audio chunks
                        formatted_transcript = transcribe_audio(formatted_audio)

                        st.success(f'***{upload_file.name} の文字起こしを完了しました***')
                        st.write(f"***{upload_file.name} の文字起こし結果***")
                        st.write(formatted_transcript)
                        all_transcriptions += formatted_transcript + "\n\n"

                        os.remove(tmp_file_path)  # Remove the temporary file
                    except Exception as e:
                        st.error(f"エラー：{upload_file.name} の文字起こし中に問題が発生しました: {e}")

            if all_transcriptions:
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

                # Provide a text area for the user to input or edit the outline
                st.write("### アウトラインを確認・編集してください（必要に応じて修正してください）:")
                user_outline = st.text_area("アウトラインを入力または編集してください", value=outline, height=300)

                # Button to proceed to report writing
                if st.button('レポートを作成'):
                    # Count chapters based on user-provided outline
                    num_chapters = outline.count("章")  # Assuming "章" is used to define chapters

                    if num_chapters == 0:
                        st.error("アウトラインに章が見つかりませんでした。アウトラインを確認してください。")
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