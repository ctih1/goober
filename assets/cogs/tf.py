import discord
from discord.ext import commands
import os
import numpy as np
import json
import pickle
import functools
import re
import time
import asyncio

ready = True
MODEL_MATCH_STRING = r"[0-9]{2}_[0-9]{2}_[0-9]{4}-[0-9]{2}_[0-9]{2}"

try:
    import tensorflow as tf
    import keras
    from keras.preprocessing.text import Tokenizer
    from keras.preprocessing.sequence import pad_sequences
    from keras.models import Sequential, load_model
    from keras.layers import Embedding, LSTM, Dense
    from keras.backend import clear_session

    if tf.config.list_physical_devices("GPU"):
        print("Using GPU acceleration")
    elif tf.config.list_physical_devices("Metal"):
        print("Using Metal for macOS acceleration")
except ImportError:
    print(
        "ERROR: Failed to import TensorFlow. Ensure you have the correct dependencies:"
    )
    print("tensorflow>=2.15.0")
    print("For macOS (Apple Silicon): tensorflow-metal")
    ready = False


class TFCallback(keras.callbacks.Callback):
    def __init__(self, bot, progress_embed: discord.Embed, message):
        self.embed = progress_embed
        self.bot = bot
        self.message = message
        self.times = [time.time()]

    async def send_message(self, message: str, description: str, **kwargs):
        if "epoch" in kwargs:
            self.times.append(time.time())
            avg_epoch_time = np.mean(np.diff(self.times))
            description = f"ETA: {round(avg_epoch_time)}s"
        self.embed.add_field(
            name=f"<t:{round(time.time())}:t> - {message}",
            value=description,
            inline=False,
        )
        await self.message.edit(embed=self.embed)

    def on_train_end(self, logs=None):
        self.bot.loop.create_task(
            self.send_message("Training stopped", "Training has been stopped.")
        )

    def on_epoch_begin(self, epoch, logs=None):
        self.bot.loop.create_task(
            self.send_message(
                f"Starting epoch {epoch}", "This might take a while", epoch=True
            )
        )

    def on_epoch_end(self, epoch, logs=None):
        self.bot.loop.create_task(
            self.send_message(
                f"Epoch {epoch} ended",
                f"Accuracy: {round(logs.get('accuracy', 0.0), 4)}",
            )
        )


class Ai:
    def __init__(self):
        model_path = settings.get("model_path")
        if model_path:
            self.__load_model(model_path)
        self.is_loaded = model_path is not None
        self.batch_size = 64

    def generate_model_name(self):
        return time.strftime("%d_%m_%Y-%H_%M", time.localtime())

    def __load_model(self, model_path):
        clear_session()
        self.model = load_model(os.path.join(model_path, "model.h5"))
        model_name = os.path.basename(model_path)
        try:
            with open(os.path.join(model_path, "tokenizer.pkl"), "rb") as f:
                self.tokenizer = pickle.load(f)
        except FileNotFoundError:
            print("Failed to load tokenizer, using default.")
            self.tokenizer = Tokenizer()
            with open("memory.json", "r") as f:
                self.tokenizer.fit_on_texts(json.load(f))
        self.is_loaded = True

    def reload_model(self):
        clear_session()
        model_path = settings.get("model_path")
        if model_path:
            self.__load_model(model_path)
            self.is_loaded = True

    async def run_async(self, func, bot, *args, **kwargs):
        return await bot.loop.run_in_executor(
            None, functools.partial(func, *args, **kwargs)
        )


class Learning(Ai):
    def create_model(self, memory, epochs=2):
        memory = memory[:2000]
        tokenizer = Tokenizer()
        tokenizer.fit_on_texts(memory)
        sequences = tokenizer.texts_to_sequences(memory)
        X, y = [], []
        for seq in sequences:
            for i in range(1, len(seq)):
                X.append(seq[:i])
                y.append(seq[i])
        maxlen = max(map(len, X))
        X = pad_sequences(X, maxlen=maxlen, padding="pre")
        y = np.array(y)

        model = Sequential(
            [
                Embedding(input_dim=VOCAB_SIZE, output_dim=128, input_length=maxlen),
                LSTM(64),
                Dense(VOCAB_SIZE, activation="softmax"),
            ]
        )

        model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        history = model.fit(X, y, epochs=epochs, batch_size=64, callbacks=[tf_callback])
        self.save_model(model, tokenizer, history)

    def save_model(self, model, tokenizer, history, name=None):
        name = name or self.generate_model_name()
        model_dir = os.path.join("models", name)
        os.makedirs(model_dir, exist_ok=True)

        with open(os.path.join(model_dir, "info.json"), "w") as f:
            json.dump(history.history, f)
        with open(os.path.join(model_dir, "tokenizer.pkl"), "wb") as f:
            pickle.dump(tokenizer, f)
        model.save(os.path.join(model_dir, "model.h5"))


class Generation(Ai):
    def generate_sentence(self, word_amount, seed):
        if not self.is_loaded:
            return False
        for _ in range(word_amount):
            token_list = self.tokenizer.texts_to_sequences([seed])[0]
            token_list = pad_sequences(
                [token_list], maxlen=self.model.input_shape[1], padding="pre"
            )
            predicted_word_index = np.argmax(
                self.model.predict(token_list, verbose=0), axis=-1
            )[0]
            output_word = next(
                (
                    w
                    for w, i in self.tokenizer.word_index.items()
                    if i == predicted_word_index
                ),
                "",
            )
            seed += " " + output_word
        return seed


VOCAB_SIZE = 100_000
settings = {}
learning = Learning()
generation = Generation()

tf_callback = None


async def setup(bot):
    await bot.add_cog(Tf(bot))
