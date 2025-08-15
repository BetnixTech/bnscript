import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import threading
import time
import requests
from io import BytesIO
import RPi.GPIO as GPIO
import base64

# ---------------------------
# BnScript Full Runtime (3D + Input + File)
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

        # Hardware
        GPIO.setmode(GPIO.BCM)
        self.led_states = {}
        self.pwm_objects = {}
        self.servo_objects = {}

        # Keyboard
        self.keys_pressed = set()
        self.root.bind("<KeyPress>", self._on_keypress)
        self.root.bind("<KeyRelease>", self._on_keyrelease)

        # Movable objects
        self.movable_objects = {}

        # 3D Models placeholder
        self.models = {}

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

    # ---------------------------
    # Print inside container
    # ---------------------------
    def printInside(self, *texts):
        text = " ".join(str(t) for t in texts)
        label = tk.Label(self.current_container, text=text, **self.styles_to_kwargs("printInside"))
        label.pack()

    # ---------------------------
    # Buttons
    # ---------------------------
    def button(self, text, func):
        btn = tk.Button(self.current_container, text=text, **self.styles_to_kwargs("button"),
                        command=lambda: threading.Thread(target=func).start())
        btn.pack(pady=5)

    # ---------------------------
    # Images
    # ---------------------------
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

    # ---------------------------
    # Frames
    # ---------------------------
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
    # Hardware
    # ---------------------------
    def onLed(self, pin):
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)
        self.led_states[pin] = True

    def offLed(self, pin):
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
        self.led_states[pin] = False

    def toggleLed(self, pin):
        GPIO.setup(pin, GPIO.OUT)
        current = self.led_states.get(pin, False)
        GPIO.output(pin, not current)
        self.led_states[pin] = not current

    def readButton(self, pin):
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        return GPIO.input(pin) == GPIO.HIGH

    def setBuzzer(self, pin, state):
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

    def setLedBrightness(self, pin, percent):
        GPIO.setup(pin, GPIO.OUT)
        if pin not in self.pwm_objects:
            pwm = GPIO.PWM(pin, 1000)
            pwm.start(percent)
            self.pwm_objects[pin] = pwm
        else:
            self.pwm_objects[pin].ChangeDutyCycle(percent)

    def setMotorSpeed(self, pin, percent):
        self.setLedBrightness(pin, percent)

    def setServo(self, pin, angle):
        GPIO.setup(pin, GPIO.OUT)
        if pin not in self.servo_objects:
            pwm = GPIO.PWM(pin, 50)
            pwm.start(0)
            self.servo_objects[pin] = pwm
        duty = angle / 18 + 2
        self.servo_objects[pin].ChangeDutyCycle(duty)
        time.sleep(0.5)
        self.servo_objects[pin].ChangeDutyCycle(0)

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
    # Windows
    # ---------------------------
    def window(self, title, icon=None, width=400, height=300, func=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry(f"{width}x{height}")

        if icon:
            try:
                img = tk.PhotoImage(file=icon)
                win.iconphoto(False, img)
            except Exception as e:
                print("Window icon load error:", e)

        container = tk.Frame(win)
        container.pack(fill="both", expand=True)
        prev_container = self.current_container
        self.current_container = container

        if func:
            func()

        self.current_container = prev_container
        return win

    # ---------------------------
    # File chooser
    # ---------------------------
    def chooseFile(self, variable_name=None):
        path = filedialog.askopenfilename()
        if variable_name:
            self.saved[variable_name] = path
            self.update_saved_display()
        return path

    # ---------------------------
    # Input box for variable
    # ---------------------------
    def inputVar(self, prompt, variable_name=None):
        var = tk.StringVar()
        frame = tk.Frame(self.current_container)
        frame.pack(pady=5)
        tk.Label(frame, text=prompt).pack(side="left")
        entry = tk.Entry(frame, textvariable=var)
        entry.pack(side="left")
        tk.Button(frame, text="OK", command=lambda: (
            self.Save(variable_name, var.get()) if variable_name else None
        )).pack(side="left")
        return var

    # ---------------------------
    # 3D model placeholders
    # ---------------------------
    def add3DModel(self, file_path, name):
        self.models[name] = {"file": file_path, "x": 0, "y": 0, "z": 0, "brightness": 1.0}
        self.printInside(f"3D Model '{name}' added: {file_path}")

    def setModelProperty(self, name, **kwargs):
        model = self.models.get(name)
        if model:
            for k, v in kwargs.items():
                if k in model:
                    model[k] = v
            self.printInside(f"3D Model '{name}' updated: {kwargs}")

    # ---------------------------
    # Run
    # ---------------------------
    def run(self):
        self.root.mainloop()
