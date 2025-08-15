import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time
import requests
from io import BytesIO
import base64
import builtins
import math, random, datetime, os, sys, json, re
import binascii
import pyglet
from pyglet.gl import *

# ---------------------------
# 3D Model Class using pyglet
# ---------------------------
class Bn3DModel:
    def __init__(self, file_path, name):
        self.name = name
        self.file_path = file_path
        self.rotation = [0, 0, 0]  # x, y, z rotation
        self.scale = 1.0
        self.position = [0, 0, 0]
        # Simple cube placeholder for demo
        self.batch = pyglet.graphics.Batch()
        self.vertex_list = self.create_cube()
    
    def create_cube(self):
        vertices = [
            1,1,1, -1,1,1, -1,-1,1, 1,-1,1,
            1,1,-1, -1,1,-1, -1,-1,-1, 1,-1,-1
        ]
        colors = [255,0,0]*8 + [0,255,0]*8
        return self.batch.add(8, GL_QUADS, None,
                              ('v3f', vertices),
                              ('c3B', colors))
    
    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        glScalef(self.scale, self.scale, self.scale)
        glRotatef(self.rotation[0], 1,0,0)
        glRotatef(self.rotation[1], 0,1,0)
        glRotatef(self.rotation[2], 0,0,1)
        self.batch.draw()
        glPopMatrix()
    
    def set_property(self, x=None, y=None, z=None, rotation=None, scale=None):
        if x is not None: self.position[0] = x
        if y is not None: self.position[1] = y
        if z is not None: self.position[2] = z
        if rotation is not None: self.rotation = rotation
        if scale is not None: self.scale = scale

