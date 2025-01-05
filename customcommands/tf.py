import discord
from discord.ext import commands
import os
from typing import List, TypedDict
import numpy as np
import json
from time import strftime, localtime
import pickle
import re
from discord import app_commands
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense
from tensorflow.keras.models import load_model
from tensorflow.keras.backend import clear_session

ready: bool = True
MODEL_MATCH_STRING = "[0-9]{2}_[0-9]{2}_[0-9]{4}-[0-9]{2}_[0-9]{2}"

try:
    tf.config.optimizer.set_jit(False)
except ImportError:
    print("ERROR: Failed to import TensorFlow.")
    ready = False

class Ai:
    def __init__(self):
        model_path = settings.get("model_path")
        if model_path:
            self.__load_model(model_path)
        self.is_loaded = model_path is not None
        self.batch_size = 32
        
    def get_model_name_from_path(self,path:str):
        print(path)
        match:re.Match = re.search(MODEL_MATCH_STRING, path)
        
        print(match.start)
        return path[match.start():][:match.end()]

    def generate_model_name(self) -> str:
        return strftime('%d_%m_%Y-%H_%M', localtime())
    
    def generate_model_abs_path(self, name:str):
        name = name or self.generate_model_name()
        return os.path.join(".","models",self.generate_model_name(),"model.h5")

    def generate_tokenizer_abs_path(self, name:str):
        name = name or self.generate_model_name()
        return os.path.join(".","models",name,"tokenizer.pkl")
        
    def generate_info_abs_path(self,name:str):
        name = name or self.generate_model_name()
        return os.path.join(".","models",name,"info.json")

        
    def save_model(self,model, tokenizer, history, _name:str=None):
        name:str = _name or self.generate_model_name()
        os.makedirs(os.path.join(".","models",name), exist_ok=True)
        
        with open(self.generate_info_abs_path(name),"w") as f:
            json.dump(history.history,f)
        
        with open(self.generate_tokenizer_abs_path(name), "wb") as f:
            pickle.dump(tokenizer,f)
        
        model.save(self.generate_model_abs_path(name))

        
    def __load_model(self, model_path:str):
        clear_session()
        self.model = load_model(os.path.join(model_path,"model.h5")) 
        
        model_name:str = self.get_model_name_from_path(model_path)
        
        try:
            with open(self.generate_tokenizer_abs_path(model_name),"rb") as f:
                self.tokenizer = pickle.load(f)
        except FileNotFoundError:
            print("Failed to load tokenizer for model... Using default")
            self.tokenizer = Tokenizer()
            
            with open("memory.json","r") as f:
                self.tokenizer.fit_on_texts(json.load(f))
        self.is_loaded = True

    def reload_model(self):
        clear_session()
        model_path:str = settings.get("model_path")
        if model_path:
            self.model = self.__load_model(model_path)

            
class Learning(Ai):
    def __init__(self):
        super().__init__()
        
    def __generate_labels_and_inputs(self,memory: List[str], tokenizer=None) -> tuple:
        if not tokenizer:
            tokenizer = Tokenizer()
            tokenizer.fit_on_texts(memory)
        sequences = tokenizer.texts_to_sequences(memory)
        
        x = []
        y = []
        for seq in sequences:
            for i in range(1, len(seq)):
                x.append(seq[:i])
                y.append(seq[i])
                
        return x,y, tokenizer
    
    def create_model(self,memory: List[str], iters:int=2):
        X,y,tokenizer = self.__generate_labels_and_inputs(memory)
        maxlen:int = max([len(x) for x in X]) 
        x_pad = pad_sequences(X, maxlen=maxlen, padding="pre")
        
        y = np.array(y)
        
        model = Sequential()
        model.add(Embedding(input_dim=VOCAB_SIZE,output_dim=128,input_length=maxlen))
        model.add(LSTM(64))
        model.add(Dense(VOCAB_SIZE, activation="softmax"))
        
        model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        history = model.fit(x_pad, y, epochs=iters, batch_size=32)
        self.save_model(model, tokenizer, history)
        
    def add_training(self,memory: List[str], iters:int=2):
        tokenizer_path = os.path.join(settings.get("model_path"),"tokenizer.pkl")
        with open(tokenizer_path, "rb") as f:
            tokenizer = pickle.load(f)
            
        X,y,_ = self.__generate_labels_and_inputs(memory, tokenizer)
        
        maxlen:int = max([len(x) for x in X]) 
        x_pad = pad_sequences(X, maxlen=maxlen, padding="pre")
        y = np.array(y)
        
        history = self.model.fit(x_pad,y, epochs=iters, validation_data=(x_pad,y), batch_size=64) # Ideally, validation data would be separate from the actual data
        self.save_model(self.model,tokenizer,history,self.get_model_name_from_path(settings.get("model_path")))
    
