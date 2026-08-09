import logging
import re
import threading

import discord
import discord.ext
import discord.ext.commands
import spacy
import spacy.lang
from spacy.tokens import Doc
from spacytextblob.spacytextblob import SpacyTextBlob

import modules.keys as k
from modules.globalvars import *

logger = logging.getLogger("goober")
nlp: spacy.language.Language | None = None


def check_resources():
    global nlp
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logging.critical(k.spacy_model_not_found())
        spacy.cli.download("en_core_web_sm")  # type: ignore
        nlp = spacy.load("en_core_web_sm")
    if "spacytextblob" not in nlp.pipe_names:
        nlp.add_pipe("spacytextblob")
    logger.info(k.spacy_initialized())


nlp_thread = threading.Thread(target=check_resources)
nlp_thread.start()

Doc.set_extension("polarity", getter=lambda doc: doc._.blob.polarity)

def is_positive(sentence):
    return False

async def send_message(
    ctx: discord.ext.commands.Context,
    message: str | None = None,
    embed: discord.Embed | None = None,
    file: discord.File | None = None,
    edit: bool = False,
    edit_message_reference: discord.Message | None = None,
) -> discord.Message:

    sent_message: discord.Message | None = None

    if edit and edit_message_reference:
        try:
            await edit_message_reference.edit(content=message, embed=embed)
            return edit_message_reference
        except Exception as e:
            await ctx.send(f"{k.edit_fail()} {e}")

    if embed:
        sent_message = await ctx.send(embed=embed, content=message)
    elif file:
        sent_message = await ctx.send(file=file, content=message)
    else:
        sent_message = await ctx.send(content=message)

    return sent_message  # type: ignore


def append_mentions_to_18digit_integer(message):
    pattern = r"\b\d{18}\b"
    return re.sub(pattern, lambda match: "", message)


def preprocess_message(message):
    nlp_thread.join()
    message = append_mentions_to_18digit_integer(message)
    if nlp is None:
        logger.error("NLP Not loaded! Quitting")
        quit(1)

    doc = nlp(message)
    tokens = [token.text for token in doc if token.is_alpha or token.is_digit]
    return " ".join(tokens)


def improve_sentence_coherence(sentence):
    return re.sub(r"\bi\b", "I", sentence)


def rephrase_for_coherence(sentence):
    words = sentence.split()
    coherent_sentence = " ".join(words)
    return coherent_sentence