# ---------------------------
# BnScript Full Runtime
# ---------------------------
class BnScriptApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BnScript Runtime")
        self.root.geometry("1200x800")
        self.current_container = None

        # Saved data
        self.saved = {}
        self.saved_container = None

        # Styles
        self.styles = {"contain": {}, "button": {}, "printInside": {}, "img": {}, "frame": {}}

        # Keyboard
        self.keys_pressed = set()
        self.root.bind("<KeyPress>", self._on_keypress)
        self.root.bind("<KeyRelease>", self._on_keyrelease)

        # Movable objects
        self.movable_objects = {}

        # 3D Models
        self.models = {}

        # Python built-ins and modules
        self.bn_globals = {name: getattr(builtins, name) for name in dir(builtins)}
        self.bn_globals.update({
            "math": math,
            "random": random,
            "datetime": datetime,
            "os": os,
            "sys": sys,
            "json": json,
            "re": re,
            "threading": threading,
            "time": time
        })

        # JS-like functions
        self.console = {"log": print}
        self.setTimeout = lambda func, ms: threading.Timer(ms/1000, func).start()
        self.now = lambda: int(time.time() * 1000)

    # ---------------------------
    # Keyboard
    # ---------------------------
    def _on_keypress(self, event):
        self.keys_pressed.add(event.keysym)

    def _on_keyrelease(self, event):
        self.keys_pressed.discard(event.keysym)

    def keyPressed(self, key):
        return key in self.keys_pressed

    # ---------------------------
    # Styling
    # ---------------------------
    def set_style(self, element, **kwargs):
        self.styles[element] = kwargs

    def styles_to_kwargs(self, element):
        s = self.styles.get(element, {})
        kwargs = {}
        if "background_color" in s: kwargs["bg"] = s["background_color"]
        if "color" in s: kwargs["fg"] = s["color"]
        if "font_size" in s or "bold" in s or "italic" in s:
            size = s.get("font_size", 12)
            weight = "bold" if s.get("bold", False) else "normal"
            slant = "italic" if s.get("italic", False) else "roman"
            kwargs["font"] = ("Arial", size, weight, slant)
        if "width" in s: kwargs["width"] = s["width"]
        if "height" in s: kwargs["height"] = s["height"]
        return kwargs

    # ---------------------------
    # Containers
    # ---------------------------
    def contain(self, func):
        frame = tk.Frame(self.root, **self.styles_to_kwargs("contain"))
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        prev_container = self.current_container
        self.current_container = frame
        func()
        self.current_container = prev_container

    def printInside(self, *texts):
        text = " ".join(str(t) for t in texts)
        label = tk.Label(self.current_container, text=text, **self.styles_to_kwargs("printInside"))
        label.pack()

    def button(self, text, func):
        btn = tk.Button(self.current_container, text=text, **self.styles_to_kwargs("button"),
                        command=lambda: threading.Thread(target=func).start())
        btn.pack(pady=5)

    def img(self, source, x=0, y=0, name=None):
        try:
            if source.startswith("http"):
                response = requests.get(source)
                image = Image.open(BytesIO(response.content))
            else:
                image = Image.open(source)
            photo = ImageTk.PhotoImage(image)
            label = tk.Label(self.current_container, image=photo)
            label.image = photo
            label.place(x=x, y=y)
            if name:
                self.movable_objects[name] = {"widget": label, "x": x, "y": y}
        except Exception as e:
            print("Image load error:", e)

    def moveObject(self, name, dx=0, dy=0):
        obj = self.movable_objects.get(name)
        if obj:
            obj["x"] += dx
            obj["y"] += dy
            obj["widget"].place(x=obj["x"], y=obj["y"])

    def frame(self, url):
        label = tk.Label(self.current_container, text=f"[FRAME: {url}]", **self.styles_to_kwargs("frame"))
        label.pack(pady=5)

    # ---------------------------
    # Save / Remove
    # ---------------------------
    def Save(self, *args):
        if len(args) == 1:
            key = str(args[0])
            value = args[0]
        else:
            key, value = args
        self.saved[key] = value
        self.update_saved_display()

    def RemoveFromSaved(self, item):
        key = str(item)
        if key in self.saved:
            del self.saved[key]
            self.update_saved_display()

    def update_saved_display(self):
        if not self.saved_container:
            self.saved_container = tk.Frame(self.root, bg="#E0FFE0")
            self.saved_container.pack(padx=10, pady=10, fill="both")
        for widget in self.saved_container.winfo_children():
            widget.destroy()
        for k, v in self.saved.items():
            label = tk.Label(self.saved_container, text=f"{k}: {v}", font=("Arial", 12), fg="green", anchor="w", justify="left")
            label.pack(fill="x", padx=5, pady=2)

    # ---------------------------
    # Encoding
    # ---------------------------
    def toBinary(self, value):
        if isinstance(value, int):
            return bin(value)[2:]
        elif isinstance(value, str):
            return ' '.join(format(ord(c), '08b') for c in value)
        else:
            raise ValueError("Unsupported type for binary conversion")

    def fromBinary(self, value):
        if ' ' in value:
            chars = value.split()
            return ''.join(chr(int(c, 2)) for c in chars)
        else:
            return int(value, 2)

    def toBase64(self, value):
        if isinstance(value, str):
            return base64.b64encode(value.encode()).decode()
        elif isinstance(value, int):
            return base64.b64encode(str(value).encode()).decode()
        else:
            raise ValueError("Unsupported type for Base64")

    def fromBase64(self, value):
        return base64.b64decode(value.encode()).decode()

    # ---------------------------
    # 3D Models
    # ---------------------------
    def add3DModel(self, file_path, name):
        model = Bn3DModel(file_path, name)
        self.models[name] = model
        self.printInside(f"3D Model '{name}' loaded: {file_path}")

    def setModelProperty(self, name, **kwargs):
        model = self.models.get(name)
        if model:
            model.set_property(
                x = kwargs.get("x", model.position[0]),
                y = kwargs.get("y", model.position[1]),
                z = kwargs.get("z", model.position[2]),
                rotation = kwargs.get("rotation", model.rotation),
                scale = kwargs.get("scale", model.scale)
            )
            self.printInside(f"3D Model '{name}' updated: {kwargs}")

    # ---------------------------
    # Call any Python / JS function
    # ---------------------------
    def callPython(self, func_name, *args, **kwargs):
        if func_name in self.bn_globals:
            return self.bn_globals[func_name](*args, **kwargs)
        else:
            raise ValueError(f"Python function '{func_name}' not found")

    def callJS(self, name, *args):
        if name in self.console:  # console.log
            self.console[name](*args)
        elif name == "setTimeout":
            self.setTimeout(*args)
        elif name == "now":
            return self.now()
        else:
            raise ValueError(f"JS function '{name}' not found")

   def toHex(value):
    """Convert a string, bytes, or number to hex representation."""
     if isinstance(value, str):
         return binascii.hexlify(value.encode()).decode()
     elif isinstance(value, bytes):
         return binascii.hexlify(value).decode()
     else:
         return binascii.hexlify(str(value).encode()).decode()
         

    def fromHex(hex_string):
      """Convert a hex string back to a normal string."""
      try:
          return binascii.unhexlify(hex_string.encode()).decode()
      except Exception:
          return None

    # ---------------------------
    # Run
    # ---------------------------
    def run(self):
        self.root.mainloop()
