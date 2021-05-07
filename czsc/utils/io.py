# coding: utf-8

import pickle
import json


def save_pkl(data, file):
    with open(file, "wb") as f:
        pickle.dump(data, f)


def read_pkl(file):
    with open(file, "rb") as f:
        data = pickle.load(f)
    return data


def save_json(data, file):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(file):
    with open(file, "r", encoding='utf-8') as f:
        data = json.load(f)
    return data

