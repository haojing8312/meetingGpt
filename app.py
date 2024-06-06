import tkinter as tk
from tkinter import messagebox,ttk
from tkinter import filedialog
import pyaudio
import wave
import threading
import os
import json
import datetime
import time
import oss2
import requests
from oss2.credentials import EnvironmentVariableCredentialsProvider


from create_word_document import create_word_document
from parse_result_json import parse_chapters, parse_meetingassistance, parse_summarization, parse_transcription
from tongyiapi import create_task, query_task_status

# 录音配置
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 10
WAVE_OUTPUT_FILENAME = "output.wav"

# 设置OSS相关参数
OSS_ENDPOINT = 'you oss endpoint'
os.environ['OSS_ACCESS_KEY_ID'] = 'you key id'
os.environ['OSS_ACCESS_KEY_SECRET'] = 'you key secret'
OSS_BUCKET_NAME = 'you bucket name'



class Recorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False

    def start_recording(self):
        self.stream = self.p.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK)
        self.frames = []
        self.is_recording = True
        threading.Thread(target=self.record).start()

    def record(self):
        while self.is_recording:
            data = self.stream.read(CHUNK)
            self.frames.append(data)

    def stop_recording(self):
        self.is_recording = False
        self.stream.stop_stream()
        self.stream.close()
        #获取当前年月日时分秒字符串
        now = datetime.datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
        #设置保存文件名
        wf = wave.open(WAVE_OUTPUT_FILENAME+"_"+now, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        return WAVE_OUTPUT_FILENAME

def upload_to_oss(file_path):
    try:
        auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
        object_name = os.path.basename(file_path)
        bucket.put_object_from_file(object_name, file_path)
        file_url = f'https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}'
        return file_url
    except oss2.exceptions.ServerError as e:
        messagebox.showerror("错误", f"上传文件到OSS时发生错误: {e}")
        return None

def get_json_from_url(url):
    # 发送GET请求到指定的URL
    response = requests.get(url)
    # 检查请求是否成功
    if response.status_code == 200:
        # 解析JSON数据
        return response.json()
    else:
        # 如果请求失败，打印错误信息
        # print(f"Failed to get JSON from URL: {url}")
        # print(f"Status code: {response.status_code}")
        return None



def summarize_meeting(file_url, access_key_id, access_key_secret):
    app_key = app_key_entry.get()
    task_id = create_task(file_url, app_key, access_key_id, access_key_secret)
    update_progress(30, "生成会议纪要")
    while True:
        status = query_task_status(task_id, access_key_id, access_key_secret)
#         messagebox.showinfo("提示", "转写状态：" + status.get('Data').get('TaskStatus'))
        if status.get('Data').get('TaskStatus') == 'COMPLETED':
            update_progress(80, "生成WORD")
            #打印返回参数
            # print("TaskStatus COMPLETED: \n" + json.dumps(status, indent=4, ensure_ascii=False))
            ############################章节速览############################
            chapters_url = status.get('Data').get('Result').get('AutoChapters')
            chapters = get_json_from_url(chapters_url)
            #打印返回json
            # print("chapters: \n" + json.dumps(chapters, indent=4, ensure_ascii=False))
            # 如果获取到了数据，解析
            if chapters:
                chapter_texts = parse_chapters(chapters)

            ############################大模型摘要############################
            summarization_url = status.get('Data').get('Result').get('Summarization')
            summarization = get_json_from_url(summarization_url)
            #打印返回json
            # print("summarization: \n" + json.dumps(summarization, indent=4, ensure_ascii=False))
            # 如果获取到了数据，解析
            if summarization:
                summary_data = parse_summarization(summarization)

            ############################智能纪要############################
            meetingassistance_url = status.get('Data').get('Result').get('MeetingAssistance')
            meetingassistance = get_json_from_url(meetingassistance_url)
            #打印返回json
            # print("meetingassistance: \n" + json.dumps(meetingassistance, indent=4, ensure_ascii=False))
            # 如果获取到了数据，解析
            if meetingassistance:
                meetingassistance_data = parse_meetingassistance(meetingassistance)

            ############################语音转写############################
            transcription_url = status.get('Data').get('Result').get('Transcription')
            transcription = get_json_from_url(transcription_url)
            #打印返回json
            # print("transcription: \n" + json.dumps(transcription, indent=4, ensure_ascii=False))
            # 如果获取到了数据，解析
            if transcription:
                transcription_data = parse_transcription(transcription)

            # 创建 Word 文档
            path = create_word_document(chapter_texts, summary_data, meetingassistance_data, transcription_data)
            update_progress(100, "完成，会议纪要路径 "+path)
            enable_buttons()
            break
        elif status.get('Data').get('TaskStatus') == 'FAILED':
            messagebox.showerror("错误", "生成会议纪要失败")
            update_progress(0, "生成失败")
            break
        else:
            #共5个任务，完成一个加10%
            completed_task_count = count_completed_tasks(status)
            #打印completed_task_count
            # print("completed_task_count: \n" + str(completed_task_count))
            update_progress(30+completed_task_count*10, "生成会议纪要")
            time.sleep(5)

def count_completed_tasks(json_str):
    data = json_str
    result = data.get("Data", {}).get("Result", {})
    task_count = 0

    for key in result:
        if result[key]:
            task_count += 1

    return task_count
# 定义文件选择函数
def choose_file():
    # 打开文件选择对话框，并设置文件过滤器
    file_path = filedialog.askopenfilename(
        title="选择音频文件",
        filetypes=[("Audio Files", "*.mp3 *.wav *.ogg"), ("All Files", "*.*")]
    )
    # 如果选择了文件，则上传文件
    if file_path:
        access_key_id = access_key_id_entry.get()
        access_key_secret = access_key_secret_entry.get()
        upload_file(file_path, access_key_id, access_key_secret)

def upload_file(file_path, access_key_id, access_key_secret):
    disable_buttons()
    update_progress(10, "文件转储")
    file_url = upload_to_oss(file_path)
    update_progress(20, "文件解析")
    summarize_meeting(file_url, access_key_id, access_key_secret)

def update_progress(progress, status):
    progress_var.set(progress)
    progress_label.config(text=f"进度：{progress}%")
    status_label.config(text=f"状态：{status}")
    root.update_idletasks()  # 确保UI实时更新
def start_recording():
    recorder.start_recording()
    messagebox.showinfo("提示", "开始录音")

def stop_recording():
    file_path = recorder.stop_recording()
    file_url = upload_to_oss(file_path)
    messagebox.showinfo("提示", "录音已保存")
    messagebox.showinfo("提示", "开始文件转写：" + file_url)
    summarize_meeting(file_url)

def disable_buttons():
    upload_button.config(state=tk.DISABLED)
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.DISABLED)

