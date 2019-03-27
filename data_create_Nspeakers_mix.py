#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : Created on 2018/8/15 11:21
# @Author     : Chao Peng, Peking University
"""
@Description:
1.混合2/3/4说话人音频
2.训练集tr:20000; 验证集cv:5000; 测试集tt:3000
3.使用最短min长度min和8k音频
4.s1/s2/s3..文件下音频和原音频不一样：以最短长度保存; 文件名改变; 能量归一化且除以了最大幅值
""" 

import os
import glob
import random
from tqdm import tqdm
import numpy as np
from scipy.io import wavfile


# 参数设置
wav_dir="/mnt/SpeechSeparation/mix/data/"   # 下级目录是2speakers,3speakers...
wsj0_dir = "/mnt/SpeechSeparation/wsj0_8k/"  # 下级目录是si_dt_05, si_et_05, si_tr_s
fs_8k = 8000  # 采样率
speaker_nums = [2,3,4]  # 生成混合说话人数据的人数
data_types = ['tr', 'cv', 'tt']
data_num = [20000, 5000, 3000]


def gen_snr():   # 根据信噪比产生权重
    snr = random.uniform(0, 0) 
    #weight = 10 ^ (snr / 20)
    return snr


def mkdir(file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path)


def norm_0db(signal):
    #signal = np.array(signal, dtype=np.float32)  # % y_norm = y /sqrt(lev);
    signal = signal / (2 ** 15 - 1)
    lp = np.sqrt(np.sum(signal**2))
    if lp > 0:
        norm_s = signal / lp
    else:
        norm_s = signal
    #norm_s = norm_s / max(norm_s) * 0.9 
    return norm_s   # 返回[-1,1]


# 三个文件夹下所有.wav文件,绝对路径;该写法对文件结构有特殊要求
si_dt_05 = glob.glob(wsj0_dir + "si_dt_05/*/*.wav")
si_et_05 = glob.glob(wsj0_dir + "si_et_05/*/*.wav")
si_tr_s  = glob.glob(wsj0_dir + "si_tr_s/*/*.wav")

# 随机生成tr/cv/tt数据集并写音频;按照比例对tr_cv进行切分
tr_cv, tt_list = si_tr_s, si_dt_05+si_et_05
random.shuffle(tr_cv)
cut_point = int(data_num[0] / (data_num[0] + data_num[1]) * len(tr_cv))
tr_list = tr_cv[:cut_point]
cv_list = tr_cv[cut_point:]
random.shuffle(tt_list)
all_wavs = [tr_list, cv_list, tt_list]


for speaker_num in speaker_nums:
    print("\nHanding " + str(speaker_num) + " speakers")
    file_list = []

    for index, data_type in enumerate(data_types):   # [tr,cv,tt]
        # [["../1.wav", "2.wav"], ["3.wav", "4.wav"]]
        type_group = []
        while len(type_group) < data_num[index]:
            wav_list_temp = random.sample(all_wavs[index], speaker_num)  # 随机选取的多个说话人音频
            wav_sorted = sorted(wav_list_temp)
            if wav_sorted not in type_group:
                type_group.append(wav_sorted)

        for wav_list in type_group:
            min_length = np.Inf
            temp_audio = []
            temp_snr = [] 
            save_wav_name = ""
            txt_a_row = ""

            for wav in wav_list:
                snr = gen_snr()
                temp_snr.append(snr)
                txt_a_row = txt_a_row + wav + " " + str(snr) + " "
                wav_name = os.path.splitext(os.path.split(wav)[1])[0]  # 音频文件名
                save_wav_name = save_wav_name + wav_name + "_" + str(snr) + "_"
                fs, data = wavfile.read(wav)
                data = norm_0db(data)
                assert fs == fs_8k

                if len(data) < min_length:
                    min_length = len(data)
                temp_audio.append(data)

            temp_snr[0] = 0.0
            save_wav_name = save_wav_name[:-1] + ".wav"
            file_list.append(txt_a_row + save_wav_name)

            merge_wav = np.zeros((speaker_num+1, min_length))
            for i in range(speaker_num):
                merge_wav[i, :] = 10**(temp_snr[i]/20) * temp_audio[i][:min_length]
            merge_wav[speaker_num, :] = np.sum(merge_wav[0:speaker_num], axis=0)

            # 调高音频幅度并还原至int16
            max_amp = np.max(abs(merge_wav))
            merge_wav = merge_wav / max_amp * 0.9
            merge_wav = merge_wav * (2 ** 15 - 1)

            # 开始写音频文件
            s_save_dir = ""
            for i in range(speaker_num):
                print("Writing %dspeakers/%s/%d/%s..."%(speaker_num, data_type, index, save_wav_name))
                s_save_dir = wav_dir+str(speaker_num)+"speakers_0dB/wav8k/min/"+data_type+"/s"+str(i+1)+"/"  #保存音频的文件夹
                mkdir(s_save_dir)
                wavfile.write(s_save_dir + save_wav_name, fs_8k, merge_wav[i].astype(np.int16))

            # 保存混合音频
            mix_dir = s_save_dir[:-3] + "mix/"
            mkdir(mix_dir)
            wavfile.write(mix_dir + save_wav_name, fs_8k, merge_wav[speaker_num].astype(np.int16))


    # 对某个数量说话人处理完毕
    str_s = str(speaker_num) + "speakers_"
    with open(wav_dir + str_s + "0dB/" + str_s + "8k_0dB.txt", "w", encoding="utf-8") as f:
        for row_txt in file_list:
            f.write(row_txt)
            f.write('\n')

print("si_dt_05:%d, si_et_05:%d, si_tr_s:%d"%(len(si_dt_05), len(si_et_05), len(si_tr_s)))
print("All done!")
