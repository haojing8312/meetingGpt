import tkinter as tk
from tkinter import messagebox
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
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.auth.credentials import AccessKeyCredential

# 录音配置
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 10
WAVE_OUTPUT_FILENAME = "output.wav"

os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'] = 'you id'
os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'] = 'you secret'

# 设置OSS相关参数
OSS_ENDPOINT = 'oss-cn-beijing.aliyuncs.com'
os.environ['OSS_ACCESS_KEY_ID'] = os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID']
os.environ['OSS_ACCESS_KEY_SECRET'] = os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET']
OSS_BUCKET_NAME = 'you bucket'



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
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
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

def create_common_request(domain, version, protocolType, method, uri):
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain(domain)
    request.set_version(version)
    request.set_protocol_type(protocolType)
    request.set_method(method)
    request.set_uri_pattern(uri)
    request.add_header('Content-Type', 'application/json')
    return request

def init_parameters(file_url):
    body = dict()
    body['AppKey'] = 'PWJ3N1ak4xN4pOut'

    input = dict()
    input['SourceLanguage'] = 'cn'
    input['TaskKey'] = 'task' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    input['FileUrl'] = file_url
    body['Input'] = input

    # AI相关参数，按需设置即可
    parameters = dict()

    # 音视频转换相关
    transcoding = dict()
    # 将原音视频文件转成mp3文件，用以后续浏览器播放
    # transcoding['TargetAudioFormat'] = 'mp3'
    # transcoding['SpectrumEnabled'] = False
    # parameters['Transcoding'] = transcoding

    # 语音识别控制相关
    transcription = dict()
    # 角色分离 ： 可选
    transcription['DiarizationEnabled'] = True
    diarization = dict()
    diarization['SpeakerCount'] = 2
    transcription['Diarization'] = diarization
    parameters['Transcription'] = transcription

    # 文本翻译控制相关 ： 可选
    parameters['TranslationEnabled'] = False
    translation = dict()
    translation['TargetLanguages'] = ['en'] # 假设翻译成英文
    parameters['Translation'] = translation

    # 章节速览相关 ： 可选，包括： 标题、议程摘要
    parameters['AutoChaptersEnabled'] = True

    # 智能纪要相关 ： 可选，包括： 待办、关键信息(关键词、重点内容、场景识别)
    parameters['MeetingAssistanceEnabled'] = True
    meetingAssistance = dict()
    meetingAssistance['Types'] = ['Actions', 'KeyInformation']
    parameters['MeetingAssistance'] = meetingAssistance

    # 摘要控制相关 ： 可选，包括： 全文摘要、发言人总结摘要、问答摘要(问答回顾)
    parameters['SummarizationEnabled'] = True
    summarization = dict()
    summarization['Types'] = ['Paragraph', 'Conversational', 'QuestionsAnswering', 'MindMap']
    parameters['Summarization'] = summarization

    # ppt抽取和ppt总结 ： 可选
    parameters['PptExtractionEnabled'] = False

    # 口语书面化 ： 可选
    parameters['TextPolishEnabled'] = True

    body['Parameters'] = parameters
    return body

def create_task(file_url):
    credentials = AccessKeyCredential(os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'], os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'])
    client = AcsClient(region_id='cn-beijing', credential=credentials)

    body = init_parameters(file_url)
    print('body:')
    print(body)
    request = create_common_request('tingwu.cn-beijing.aliyuncs.com', '2023-09-30', 'https', 'PUT', '/openapi/tingwu/v2/tasks')
    request.add_query_param('type', 'offline')
    request.set_content(json.dumps(body).encode('utf-8'))

    response = client.do_action_with_exception(request)
    response_json = json.loads(response)
    print("response: \n" + json.dumps(response_json,indent=4, ensure_ascii=False))
    return response_json.get('Data').get('TaskId')

def query_task_status(task_id):
    credentials = AccessKeyCredential(os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'], os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'])
    client = AcsClient(region_id='cn-beijing', credential=credentials)

    uri = f'/openapi/tingwu/v2/tasks/{task_id}'
    #定义变量获取当前日期 不包括时分秒
    current_time = datetime.datetime.now().strftime('%Y-%m-%d')


    request = create_common_request('tingwu.cn-beijing.aliyuncs.com', '2023-09-30', 'https', 'GET', uri)

    response = client.do_action_with_exception(request)
    #打印返回参数
    print("query_task_status: \n" + json.dumps(json.loads(response), indent=4, ensure_ascii=False))
    return json.loads(response)

