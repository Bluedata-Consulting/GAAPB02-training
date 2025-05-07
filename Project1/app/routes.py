from flask import Blueprint, jsonify, request
import os, json, redis 
from .cards import detect_card_type
from .prompt_builder import build_prompt

# create blueprint of app
bp = Blueprint("api",__name__)

from openai import AzureOpenAI
client = AzureOpenAI(api_version="2024-12-01-preview")

@bp.route("/chat",methods=['GET','POST'])
def chat():
    msg = request.get_json(force=True,)['message']
    hist = [] # idenally to be feteched for redis
    card = detect_card_type(msg)
    prompt = build_prompt(card,hist, msg)

    # send the prompt to openai model deployed and fetch the response
    response = client.chat.completions.create(messages=prompt, model="telcogpt",
                                              temperature=0.2,max_tokens=500)
    output = response.choices[0].message.content
    return jsonify({"answer":output})
