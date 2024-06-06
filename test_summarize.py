import json
import os
from create_word_document import create_word_document
from parse_result_json import parse_chapters, parse_meetingassistance, parse_summarization, parse_transcription

# 定义解析函数
def load_local_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
# 测试函数
def test_local_json():
    base_path = 'json'
    text_polish = load_local_json(os.path.join(base_path, 'TextPolish.json'))
    meeting_assistance = load_local_json(os.path.join(base_path, 'MeetingAssistance.json'))
    auto_chapters = load_local_json(os.path.join(base_path, 'AutoChapters.json'))
    summarization = load_local_json(os.path.join(base_path, 'Summarization.json'))
    transcription = load_local_json(os.path.join(base_path, 'Transcription.json'))

    # 打印返回参数
    print("TextPolish: \n" + json.dumps(text_polish, indent=4, ensure_ascii=False))
    print("MeetingAssistance: \n" + json.dumps(meeting_assistance, indent=4, ensure_ascii=False))
    print("AutoChapters: \n" + json.dumps(auto_chapters, indent=4, ensure_ascii=False))
    print("Summarization: \n" + json.dumps(summarization, indent=4, ensure_ascii=False))
    print("Transcription: \n" + json.dumps(transcription, indent=4, ensure_ascii=False))

    # 解析 JSON 数据
    chapter_texts = parse_chapters(auto_chapters)
    summary_data = parse_summarization(summarization)
    meetingassistance_data = parse_meetingassistance(meeting_assistance)
    transcription_data = parse_transcription(transcription)

    # 创建 Word 文档
    create_word_document(chapter_texts, summary_data, meetingassistance_data, transcription_data)

if __name__ == "__main__":
    test_local_json()