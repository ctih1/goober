import re
import discord.ext
import discord.ext.commands
from modules.globalvars import *
import spacy
from spacy.tokens import Doc
from spacytextblob.spacytextblob import SpacyTextBlob
import discord
import modules.keys as k

import logging
logger = logging.getLogger("goober")


def check_resources():
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logging.critical(k.spacy_model_not_found())
        spacy.cli.download("en_core_web_sm") # type: ignore
        nlp = spacy.load("en_core_web_sm")
    if "spacytextblob" not in nlp.pipe_names:
        nlp.add_pipe("spacytextblob")
    logger.info(k.spacy_initialized())

check_resources()

nlp = spacy.load("en_core_web_sm")
nlp.add_pipe("spacytextblob")
Doc.set_extension("polarity", getter=lambda doc: doc._.blob.polarity)

def is_positive(sentence):
    doc = nlp(sentence)
    sentiment_score = doc._.polarity  # from spacytextblob

    debug_message = f"{k.sentence_positivity()} {sentiment_score}{RESET}"
    logger.debug(debug_message)

    return sentiment_score > 0.6 # had to raise the bar because it kept saying "death to jews" was fine and it kept reacting to them

async def send_message(ctx: discord.ext.commands.Context,
        message: str | None = None,
        embed: discord.Embed | None = None,
        file: discord.File | None = None,
        edit: bool = False,
        message_reference: discord.Message | None = None
    ) -> discord.Message | None:

    sent_message: discord.Message | None = None
    
    if edit and message_reference:
        try:
            await message_reference.edit(content=message, embed=embed)
            return message_reference
        except Exception as e:
            await ctx.send(f"{k.edit_fail()} {e}")
            return None

    if embed:
        sent_message = await ctx.send(embed=embed, content=message)
    elif file:
        sent_message = await ctx.send(file=file, content=message)
    else:
        sent_message = await ctx.send(content=message)
        
    return sent_message

def append_mentions_to_18digit_integer(message):
    pattern = r'\b\d{18}\b'
    return re.sub(pattern, lambda match: "", message)

def preprocess_message(message):
    message = append_mentions_to_18digit_integer(message)
    doc = nlp(message)
    tokens = [token.text for token in doc if token.is_alpha or token.is_digit]
    return " ".join(tokens)

def improve_sentence_coherence(sentence):
    return re.sub(r'\bi\b', 'I', sentence)

def rephrase_for_coherence(sentence):
    words = sentence.split()
    coherent_sentence = " ".join(words)
    return coherent_sentence