def get_json_from_url(url):
    # 发送GET请求到指定的URL
    response = requests.get(url)
    # 检查请求是否成功
    if response.status_code == 200:
        # 解析JSON数据
        return response.json()
    else:
        # 如果请求失败，打印错误信息
        print(f"Failed to get JSON from URL: {url}")
        print(f"Status code: {response.status_code}")
        return None

def parse_chapters(json_data):
    # 提取章节信息
    chapters = json_data.get('AutoChapters', [])
    # 遍历章节并打印标题和摘要
    for chapter in chapters:
        print(f"章节ID: {chapter['Id']}")
        print(f"标题: {chapter['Headline']}")
        print(f"摘要: {chapter['Summary']}")
        print("---")

def parse_summarization(data):
    # 打印任务ID
    print("任务ID:", data["TaskId"])

    # 打印段落摘要
    print("\n全文摘要结果:")
    #判断是否存在Summarization和ParagraphSummary
    if "Summarization" in data:
        if "ParagraphSummary" in data["Summarization"]:
            print(data["Summarization"]["ParagraphSummary"])

        # 打印对话摘要
        print("\n对话摘要:")
        if "ConversationalSummary" in data["Summarization"]:
            for conversational_summary in data["Summarization"]["ConversationalSummary"]:
                print("发言人ID:", conversational_summary["SpeakerId"])
                print("发言人名称:", conversational_summary["SpeakerName"])
                print("摘要:", conversational_summary["Summary"])
                print("---")

        # 打印问题回答摘要
        print("\n问题回答摘要:")
        if "QuestionsAnsweringSummary" in data["Summarization"]:
            for qa_summary in data["Summarization"]["QuestionsAnsweringSummary"]:
                print("问题:", qa_summary["Question"])
                print("答案:", qa_summary["Answer"])

def summarize_meeting(file_url):
    task_id = create_task(file_url)
    messagebox.showinfo("提示", "转写任务id：" + task_id)
    while True:
        status = query_task_status(task_id)
        messagebox.showinfo("提示", "转写状态：" + status.get('Data').get('TaskStatus'))
        if status.get('Data').get('TaskStatus') == 'COMPLETED':
            #打印返回参数
            print("TaskStatus COMPLETED: \n" + json.dumps(status, indent=4, ensure_ascii=False))
            ############################章节速览相关############################
            chapters_url = status.get('Data').get('Result').get('AutoChapters')
            chapters = get_json_from_url(chapters_url)
            #打印返回json
            print("chapters: \n" + json.dumps(chapters, indent=4, ensure_ascii=False))
            # 如果获取到了数据，解析
            if chapters:
                parse_chapters(chapters)

            ############################大模型摘要相关############################
            summarization_url = status.get('Data').get('Result').get('Summarization')
            summarization = get_json_from_url(summarization_url)
            #打印返回json
            print("summarization: \n" + json.dumps(summarization, indent=4, ensure_ascii=False))
            # 如果获取到了数据，解析
            if summarization:
                parse_summarization(summarization)


            messagebox.showinfo("提示","会议纪要已生成")
            break
        elif status.get('Data').get('TaskStatus') == 'FAILED':
            messagebox.showerror("错误", "生成会议纪要失败")
            break
        else:
            time.sleep(5)
# 定义文件选择函数
def choose_file():
    # 打开文件选择对话框，并设置文件过滤器
    file_path = filedialog.askopenfilename(
        title="选择音频文件",
        filetypes=[("Audio Files", "*.mp3 *.wav *.ogg"), ("All Files", "*.*")]
    )
    # 如果选择了文件，则上传文件
    if file_path:
        upload_file(file_path)

def upload_file(file_path):
    file_url = upload_to_oss(file_path)
    messagebox.showinfo("提示", "开始文件转写：" + file_url)
    summarize_meeting(file_url)

def start_recording():
    recorder.start_recording()
    messagebox.showinfo("提示", "开始录音")

def stop_recording():
    file_path = recorder.stop_recording()
    file_url = upload_to_oss(file_path)
    messagebox.showinfo("提示", "录音已保存")
    messagebox.showinfo("提示", "开始文件转写：" + file_url)
    summarize_meeting(file_url)

# 创建图形界面
root = tk.Tk()
root.title("会议纪要生成器")

recorder = Recorder()

upload_button = tk.Button(root, text="上传文件", command=choose_file)
upload_button.pack(pady=10)

start_button = tk.Button(root, text="开始录音", command=start_recording)
start_button.pack(pady=10)

stop_button = tk.Button(root, text="停止录音", command=stop_recording)
stop_button.pack(pady=10)

root.mainloop()
