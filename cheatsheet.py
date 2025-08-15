bns = BnScriptApp()

set_style("button", color="white", background_color="blue", font_size=14)

contain(lambda: [
    printInside("Hello BnScript!"),
    button("Click Me", lambda: printInside("Clicked!")),
    img("cat.png", x=50, y=50, name="cat")
])

# Move image when space pressed
def move_cat():
    if keyPressed("space"):
        moveObject("cat", 10, 0)

# Save / remove
Save("score", 100)
RemoveFromSaved("score")

# 3D model
add3DModel("model.obj", "cube")
setModelProperty("cube", x=1, y=2, z=0, rotation=[45,0,0], scale=2)

# Encoding
bin_val = toBinary("hello")
decoded = fromBinary(bin_val)
b64 = toBase64("hello")
decoded_b64 = fromBase64(b64)

# Run app
run()
