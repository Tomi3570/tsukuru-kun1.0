import streamlit as st
import tempfile
import re
import os
from pydub import AudioSegment
from helpers import (
    format_audio,
    transcribe_audio,
    create_outline,
    write_chapters,
    save_transcription_to_docx,
    save_report_to_docx
)

# Initialize session state variables if not already set
if 'transcription_done' not in st.session_state:
    st.session_state['transcription_done'] = False
if 'report_generated' not in st.session_state:
    st.session_state['report_generated'] = False

# Show title and description.
st.title("📄 つくる君")
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
    st.divider()
    st.write("### 文字起こし")
    upload_files = st.file_uploader(
        '音声ファイルをアップロード',
        type=['m4a', 'mp3', 'webm', 'mp4', 'mpga', 'wav'],
        accept_multiple_files=True
    )
    if upload_files and not st.session_state['transcription_done']:
        # Show "文字起こし開始" button only if transcription is not done
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
                        all_transcriptions += formatted_transcript + "\n\n"

                        #os.remove(tmp_file_path)  # Remove the temporary file
                        # Store the audio file path in session state for playback
                        st.session_state['audio_file_path'] = tmp_file.name
                        st.session_state['audio_saved'] = True

                    except Exception as e:
                        st.error(f"エラー：{upload_file.name} の文字起こし中に問題が発生しました: {e}")

            if all_transcriptions:
                # Debugging output
                st.write("transcript completed")  
                
                # Store transcription in session_state
                st.session_state['all_transcriptions'] = all_transcriptions
                st.session_state['transcription_done'] = True
    
    # Download Transcript
    if st.session_state['transcription_done'] and not st.session_state['report_generated']:
        all_transcriptions = st.session_state['all_transcriptions'] 
    
        # Allow the user to play a portion of the audio (e.g., the first 30 seconds)
        st.write("***プレビュー***")
        if 'audio_file_path' in st.session_state:
            if os.path.exists(st.session_state['audio_file_path']):
                try:
                    # Use a buffer to load only a portion of the audio
                    with open(st.session_state['audio_file_path'], "rb") as audio_file:
                        audio = AudioSegment.from_file(audio_file)
            
                    preview_audio = audio[:60000]  # Get only the first 60 seconds
                    
                    # Save the preview audio to a temporary file for playback
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
                        preview_audio.export(audio_file.name, format="mp3")

                    # Load and play the audio file
                    with open(audio_file.name, "rb") as f:
                        audio_bytes = f.read()

                    st.audio(audio_bytes, format="audio/mp3")
            
                except Exception as e:
                    st.error(f"プレビュー中にエラーが発生しました: {e}")
            else:
                st.error("プレビュー用の音声ファイルが見つかりません。")

        st.write(all_transcriptions[:400] + "...") #文字お越しの一部のみを表示

        
        docx_transcription = save_transcription_to_docx(all_transcriptions)
        st.download_button(
            label="文字起こしをダウンロード (.docx)",
            data=docx_transcription,
            file_name="transcription.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="download_transcription"
        )

        # Proceed to outline creation
        with st.spinner('アウトラインを生成中...'):
            outline = create_outline(all_transcriptions)

        # Store outline in session_state
        st.session_state['outline'] = outline

        # Provide a text area for the user to edit the outline
        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()
        st.write("### アウトラインを確認")
        user_outline = st.text_area("レポートのアウトラインを作成しました。必要に応じて修正してください。", value=outline, height=300)
        st.session_state['user_outline'] = user_outline
        
    # If the transcription and outline are available in the session state, show the report generation button
    if 'outline' in st.session_state and st.session_state['outline']:
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

                # Store the state that the report has been generated
                st.session_state['report_generated'] = True

                # Prepare the report for download
                docx_file = save_report_to_docx("レポート", user_outline, written_chapters)
                st.download_button(
                    label="レポートをダウンロード (.docx)",
                    data=docx_file,
                    file_name="report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_report"
                )
