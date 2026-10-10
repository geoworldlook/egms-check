import os
def mount(path, force_remount=False):
    os.makedirs(os.path.join(path, "MyDrive"), exist_ok=True)
    print("Mounted at", path, "(TEST: atrapa Dysku Google)")