def enable_buttons():
    upload_button.config(state=tk.NORMAL)
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.NORMAL)

# 创建图形界面
root = tk.Tk()
root.title("会议纪要生成器")

# 输入框和标签
tk.Label(root, text="APP_KEY").pack(pady=5)
app_key_entry = tk.Entry(root, width=50)
app_key_entry.pack(pady=5)

tk.Label(root, text="ACCESS_KEY_ID").pack(pady=5)
access_key_id_entry = tk.Entry(root, width=50)
access_key_id_entry.pack(pady=5)

tk.Label(root, text="ACCESS_KEY_SECRET").pack(pady=5)
access_key_secret_entry = tk.Entry(root, width=50, show="*")
access_key_secret_entry.pack(pady=5)

# 新增：进度条变量和组件
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(root, length=300, variable=progress_var, maximum=100)
progress_bar.pack(pady=10)

progress_label = tk.Label(root, text="进度：0%")
progress_label.pack(pady=5)

status_label = tk.Label(root, text="状态：等待操作")
status_label.pack(pady=10)

recorder = Recorder()

upload_button = tk.Button(root, text="上传文件", command=choose_file)
upload_button.pack(pady=10)

start_button = tk.Button(root, text="开始录音", command=start_recording)
start_button.pack(pady=10)

stop_button = tk.Button(root, text="停止录音", command=stop_recording)
stop_button.pack(pady=10)

root.mainloop()
