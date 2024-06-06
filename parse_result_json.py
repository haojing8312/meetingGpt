import json

#解析智能纪要
def parse_meetingassistance(json_data):
    keywords_text = "无关键词"
    key_sentences_text = "无重点内容"
    actions_text = "无待办事项"
    if "MeetingAssistance" in json_data:
        meeting_assistance = json_data.get("MeetingAssistance", {})
        # 获取关键词
        keywords = meeting_assistance.get("Keywords", [])
        keywords_text = ", ".join(keywords) if keywords else "无关键词"

        # 获取重点内容
        key_sentences = meeting_assistance.get("KeySentences", [])
        key_sentences_texts = [sentence["Text"] for sentence in key_sentences if "Text" in sentence]
        key_sentences_text = "\n".join(key_sentences_texts) if key_sentences_texts else "无重点内容"

        # 获取待办事项
        actions = meeting_assistance.get("Actions", [])
        actions_texts = [action["Text"] for action in actions if "Text" in action]
        actions_text = "\n".join(actions_texts) if actions_texts else "无待办事项"

    result = {
        "keywords": keywords_text,
        "key_sentences": key_sentences_text,
        "actions": actions_text
    }

    return result

#解析章节速览
def parse_chapters(json_data):
    # 提取章节信息
    chapters = json_data.get('AutoChapters', [])
    chapter_texts = []
    # 遍历章节并打印标题和摘要
    for chapter in chapters:
        chapter_texts.append({
                    'title': chapter['Headline'],
                    'summary': chapter['Summary'],
                    'id': chapter['Id']
                })
    return chapter_texts
#解析大模型摘要
def parse_summarization(data):
    summary_data = {
            'paragraph_summary': '',
            'conversational_summary': [],
            'qa_summary': []
        }
    # 打印任务ID
    print("任务ID:", data["TaskId"])

    # 打印段落摘要
    print("\n全文摘要结果:")
    #判断是否存在Summarization和ParagraphSummary
    if "Summarization" in data:
        if "ParagraphSummary" in data["Summarization"]:
            summary_data['paragraph_summary']=data["Summarization"]["ParagraphSummary"]
            print(data["Summarization"]["ParagraphSummary"])

        # 打印对话摘要
        print("\n对话摘要:")
        if "ConversationalSummary" in data["Summarization"]:
            for conversational_summary in data["Summarization"]["ConversationalSummary"]:
                summary_data['conversational_summary'].append({
                            'speaker_id': conversational_summary["SpeakerId"],
                            'speaker_name': conversational_summary["SpeakerName"],
                            'summary': conversational_summary["Summary"]
                        })
                print("发言人ID:", conversational_summary["SpeakerId"])
                print("发言人名称:", conversational_summary["SpeakerName"])
                print("摘要:", conversational_summary["Summary"])
                print("---")

        # 打印问题回答摘要
        print("\n问题回答摘要:")
        if "QuestionsAnsweringSummary" in data["Summarization"]:
            for qa_summary in data["Summarization"]["QuestionsAnsweringSummary"]:
                summary_data['qa_summary'].append({
                            'question': qa_summary["Question"],
                            'answer': qa_summary["Answer"]
                        })
                print("问题:", qa_summary["Question"])
                print("答案:", qa_summary["Answer"])

    return summary_data

#解析语音转写
def parse_transcription(json_data):
    transcription = json_data.get("Transcription", {})

    # 提取转写文本并区分段落
    paragraphs = transcription.get("Paragraphs", [])
    transcription_texts = []
    for paragraph in paragraphs:
        paragraph_id = paragraph.get("ParagraphId", "无段落ID")
        words = paragraph.get("Words", [])
        paragraph_text = "".join([word["Text"] for word in words if "Text" in word])
        transcription_texts.append(paragraph_text)

    result = {
        "transcription": transcription_texts
    }
    return result