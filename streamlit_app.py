import streamlit as st
import openai
import os
from openai import OpenAI
from pydub import AudioSegment
from pydub.utils import which
from docx import Document
from io import BytesIO
import tempfile

# Set the path to ffmpeg and ffprobe if needed
AudioSegment.converter = which("ffmpeg")
AudioSegment.ffprobe = which("ffprobe")

# Function to split audio into chunks
def format_audio(audio_file_path, chunk_duration_ms=360000):  # 6 minutes chunks
    audio = AudioSegment.from_file(audio_file_path)
    duration_ms = len(audio)
    chunks = []

    for start_time in range(0, duration_ms, chunk_duration_ms):
        end_time = min(start_time + chunk_duration_ms, duration_ms)
        chunk = audio[start_time:end_time]
        chunks.append(chunk)

    return chunks

# Function for formatting transcript
def format_transcription(transcript):
    prompt = (
        "以下の文字起こしテキストを読みやすく整形してください。内容はそのままに、段落分けや句読点の追加などを行ってください。\n\n"
        f"{transcript}"
    )

    response = openai.chat.completions.create(
        messages=[
            {"role": "system", "content": "あなたは優秀な日本語のエディターです。"},
            {"role": "user", "content": prompt}
        ],
        model="gpt-4o",
        max_tokens=4096,
        temperature=0
    )

    return response.choices[0].message.content

# Function to transcribe the audio chunks
def transcribe_audio(chunks):
    client = openai.OpenAI()
    full_transcript = ""

    for i, chunk in enumerate(chunks):
        # Save chunk to a temporary file
        chunk_path = f"temp_chunk_{i}.mp3"
        chunk.export(chunk_path, format="mp3")

        # Transcribe audio chunk
        with open(chunk_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                language="ja",
                response_format="text",
            )

        formatted_transcript = format_transcription(transcript)  # Format transcript
        full_transcript += formatted_transcript + "\n" # Append chunks
        os.remove(chunk_path) # Remove the temporary chunk file

    return full_transcript

# Function to save transcription as a .docx file
def save_transcription_to_docx(transcription_text):
    doc = Document()
    doc.add_heading('音声文字起こし結果', 0)

    # Add each paragraph from the transcription
    paragraphs = transcription_text.split("\n")
    for para in paragraphs:
        doc.add_paragraph(para)

    # Save the document in memory
    doc_io = BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io

#______________________________________________
# Show title and description.
st.title("📄 つくる君2.0")
st.write(
    "音声ファイルからレポートを作成します。"
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
        '音声文字起こしするファイルを選択してください。APIの上限により25MB以上のファイルは文字起こし不可です。ファイルを分割する等容量を少なくしてください。',
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

            # Optionally, allow the user to download the combined transcription
            if all_transcriptions:
                docx_file = save_transcription_to_docx(all_transcriptions)
                st.download_button(
                    label="文字起こし結果をダウンロード (.docx)",
                    data=docx_file,
                    file_name="transcription.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )