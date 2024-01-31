from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks


from moviepy.editor import VideoFileClip


from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

from modelscope.hub.snapshot_download import snapshot_download

import os

import ffmpeg

from faster_whisper import WhisperModel
import math

import torch

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM,pipeline


# 指定本地目录
local_dir_root = "./models_from_modelscope"

model_dir_cirm = snapshot_download('damo/speech_frcrn_ans_cirm_16k', cache_dir=local_dir_root)

model_dir_ins = snapshot_download('damo/nlp_csanmt_translation_en2zh', cache_dir=local_dir_root)



# 合并字幕
def merge_sub(video_path,srt_path):

    if os.path.exists("./test_srt.mp4"):
        os.remove("./test_srt.mp4")

    ffmpeg.input(video_path).output("./test_srt.mp4", vf="subtitles=" + srt_path).run()

    return "./test_srt.mp4"


def make_tran_ja2zh():

    pipe = pipeline(model="larryvrh/mt5-translation-ja_zh")

    with open("./video.srt", 'r',encoding="utf-8") as file:
        gweight_data = file.read()

    result = gweight_data.split("\n\n")

    if os.path.exists("./two.srt"):
        os.remove("./two.srt")

    for res in result:

        line_srt = res.split("\n")
        
        try:

            translated_text = pipe(f'<-ja2zh-> {line_srt[2]}')[0]['translation_text']
            print(translated_text)

        except IndexError as e:
            # 处理下标越界异常
            print(f"翻译完毕")
            break
        except Exception as e:
             print(str(e))
             
        
        with open("./two.srt","a",encoding="utf-8")as f:f.write(f"{line_srt[0]}\n{line_srt[1]}\n{line_srt[2]}\n{translated_text}\n\n")

    return "翻译完毕"


def make_tran_zh2en():

    tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-zh-en")

    model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-zh-en")

    with open("./video.srt", 'r',encoding="utf-8") as file:
        gweight_data = file.read()

    result = gweight_data.split("\n\n")

    if os.path.exists("./two.srt"):
        os.remove("./two.srt")

    for res in result:

        line_srt = res.split("\n")
        try:

            tokenized_text = tokenizer.prepare_seq2seq_batch([line_srt[2]], return_tensors='pt')
            translation = model.generate(**tokenized_text)
            translated_text = tokenizer.batch_decode(translation, skip_special_tokens=False)[0]
            translated_text = translated_text.replace("<pad>","").replace("</s>","").strip()
            print(translated_text)

        except IndexError as e:
            # 处理下标越界异常
            print(f"翻译完毕")
            break
        except Exception as e:
             print(str(e))
             
        
        with open("./two.srt","a",encoding="utf-8")as f:f.write(f"{line_srt[0]}\n{line_srt[1]}\n{line_srt[2]}\n{translated_text}\n\n")

    return "翻译完毕"

# 翻译字幕
def make_tran():

    pipeline_ins = pipeline(task=Tasks.translation, model=model_dir_ins)

    with open("./video.srt", 'r',encoding="utf-8") as file:
        gweight_data = file.read()

    result = gweight_data.split("\n\n")

    if os.path.exists("./two.srt"):
        os.remove("./two.srt")

    for res in result:

        line_srt = res.split("\n")
        try:
            outputs = pipeline_ins(input=line_srt[2])
            print(outputs['translation'])
        except IndexError as e:
            # 处理下标越界异常
            print(f"翻译完毕")
            break
        except Exception as e:
             print(str(e))
             
          
        
        
        with open("./two.srt","a",encoding="utf-8")as f:f.write(f"{line_srt[0]}\n{line_srt[1]}\n{line_srt[2]}\n{outputs['translation']}\n\n")

    return "翻译完毕"



def convert_seconds_to_hms(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = math.floor((seconds % 1) * 1000)
    output = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"
    return output

# 制作字幕文件
def make_srt(file_path,model_name="small"):


    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # if device == "cuda":
    #     model = WhisperModel(model_name, device="cuda", compute_type="float16",download_root="./model_from_whisper",local_files_only=False)
    # else:
    #     model = WhisperModel(model_name, device="cpu", compute_type="int8",download_root="./model_from_whisper",local_files_only=False)
    # or run on GPU with INT8
    # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        
    if device == "cuda":
        try:
            model = WhisperModel(model_name, device="cuda", compute_type="float16",download_root="./model_from_whisper",local_files_only=False)
        except Exception as e:
            model = WhisperModel(model_name, device="cuda", compute_type="int8_float16",download_root="./model_from_whisper",local_files_only=False)
    else:
        model = WhisperModel(model_name, device="cpu", compute_type="int8",download_root="./model_from_whisper",local_files_only=False)

    segments, info = model.transcribe(file_path, beam_size=5,vad_filter=True,vad_parameters=dict(min_silence_duration_ms=500))

    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
    count = 0
    with open('./video.srt', 'w',encoding="utf-8") as f:  # Open file for writing
        for segment in segments:
            count +=1
            duration = f"{convert_seconds_to_hms(segment.start)} --> {convert_seconds_to_hms(segment.end)}\n"
            text = f"{segment.text.lstrip()}\n\n"
            
            f.write(f"{count}\n{duration}{text}")  # Write formatted string to the file
            print(f"{duration}{text}",end='')

    return "转写完毕"



# 提取人声
def movie2audio(video_path):

    # 读取视频文件
    video = VideoFileClip(video_path)

    # 提取视频文件中的声音
    audio = video.audio

    # 将声音保存为WAV格式
    audio.write_audiofile("./audio.wav")

    ans = pipeline(
        Tasks.acoustic_noise_suppression,
        model=model_dir_cirm)
    
    ans('./audio.wav',output_path='./output.wav')

    return "./output.wav"
