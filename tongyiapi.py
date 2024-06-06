import datetime
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.auth.credentials import AccessKeyCredential

def init_parameters(file_url, app_key):
    body = dict()
    body['AppKey'] = app_key

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
def create_task(file_url, app_key, access_key_id, access_key_secret):
    credentials = AccessKeyCredential(access_key_id, access_key_secret)
    client = AcsClient(region_id='cn-beijing', credential=credentials)

    body = init_parameters(file_url, app_key)
    print('body:')
    print(body)
    request = create_common_request('tingwu.cn-beijing.aliyuncs.com', '2023-09-30', 'https', 'PUT', '/openapi/tingwu/v2/tasks')
    request.add_query_param('type', 'offline')
    request.set_content(json.dumps(body).encode('utf-8'))

    response = client.do_action_with_exception(request)
    response_json = json.loads(response)
    print("response: \n" + json.dumps(response_json,indent=4, ensure_ascii=False))
    return response_json.get('Data').get('TaskId')

def query_task_status(task_id, access_key_id, access_key_secret):
    credentials = AccessKeyCredential(access_key_id, access_key_secret)
    client = AcsClient(region_id='cn-beijing', credential=credentials)

    uri = f'/openapi/tingwu/v2/tasks/{task_id}'
    #定义变量获取当前日期 不包括时分秒
    current_time = datetime.datetime.now().strftime('%Y-%m-%d')


    request = create_common_request('tingwu.cn-beijing.aliyuncs.com', '2023-09-30', 'https', 'GET', uri)

    response = client.do_action_with_exception(request)
    #打印返回参数
    print("query_task_status: \n" + json.dumps(json.loads(response), indent=4, ensure_ascii=False))
    return json.loads(response)