class Generation(Ai):
    def __init__(self):
        super().__init__()
        
    def generate_sentence(self, word_amount:int, seed:str):
        if not self.is_loaded:
            return False
        for _ in range(word_amount):
            token_list = self.tokenizer.texts_to_sequences([seed])[0]
            token_list = pad_sequences([token_list], maxlen=self.model.layers[0].input_shape[1], padding="pre")

            output_word = "" # Sometimes model fails to predict the word, so using a fallback 

            predicted_probs = self.model.predict(token_list, verbose=0)
            predicted_word_index = np.argmax(predicted_probs, axis=-1)[0]

            for word, index in self.tokenizer.word_index.items():
                if index == predicted_word_index:
                    output_word = word
                    break

            seed += " " + output_word
        return seed
        
    
VOCAB_SIZE = 100_000

SETTINGS_TYPE = TypedDict("SETTINGS_TYPE", {
    "model_path":str, # path to the base folder of the model, aka .../models/05-01-2025-22_31/
    "tokenizer_path":str,
})


model_dropdown_items = []
settings: SETTINGS_TYPE = {}

learning:Learning
generation: Generation

class Settings:
    def __init__(self):
        self.settings_path:str = os.path.join(".","models","settings.json")
        
    def load(self):
        global settings
        try:
            with open(self.settings_path,"r") as f:
                settings = json.load(f)
        except FileNotFoundError:
            with open(self.settings_path,"w") as f:
                json.dump({},f)

    def change_model(self,new_model_base_path:str):
        global settings
        new_model_path = os.path.join(".","models",new_model_base_path)
                
        with open(self.settings_path,"r") as f:
            settings = json.load(f)
            
        settings["model_path"] = new_model_path
        
        with open(self.settings_path, "w") as f:
            json.dump(settings,f)


class Dropdown(discord.ui.Select):
    def __init__(self, items:List[str]):
        global model_dropdown_items
        model_dropdown_items = []
        
        for item in items:
            model_dropdown_items.append(
                discord.SelectOption(label=item)
            )
        
        super().__init__(placeholder="Select model", options=model_dropdown_items)
        
    async def callback(self, interaction: discord.Interaction):
        if int(interaction.user.id) != int(os.getenv("ownerid")):
            await interaction.message.channel.send("KILL YOURSELF")
        Settings().change_model(self.values[0])
        await interaction.message.channel.send(f"Changed model to {self.values[0]}")
    
class DropdownView(discord.ui.View):
    def __init__(self, timeout, models):
        super().__init__(timeout=timeout)
        self.add_item(Dropdown(models))


class Tf(commands.Cog):
    @staticmethod
    def needs_ready(func):
        def inner(args:tuple, kwargs:dict):
            if not ready: 
                raise AttributeError("Not ready!")
            a = func(*args, **kwargs)
            return a
        return inner
        
    
    def __init__(self, bot):
        global learning, generation
        global ready
        os.makedirs(os.path.join(".","models"), exist_ok=True)
        Settings().load()
        self.bot = bot
        learning = Learning()
        generation = Generation()
    

    @app_commands.command(name="start", description="Starts the bot")
    async def start(self, interaction: discord.Interaction):
        await interaction.response.send_message("hi")
        
    @app_commands.command(name="generate", description="Generates a sentence")
    async def generate(self, interaction: discord.Interaction, seed: str, word_amount: int = 5):
        await interaction.response.defer()
        sentence = generation.generate_sentence(word_amount, seed)
        await interaction.followup.send(sentence)
    
    @app_commands.command(name="create", description="Trains the model with memory")
    async def create(self, interaction: discord.Interaction):
        await interaction.response.defer()
        with open("memory.json", "r") as f:
            memory: List[str] = json.load(f)
        learning.create_model(memory)  # TODO: CHANGE
        await interaction.followup.send("Trained successfully!")
        
    @app_commands.command(name="train", description="Trains the model further with memory")
    async def train(self, interaction: discord.Interaction):
        await interaction.response.defer()
        with open("memory.json", "r") as f:
            memory: List[str] = json.load(f)
        learning.add_training(memory, 2)
        await interaction.followup.send("Finished training!")
    
    @app_commands.command(name="change", description="Change the model")
    async def change(self, interaction: discord.Interaction, model: str = None):
        embed = discord.Embed(title="Change model", description="Which model would you like to use?")
        if model is None:
            models: List[str] = os.listdir(os.path.join(".", "models"))
            models = [folder for folder in models if re.match(MODEL_MATCH_STRING, folder)]
            if len(models) == 0:
                models = ["No models available."]
            await interaction.response.send_message(embed=embed, view=DropdownView(90, models))
        learning.reload_model()
        generation.reload_model()


async def setup(bot):
    await bot.add_cog(Tf(bot))
